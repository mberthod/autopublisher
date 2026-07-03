# Bloc 3 — Génération de posts (texte + image)

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Pipeline complet Persona + angle → draft (texte + image) validé en BDD

---

## 🎯 Objectif

À partir d'un `Persona` (créé par GrilledMe, bloc 2) et d'un `angle_editorial` (issu du planning rolling 30j), produire un **Post draft** contenant :
- Le texte formaté selon la Charte de Branding du Persona
- Une image (photo via FAL.ai **ou** carrousel via Playwright — voir bloc 4)
- Le statut "draft" en BDD (pas publié)

---

## 📥 Inputs

```python
# POST /api/v1/posts/generate
{
  "planning_id": "uuid",                # Référence vers la table plannings
  "persona_id": "uuid",                  # Référence vers la table personas
  "angle_editorial": "douleur des propriétaires Airbnb face au bruit",  # string
  "format": "text_only" | "image" | "carousel",  # enum
  "platform": "linkedin" | "instagram"            # enum
}
```

---

## 📤 Outputs

```python
# 200 OK
{
  "post_id": "uuid",
  "status": "draft",
  "text": "Le texte complet du post, formaté selon la charte...",
  "image_url": "https://cdn.example.com/posts/abc123.png" | null,
  "carousel_urls": ["https://...1", "https://...2"] | null,
  "generation_metadata": {
    "llm_model": "deepseek-v4",
    "llm_tokens_in": 2400,
    "llm_tokens_out": 480,
    "image_provider": "fal.ai" | "playwright" | null,
    "generation_time_ms": 8500
  }
}
```

---

## 🏗️ Architecture cible

```
[API /posts/generate]
    │
    ▼
[PostService.generate()]
    │
    ├──► [PersonaService.get_full()] ──► [DB SQLite]
    │         (charge persona + charte de branding)
    │
    ├──► [LLMService.generate_text()]
    │         │
    │         ├──► Construit system prompt :
    │         │   "Tu es un community manager pour {{persona.besoin}}.
    │         │    Tu écris pour {{persona.cible}}.
    │         │    Ton: {{charte.ton}}.
    │         │    Mots interdits: {{charte.mots_interdits}}.
    │         │    Emojis autorisés: {{charte.emojis_autorises}}.
    │         │    Structure des phrases: {{charte.structure_}}."
    │         │
    │         ├──► User prompt :
    │         │   "Angle éditorial: {{angle_editorial}}.
    │         │    Plateforme: {{platform}}.
    │         │    Longueur cible: {{platform == 'linkedin' ? '1300-2000' : '200-500'}} caractères."
    │         │
    │         └──► Appel DeepSeek V4 (API OpenAI-compatible)
    │
    ├──► [ImageService.generate()]
    │         │
    │         ├──► Si format == "text_only" : return None
    │         │
    │         ├──► Si format == "image" :
    │         │   └──► FAL.ai Flux.1 (model: "fal-ai/flux/schnell")
    │         │         prompt = "image RSE pour {{angle_editorial}}, style {{charte.ton_visuel}}"
    │         │
    │         └──► Si format == "carousel" :
    │             └──► Délègue au bloc 4 (carrousels Playwright)
    │
    └──► [DB SQLite]
          INSERT INTO posts (id, planning_id, persona_id, text, image_url, carousel_urls, status='draft', created_at)
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
├── bloc-3-generation/
│   ├── SPEC.md                  ← ce fichier
│   ├── README.md
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI app (route /posts/generate)
│   │   ├── config.py            ← Pydantic Settings
│   │   ├── models.py            ← SQLAlchemy models
│   │   ├── schemas.py           ← Pydantic schemas
│   │   ├── db.py                ← SQLite session
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── persona_service.py
│   │       ├── llm_service.py
│   │       └── image_service.py
│   └── tests/
│       ├── test_llm_service.py
│       ├── test_image_service.py
│       └── test_post_e2e.py
```

---

## 🛠️ Dépendances à ajouter

Dans `pyproject.toml` (du bloc 3) :
```toml
[project]
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn>=0.32,<1",
  "sqlalchemy>=2.0,<3",
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.6,<3",
  "httpx>=0.28,<1",                      # appels LLM + FAL.ai
  "openai>=1.54,<2",                      # SDK OpenAI pour DeepSeek (compatible)
  "fal-client>=0.4,<1",                   # SDK FAL.ai
  "python-multipart>=0.0.12,<1",
  "loguru>=0.7,<1",
]
```

---

## 🔑 Variables d'environnement

`.env` (à créer par Mathieu) :
```bash
# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4

# FAL.ai
FAL_KEY=...

# Database
DATABASE_URL=sqlite:///./data/saas_rse.db

# Logging
LOG_LEVEL=INFO
```

---

## 🧪 Critères d'acceptation

### Tests unitaires
- [ ] `test_llm_service.py` : `LLMService.generate_text()` retourne un texte non vide, < 2500 chars pour LinkedIn
- [ ] `test_llm_service.py` : le system prompt contient bien le persona (test avec mock)
- [ ] `test_image_service.py` : FAL.ai est appelé avec le bon prompt (mock)
- [ ] `test_image_service.py` : `format="text_only"` → `image_url=None`

### Test E2E (`test_post_e2e.py`)
- [ ] POST `/api/v1/posts/generate` avec persona, angle, format="image" → 200, body contient `text` non vide et `image_url` (URL valide)
- [ ] Le post créé a `status="draft"` en BDD
- [ ] Le post créé a un `created_at` récent
- [ ] L'image_url pointe vers un fichier accessible (HTTP 200)

### Vérification manuelle
- [ ] Lancer l'API : `uvicorn app.main:app --reload --port 8000`
- [ ] Ouvrir `http://localhost:8000/docs` (Swagger auto)
- [ ] POST `/api/v1/posts/generate` avec persona Noisyless + angle "douleur bruit Airbnb" + format="image"
- [ ] Vérifier : le texte parle bien de bruit/location courte durée, l'image est cohérente, post créé en BDD

---

## 📚 Modèle de données (à importer du bloc 1)

Si le bloc 1 n'est pas encore fait, **utilise ces modèles minimaux** dans `models.py` :

```python
# app/models.py
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

Base = declarative_base()

class Persona(Base):
    __tablename__ = "personas"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bu = Column(String, nullable=False)  # "noisyless" | "afluxo" | "mbhrep"
    nom = Column(String, nullable=False)
    besoins = Column(Text, nullable=False)
    frustrations = Column(Text, nullable=False)
    cible = Column(Text, nullable=False)
    charte_branding = Column(JSON, nullable=False)  # {ton, mots_interdits, emojis_autorises, structure, longueur_cible}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Planning(Base):
    __tablename__ = "plannings"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    persona_id = Column(String, ForeignKey("personas.id"), nullable=False)
    date_debut = Column(DateTime, nullable=False)
    date_fin = Column(DateTime, nullable=False)
    posts = relationship("Post", back_populates="planning")
    persona = relationship("Persona")

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    planning_id = Column(String, ForeignKey("plannings.id"), nullable=False)
    persona_id = Column(String, ForeignKey("personas.id"), nullable=False)
    platform = Column(String, nullable=False)  # "linkedin" | "instagram"
    angle_editorial = Column(Text, nullable=False)
    format = Column(String, nullable=False)  # "text_only" | "image" | "carousel"
    text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    carousel_urls = Column(JSON, nullable=True)
    status = Column(String, default="draft", nullable=False)  # "draft" | "validated" | "scheduled" | "published" | "failed"
    generation_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    planning = relationship("Planning", back_populates="posts")
    persona = relationship("Persona")
```

---

## 📝 Pydantic schemas

```python
# app/schemas.py
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class PostGenerateRequest(BaseModel):
    planning_id: str
    persona_id: str
    angle_editorial: str = Field(..., min_length=10)
    format: Literal["text_only", "image", "carousel"]
    platform: Literal["linkedin", "instagram"]

class PostGenerateResponse(BaseModel):
    post_id: str
    status: str
    text: str
    image_url: Optional[str] = None
    carousel_urls: Optional[list[str]] = None
    generation_metadata: dict
```

---

## ⚠️ Points d'attention

1. **Coût LLM** : un appel DeepSeek V4 par post ≈ 2-3k tokens → ~$0.001-0.003. Pour 90 posts/mois, c'est ~$0.20/mois. Négligeable. Mais teste avec un rate limiter sur l'endpoint pour pas qu'un bug parte en boucle.

2. **Timeout FAL.ai** : les générations d'images peuvent prendre 10-30s. Mets un `timeout=60` sur l'appel httpx.

3. **Pas de retry ici** : la résilience (retry sur 3 tentatives) est gérée par le bloc 7. Ce bloc fait 1 tentative, remonte l'erreur, c'est tout.

4. **Image prompt** : ne pas juste passer l'angle brut à FAL.ai. Construis un prompt enrichi qui inclut le BU et la charte :
   ```
   "Photo professionnel RSE, style minimal et lumineux, illustrant : {{angle_editorial}}. 
   Pas de texte dans l'image. Couleurs: {{charte.couleurs}}."
   ```

5. **Stockage des images** : pour la phase A, on stocke localement dans `./data/posts/` et on sert via un endpoint `/static/posts/`. Pas de CDN/S3 pour l'instant. Migration phase B.

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-3-generation

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Créer la DB
python -c "from app.db import init_db; init_db()"

# Lancer l'API
uvicorn app.main:app --reload --port 8000

# Tests
pytest -v
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Publication sur LinkedIn/Instagram (c'est l'extension, bloc 5)
- ❌ Génération de carrousels visuels (c'est le bloc 4)
- ❌ Retry en cas d'échec (c'est le bloc 7)
- ❌ Interface web (c'est le bloc 6, dashboard)
- ❌ GrilledMe (c'est le bloc 2, code par Mathieu)
- ❌ Auth/multi-tenant (phase B)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 3 (génération de posts)
dans /data/home-mathieu/saas-rse/bloc-3-generation/.

Règles strictes :
1. Demande confirmation avant toute décision d'archi non couverte par le SPEC
   (ex: choix d'ORM secondaire, structure de package, etc.)
2. N'écris PAS de tests avant que le code de prod soit fonctionnel
3. Utilise les modèles SQLAlchemy du SPEC, ne les change pas
4. Le service LLM doit utiliser le SDK OpenAI avec base_url=https://api.deepseek.com/v1
5. Le service Image doit utiliser fal-client pour FAL.ai
6. Chaque service doit être testable indépendamment (injection de dépendances)
7. Logs structurés avec loguru (niveau INFO par défaut)
8. Pas de commentaires évidents, code self-documenting
9. Pydantic v2 syntaxe stricte (model_config, Field, etc.)
10. Tests pytest qui marchent, pas juste des squelettes

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent
- Les décisions d'archi prises (pour validation)
- Les limitations connues
```
