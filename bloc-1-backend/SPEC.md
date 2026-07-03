# Bloc 1 — Backend FastAPI squelette + DB

> **Statut** : SPEC à implémenter par Claude Code
> **Owner** : Mathieu (revieweur), Claude Code (implémenteur)
> **Livrable** : API FastAPI avec CRUD sur personas/plannings/posts + DB SQLite init

---

## 🎯 Objectif

API REST basique qui sert de **socle architectural** pour tous les autres blocs. À l'issue :
- DB SQLite créée automatiquement
- Endpoints CRUD sur les 3 entités principales (persona, planning, post)
- Modèles SQLAlchemy 2 + Pydantic v2 stricts
- Tests pytest qui passent
- OpenAPI auto-généré (Swagger UI sur `/docs`)

**Ce bloc ne contient PAS** : génération de texte, génération d'images, queue, retry, extension, dashboard. C'est juste la base.

---

## 📥 Inputs (endpoints)

### Personas
- `POST /api/v1/personas` — créer un persona
- `GET /api/v1/personas` — lister tous les personas (avec pagination simple)
- `GET /api/v1/personas/{id}` — récupérer un persona
- `PATCH /api/v1/personas/{id}` — modifier un persona (overrides partiels)
- `DELETE /api/v1/personas/{id}` — supprimer un persona (cascade sur plannings+posts)

### Plannings
- `POST /api/v1/plannings` — créer un planning lié à un persona
- `GET /api/v1/plannings` — lister
- `GET /api/v1/plannings/{id}` — récupérer un planning avec ses posts
- `PATCH /api/v1/plannings/{id}` — modifier
- `DELETE /api/v1/plannings/{id}` — supprimer

### Posts
- `POST /api/v1/posts` — créer un post draft lié à un planning
- `GET /api/v1/posts` — lister avec filtres (status, persona_id, planning_id, platform)
- `GET /api/v1/posts/{id}` — récupérer
- `PATCH /api/v1/posts/{id}` — modifier (champs: text, image_url, carousel_urls, status, scheduled_for)
- `DELETE /api/v1/posts/{id}` — supprimer

### Health
- `GET /healthz` — liveness probe
- `GET /readyz` — readiness probe (vérifie que la DB répond)

---

## 📤 Outputs (réponses)

Toutes les réponses en JSON. Format standard :
```json
// Succès
{ "id": "uuid", ...champs... }

// Erreur
{ "detail": "Human-readable error message" }
```

Codes HTTP standards : 200, 201 (created), 204 (no content), 400, 404, 422 (validation), 500.

---

## 🏗️ Architecture cible

```
[Client (curl / dashboard / Claude Code)]
    │
    ▼
[FastAPI app: uvicorn app.main:app]
    │
    ├──► [API routes: app/api/*_routes.py]
    │         │
    │         └──► [Services: app/services/*_service.py]
    │                   │
    │                   ▼
    │              [SQLAlchemy session]
    │                   │
    │                   ▼
    │              [SQLite file: ./data/saas_rse.db]
    │
    └──► [OpenAPI auto: GET /docs]
```

---

## 📁 Structure de fichiers

```
/data/home-mathieu/saas-rse/
└── bloc-1-backend/
    ├── SPEC.md                          ← ce fichier
    ├── README.md
    ├── pyproject.toml
    ├── .env.example
    ├── .gitignore
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                      ← FastAPI app + lifespan
    │   ├── config.py                    ← Pydantic Settings
    │   ├── db.py                        ← engine, session, init_db
    │   ├── models.py                    ← SQLAlchemy models
    │   ├── schemas.py                   ← Pydantic schemas
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── persona_routes.py
    │   │   ├── planning_routes.py
    │   │   ├── post_routes.py
    │   │   └── health_routes.py
    │   └── services/
    │       ├── __init__.py
    │       ├── persona_service.py
    │       ├── planning_service.py
    │       └── post_service.py
    ├── data/                            ← créé à l'init, contient la DB
    │   └── .gitkeep
    └── tests/
        ├── conftest.py                  ← fixtures (db session, client HTTP)
        ├── test_persona_crud.py
        ├── test_planning_crud.py
        ├── test_post_crud.py
        └── test_health.py
```

---

## 🛠️ Dépendances

```toml
[project]
name = "saas-rse-backend"
version = "0.1.0"
description = "Backend FastAPI pour SaaS RSE automation"
requires-python = ">=3.11,<3.13"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.32,<1",
  "sqlalchemy>=2.0,<3",
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.6,<3",
  "python-multipart>=0.0.12,<1",
  "loguru>=0.7,<1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.24,<1",
  "httpx>=0.28,<1",       # TestClient async
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 🔑 Variables d'environnement

`.env` (à créer à partir de `.env.example`) :
```bash
# Database
DATABASE_URL=sqlite:///./data/saas_rse.db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true            # dev only

# Logging
LOG_LEVEL=INFO

# App
APP_ENV=development        # development | production
```

---

## 📝 Modèles SQLAlchemy (CORE — utilisé par tous les autres blocs)

```python
# app/models.py
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

Base = declarative_base()


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Persona(Base):
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=gen_uuid)
    bu = Column(String, nullable=False)  # "noisyless" | "afluxo" | "mbhrep"
    nom = Column(String, nullable=False)
    besoins = Column(Text, nullable=False)
    frustrations = Column(Text, nullable=False)
    cible = Column(Text, nullable=False)
    charte_branding = Column(JSON, nullable=False)
    # charte_branding = {
    #   "ton": "professional_warm",
    #   "mots_interdits": ["cheap", "disrupt"],
    #   "emojis_autorises": ["✅", "🔧"],
    #   "structure_phrases": "courtes, max 20 mots",
    #   "longueur_cible": 1500,
    #   "couleurs": ["#FF6B35", "#1A1A1A"]
    # }
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    plannings = relationship("Planning", back_populates="persona", cascade="all, delete-orphan")


class Planning(Base):
    __tablename__ = "plannings"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    date_debut = Column(DateTime, nullable=False)
    date_fin = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    persona = relationship("Persona", back_populates="plannings")
    posts = relationship("Post", back_populates="planning", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    planning_id = Column(String, ForeignKey("plannings.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(String, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)  # "linkedin" | "instagram"
    angle_editorial = Column(Text, nullable=False)
    format = Column(String, nullable=False)  # "text_only" | "image" | "carousel"
    text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    carousel_urls = Column(JSON, nullable=True)
    status = Column(String, default="draft", nullable=False)
    # "draft" | "validated" | "scheduled" | "published" | "failed"
    scheduled_for = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    published_url = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    planning = relationship("Planning", back_populates="posts")
    persona = relationship("Persona")
```

**⚠️ Important** : ce sont les modèles de référence. **Les autres blocs (2, 3, 4, 5, 6, 7) doivent réutiliser ces modèles** sans les modifier. Si un autre bloc a besoin d'un champ, il faut d'abord modifier ce SPEC et faire évoluer les modèles.

---

## 📝 Pydantic Schemas

```python
# app/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime


# --- Persona ---

class PersonaCreate(BaseModel):
    bu: Literal["noisyless", "afluxo", "mbhrep"]
    nom: str = Field(..., min_length=1, max_length=200)
    besoins: str = Field(..., min_length=10)
    frustrations: str = Field(..., min_length=10)
    cible: str = Field(..., min_length=10)
    charte_branding: dict


class PersonaUpdate(BaseModel):
    """Overriding partiel : tous les champs optionnels"""
    bu: Optional[Literal["noisyless", "afluxo", "mbhrep"]] = None
    nom: Optional[str] = None
    besoins: Optional[str] = None
    frustrations: Optional[str] = None
    cible: Optional[str] = None
    charte_branding: Optional[dict] = None


class PersonaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bu: str
    nom: str
    besoins: str
    frustrations: str
    cible: str
    charte_branding: dict
    created_at: datetime
    updated_at: datetime


# --- Planning ---

class PlanningCreate(BaseModel):
    persona_id: str
    date_debut: datetime
    date_fin: datetime


class PlanningUpdate(BaseModel):
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class PlanningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    date_debut: datetime
    date_fin: datetime
    created_at: datetime
    updated_at: datetime


# --- Post ---

class PostCreate(BaseModel):
    planning_id: str
    persona_id: str
    platform: Literal["linkedin", "instagram"]
    angle_editorial: str = Field(..., min_length=10)
    format: Literal["text_only", "image", "carousel"]


class PostUpdate(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None
    carousel_urls: Optional[list[str]] = None
    status: Optional[Literal["draft", "validated", "scheduled", "published", "failed"]] = None
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    planning_id: str
    persona_id: str
    platform: str
    angle_editorial: str
    format: str
    text: Optional[str]
    image_url: Optional[str]
    carousel_urls: Optional[list[str]]
    status: str
    scheduled_for: Optional[datetime]
    published_at: Optional[datetime]
    published_url: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## 🏗️ Skeleton de l'app

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app.config import settings
from app.db import init_db
from app.api import persona_routes, planning_routes, post_routes, health_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up SaaS RSE backend")
    init_db()
    logger.info(f"Database initialized at {settings.database_url}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="SaaS RSE Backend",
    version="0.1.0",
    description="API pour automation de publications RSE",
    lifespan=lifespan,
)

app.include_router(health_routes.router, tags=["health"])
app.include_router(persona_routes.router, prefix="/api/v1/personas", tags=["personas"])
app.include_router(planning_routes.router, prefix="/api/v1/plannings", tags=["plannings"])
app.include_router(post_routes.router, prefix="/api/v1/posts", tags=["posts"])
```

```python
# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base
from loguru import logger
import os

# Crée le dossier data/ si nécessaire
os.makedirs("./data", exist_ok=True)

engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Crée toutes les tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("DB tables created")


def get_db() -> Session:
    """Dependency FastAPI pour obtenir une session DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/saas_rse.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"
    app_env: str = "development"


settings = Settings()
```

---

## 🧪 Critères d'acceptation

### Tests unitaires

**`test_persona_crud.py`** :
- [ ] POST `/api/v1/personas` avec body valide → 201, retourne un PersonaRead avec id
- [ ] POST avec body invalide (champs manquants) → 422
- [ ] GET `/api/v1/personas` (vide au début) → 200, `[]`
- [ ] GET après création → 200, liste avec 1 élément
- [ ] GET `/{id}` → 200
- [ ] GET `/{id_inexistant}` → 404
- [ ] PATCH `/{id}` avec un champ → 200, champ modifié
- [ ] DELETE `/{id}` → 204, GET suivant → 404

**`test_planning_crud.py`** : idem pour plannings + **test cascade** (supprimer persona → ses plannings disparaissent)

**`test_post_crud.py`** : idem pour posts + **test filtres** (GET `/api/v1/posts?status=draft&platform=linkedin`)

**`test_health.py`** :
- [ ] GET `/healthz` → 200, `{"status": "ok"}`
- [ ] GET `/readyz` → 200 (vérifie que la DB répond)

### Vérification manuelle

```bash
cd /data/home-mathieu/saas-rse/bloc-1-backend

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Lancer l'API
uvicorn app.main:app --reload --port 8000

# Tests
pytest -v

# Ouvrir Swagger
# http://localhost:8000/docs

# Test manuel avec curl
curl -X POST http://localhost:8000/api/v1/personas \
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
  }'
```

---

## ⚠️ Points d'attention

1. **Cascade deletes** : supprimer un persona doit supprimer ses plannings et posts (configuré via `cascade="all, delete-orphan"`). Tester ce comportement.

2. **Timestamps** : `created_at` et `updated_at` sont gérés par SQLAlchemy, pas par l'app. `onupdate=datetime.utcnow` met à jour `updated_at` automatiquement.

3. **Validation Pydantic v2 stricte** : utilise `model_config = ConfigDict(from_attributes=True)` pour les schémas Read, et `Field(..., min_length=...)` pour les contraintes.

4. **Pas d'auth dans ce bloc** : pas d'authentification, on est en LAN mono-user (cf décision /grilling).

5. **SQLite thread safety** : ajoute `connect_args={"check_same_thread": False}` pour FastAPI (multi-thread).

6. **Pas de migration** : pour la phase A, on utilise `Base.metadata.create_all()`. Pas d'Alembic. Si tu changes un modèle, tu supprimes la DB et tu la recréés. Migration Alembic en phase B.

7. **Services pattern** : mets la logique métier dans `services/`, pas dans les routes. Les routes ne font que de la validation et du transport.

8. **Logs structurés** : utilise `loguru.logger.info(...)` partout, pas `print()`. Format structuré avec contexte (ex: `logger.bind(post_id=post.id).info("Post created")`).

9. **Erreurs HTTP propres** : lève des `HTTPException(status_code=..., detail="...")` depuis les services, pas de retour de tuples d'erreur.

---

## 🔌 Intégration avec les autres blocs

**Ce bloc est le socle** : tous les autres blocs (2, 3, 4, 5, 6, 7) dépendent de ce bloc.

- **Bloc 2 (GrilledMe)** : utilise `persona_service.create()` pour sauvegarder les personas générés
- **Bloc 3 (Génération posts)** : utilise `post_service.create()` et `post_service.update()`
- **Bloc 5 (Extension)** : utilise `post_service.get_pending_to_publish()` (nouveau endpoint à ajouter) et `post_service.update_status()`
- **Bloc 6 (Dashboard)** : consomme tous les endpoints CRUD
- **Bloc 7 (Résilience)** : utilise `post_service.update_status()` pour marquer "failed" après 3 retries

**⚠️ Si tu ajoutes des endpoints ou modèles dans ce bloc, documente-les en haut de ce SPEC pour que les autres blocs sachent quoi utiliser.**

---

## 🚀 Commandes utiles (pour Mathieu)

```bash
cd /data/home-mathieu/saas-rse/bloc-1-backend

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Reset DB (si tu changes un modèle)
rm -f data/saas_rse.db

# Lancer l'API
uvicorn app.main:app --reload --port 8000

# Tests
pytest -v
pytest -v --cov=app  # avec coverage

# Swagger
open http://localhost:8000/docs
```

---

## ❌ Ce que ce bloc ne fait PAS

- ❌ Génération de texte (bloc 3)
- ❌ Génération d'images (blocs 3, 4)
- ❌ Queue, retry, alertes Telegram (bloc 7)
- ❌ Extension Chrome (bloc 5)
- ❌ Dashboard web (bloc 6)
- ❌ GrilledMe (bloc 2)
- ❌ Auth, multi-tenant (phase B)
- ❌ Migrations Alembic (phase B)
- ❌ Scraping analytics (phase B+)

---

## 🤖 Prompt pour Claude Code

```
Lis ce fichier SPEC.md en entier. Implémente le bloc 1 (backend FastAPI + DB)
dans /data/home-mathieu/saas-rse/bloc-1-backend/.

Règles strictes :
1. Demande confirmation avant toute décision d'archi non couverte par le SPEC
2. Les modèles SQLAlchemy du SPEC sont la référence — ne les change pas
3. SQLAlchemy 2 syntaxe (Mapped, mapped_column, etc.) tolérée, mais Column OK
4. Pydantic v2 strict (ConfigDict, Field, model_dump, model_validate)
5. Cascade deletes configurés (persona → plannings → posts)
6. Tests pytest qui couvrent : create, read, list, update, delete, cascade, filtres
7. Services pattern : logique métier dans services/, pas dans routes/
8. Logs loguru avec contexte (bind)
9. .env.example documenté, pas de secrets commités
10. README avec procédure de setup et de test

Quand tu as fini, liste précisément :
- Les fichiers créés
- Les tests qui passent
- Les décisions d'archi prises
- Les limitations connues
- Les instructions de test manuel pour Mathieu
```
