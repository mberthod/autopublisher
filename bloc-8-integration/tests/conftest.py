"""
Fixtures partagées pour les tests E2E.
Chaque fixture crée des données via l'API et les nettoie après le test.
"""
import pytest
import httpx
from datetime import datetime

BASE = {
    "bloc1": "http://localhost:8000",
    "bloc2": "http://localhost:8001",
    "bloc3": "http://localhost:8003",
    "bloc7": "http://localhost:8002",
}

SAMPLE_PERSONA = {
    "bu": "noisyless",
    "nom": "Test — Propriétaire location courte durée",
    "besoins": "Réduire les plaintes de voisins, maintenir une note 4.8+ sur Airbnb",
    "frustrations": "Les nuisances sonores la nuit, les remboursements causés par le bruit",
    "cible": "Propriétaires français de 1 à 5 biens en location courte durée",
    "charte_branding": {
        "ton": "expert mais accessible",
        "mots_interdits": ["cheap", "disrupt", "révolutionnaire"],
        "longueur_cible": 1500,
        "emojis": ["✅", "🔧", "📊"],
    },
}


@pytest.fixture(scope="session")
def bloc1_url():
    return BASE["bloc1"]


@pytest.fixture(scope="session")
def bloc2_url():
    return BASE["bloc2"]


@pytest.fixture(scope="session")
def bloc7_url():
    return BASE["bloc7"]


@pytest.fixture(scope="session")
def bloc3_url():
    return BASE["bloc3"]


@pytest.fixture
async def test_persona(bloc1_url):
    """Crée un persona de test et le supprime après le test."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/personas", json=SAMPLE_PERSONA)
        assert r.status_code == 201, f"Failed to create persona: {r.text}"
        persona = r.json()

    yield persona

    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        await client.delete(f"/api/v1/personas/{persona['id']}")


@pytest.fixture
async def test_planning(bloc1_url, test_persona):
    """Crée un planning de test lié au persona de test."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/plannings", json={
            "persona_id": test_persona["id"],
            "date_debut": "2026-01-01T00:00:00",
            "date_fin": "2026-12-31T00:00:00",
        })
        assert r.status_code == 201, f"Failed to create planning: {r.text}"
        planning = r.json()

    yield planning

    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        await client.delete(f"/api/v1/plannings/{planning['id']}")


@pytest.fixture
async def test_post(bloc1_url, test_persona, test_planning):
    """Crée un post de test (status=draft)."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/posts", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "platform": "linkedin",
            "format": "text_only",
            "angle_editorial": "Test E2E — Les 5 sources de bruit sous-estimées",
        })
        assert r.status_code == 201, f"Failed to create post: {r.text}"
        post = r.json()

    yield post

    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        await client.delete(f"/api/v1/posts/{post['id']}")


@pytest.fixture
async def test_scheduled_post(bloc1_url, test_post):
    """Passe un post en status=scheduled."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.patch(f"/api/v1/posts/{test_post['id']}", json={
            "status": "scheduled",
            "text": "Post de test E2E généré automatiquement. #RSE #NoisyLess",
            "scheduled_for": "2026-07-03T09:00:00",
        })
        assert r.status_code == 200
        yield r.json()
