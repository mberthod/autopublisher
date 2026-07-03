# Bloc 8 — Tests d'intégration + recette Phase A

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : Suite de tests E2E qui valide la chaîne complète Persona → Post → Publication, + recette manuelle de la Phase A

---

## 🎯 Objectif

À l'issue de la Semaine 6, le système complet doit produire **30 posts publiés automatiquement** sur les 3 BU. Ce bloc :
1. Définit la **suite de tests E2E** qui valide le flow complet (mocké pour les parties externes)
2. Définit la **procédure de recette manuelle** que Mathieu exécute pour valider le critère de succès S5
3. Documente les **gates hebdomadaires S1-S5** comme critères bloquants

**Ce bloc ne contient PAS** : nouveau code de prod, juste des tests et de la doc.

---

## 🏗️ Architecture cible

```
[Tests E2E automatisés (pytest)]
    │
    ├──► [Test 1: GrilledMe → Persona]
    │   - Démarre une session GrilledMe
    │   - Envoie 10 messages (avec mock LLM pour rapidité)
    │   - Vérifie qu'un Persona est créé en BDD
    │
    ├──► [Test 2: Persona → Post generation]
    │   - Charge un Persona existant
    │   - Appelle /api/v1/posts/generate (avec mock LLM + FAL.ai)
    │   - Vérifie qu'un Post draft est créé avec text + image_url
    │
    ├──► [Test 3: Post → Queue → Retry]
    │   - Crée un post status=validated
    │   - Pousse une tâche publish dans la queue (bloc 7)
    │   - Le worker doit retry 3 fois puis marquer failed
    │
    ├──► [Test 4: Post → Image (FAL.ai)]
    │   - Avec un vrai appel FAL.ai (test intégration)
    │   - Vérifie que l'image est uploadée et accessible
    │
    └──► [Test 5: Extension → Backend callback]
        - Simule l'extension qui POST un callback SUCCESS
        - Vérifie que le post passe en status=published
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-8-integration/
    ├── SPEC.md
    ├── README.md
    ├── RECETTE.md                          ← procédure de validation manuelle
    ├── pyproject.toml                      ← tests pytest uniquement
    ├── .env.example
    ├── tests/
    │   ├── conftest.py                     ← fixtures globales (DB, services mockés)
    │   ├── e2e/
    │   │   ├── test_grillme_to_persona.py
    │   │   ├── test_persona_to_post.py
    │   │   ├── test_post_to_queue.py
    │   │   ├── test_image_generation.py
    │   │   └── test_extension_callback.py
    │   └── fixtures/
    │       ├── sample_persona.json
    │       ├── sample_post.json
    │       └── mock_llm_responses.json
    └── scripts/
        ├── run_recette.sh                  ← script qui exécute tous les checks manuels
        └── reset_db.sh                     ← reset complet de la DB pour test
```

---

## 🛠️ Dépendances

```toml
[project]
name = "saas-rse-integration"
version = "0.1.0"
description = "Tests d'intégration pour SaaS RSE"
requires-python = ">=3.11,<3.13"
dependencies = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.24,<1",
  "httpx>=0.28,<1",
  "sqlalchemy>=2.0,<3",
]

[project.optional-dependencies]
dev = [
  "pytest-mock>=3.14,<4",
  "pytest-cov>=5.0,<6",
]
```

---

## 🔑 Variables d'environnement

`.env` (pour les tests) :
```bash
# Test DB (isolée, dans /tmp)
TEST_DATABASE_URL=sqlite:////tmp/saas_rse_test.db

# API backend (pour tests E2E)
TEST_API_URL=http://localhost:8000/api/v1

# Mocks activés par défaut
MOCK_LLM=true
MOCK_FAL_AI=true
MOCK_TELEGRAM=true

# Pour les tests d'intégration "réels", mettre à false
# MOCK_LLM=false
# MOCK_FAL_AI=false
```

---

## 🧪 Tests E2E (détaillés)

### `test_grillme_to_persona.py`

**Objectif** : valider que GrilledMe produit un Persona exploitable

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_grilledme_full_conversation_creates_persona():
    """Conversation simulée de 10 messages → Persona créé en BDD"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Start session
        r = await client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"})
        assert r.status_code == 201
        session_id = r.json()["session_id"]
        assert r.json()["first_question"]

        # 2. Enchaîner 10 messages (réponses mockées, agent LLM réel ou mocké)
        messages = [
            "Propriétaires de locations courte durée en France, 1-5 biens",
            "Réduire les nuisances sonores, maintenir 4.8+ étoiles",
            "Plaintes des voisins, demandes de remboursement",
            "Solutions concrètes, mesurables, installables soi-même",
            "Ton chaleureux mais expert, jamais vendeur",
            "Pas de mots comme 'cheap' ou 'disrupt'",
            "Emojis techniques: ✅ 🔧 📊",
            "Phrases courtes, max 20 mots",
            "1500 caractères par post LinkedIn",
            "OK c'est bon"
        ]
        for msg in messages:
            r = await client.post(
                f"/api/v1/grillme/sessions/{session_id}/messages",
                json={"user_message": msg}
            )
            assert r.status_code == 200
            data = r.json()
            if data.get("is_complete"):
                break

        # 3. Vérifier que le Persona est créé
        assert data["is_complete"] is True

        r = await client.get(f"/api/v1/grillme/sessions/{session_id}/persona")
        assert r.status_code == 200
        persona = r.json()["persona"]

        # 4. Le Persona doit être exploitable
        assert persona["bu"] == "noisyless"
        assert len(persona["besoins"]) > 20
        assert len(persona["frustrations"]) > 20
        assert len(persona["cible"]) > 20
        assert "ton" in persona["charte_branding"]
        assert "mots_interdits" in persona["charte_branding"]
        assert len(persona["charte_branding"]["mots_interdits"]) > 0
```

### `test_persona_to_post.py`

**Objectif** : valider que la génération de posts produit un draft publiable

```python
@pytest.mark.asyncio
async def test_persona_to_post_generation():
    """À partir d'un Persona + angle, génère un Post draft valide"""
    # 1. Charger un Persona de test (ou le créer)
    persona_id = create_test_persona(bu="noisyless")

    # 2. Générer un post
    async with AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/posts/generate", json={
            "planning_id": create_test_planning(persona_id).id,
            "persona_id": persona_id,
            "angle_editorial": "Les 5 sources de bruit les plus sous-estimées en location courte durée",
            "format": "image",
            "platform": "linkedin"
        })
        assert r.status_code == 200
        post = r.json()

        # 3. Vérifications
        assert post["text"] is not None
        assert 200 < len(post["text"]) < 3000  # Longueur raisonnable
        assert post["image_url"] is not None
        assert post["image_url"].startswith("http")
        assert post["status"] == "draft"
        assert post["generation_metadata"]["llm_model"] == "deepseek-v4"


@pytest.mark.asyncio
async def test_persona_to_post_carousel():
    """Test spécifique pour le format carrousel"""
    # ... idem avec format="carousel", platform="instagram"
    # Vérifie que carousel_urls contient au moins 3 URLs
```

### `test_post_to_queue.py`

**Objectif** : valider la résilience (3 retries, puis failed)

```python
@pytest.mark.asyncio
async def test_post_publish_fails_after_3_retries():
    """Un post qui échoue 3 fois doit être marqué failed + Telegram alert"""
    # 1. Créer un post validé
    post = create_validated_post(bu="noisyless", platform="linkedin")

    # 2. Pousser dans la queue avec un handler qui échoue
    with mock.patch("bloc_7.services.queue_service.HANDLERS") as mock_handlers:
        mock_handlers["publish_post"].side_effect = Exception("LinkedIn down")

        # 3. Démarrer le worker (en background)
        worker_task = asyncio.create_task(run_worker_for_test())

        # 4. Enqueue
        task_id = await enqueue_task("publish_post", {"post_id": post.id})

        # 5. Attendre 40s (1+5+30 = 36s + marge)
        await asyncio.sleep(40)

        # 6. Vérifier que le post est failed
        async with AsyncClient(base_url="http://localhost:8000") as client:
            r = await client.get(f"/api/v1/posts/{post.id}")
            assert r.json()["status"] == "failed"
            assert r.json()["error_code"] is not None

        # 7. Vérifier que 3 attempts ont eu lieu
        queue_task = await get_queue_task(task_id)
        assert queue_task.attempts == 3
        assert queue_task.status == "failed"

        # 8. Vérifier que Telegram a été appelé
        mock_telegram.assert_called_once()
```

### `test_image_generation.py`

**Objectif** : valider l'intégration réelle avec FAL.ai (test d'intégration, pas unitaire)

```python
@pytest.mark.integration  # Marqueur pour skip en CI
@pytest.mark.asyncio
async def test_fal_ai_real_image_generation():
    """Génère une vraie image via FAL.ai (coût: ~$0.003)"""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run")

    service = ImageService(api_key=os.getenv("FAL_KEY"))
    url = await service.generate(
        prompt="Photo minimaliste d'un appartement moderne silencieux",
        width=1024,
        height=1024,
    )

    assert url.startswith("https://")
    # Vérifier que l'image est accessible
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        assert r.status_code == 200
        assert len(r.content) > 10_000  # Au moins 10KB
```

### `test_extension_callback.py`

**Objectif** : simuler l'extension qui notifie le backend

```python
@pytest.mark.asyncio
async def test_extension_success_callback():
    """L'extension POST un callback SUCCESS → post marqué published"""
    post = create_validated_post(bu="noisyless", platform="linkedin")

    async with AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post(f"/api/v1/tasks/{post.task_id}/callback", json={
            "status": "success",
            "post_url": "https://linkedin.com/posts/mathieu-...",
            "published_at": "2026-07-15T09:03:42Z"
        })
        assert r.status_code == 200

        # Vérifier que le post est passé en published
        r = await client.get(f"/api/v1/posts/{post.id}")
        assert r.json()["status"] == "published"
        assert r.json()["published_url"] is not None
        assert r.json()["published_at"] is not None
```

---

## 📋 Procédure de recette manuelle (RECETTE.md)

### Semaine 1 — Gate S1 : GrilledMe

**Critère** : GrilledMe produit un Persona exploitable pour Noisyless.

**Procédure** :
1. Lancer le backend : `cd bloc-1-backend && uvicorn app.main:app --reload --port 8000`
2. Lancer GrilledMe : `cd bloc-2-grillme && uvicorn app.main:app --reload --port 8001`
3. Démarrer une session : `curl -X POST http://localhost:8001/api/v1/grillme/sessions -d '{"bu":"noisyless"}' -H "Content-Type: application/json"`
4. Enchaîner 8-12 messages (répondre honnêtement, challenger si l'IA pose des questions vagues)
5. Vérifier le Persona final :
   - Le `nom` est-il descriptif ?
   - Les `besoins` sont-ils concrets (pas génériques) ?
   - Les `frustrations` sont-elles spécifiques ?
   - La `charte_branding` est-elle utilisable (longueur_cible, ton, mots_interdits) ?

**Validation** : tu valides subjectivement que ce Persona te **convainc**. Si oui → S1 passe, on continue. Si non → itère avec Claude Code sur les prompts.

### Semaine 2 — Gate S2 : Génération de posts

**Critère** : 1 post généré end-to-end est publiable en l'état.

**Procédure** :
1. Charger le Persona Noisyless créé en S1
2. Appeler : `curl -X POST http://localhost:8000/api/v1/posts/generate -d '{"planning_id":"...","persona_id":"...","angle_editorial":"...","format":"image","platform":"linkedin"}' -H "Content-Type: application/json"`
3. Vérifier le post généré :
   - Le texte est-il cohérent avec le Persona ?
   - L'image est-elle pertinente (ouvrir l'URL) ?
   - Tu jugerais ce post publiable tel quel sur ton compte pro ?

**Validation** : tu valides subjectivement. Si oui → S2 passe.

### Semaine 3 — Gate S3 : Extension publie 1 post

**Critère** : l'extension Chrome publie 1 post sur LinkedIn sans intervention.

**Procédure** :
1. Charger l'extension en mode développeur
2. **Utiliser un compte LinkedIn de test** (pas ton compte BU)
3. Marquer un post draft comme `validated` en BDD
4. L'extension doit le publier dans les 5 minutes
5. Vérifier sur linkedin.com : le post est là
6. Vérifier en BDD : status='published', published_url rempli

**Validation** : l'extension a publié automatiquement. Si oui → S3 passe.

### Semaine 4-5 — Gate S4 : 7 posts en 7 jours

**Critère** : 7 posts sont publiés sur 7 jours, 1 par BU (Noisyless, Afluxo, MBHREP) en rotation.

**Procédure** :
1. Planifier 7 posts validés : 2-3 Noisyless, 2-3 Afluxo, 1-2 MBHREP
2. Répartir sur 7 jours (1 par jour)
3. Chaque jour : vérifier que le post est publié sur la bonne plateforme
4. Vérifier qu'il n'y a pas eu d'erreur côté extension

**Validation** : 7/7 posts publiés sans intervention. Si oui → S4 passe.

### Semaine 6 — Gate S5 (finale) : 30 posts cumulés, 0 ban, <5% échecs

**Critère** : 30 posts publiés au total, dont <5% en échec (max 1-2 échecs), 0 ban de compte.

**Procédure** :
1. Compter le total de posts `status='published'` en BDD : `SELECT COUNT(*) FROM posts WHERE status='published'`
2. Compter les échecs : `SELECT COUNT(*) FROM posts WHERE status='failed'`
3. Calculer le ratio : `failed / (published + failed)`. Si < 5% → OK
4. Vérifier que les 3 comptes LinkedIn sont toujours actifs (pas de ban)
5. Vérifier qu'aucune publication n'a été faite **manuellement** (sinon c'est de la triche, le critère est "sans intervention")

**Validation** : si 30+ posts, <5% échecs, 0 ban → **Phase A réussie**, on peut passer en Phase B.

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-8-integration

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Tests unitaires (rapides, mocks)
pytest -v

# Tests d'intégration (lents, vrais appels API)
RUN_INTEGRATION_TESTS=1 pytest -v -m integration

# Avec coverage
pytest --cov=bloc_1_backend --cov=bloc_2_grillme --cov=bloc_3_generation --cov=bloc_7_resilience

# Reset DB pour test
./scripts/reset_db.sh

# Run recette complète
./scripts/run_recette.sh
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Nouveau code de prod (il valide juste l'existant)
- ❌ Tests unitaires des autres blocs (chaque bloc a ses propres tests)
- ❌ Tests de performance / load testing
- ❌ Tests de sécurité (pentest, à faire en phase B)
- ❌ Tests de compatibilité navigateur (l'extension est testée manuellement)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 8 (tests d'intégration + recette)
dans /data/home-mathieu/saas-rse/bloc-8-integration/.

Règles strictes :
1. AUCUN code de prod — uniquement des tests et de la doc
2. Tests E2E utilisent httpx.AsyncClient + vraie DB (test DB isolée)
3. Tests d'intégration marqués @pytest.mark.integration (skippables en CI)
4. Mocks pour LLM, FAL.ai, Telegram par défaut (rapide)
5. Procedure RECETTE.md doit être testable par Mathieu sans aide
6. Tests qui passent vraiment (pas des squelettes)
7. README explique la différence entre tests unitaires (chaque bloc) et E2E (ce bloc)

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent
- Les décisions d'archi prises
- Les limitations connues
- Une estimation du temps d'exécution complet de la suite
```
