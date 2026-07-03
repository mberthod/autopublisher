import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.models import Base

TEST_DB_URL = "sqlite:///./data/test_generation.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SAMPLE_CHARTE = {
    "ton": "professional_warm",
    "mots_interdits": ["cheap", "disrupt"],
    "emojis_autorises": ["✅", "🔧"],
    "structure_phrases": "courtes, max 20 mots",
    "longueur_cible": 1500,
    "couleurs": ["#FF6B35", "#1A1A1A"],
}


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    # Ajouter generation_metadata si absente (même migration que prod)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE posts ADD COLUMN generation_metadata JSON"))
            conn.commit()
        except Exception:
            pass
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_persona(db):
    from app.models import Persona
    persona = Persona(
        bu="noisyless",
        nom="Propriétaire Airbnb stressé",
        besoins="Réduire les nuisances sonores signalées par les locataires",
        frustrations="Messages hostiles des voisins, notes Airbnb en baisse",
        cible="Propriétaires de locations courte durée, 30-55 ans, zone urbaine",
        charte_branding=SAMPLE_CHARTE,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@pytest.fixture
def sample_planning(db, sample_persona):
    from app.models import Planning
    from datetime import datetime
    planning = Planning(
        persona_id=sample_persona.id,
        date_debut=datetime(2026, 8, 1),
        date_fin=datetime(2026, 8, 31),
    )
    db.add(planning)
    db.commit()
    db.refresh(planning)
    return planning
