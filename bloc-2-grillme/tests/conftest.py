import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.models import Base

TEST_DB_URL = "sqlite:///./data/test_grillme.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
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


FULL_MATRIX = {
    "cible": "Propriétaires de locations courte durée en zone urbaine (Paris, Lyon), 1-5 biens, 30-55 ans",
    "besoins": "Réduire les nuisances sonores; maintenir note 4.8+; éviter plaintes voisins",
    "frustrations": "Messages hostiles des voisins; demandes de remboursement; baisse classement Airbnb",
    "charte": {
        "ton": "professional_warm",
        "mots_interdits": ["cheap", "disrupt"],
        "emojis": ["✅", "🔧"],
    },
}

INTERROGATOR_RESPONSE_IN_PROGRESS = {
    "matrix_update": {"cible": "Propriétaires Airbnb urbains, 30-55 ans"},
    "next_question": "Quels sont les principaux besoins de votre cible ?",
    "is_complete": False,
    "reasoning": "La cible est renseignée, passons aux besoins",
    "matrix_progress": 0.25,
}

INTERROGATOR_RESPONSE_COMPLETE = {
    "matrix_update": {"charte": {"ton": "professional_warm", "mots_interdits": ["cheap"]}},
    "next_question": None,
    "is_complete": True,
    "reasoning": "La matrice est complète",
    "matrix_progress": 1.0,
}

STRATEGIST_RESPONSE = {
    "nom": "Propriétaire Airbnb stressé par le bruit",
    "besoins": "Réduire nuisances; maintenir note 4.8+; éviter litiges",
    "frustrations": "Voisins mécontents; remboursements; déclassement Airbnb",
    "cible": "Propriétaires de locations courte durée en zone urbaine, 30-55 ans, sensibles à la qualité",
    "charte_branding": {
        "ton": "professional_warm",
        "mots_interdits": ["cheap", "disrupt"],
        "emojis_autorises": ["✅", "🔧", "📊"],
        "structure_phrases": "courtes, max 20 mots, voix active",
        "longueur_cible": 1500,
        "couleurs": ["#FF6B35", "#1A1A1A"],
    },
    "transcript_summary": "5 échanges : cible validée, besoins détaillés, charte confirmée",
}
