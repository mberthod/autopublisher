# EVOLUTION_SAAS.md — Guide d'implémentation complet

> **Objectif** : Documenter exhaustivement chaque modification nécessaire pour que le SaaS atteigne son objectif final : 30 posts publiés automatiquement, sans intervention humaine, sur 3 BU × 2 plateformes.
>
> **Règle** : Ce document ne contient aucune estimation de temps ni évaluation. Uniquement des instructions techniques précises.

---

## TABLE DES MATIÈRES

1. [Bloc 1 — Backend](#bloc-1--backend)
2. [Bloc 2 — GrilledMe (REFONTE)](#bloc-2--grillme-refonte)
3. [Bloc 3 — Génération](#bloc-3--génération)
4. [Bloc 4 — Carrousels](#bloc-4--carrousels)
5. [Bloc 5 — Extension Chrome (IMPLÉMENTATION RÉELLE)](#bloc-5--extension-chrome-implémentation-réelle)
6. [Bloc 6 — Dashboard](#bloc-6--dashboard)
7. [Bloc 7 — Résilience (CONNEXION RÉELLE)](#bloc-7--résilience-connexion-réelle)
8. [Bloc 8 — Intégration](#bloc-8--intégration)
9. [Transverse — Infrastructure & Déploiement](#transverse--infrastructure--déploiement)
10. [Transverse — Sécurité](#transverse--sécurité)
11. [Transverse — Fonctionnalités manquantes](#transverse--fonctionnalités-manquantes)
12. [Transverse — Qualité du code](#transverse--qualité-du-code)
13. [Checklist finale de vérification](#checklist-finale-de-vérification)

---

## BLOC 1 — BACKEND

### 1.1 Ajouter un endpoint de filtrage par date de publication échue

**Fichier** : `bloc-1-backend/app/api/post_routes.py`

Ajouter un paramètre `scheduled_for_before` au endpoint `list_posts` :

```python
@router.get("", response_model=list[PostRead])
def list_posts(
    # ... paramètres existants ...
    scheduled_for_before: Optional[str] = Query(None, description="Filter posts scheduled before ISO datetime"),
    db: Session = Depends(get_db),
):
    return post_service.list_all(
        db,
        # ... params existants ...
        scheduled_for_before=scheduled_for_before,
    )
```

**Fichier** : `bloc-1-backend/app/services/post_service.py`

Ajouter le filtre dans `list_all` :

```python
def list_all(
    db: Session,
    # ... params existants ...
    scheduled_for_before: Optional[str] = None,
) -> list[Post]:
    query = db.query(Post)
    # ... filtres existants ...
    if scheduled_for_before:
        query = query.filter(Post.scheduled_for <= scheduled_for_before)
    return query.offset(skip).limit(limit).all()
```

### 1.2 Valider la structure de `charte_branding`

**Fichier** : `bloc-1-backend/app/schemas.py`

Remplacer `charte_branding: dict` par un modèle Pydantic strict :

```python
from pydantic import BaseModel, Field

class CharteBranding(BaseModel):
    ton: str = Field(..., min_length=2)
    mots_interdits: list[str] = Field(default_factory=list)
    emojis_autorises: list[str] = Field(default_factory=list)
    structure_phrases: str = ""
    longueur_cible: int = Field(default=1500, ge=100, le=5000)
    couleurs: list[str] = Field(default_factory=lambda: ["#000000", "#FFFFFF"])

class PersonaCreate(BaseModel):
    # ... champs existants ...
    charte_branding: CharteBranding

class PersonaUpdate(BaseModel):
    # ... champs existants ...
    charte_branding: Optional[CharteBranding] = None
```

### 1.3 Ajouter une authentification basique par token API

**Fichier** : `bloc-1-backend/app/config.py`

```python
class Settings(BaseSettings):
    # ... champs existants ...
    api_token: str = ""
```

**Fichier** : `bloc-1-backend/app/main.py`

```python
from fastapi import Depends, HTTPException, Header

async def verify_token(x_api_token: str = Header(None)):
    if settings.api_token and x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")

app = FastAPI(
    # ... config existante ...
    dependencies=[Depends(verify_token)] if settings.api_token else [],
)
```

**Fichier** : `bloc-1-backend/.env.example`

```bash
API_TOKEN=change-me-in-production
```

### 1.4 Ajouter un endpoint de statistiques globales

**Fichier** : `bloc-1-backend/app/api/` — créer `stats_routes.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import Post

router = APIRouter()

@router.get("/api/v1/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Post).count()
    by_status = dict(
        db.query(Post.status, func.count(Post.id))
        .group_by(Post.status)
        .all()
    )
    by_platform = dict(
        db.query(Post.platform, func.count(Post.id))
        .group_by(Post.platform)
        .all()
    )
    return {
        "total_posts": total,
        "by_status": by_status,
        "by_platform": by_platform,
    }
```

Enregistrer dans `main.py` : `app.include_router(stats_routes.router, tags=["stats"])`

### 1.5 Rendre les CORS origins configurables

**Fichier** : `bloc-1-backend/app/config.py`

```python
class Settings(BaseSettings):
    # ... champs existants ...
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
```

**Fichier** : `bloc-1-backend/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## BLOC 2 — GRILLME (REFONTE)

### Objectif

Remplacer le formulaire linéaire actuel par un **vrai agent conversationnel** qui :
- Pose UNE question à la fois
- Adapte la question suivante en fonction de la réponse précédente
- Challenge les réponses vagues
- Décide lui-même quand la matrice est complète
- Ne dépasse pas 12 échanges

### 2.1 Remplacer `interrogator_agent.py`

**Fichier** : `bloc-2-grillme/app/agents/interrogator_agent.py`

Supprimer le contenu actuel et implémenter :

```python
import json
from typing import Any, Optional
from loguru import logger
from openai import OpenAI
from app.agents.base_agent import BaseAgent

INTERROGATOR_SYSTEM_PROMPT = """Tu es GrilledMe, un assistant expert en personas marketing.

Objectif : remplir un schéma de persona pour le BU {bu} via une discussion.
Le persona final servira à générer des posts sur les réseaux sociaux.

Champs à remplir :
- cible (qui est la personne idéale ? âge, profession, contexte de vie, localisation)
- besoins (quels problèmes essaie-t-elle de résoudre ? quels objectifs ?)
- frustrations (quelles sont ses douleurs quotidiennes ? qu'est-ce qui l'empêche de dormir ?)
- charte (directives éditoriales : ton, mots interdits, emojis, structure de phrases, longueur cible, couleurs)

Règles strictes :
1. Tu poses UNE seule question à la fois
2. Tu CHALLENGES les réponses vagues : "Peux-tu me donner un exemple concret ?", "C'est encore trop général, tu peux être plus précis ?"
3. Tu refuses de passer à un autre champ tant que le précédent n'est pas validé
4. Si l'utilisateur dit "je sais pas" ou donne une réponse évasive, propose 2-3 options concrètes pour l'aider
5. Tu ne génères JAMAIS de post ici, tu n'es qu'en mode questionnement
6. Tu ne dépasses JAMAIS 12 échanges au total (sois efficace)
7. Quand la matrice est 100% remplie, retourne is_complete=true avec next_question=null
8. Pour la charte, pose des questions spécifiques : ton souhaité, mots à bannir, emojis ok ou pas, longueur des posts

Format de réponse JSON STRICT (rien d'autre, pas de markdown, pas de texte avant/après) :
{{
  "matrix_update": {{"champ": "valeur mise à jour"}},
  "next_question": "ta prochaine question" ou null,
  "is_complete": false ou true,
  "reasoning": "pourquoi cette question OU pourquoi c'est complet",
  "matrix_progress": 0.0 à 1.0
}}

Contexte actuel :
- BU : {bu}
- Matrice partielle : {matrix_json}
- Transcript : {transcript_json}
- Nombre d'échanges : {exchange_count}/12
"""


class InterrogatorAgent(BaseAgent):
    def __init__(self, client: Optional[OpenAI] = None):
        super().__init__(client)

    def start_session(self, bu: str) -> dict:
        """Appelé au début d'une session. Retourne la première question."""
        system_prompt = INTERROGATOR_SYSTEM_PROMPT.format(
            bu=bu,
            matrix_json="{}",
            transcript_json="[]",
            exchange_count=0,
        )
        user_prompt = f"Démarre l'onboarding pour le BU {bu}. Pose ta première question."
        raw = self.call(system_prompt, user_prompt)
        result = self.extract_json(raw)
        self._validate_response(result)
        return result

    def process_message(self, bu: str, matrix: dict, transcript: list, user_message: str) -> dict:
        """Appelé à chaque message utilisateur. Retourne la prochaine question ou is_complete=true."""
        exchange_count = len([t for t in transcript if t.get("role") == "user"])
        system_prompt = INTERROGATOR_SYSTEM_PROMPT.format(
            bu=bu,
            matrix_json=json.dumps(matrix, ensure_ascii=False, indent=2),
            transcript_json=json.dumps(transcript, ensure_ascii=False, indent=2),
            exchange_count=exchange_count,
        )
        user_prompt = f"L'utilisateur vient de répondre : \"{user_message}\"\n\nAnalyse cette réponse, mets à jour la matrice si pertinent, et décide de la suite."
        raw = self.call(system_prompt, user_prompt)
        result = self.extract_json(raw)
        self._validate_response(result)
        return result

    def _validate_response(self, result: dict) -> None:
        required = ["matrix_update", "next_question", "is_complete", "reasoning", "matrix_progress"]
        missing = [k for k in required if k not in result]
        if missing:
            raise ValueError(f"Interrogator response missing fields: {missing}")
        if result["is_complete"] and result["next_question"] is not None:
            raise ValueError("is_complete=true but next_question is not null")
        if not result["is_complete"] and result["next_question"] is None:
            raise ValueError("is_complete=false but next_question is null")
```

### 2.2 Adapter `grillme_service.py`

**Fichier** : `bloc-2-grillme/app/services/grillme_service.py`

Remplacer la logique actuelle de `start_session` et `handle_message` :

```python
def start_session(db: Session, bu: str, interrogator: Optional[InterrogatorAgent] = None) -> tuple[str, str]:
    if interrogator is None:
        interrogator = InterrogatorAgent()

    result = interrogator.start_session(bu)
    first_question = result["next_question"]

    session = GrilledMeSession(
        bu=bu,
        matrix={},
        transcript=[{
            "role": "assistant",
            "content": first_question,
            "timestamp": datetime.utcnow().isoformat(),
        }],
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.bind(session_id=session.id, bu=bu).info("GrilledMe session started")
    return session.id, first_question


def handle_message(
    db: Session,
    session_id: str,
    user_message: str,
    interrogator: Optional[InterrogatorAgent] = None,
    strategist: Optional[StrategistAgent] = None,
) -> dict:
    session = db.query(GrilledMeSession).filter(GrilledMeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Session is {session.status}, not in_progress")

    if interrogator is None:
        interrogator = InterrogatorAgent()
    if strategist is None:
        strategist = StrategistAgent()

    matrix = dict(session.matrix)
    transcript = list(session.transcript)

    # Ajouter le message utilisateur au transcript
    transcript.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Appeler l'agent interrogateur
    result = interrogator.process_message(session.bu, matrix, transcript, user_message)

    # Mettre à jour la matrice avec les valeurs extraites par l'agent
    matrix_update = result.get("matrix_update", {})
    for field, value in matrix_update.items():
        if value:
            matrix[field] = value

    is_complete = result.get("is_complete", False)
    next_question = result.get("next_question")
    progress = result.get("matrix_progress", 0.0)

    if next_question:
        transcript.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat(),
        })

    session.matrix = matrix
    session.transcript = transcript
    session.updated_at = datetime.utcnow()

    if is_complete:
        persona_data = strategist.create_persona(session.bu, matrix)
        persona = persona_service.create(
            db=db,
            bu=session.bu,
            nom=persona_data["nom"],
            besoins=persona_data["besoins"],
            frustrations=persona_data["frustrations"],
            cible=persona_data["cible"],
            charte_branding=persona_data["charte_branding"],
        )
        session.persona_id = persona.id
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        logger.bind(session_id=session_id, persona_id=persona.id).info("Session completed, persona saved")

    db.commit()
    db.refresh(session)

    # Déterminer le champ en cours
    matrix_fields = ["cible", "besoins", "frustrations", "charte"]
    current_field = next((f for f in matrix_fields if not matrix.get(f)), None)

    return {
        "next_question": next_question,
        "matrix_progress": progress,
        "current_field": current_field,
        "is_complete": is_complete,
    }
```

### 2.3 Mettre à jour les tests

**Fichier** : `bloc-2-grillme/tests/test_interrogator_agent.py`

Adapter les tests pour qu'ils testent les nouvelles méthodes `start_session` et `process_message` :

```python
def test_start_session_returns_first_question():
    mock_client = make_mock_client({
        "matrix_update": {},
        "next_question": "Qui est ta cible idéale pour Noisyless ?",
        "is_complete": False,
        "reasoning": "Début de l'onboarding, on commence par la cible",
        "matrix_progress": 0.0,
    })
    agent = InterrogatorAgent(client=mock_client)
    result = agent.start_session("noisyless")
    assert result["next_question"] is not None
    assert len(result["next_question"]) > 10
    assert result["is_complete"] is False

def test_process_message_challenges_vague_answer():
    mock_client = make_mock_client({
        "matrix_update": {},
        "next_question": "C'est vague. Peux-tu me donner un exemple concret de ta cible ?",
        "is_complete": False,
        "reasoning": "Réponse trop vague, on challenge",
        "matrix_progress": 0.0,
    })
    agent = InterrogatorAgent(client=mock_client)
    result = agent.process_message(
        "noisyless",
        {"cible": ""},
        [{"role": "assistant", "content": "Qui est ta cible ?", "timestamp": "..."}],
        "les gens",
    )
    assert "vague" in result["next_question"].lower() or "concret" in result["next_question"].lower()

def test_process_message_complete_matrix():
    mock_client = make_mock_client({
        "matrix_update": {},
        "next_question": None,
        "is_complete": True,
        "reasoning": "Tous les champs sont remplis avec des réponses précises",
        "matrix_progress": 1.0,
    })
    agent = InterrogatorAgent(client=mock_client)
    result = agent.process_message(
        "noisyless",
        {"cible": "...", "besoins": "...", "frustrations": "...", "charte": {...}},
        [],
        "C'est parfait, je valide",
    )
    assert result["is_complete"] is True
    assert result["next_question"] is None

def test_process_message_proposes_options_on_dont_know():
    mock_client = make_mock_client({
        "matrix_update": {},
        "next_question": "Voici 3 options possibles : 1) Propriétaires Airbnb 2) Gérants d'hôtels 3) Syndics de copropriété. Laquelle correspond le mieux ?",
        "is_complete": False,
        "reasoning": "L'utilisateur ne sait pas, on propose des options",
        "matrix_progress": 0.0,
    })
    agent = InterrogatorAgent(client=mock_client)
    result = agent.process_message(
        "noisyless",
        {"cible": ""},
        [{"role": "assistant", "content": "Qui est ta cible ?", "timestamp": "..."}],
        "je sais pas",
    )
    assert "option" in result["next_question"].lower() or "1)" in result["next_question"]
```

### 2.4 Ajouter un hard cap à 12 échanges

**Fichier** : `bloc-2-grillme/app/services/grillme_service.py`

Dans `handle_message`, avant l'appel à l'agent :

```python
exchange_count = len([t for t in session.transcript if t.get("role") == "user"])
if exchange_count >= 12:
    raise HTTPException(
        status_code=400,
        detail="Maximum de 12 échanges atteint. Veuillez démarrer une nouvelle session."
    )
```

---

## BLOC 3 — GÉNÉRATION

### 3.1 Intégrer l'appel au bloc 4 pour les carrousels

**Fichier** : `bloc-3-generation/app/services/post_service.py`

Remplacer le bloc `elif req.format == "carousel":` par un vrai appel HTTP :

```python
elif req.format == "carousel":
    image_provider = "playwright"
    try:
        carousel_url = f"{settings.carousel_service_url}/api/v1/carousel/generate"
        # Construire les slides à partir du texte généré
        slides = _build_carousel_slides(llm_result["text"], persona)
        carousel_resp = httpx.post(
            carousel_url,
            json={
                "bu": persona.bu,
                "theme": "bold" if req.platform == "instagram" else "modern",
                "slides": slides,
                "output_dir": f"./data/carousels/{post.id}",
            },
            timeout=120,
        )
        carousel_resp.raise_for_status()
        carousel_data = carousel_resp.json()
        post.carousel_urls = carousel_data.get("image_urls", [])
    except Exception as exc:
        logger.bind(post_id=post.id).error(f"Carousel generation failed: {exc}")
```

Ajouter la fonction helper :

```python
def _build_carousel_slides(text: str, persona) -> list[dict]:
    """Découpe le texte généré en slides de carrousel."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    slides = []
    for i, para in enumerate(paragraphs[:10]):
        lines = para.split("\n")
        title = lines[0][:80] if lines else ""
        body = "\n".join(lines[1:]) if len(lines) > 1 else para
        slides.append({
            "index": i,
            "title": title if i == 0 else None,
            "body": body[:350],
            "background": "solid",
            "background_color": persona.charte_branding.get("couleurs", ["#1A1A2E"])[0] if i == 0 else "#F7F7F7",
            "text_color": "#FFFFFF" if i == 0 else "#1A1A1A",
        })
    return slides
```

**Fichier** : `bloc-3-generation/app/config.py`

```python
class Settings(BaseSettings):
    # ... champs existants ...
    carousel_service_url: str = "http://localhost:8004"
```

### 3.2 Ajouter un rate limiter sur `/api/v1/posts/generate`

**Fichier** : `bloc-3-generation/app/main.py`

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

# Rate limiter simple : max 10 requêtes par minute
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/api/v1/posts/generate":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # 1 minute
        _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now - t < window]
        if len(_rate_limit_store[client_ip]) >= 10:
            raise HTTPException(status_code=429, detail="Too many requests. Max 10 per minute.")
        _rate_limit_store[client_ip].append(now)
    return await call_next(request)
```

### 3.3 Ajouter la génération vidéo (placeholder)

**Fichier** : `bloc-3-generation/app/schemas.py`

```python
class PostGenerateRequest(BaseModel):
    # ... champs existants ...
    format: Literal["text_only", "image", "carousel", "video"]
```

**Fichier** : `bloc-3-generation/app/services/post_service.py`

```python
elif req.format == "video":
    image_provider = "video_generation"
    logger.bind(post_id=post.id).info("Video format — not yet implemented, falling back to image")
    # Fallback : générer une image à la place
    image_url = image_svc.generate(
        post_id=post.id,
        angle_editorial=req.angle_editorial,
        charte=persona.charte_branding or {},
    )
    if image_url:
        post.image_url = image_url
```

### 3.4 Enqueuer les tâches de génération dans le bloc 7

**Fichier** : `bloc-3-generation/app/services/post_service.py`

Ajouter après la création du post :

```python
# Enqueuer dans le bloc 7 pour résilience
try:
    resilience_url = f"{settings.resilience_service_url}/api/v1/queue/tasks"
    httpx.post(
        resilience_url,
        params={"task_type": "generate_text", "max_retries": 3},
        json={"post_id": post.id, "persona_id": req.persona_id, "angle": req.angle_editorial},
        timeout=5,
    )
except Exception:
    pass  # Non-bloquant si le bloc 7 est down
```

**Fichier** : `bloc-3-generation/app/config.py`

```python
class Settings(BaseSettings):
    # ... champs existants ...
    resilience_service_url: str = "http://localhost:8002"
```

---

## BLOC 4 — CARROUSELS

### 4.1 Corriger l'indexation des slides

**Fichier** : `bloc-4-carrousels/app/templates/bold.html`

Remplacer `{{ slide.index + 1 }}` par `{{ slide.index }}` (si l'index est 1-based dans le schéma) ou inversement. Vérifier la cohérence entre le schéma (`index: int` 1-based) et les templates.

**Fichier** : `bloc-4-carrousels/app/templates/instagram.html`

Même correction sur `{{ slide.index + 1 }}`.

### 4.2 Ajouter le support des formats non-carrés

**Fichier** : `bloc-4-carrousels/app/schemas.py`

```python
class CarouselSpec(BaseModel):
    # ... champs existants ...
    width: int = 1080
    height: int = 1080
    # Formats prédéfinis :
    # Instagram carré: 1080x1080
    # Instagram portrait: 1080x1350
    # Instagram story: 1080x1920
    # LinkedIn paysage: 1200x627
```

### 4.3 Ajouter un endpoint de nettoyage des PNGs

**Fichier** : `bloc-4-carrousels/api_server.py`

```python
import shutil
from datetime import datetime, timedelta

@app.post("/api/v1/carousel/cleanup")
async def cleanup_old_carousels(max_age_hours: int = 72):
    """Supprime les carrousels générés il y a plus de N heures."""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    carousels_dir = Path("./data/carousels")
    deleted = 0
    for subdir in carousels_dir.iterdir():
        if subdir.is_dir():
            mtime = datetime.fromtimestamp(subdir.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(subdir)
                deleted += 1
    return {"deleted": deleted}
```

---

## BLOC 5 — EXTENSION CHROME (IMPLÉMENTATION RÉELLE)

### 5.1 Implémenter `linkedin-publisher.js`

**Fichier** : `bloc-5-extension/content/linkedin-publisher.js`

Remplacer le contenu actuel par une implémentation complète :

```javascript
// Content script LinkedIn — publication automatique
import { humanType } from './shared/human-typer.js';
import { uploadMedia } from './shared/media-uploader.js';
import { waitForElement } from './shared/wait-for-element.js';

const SELECTORS = {
  btnStartPost: 'button[aria-label="Commencer un post"]',
  btnStartPostAlt: 'button.share-box-feed-entry__trigger',
  textEditor: 'div[role="textbox"][contenteditable="true"]',
  fileInput: 'input[type="file"][accept*="image"]',
  btnSubmit: 'button.share-actions__primary-action',
  btnPublish: 'button[aria-label="Publier"]',
  successToast: 'div[role="alert"]',
  postUrl: 'a[data-attribute="post-url"]',
  feedContainer: 'div.scaffold-finite-scroll__content',
};

async function publish(task) {
  const { text, mediaUrls, selectors } = task;
  const sel = { ...SELECTORS, ...(selectors?.linkedin || {}) };

  try {
    // 1. Vérifier qu'on est connecté
    const feed = await waitForElement(sel.feedContainer, 5000);
    if (!feed) {
      return { success: false, error: 'AUTH_REQUIRED', message: 'Not logged into LinkedIn' };
    }

    // 2. Cliquer sur "Commencer un post"
    const btnCompose = await waitForElement(sel.btnStartPost, 5000)
      || await waitForElement(sel.btnStartPostAlt, 5000);
    if (!btnCompose) {
      return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'Compose button not found' };
    }
    btnCompose.click();
    await sleep(1000, 2000);

    // 3. Attendre l'éditeur de texte
    const editor = await waitForElement(sel.textEditor, 10000);
    if (!editor) {
      return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'Text editor not found' };
    }

    // 4. Taper le texte
    editor.focus();
    await humanType(editor, text);

    // 5. Uploader les médias si présents
    if (mediaUrls && mediaUrls.length > 0) {
      for (const url of mediaUrls) {
        const fileInput = await waitForElement(sel.fileInput, 5000);
        if (fileInput) {
          await uploadMedia(fileInput, url);
          await sleep(2000, 4000);
        }
      }
    }

    // 6. Cliquer Publier
    await sleep(1000, 2000);
    const btnPublish = await waitForElement(sel.btnSubmit, 10000)
      || await waitForElement(sel.btnPublish, 10000);
    if (!btnPublish) {
      return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'Publish button not found' };
    }
    btnPublish.click();

    // 7. Attendre le toast de succès
    const toast = await waitForElement(sel.successToast, 15000);
    if (!toast) {
      return { success: false, error: 'PUBLISH_TIMEOUT', message: 'No success confirmation after 15s' };
    }

    // 8. Extraire l'URL du post
    await sleep(2000, 3000);
    const postLink = document.querySelector(sel.postUrl);
    const postUrl = postLink ? postLink.href : null;

    return { success: true, postUrl };

  } catch (err) {
    return { success: false, error: 'UNKNOWN', message: err.message };
  }
}

function sleep(min, max) {
  const ms = Math.floor(Math.random() * (max - min) + min);
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Écouter les messages du service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'publish') {
    publish(message.task).then(sendResponse);
    return true; // Garder le canal ouvert pour la réponse async
  }
});
```

### 5.2 Implémenter `instagram-publisher.js`

**Fichier** : `bloc-5-extension/content/instagram-publisher.js`

```javascript
import { humanType } from './shared/human-typer.js';
import { uploadMedia } from './shared/media-uploader.js';
import { waitForElement } from './shared/wait-for-element.js';

const SELECTORS = {
  btnNewPost: 'svg[aria-label="Nouvelle publication"]',
  btnNewPostAlt: 'a[href="/"]', // Fallback : cliquer sur le logo puis le +
  btnSelectFile: 'button',
  fileInput: 'input[type="file"]',
  nextButton: 'div[role="button"]',
  captionEditor: 'textarea[aria-label="Écrire une légende…"]',
  captionEditorAlt: 'div[role="textbox"]',
  shareButton: 'div[role="button"]',
  feedPresent: 'section main',
};

async function publish(task) {
  const { text, mediaUrls, selectors } = task;
  const sel = { ...SELECTORS, ...(selectors?.instagram || {}) };

  try {
    // 1. Vérifier qu'on est connecté
    const feed = await waitForElement(sel.feedPresent, 5000);
    if (!feed) {
      return { success: false, error: 'AUTH_REQUIRED', message: 'Not logged into Instagram' };
    }

    // 2. Cliquer sur "Nouvelle publication"
    const btnNew = await waitForElement(sel.btnNewPost, 5000);
    if (!btnNew) {
      return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'New post button not found' };
    }
    btnNew.closest('a')?.click() || btnNew.closest('div')?.click() || btnNew.click();
    await sleep(1000, 2000);

    // 3. Uploader le média
    if (mediaUrls && mediaUrls.length > 0) {
      const fileInput = await waitForElement(sel.fileInput, 10000);
      if (!fileInput) {
        return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'File input not found' };
      }
      await uploadMedia(fileInput, mediaUrls[0]);
      await sleep(2000, 3000);

      // Cliquer "Suivant" après upload
      const nextBtn = await waitForElement(sel.nextButton, 10000);
      if (nextBtn) nextBtn.click();
      await sleep(1000, 2000);

      // Second "Suivant" (filtres)
      const nextBtn2 = await waitForElement(sel.nextButton, 5000);
      if (nextBtn2) nextBtn2.click();
      await sleep(1000, 2000);
    }

    // 4. Écrire la légende
    const captionEditor = await waitForElement(sel.captionEditor, 10000)
      || await waitForElement(sel.captionEditorAlt, 10000);
    if (captionEditor) {
      captionEditor.focus();
      await humanType(captionEditor, text);
    }

    // 5. Partager
    await sleep(1000, 2000);
    const shareBtn = await waitForElement(sel.shareButton, 10000);
    if (!shareBtn) {
      return { success: false, error: 'SELECTOR_NOT_FOUND', message: 'Share button not found' };
    }
    shareBtn.click();

    // 6. Attendre confirmation
    await sleep(3000, 5000);

    return { success: true, postUrl: null };

  } catch (err) {
    return { success: false, error: 'UNKNOWN', message: err.message };
  }
}

function sleep(min, max) {
  const ms = Math.floor(Math.random() * (max - min) + min);
  return new Promise(resolve => setTimeout(resolve, ms));
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'publish') {
    publish(message.task).then(sendResponse);
    return true;
  }
});
```

### 5.3 Implémenter le flux complet dans `service-worker.js`

**Fichier** : `bloc-5-extension/background/service-worker.js`

Remplacer la fonction `executeTask` par :

```javascript
import { fetchPendingTasks, sendCallback } from './api-client.js';
import { getSelectors } from './remote-selectors.js';
import { enqueueTask, dequeueTask, getQueueSize } from './task-queue.js';

const POLL_INTERVAL_MINUTES = 5;
const MIN_HOURS_BETWEEN_POSTS = 4;
const PLATFORM_URLS = {
  linkedin: 'https://www.linkedin.com/feed/',
  instagram: 'https://www.instagram.com/',
};

let lastPublishTime = null;

chrome.alarms.create('pollTasks', { periodInMinutes: POLL_INTERVAL_MINUTES });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'pollTasks') {
    await pollAndEnqueue();
    await processQueue();
  }
});

// Également lancer au démarrage
chrome.runtime.onInstalled.addListener(() => {
  pollAndEnqueue();
});
chrome.runtime.onStartup.addListener(() => {
  pollAndEnqueue();
});

async function pollAndEnqueue() {
  try {
    const tasks = await fetchPendingTasks();
    for (const task of tasks) {
      await enqueueTask(task);
    }
    updateBadge();
  } catch (err) {
    console.error('Poll failed:', err);
  }
}

async function processQueue() {
  const queueSize = await getQueueSize();
  if (queueSize === 0) return;

  // Rate limiting : minimum 4h entre 2 publications
  if (lastPublishTime) {
    const hoursSinceLast = (Date.now() - lastPublishTime) / (1000 * 60 * 60);
    if (hoursSinceLast < MIN_HOURS_BETWEEN_POSTS) {
      console.log(`Rate limited: ${hoursSinceLast.toFixed(1)}h since last publish`);
      return;
    }
  }

  const task = await dequeueTask();
  if (!task) return;

  const result = await executeTask(task);

  // Callback au backend
  try {
    await sendCallback(task.task_id, result);
  } catch (err) {
    console.error('Callback failed:', err);
  }

  if (result.success) {
    lastPublishTime = Date.now();
  }

  updateBadge();
}

async function executeTask(task) {
  const selectors = await getSelectors();
  const platformUrl = PLATFORM_URLS[task.platform];
  if (!platformUrl) {
    return { success: false, error: 'UNKNOWN_PLATFORM', message: `Unknown platform: ${task.platform}` };
  }

  try {
    // 1. Ouvrir un onglet masqué sur la plateforme
    const tab = await chrome.tabs.create({
      url: platformUrl,
      active: false,
    });

    // 2. Attendre que la page soit chargée
    await waitForTabLoad(tab.id);

    // 3. Envoyer un message au content script pour publier
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'publish',
      task: { ...task, selectors },
    });

    // 4. Fermer l'onglet
    await chrome.tabs.remove(tab.id);

    if (response && response.success) {
      return {
        status: 'success',
        post_url: response.postUrl || null,
        published_at: new Date().toISOString(),
      };
    } else {
      return {
        status: 'failed',
        error_code: response?.error || 'UNKNOWN',
        error_message: response?.message || 'Publication failed',
      };
    }
  } catch (err) {
    return {
      status: 'failed',
      error_code: 'EXTENSION_ERROR',
      error_message: err.message,
    };
  }
}

function waitForTabLoad(tabId) {
  return new Promise((resolve) => {
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        setTimeout(resolve, 2000); // Attendre 2s de plus pour le rendu
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    // Timeout de sécurité
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    }, 30000);
  });
}

function updateBadge() {
  getQueueSize().then(size => {
    chrome.action.setBadgeText({ text: size > 0 ? String(size) : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#6C63FF' });
  });
}

// Message depuis le popup pour forcer un check
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'forceCheck') {
    pollAndEnqueue().then(() => processQueue()).then(() => {
      sendResponse({ ok: true });
    });
    return true;
  }
  if (message.action === 'getStatus') {
    getQueueSize().then(size => {
      sendResponse({
        queueSize: size,
        lastPublish: lastPublishTime,
      });
    });
    return true;
  }
});
```

### 5.4 Implémenter `media-uploader.js`

**Fichier** : `bloc-5-extension/content/shared/media-uploader.js`

```javascript
export async function uploadMedia(fileInput, url) {
  // 1. Télécharger le fichier depuis le backend
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download media: ${response.status}`);
  }
  const blob = await response.blob();

  // 2. Créer un File object
  const ext = url.split('.').pop().split('?')[0] || 'png';
  const filename = `post-media.${ext}`;
  const file = new File([blob], filename, { type: blob.type });

  // 3. Injecter dans l'input file via DataTransfer
  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;

  // 4. Déclencher l'événement change
  fileInput.dispatchEvent(new Event('change', { bubbles: true }));
}
```

### 5.5 Améliorer `human-typer.js`

**Fichier** : `bloc-5-extension/content/shared/human-typer.js`

Ajouter la simulation de mouvement de souris :

```javascript
export async function humanType(element, text) {
  for (const char of text) {
    element.dispatchEvent(new InputEvent('input', {
      inputType: 'insertText',
      data: char,
      bubbles: true,
    }));
    // Insérer le caractère dans le contenu
    if (element.isContentEditable) {
      document.execCommand('insertText', false, char);
    } else {
      element.value += char;
    }
    const delay = 50 + Math.random() * 100; // 50-150ms
    await new Promise(r => setTimeout(r, delay));
  }
}

export async function simulateMouseMove(targetElement) {
  // Mouvement de souris non-linéaire (bezier simplifié)
  const targetRect = targetElement.getBoundingClientRect();
  const targetX = targetRect.left + targetRect.width / 2;
  const targetY = targetRect.top + targetRect.height / 2;

  const startX = Math.random() * window.innerWidth;
  const startY = Math.random() * window.innerHeight;

  const steps = 20 + Math.floor(Math.random() * 20);
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Courbe de Bézier quadratique
    const cpX = (startX + targetX) / 2 + (Math.random() - 0.5) * 200;
    const cpY = (startY + targetY) / 2 + (Math.random() - 0.5) * 200;
    const x = (1-t)*(1-t)*startX + 2*(1-t)*t*cpX + t*t*targetX;
    const y = (1-t)*(1-t)*startY + 2*(1-t)*t*cpY + t*t*targetY;

    document.dispatchEvent(new MouseEvent('mousemove', {
      clientX: x, clientY: y, bubbles: true,
    }));
    await new Promise(r => setTimeout(r, 5 + Math.random() * 15));
  }
}

export async function humanScroll() {
  const scrollAmount = 100 + Math.random() * 300;
  window.scrollBy({ top: scrollAmount, behavior: 'smooth' });
  await new Promise(r => setTimeout(r, 500 + Math.random() * 1000));
}
```

### 5.6 Implémenter le scraping analytics J-1

**Fichier** : `bloc-5-extension/content/` — créer `analytics-scraper.js`

```javascript
// Content script injecté sur les pages de posts pour scraper les métriques

async function scrapeLinkedInPostMetrics() {
  const metrics = {
    likes: 0,
    comments: 0,
    reposts: 0,
    views: 0,
  };

  // Sélecteurs LinkedIn (à maintenir)
  const likesEl = document.querySelector('span[data-test="likes-count"]')
    || document.querySelector('button[aria-label*="like"] span');
  const commentsEl = document.querySelector('button[aria-label*="comment"] span');
  const repostsEl = document.querySelector('button[aria-label*="repost"] span');
  const viewsEl = document.querySelector('span[data-test="views-count"]');

  if (likesEl) metrics.likes = parseInt(likesEl.textContent.replace(/\D/g, '')) || 0;
  if (commentsEl) metrics.comments = parseInt(commentsEl.textContent.replace(/\D/g, '')) || 0;
  if (repostsEl) metrics.reposts = parseInt(repostsEl.textContent.replace(/\D/g, '')) || 0;
  if (viewsEl) metrics.views = parseInt(viewsEl.textContent.replace(/\D/g, '')) || 0;

  return metrics;
}

async function scrapeInstagramPostMetrics() {
  const metrics = {
    likes: 0,
    comments: 0,
  };

  const likesEl = document.querySelector('a[href*="liked_by"] span')
    || document.querySelector('section span');
  if (likesEl) metrics.likes = parseInt(likesEl.textContent.replace(/\D/g, '')) || 0;

  return metrics;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'scrapeAnalytics') {
    const platform = message.platform;
    const scraper = platform === 'linkedin' ? scrapeLinkedInPostMetrics : scrapeInstagramPostMetrics;
    scraper().then(sendResponse);
    return true;
  }
});
```

**Fichier** : `bloc-5-extension/background/service-worker.js`

Ajouter une alarme quotidienne pour le scraping :

```javascript
chrome.alarms.create('scrapeAnalytics', {
  periodInMinutes: 24 * 60, // Toutes les 24h
  when: getNext9AM(),
});

function getNext9AM() {
  const now = new Date();
  const next = new Date(now);
  next.setHours(9, 0, 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next.getTime();
}

async function scrapeAnalyticsForPublishedPosts() {
  // Récupérer les posts publiés hier depuis le backend
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dateStr = yesterday.toISOString().split('T')[0];

  const response = await fetch(`${API_BASE_URL}/api/v1/posts?status=published&scheduled_for_date=${dateStr}`);
  const posts = await response.json();

  for (const post of posts) {
    if (!post.published_url) continue;
    const platformUrl = post.platform === 'linkedin'
      ? 'https://www.linkedin.com'
      : 'https://www.instagram.com';

    const tab = await chrome.tabs.create({ url: post.published_url, active: false });
    await waitForTabLoad(tab.id);

    const metrics = await chrome.tabs.sendMessage(tab.id, {
      action: 'scrapeAnalytics',
      platform: post.platform,
    });

    // Envoyer les métriques au backend
    await fetch(`${API_BASE_URL}/api/v1/posts/${post.id}/metrics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metrics),
    });

    await chrome.tabs.remove(tab.id);
    await new Promise(r => setTimeout(r, 5000)); // Pause entre chaque post
  }
}
```

### 5.7 Ajouter l'endpoint metrics au bloc 1

**Fichier** : `bloc-1-backend/app/models.py`

```python
class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    reposts = Column(Integer, default=0)
    views = Column(Integer, default=0)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Fichier** : `bloc-1-backend/app/api/post_routes.py`

```python
@router.post("/{post_id}/metrics", status_code=201)
def add_post_metrics(post_id: str, metrics: dict, db: Session = Depends(get_db)):
    post = post_service.get_by_id(db, post_id)
    metric = PostMetrics(post_id=post_id, **metrics)
    db.add(metric)
    db.commit()
    return {"ok": True}
```

---

## BLOC 6 — DASHBOARD

### 6.1 Ajouter la page GrilledMe

**Fichier** : `bloc-6-dashboard/src/routes/grillme/+page.svelte`

Créer une page d'onboarding conversationnel :

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { PUBLIC_GRILLME_URL } from '$env/static/public';

  let sessionId = '';
  let messages: Array<{ role: string; content: string }> = [];
  let userInput = '';
  let loading = false;
  let isComplete = false;
  let persona: any = null;
  let error = '';
  let progress = 0;

  async function startSession() {
    loading = true;
    error = '';
    try {
      const resp = await fetch(`${PUBLIC_GRILLME_URL}/api/v1/grillme/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bu: 'noisyless' }),
      });
      const data = await resp.json();
      sessionId = data.session_id;
      messages = [{ role: 'assistant', content: data.first_question }];
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function sendMessage() {
    if (!userInput.trim() || !sessionId) return;
    const msg = userInput.trim();
    messages = [...messages, { role: 'user', content: msg }];
    userInput = '';
    loading = true;

    try {
      const resp = await fetch(`${PUBLIC_GRILLME_URL}/api/v1/grillme/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: msg }),
      });
      const data = await resp.json();
      progress = data.matrix_progress;

      if (data.next_question) {
        messages = [...messages, { role: 'assistant', content: data.next_question }];
      }

      if (data.is_complete) {
        isComplete = true;
        const personaResp = await fetch(`${PUBLIC_GRILLME_URL}/api/v1/grillme/sessions/${sessionId}/persona`);
        persona = (await personaResp.json()).persona;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
</script>

<svelte:head><title>GrilledMe — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <h1>GrilledMe</h1>
    <p class="subtitle">Onboarding conversationnel — Définissez votre persona</p>
  </div>

  {#if !sessionId}
    <button class="btn btn-primary" on:click={startSession} disabled={loading}>
      {loading ? 'Démarrage…' : 'Démarrer l\'onboarding'}
    </button>
  {:else if isComplete && persona}
    <div class="card" style="padding: 24px;">
      <h2>Persona créé avec succès</h2>
      <p><strong>{persona.nom}</strong></p>
      <p>BU : {persona.bu}</p>
      <p>Cible : {persona.cible}</p>
      <p>Besoins : {persona.besoins}</p>
      <p>Frustrations : {persona.frustrations}</p>
      <details>
        <summary>Charte de branding</summary>
        <pre>{JSON.stringify(persona.charte_branding, null, 2)}</pre>
      </details>
    </div>
  {:else}
    <div class="progress-bar-container">
      <div class="progress-bar-fill" style="width: {progress * 100}%"></div>
      <span>{Math.round(progress * 100)}%</span>
    </div>

    <div class="chat-container">
      {#each messages as msg}
        <div class="message {msg.role}">
          <div class="message-bubble">{msg.content}</div>
        </div>
      {/each}
    </div>

    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <div class="input-row">
      <textarea
        bind:value={userInput}
        placeholder="Votre réponse…"
        on:keydown={handleKeydown}
        disabled={loading}
        rows="3"
      ></textarea>
      <button class="btn btn-primary" on:click={sendMessage} disabled={loading || !userInput.trim()}>
        {loading ? '…' : 'Envoyer'}
      </button>
    </div>
  {/if}
</main>

<style>
  .progress-bar-container {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }
  .progress-bar-fill {
    height: 6px;
    background: var(--color-primary);
    border-radius: 3px;
    transition: width 0.3s;
  }
  .chat-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 60vh;
    overflow-y: auto;
    margin-bottom: 16px;
  }
  .message {
    display: flex;
  }
  .message.user {
    justify-content: flex-end;
  }
  .message-bubble {
    max-width: 70%;
    padding: 10px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.5;
  }
  .message.assistant .message-bubble {
    background: #F3F4F6;
    color: #111827;
  }
  .message.user .message-bubble {
    background: var(--color-primary);
    color: #fff;
  }
  .input-row {
    display: flex;
    gap: 8px;
    align-items: flex-end;
  }
  .input-row textarea {
    flex: 1;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 10px;
    font-family: inherit;
    font-size: 14px;
    resize: vertical;
  }
</style>
```

### 6.2 Ajouter la page d'édition de Persona

**Fichier** : `bloc-6-dashboard/src/routes/personas/+page.svelte`

Créer une page listant les personas avec possibilité d'édition :

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Persona } from '$lib/types';

  let personas: Persona[] = [];
  let loading = true;
  let error = '';
  let editingId: string | null = null;
  let editForm: Partial<Persona> = {};

  onMount(async () => {
    try {
      personas = await api.personas.list();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  function startEdit(p: Persona) {
    editingId = p.id;
    editForm = { ...p };
  }

  async function saveEdit() {
    if (!editingId) return;
    try {
      const updated = await api.personas.update(editingId, editForm);
      personas = personas.map(p => p.id === updated.id ? updated : p);
      editingId = null;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function deletePersona(id: string) {
    if (!confirm('Supprimer ce persona ?')) return;
    try {
      await api.personas.delete(id);
      personas = personas.filter(p => p.id !== id);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }
</script>

<svelte:head><title>Personas — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <h1>Personas</h1>
    <p class="subtitle">{personas.length} persona{personas.length !== 1 ? 's' : ''}</p>
  </div>

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else if error}
    <div class="error-banner">{error}</div>
  {:else}
    <div class="persona-grid">
      {#each personas as persona (persona.id)}
        <div class="card">
          {#if editingId === persona.id}
            <label>Nom <input bind:value={editForm.nom} /></label>
            <label>BU <input bind:value={editForm.bu} /></label>
            <label>Besoins <textarea bind:value={editForm.besoins} rows="3" /></label>
            <label>Frustrations <textarea bind:value={editForm.frustrations} rows="3" /></label>
            <label>Cible <textarea bind:value={editForm.cible} rows="3" /></label>
            <div class="btn-row">
              <button class="btn btn-primary btn-sm" on:click={saveEdit}>Sauvegarder</button>
              <button class="btn btn-secondary btn-sm" on:click={() => editingId = null}>Annuler</button>
            </div>
          {:else}
            <h3>{persona.nom}</h3>
            <span class="bu-tag bu-{persona.bu}">{persona.bu}</span>
            <p class="field-label">Cible</p>
            <p class="field-value">{persona.cible}</p>
            <p class="field-label">Besoins</p>
            <p class="field-value">{persona.besoins}</p>
            <p class="field-label">Frustrations</p>
            <p class="field-value">{persona.frustrations}</p>
            <div class="btn-row">
              <button class="btn btn-secondary btn-sm" on:click={() => startEdit(persona)}>Modifier</button>
              <button class="btn btn-danger btn-sm" on:click={() => deletePersona(persona.id)}>Supprimer</button>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</main>

<style>
  .persona-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }
  .field-label {
    font-size: 11px;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
    margin: 8px 0 2px;
  }
  .field-value {
    font-size: 13px;
    color: #374151;
    margin: 0;
  }
  .btn-row {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    font-weight: 600;
    color: #6B7280;
    margin-bottom: 8px;
  }
  label input, label textarea {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: inherit;
    font-size: 13px;
  }
</style>
```

### 6.3 Centraliser la configuration des URLs de services

**Fichier** : `bloc-6-dashboard/src/lib/api.ts`

Remplacer les URLs hardcodées par des variables d'environnement :

```typescript
const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const GRILLME_BASE = import.meta.env.PUBLIC_GRILLME_URL || 'http://localhost:8001/api/v1';
const GENERATION_BASE = import.meta.env.PUBLIC_GENERATION_URL || 'http://localhost:8003';
const CAROUSEL_BASE = import.meta.env.PUBLIC_CAROUSEL_URL || 'http://localhost:8004';
const RESILIENCE_BASE = import.meta.env.PUBLIC_RESILIENCE_URL || 'http://localhost:8002';
```

---

## BLOC 7 — RÉSILIENCE (CONNEXION RÉELLE)

### 7.1 Implémenter les task handlers avec de vrais appels

**Fichier** : `bloc-7-resilience/app/workers/task_handlers.py`

Remplacer les stubs par des implémentations réelles :

```python
import httpx
from typing import Callable
from loguru import logger
from app.config import settings


def handle_publish_post(payload: dict) -> dict:
    """
    Appelle le bloc 1 pour marquer le post comme prêt à être publié,
    puis notifie l'extension Chrome.
    """
    post_id = payload.get("post_id")
    logger.bind(post_id=post_id).info("Publishing post via extension callback")

    # Mettre à jour le statut du post dans le bloc 1
    bloc1_url = settings.bloc1_api_url
    try:
        resp = httpx.patch(
            f"{bloc1_url}/api/v1/posts/{post_id}",
            json={"status": "scheduled"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Failed to update post status: {exc}")
        raise

    return {"published": True, "post_id": post_id}


def handle_generate_text(payload: dict) -> dict:
    """
    Appelle le bloc 3 pour générer le texte d'un post.
    """
    post_id = payload.get("post_id")
    persona_id = payload.get("persona_id")
    angle = payload.get("angle", "")
    planning_id = payload.get("planning_id", "")
    platform = payload.get("platform", "linkedin")

    logger.bind(post_id=post_id).info("Generating text via bloc 3")

    generation_url = settings.generation_service_url
    try:
        resp = httpx.post(
            f"{generation_url}/api/v1/posts/generate",
            json={
                "planning_id": planning_id,
                "persona_id": persona_id,
                "angle_editorial": angle,
                "format": "text_only",
                "platform": platform,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"generated": True, "post_id": data.get("post_id", post_id), "text": data.get("text", "")}
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Text generation failed: {exc}")
        raise


def handle_generate_image(payload: dict) -> dict:
    """
    Appelle le bloc 3 pour générer une image.
    """
    post_id = payload.get("post_id")
    persona_id = payload.get("persona_id")
    angle = payload.get("angle", "")
    planning_id = payload.get("planning_id", "")
    platform = payload.get("platform", "linkedin")

    logger.bind(post_id=post_id).info("Generating image via bloc 3")

    generation_url = settings.generation_service_url
    try:
        resp = httpx.post(
            f"{generation_url}/api/v1/posts/generate",
            json={
                "planning_id": planning_id,
                "persona_id": persona_id,
                "angle_editorial": angle,
                "format": "image",
                "platform": platform,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"generated": True, "post_id": data.get("post_id", post_id), "image_url": data.get("image_url", "")}
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Image generation failed: {exc}")
        raise


TASK_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "publish_post": handle_publish_post,
    "generate_text": handle_generate_text,
    "generate_image": handle_generate_image,
}
```

### 7.2 Ajouter les URLs de services dans la config

**Fichier** : `bloc-7-resilience/app/config.py`

```python
class Settings(BaseSettings):
    # ... champs existants ...
    bloc1_api_url: str = "http://localhost:8000"
    generation_service_url: str = "http://localhost:8003"
```

### 7.3 Mettre à jour le statut du post dans le bloc 1 après échec

**Fichier** : `bloc-7-resilience/app/workers/queue_worker.py`

Dans `_maybe_alert`, ajouter la mise à jour du post dans le bloc 1 :

```python
def _maybe_alert(task) -> None:
    # Mettre à jour le post dans le bloc 1
    post_id = task.payload.get("post_id")
    if post_id:
        try:
            httpx.patch(
                f"{settings.bloc1_api_url}/api/v1/posts/{post_id}",
                json={
                    "status": "failed",
                    "error_code": task.last_error_code or "UNKNOWN",
                    "error_message": task.last_error or "",
                },
                timeout=10,
            )
        except Exception as exc:
            logger.bind(post_id=post_id).error(f"Failed to update post status in bloc 1: {exc}")

    # Envoyer l'alerte Telegram
    send_telegram_alert(
        task_id=task.id,
        task_type=task.task_type,
        attempts=task.attempts,
        max_retries=task.max_retries,
        error_code=task.last_error_code or "UNKNOWN",
        error_message=task.last_error or "",
        payload=task.payload,
        completed_at=str(task.completed_at or datetime.utcnow()),
    )
```

Ajouter l'import : `import httpx`

---

## BLOC 8 — INTÉGRATION

### 8.1 Ajouter un test E2E du flux complet

**Fichier** : `bloc-8-integration/tests/e2e/` — créer `test_full_flow.py`

```python
"""
Test E2E — Flux complet : GrilledMe → Persona → Post → Queue → Callback
"""
import pytest
import httpx


@pytest.mark.slow
@pytest.mark.bloc1
@pytest.mark.bloc2
@pytest.mark.bloc3
@pytest.mark.bloc7
async def test_full_flow_grillme_to_published(bloc1_url, bloc2_url, bloc3_url, bloc7_url):
    """
    Flux complet :
    1. Créer un persona via GrilledMe
    2. Créer un planning
    3. Générer un post
    4. Enqueuer dans la queue
    5. Simuler le callback de l'extension
    6. Vérifier que le post est published
    """
    async with httpx.AsyncClient(timeout=120.0) as client:

        # 1. GrilledMe → Persona
        r = await client.post(f"{bloc2_url}/api/v1/grillme/sessions", json={"bu": "noisyless"})
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        answers = [
            "Propriétaires Airbnb en France, 1-5 biens, 35-55 ans",
            "Maintenir note 4.8+, éviter plaintes voisins",
            "Nuisances sonores nocturnes, remboursements",
            "Solutions acoustiques simples et rapides",
            "Ton expert mais accessible",
            "Éviter cheap, disruptif, révolutionnaire",
            "Emojis techniques : ✅ 🔧 📊",
            "Posts LinkedIn 1500 chars max",
            "Couleurs : #FF6B35 et #1A1A1A",
            "C'est parfait, je valide",
        ]
        for answer in answers:
            r = await client.post(
                f"{bloc2_url}/api/v1/grillme/sessions/{session_id}/messages",
                json={"user_message": answer},
            )
            if r.json().get("is_complete"):
                break

        r = await client.get(f"{bloc2_url}/api/v1/grillme/sessions/{session_id}/persona")
        persona = r.json()["persona"]
        persona_id = persona["id"]

        # 2. Créer un planning
        r = await client.post(f"{bloc1_url}/api/v1/plannings", json={
            "persona_id": persona_id,
            "date_debut": "2026-01-01T00:00:00",
            "date_fin": "2026-12-31T00:00:00",
        })
        planning_id = r.json()["id"]

        # 3. Générer un post
        r = await client.post(f"{bloc3_url}/api/v1/posts/generate", json={
            "planning_id": planning_id,
            "persona_id": persona_id,
            "angle_editorial": "Les 5 sources de bruit sous-estimées en location courte durée",
            "format": "text_only",
            "platform": "linkedin",
        })
        assert r.status_code == 200
        post = r.json()
        post_id = post["post_id"]
        assert post["text"] is not None
        assert len(post["text"]) > 100

        # 4. Enqueuer dans la queue
        r = await client.post(
            f"{bloc7_url}/api/v1/queue/tasks",
            params={"task_type": "publish_post", "max_retries": 3},
            json={"post_id": post_id, "platform": "linkedin"},
        )
        assert r.status_code == 201

        # 5. Simuler le callback de l'extension
        r = await client.post(f"{bloc1_url}/api/v1/tasks/{post_id}/callback", json={
            "status": "success",
            "post_url": "https://www.linkedin.com/posts/test-e2e-abc123",
            "published_at": "2026-07-04T09:00:00Z",
        })
        assert r.status_code == 200

        # 6. Vérifier que le post est published
        r = await client.get(f"{bloc1_url}/api/v1/posts/{post_id}")
        post_final = r.json()
        assert post_final["status"] == "published"
        assert post_final["published_url"] is not None

        # Cleanup
        await client.delete(f"{bloc1_url}/api/v1/posts/{post_id}")
        await client.delete(f"{bloc1_url}/api/v1/plannings/{planning_id}")
        await client.delete(f"{bloc1_url}/api/v1/personas/{persona_id}")
```

### 8.2 Ajouter un test de charge (30 posts)

**Fichier** : `bloc-8-integration/tests/e2e/` — créer `test_load_30_posts.py`

```python
"""
Test de charge — Génération de 30 posts en masse.
"""
import pytest
import httpx
import asyncio


@pytest.mark.slow
@pytest.mark.bloc3
async def test_generate_30_posts(bloc3_url, test_persona, test_planning):
    """Génère 30 posts text_only et vérifie qu'ils sont tous créés."""
    angles = [
        f"Angle éditorial numéro {i} pour le test de charge"
        for i in range(1, 31)
    ]

    async def generate_one(angle: str):
        async with httpx.AsyncClient(base_url=bloc3_url, timeout=120.0) as client:
            r = await client.post("/api/v1/posts/generate", json={
                "planning_id": test_planning["id"],
                "persona_id": test_persona["id"],
                "angle_editorial": angle,
                "format": "text_only",
                "platform": "linkedin",
            })
            return r

    # Générer en parallèle par lots de 5 (rate limit)
    post_ids = []
    for batch in range(0, 30, 5):
        batch_angles = angles[batch:batch+5]
        responses = await asyncio.gather(*[generate_one(a) for a in batch_angles])
        for r in responses:
            if r.status_code == 200:
                post_ids.append(r.json()["post_id"])
        await asyncio.sleep(2)  # Pause entre les lots

    assert len(post_ids) == 30, f"Only {len(post_ids)} posts generated out of 30"

    # Cleanup
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        for pid in post_ids:
            await client.delete(f"/api/v1/posts/{pid}")
```

---

## TRANSVERSE — INFRASTRUCTURE & DÉPLOIEMENT

### 9.1 Créer un docker-compose.yml

**Fichier** : `docker-compose.yml` (à la racine)

```yaml
version: '3.8'

services:
  bloc1-backend:
    build:
      context: ./bloc-1-backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./bloc-1-backend/data:/app/data
      - ./bloc-1-backend/.env:/app/.env
    restart: unless-stopped

  bloc2-grillme:
    build:
      context: ./bloc-2-grillme
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    volumes:
      - ./bloc-1-backend/data:/app/data
      - ./bloc-2-grillme/.env:/app/.env
    depends_on:
      - bloc1-backend
    restart: unless-stopped

  bloc3-generation:
    build:
      context: ./bloc-3-generation
      dockerfile: Dockerfile
    ports:
      - "8003:8003"
    volumes:
      - ./bloc-1-backend/data:/app/data
      - ./bloc-3-generation/data/posts:/app/data/posts
      - ./bloc-3-generation/.env:/app/.env
    depends_on:
      - bloc1-backend
    restart: unless-stopped

  bloc4-carrousels:
    build:
      context: ./bloc-4-carrousels
      dockerfile: Dockerfile
    ports:
      - "8004:8004"
    volumes:
      - ./bloc-4-carrousels/data/carousels:/app/data/carousels
    restart: unless-stopped

  bloc7-resilience:
    build:
      context: ./bloc-7-resilience
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    volumes:
      - ./bloc-1-backend/data:/app/data
      - ./bloc-7-resilience/.env:/app/.env
    depends_on:
      - bloc1-backend
    restart: unless-stopped
```

### 9.2 Créer les Dockerfiles

**Fichier** : `bloc-1-backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app/ ./app/
RUN mkdir -p /app/data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Idem pour les blocs 2, 3, 4, 7 (adapter le port).

### 9.3 Créer un script de démarrage unifié

**Fichier** : `start_all.sh` (à la racine)

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

start_service() {
  local name=$1
  local dir=$2
  local port=$3
  local module=$4

  echo "Starting $name on port $port..."
  cd "$SCRIPT_DIR/$dir"
  if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
  fi
  uvicorn "$module" --host 0.0.0.0 --port "$port" &
  cd "$SCRIPT_DIR"
}

start_service "bloc-1-backend"   "bloc-1-backend"   8000 "app.main:app"
start_service "bloc-2-grillme"  "bloc-2-grillme"   8001 "app.main:app"
start_service "bloc-7-resilience" "bloc-7-resilience" 8002 "app.main:app"
start_service "bloc-3-generation" "bloc-3-generation" 8003 "app.main:app"
start_service "bloc-4-carrousels"  "bloc-4-carrousels"  8004 "api_server:app"

echo ""
echo "All services started."
echo "Dashboard: cd bloc-6-dashboard && npm run dev"
echo "Extension: Load unpacked from bloc-5-extension/ in chrome://extensions"
echo ""
echo "Press Ctrl+C to stop all services."

wait
```

### 9.4 Extraire les modèles partagés dans un package commun

**Fichier** : `bloc-1-backend/app/models.py`

Ajouter en haut du fichier un commentaire indiquant que ce fichier est la source de vérité :

```python
# ⚠️ SOURCE DE VÉRITÉ — Ne pas dupliquer dans les autres blocs.
# Les autres blocs doivent importer ces modèles ou pointer vers la même DB.
# Si un autre bloc a besoin d'un champ, modifier CE fichier d'abord.
```

**Fichier** : `bloc-2-grillme/app/models.py` et `bloc-3-generation/app/models.py`

Remplacer les modèles dupliqués par un import :

```python
# ⚠️ Ne pas modifier — les modèles sont importés du bloc 1
import sys
sys.path.insert(0, "/data/home-mathieu/saas-rse/bloc-1-backend")
from app.models import Persona, Planning, Post, Base, gen_uuid
```

---

## TRANSVERSE — SÉCURITÉ

### 10.1 Ajouter HTTPS en développement local

**Fichier** : `bloc-1-backend/app/main.py`

```python
# En production, utiliser un reverse proxy (Caddy/Nginx) pour le HTTPS.
# Pour le dev local avec l'extension Chrome, générer un certificat auto-signé :
# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### 10.2 Valider les uploads d'images

**Fichier** : `bloc-3-generation/app/services/image_service.py`

```python
def _download_image(self, post_id: str, url: str) -> str:
    os.makedirs("./data/posts", exist_ok=True)
    path = f"./data/posts/{post_id}.png"

    with httpx.stream("GET", url, timeout=60) as r:
        r.raise_for_status()

        # Vérifier le content-type
        content_type = r.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"Invalid content type: {content_type}")

        # Vérifier la taille max (10 MB)
        content_length = r.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            raise ValueError("Image too large (>10MB)")

        with open(path, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)

    return path
```

### 10.3 Ne pas commiter les `.env`

**Fichier** : `.gitignore` (à la racine)

Vérifier que tous les `.env` sont ignorés :

```gitignore
.env
*.db
__pycache__/
.venv/
node_modules/
.coverage
data/posts/*
data/carousels/*
```

Supprimer les `.env` déjà commités :

```bash
git rm --cached bloc-1-backend/.env bloc-2-grillme/.env bloc-3-generation/.env bloc-6-dashboard/.env bloc-7-resilience/.env
```

---

## TRANSVERSE — FONCTIONNALITÉS MANQUANTES

### 11.1 Rendre les BUs configurables (non hardcodées)

**Fichier** : `bloc-1-backend/app/models.py`

Ajouter une table `BusinessUnit` :

```python
class BusinessUnit(Base):
    __tablename__ = "business_units"

    id = Column(String, primary_key=True, default=gen_uuid)
    slug = Column(String, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

**Fichier** : `bloc-1-backend/app/schemas.py`

Remplacer les `Literal["noisyless", "afluxo", "mbhrep"]` par `str` avec validation :

```python
class PersonaCreate(BaseModel):
    bu: str = Field(..., min_length=1, max_length=50)
    # La validation que le BU existe se fait dans le service
```

**Fichier** : `bloc-1-backend/app/services/persona_service.py`

```python
def create(db: Session, data: PersonaCreate) -> Persona:
    # Vérifier que le BU existe
    bu = db.query(BusinessUnit).filter(BusinessUnit.slug == data.bu).first()
    if not bu:
        raise HTTPException(status_code=400, detail=f"Business unit '{data.bu}' not found")
    # ... reste de la fonction
```

### 11.2 Ajouter la planification intelligente (meilleurs horaires)

**Fichier** : `bloc-3-generation/app/services/` — créer `scheduling_service.py`

```python
"""
Service de planification intelligente.
Suggère les meilleurs créneaux de publication par plateforme.
"""

BEST_TIMES = {
    "linkedin": [
        {"day": "tuesday", "hour": 8, "score": 0.9},
        {"day": "tuesday", "hour": 10, "score": 0.85},
        {"day": "wednesday", "hour": 8, "score": 0.88},
        {"day": "wednesday", "hour": 12, "score": 0.82},
        {"day": "thursday", "hour": 9, "score": 0.87},
    ],
    "instagram": [
        {"day": "monday", "hour": 11, "score": 0.85},
        {"day": "tuesday", "hour": 10, "score": 0.82},
        {"day": "wednesday", "hour": 11, "score": 0.88},
        {"day": "thursday", "hour": 12, "score": 0.84},
        {"day": "friday", "hour": 9, "score": 0.80},
    ],
}

def suggest_schedule(platform: str, n: int = 7) -> list[dict]:
    """Suggère N créneaux optimaux pour une plateforme donnée."""
    times = BEST_TIMES.get(platform, BEST_TIMES["linkedin"])
    # Trier par score décroissant et prendre les N premiers
    sorted_times = sorted(times, key=lambda t: t["score"], reverse=True)
    return sorted_times[:n]
```

---

## TRANSVERSE — QUALITÉ DU CODE

### 12.1 Supprimer les fichiers qui ne devraient pas être commités

```bash
# Fichiers à supprimer du repo
rm bloc-1-backend/.coverage
rm bloc-1-backend/data/saas_rse.db
rm bloc-1-backend/data/test_saas_rse.db
rm bloc-2-grillme/data/test_grillme.db
rm bloc-3-generation/data/test_generation.db
rm bloc-7-resilience/data/test_resilience.db

# Ajouter au .gitignore
echo "*.db" >> .gitignore
echo ".coverage" >> .gitignore
```

### 12.2 Corriger les tests qui ne testent pas le vrai code

**Fichier** : `bloc-2-grillme/tests/test_interrogator_agent.py`

Après la refonte de l'agent (section 2.1), les tests doivent appeler `start_session()` et `process_message()` au lieu de méthodes qui n'existent pas. Voir section 2.3 pour les nouveaux tests.

### 12.3 Ajouter un linter/formatter

**Fichier** : `pyproject.toml` (racine ou chaque bloc)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.12"
strict = true
```

---

## CHECKLIST FINALE DE VÉRIFICATION

Avant de considérer le SaaS comme opérationnel, vérifier chaque point :

### Flux complet
- [ ] GrilledMe pose des questions adaptatives (pas un formulaire linéaire)
- [ ] GrilledMe challenge les réponses vagues
- [ ] GrilledMe ne dépasse pas 12 échanges
- [ ] Un persona complet est créé en BDD après l'onboarding
- [ ] La génération de post LinkedIn produit un texte avec hook + développement + CTA
- [ ] La génération de post Instagram produit un visual + caption + hashtags
- [ ] Les images sont générées via FAL.ai et servies localement
- [ ] Les carrousels sont générés via Playwright (appel HTTP du bloc 3 au bloc 4)
- [ ] Les posts sont planifiables avec une date
- [ ] L'extension Chrome poll le backend toutes les 5 minutes
- [ ] L'extension Chrome publie réellement sur LinkedIn (compte test)
- [ ] L'extension Chrome publie réellement sur Instagram (compte test)
- [ ] L'extension Chrome envoie un callback SUCCESS au backend
- [ ] L'extension Chrome envoie un callback FAILED en cas d'erreur
- [ ] Le bloc 7 retry 3 fois avant de marquer failed
- [ ] Le bloc 7 envoie une alerte Telegram après 3 échecs
- [ ] Le bloc 7 met à jour le statut du post dans le bloc 1 après échec
- [ ] Le dashboard affiche les posts du jour
- [ ] Le dashboard affiche le planning éditorial
- [ ] Le dashboard affiche les analytics (posts publiés)
- [ ] La page GrilledMe fonctionne dans le dashboard
- [ ] La page d'édition de persona fonctionne dans le dashboard
- [ ] Le studio de contenu permet la génération en masse

### Robustesse
- [ ] Rate limiting sur `/api/v1/posts/generate`
- [ ] Authentification par token API sur tous les endpoints
- [ ] Validation de la structure `charte_branding`
- [ ] Les CORS origins sont configurables (pas d'IPs hardcodées)
- [ ] Les URLs de services sont configurables (pas d'IPs hardcodées)
- [ ] Les `.env` ne sont pas commités
- [ ] Les `.db` et `.coverage` ne sont pas commités
- [ ] Les modèles ne sont pas dupliqués entre les blocs
- [ ] Un `docker-compose.yml` permet de tout démarrer
- [ ] Un script `start_all.sh` permet de tout démarrer

### Sécurité
- [ ] Token API requis pour les appels backend
- [ ] Validation des uploads d'images (type, taille)
- [ ] Pas de secrets dans le code source
- [ ] Les sessions LinkedIn/Instagram utilisent les cookies du navigateur (pas de mots de passe)

### Tests
- [ ] Tous les tests unitaires passent (`pytest -v` dans chaque bloc)
- [ ] Les tests E2E du flux complet passent
- [ ] Les tests de charge (30 posts) passent
- [ ] Les tests d'intégration FAL.ai passent (si `RUN_INTEGRATION_TESTS=1`)
- [ ] Les tests de l'extension Chrome passent (`npm test` dans bloc-5-extension)

### Documentation
- [ ] README.md à jour avec la procédure de démarrage complète
- [ ] RECETTE.md à jour avec les gates S1-S5
- [ ] Ce document (evolution_saas.md) reflète l'état réel du code
