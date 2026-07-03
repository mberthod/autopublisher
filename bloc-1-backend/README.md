# Bloc 1 — Backend FastAPI

Socle API REST pour le SaaS RSE : CRUD sur Personas, Plannings et Posts, avec SQLite et SQLAlchemy 2.

## Setup

```bash
cd /data/home-mathieu/saas-rse/bloc-1-backend

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
```

## Lancer l'API

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI disponible sur http://localhost:8000/docs

## Tests

```bash
pytest -v
pytest -v --cov=app --cov-report=term-missing
```

## Reset de la DB

```bash
rm -f data/saas_rse.db
# Relancer l'API pour recréer automatiquement les tables
```

## Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | /healthz | Liveness probe |
| GET | /readyz | Readiness probe (vérifie la DB) |
| POST | /api/v1/personas | Créer un persona |
| GET | /api/v1/personas | Lister les personas |
| GET | /api/v1/personas/{id} | Récupérer un persona |
| PATCH | /api/v1/personas/{id} | Modifier un persona |
| DELETE | /api/v1/personas/{id} | Supprimer (cascade plannings+posts) |
| POST | /api/v1/plannings | Créer un planning |
| GET | /api/v1/plannings | Lister |
| GET | /api/v1/plannings/{id} | Récupérer avec ses posts |
| PATCH | /api/v1/plannings/{id} | Modifier |
| DELETE | /api/v1/plannings/{id} | Supprimer (cascade posts) |
| POST | /api/v1/posts | Créer un post draft |
| GET | /api/v1/posts | Lister (filtres: status, persona_id, planning_id, platform) |
| GET | /api/v1/posts/{id} | Récupérer |
| PATCH | /api/v1/posts/{id} | Modifier |
| DELETE | /api/v1/posts/{id} | Supprimer |

## Test manuel rapide

```bash
# Créer un persona
curl -s -X POST http://localhost:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -d '{
    "bu": "noisyless",
    "nom": "Propriétaire Airbnb stressé par le bruit",
    "besoins": "Trouver des solutions concrètes pour réduire les nuisances sonores",
    "frustrations": "Locataires qui se plaignent, notes 4 étoiles au lieu de 5",
    "cible": "Propriétaires de locations courte durée en France",
    "charte_branding": {
      "ton": "professional_warm",
      "mots_interdits": ["cheap", "disrupt"],
      "emojis_autorises": ["✅", "🔧"],
      "structure_phrases": "courtes, max 20 mots",
      "longueur_cible": 1500
    }
  }' | python3 -m json.tool

# Lister les personas
curl -s http://localhost:8000/api/v1/personas | python3 -m json.tool

# Health
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/readyz
```
