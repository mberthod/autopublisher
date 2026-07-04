import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base


@pytest.fixture
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


COOKIES = [
    {"name": "li_at", "value": "AQEDxxx", "domain": ".linkedin.com", "path": "/", "secure": True, "httpOnly": True},
    {"name": "JSESSIONID", "value": "ajax:123", "domain": ".linkedin.com", "path": "/"},
]


def test_upsert_and_get_session(client):
    r = client.post("/api/v1/sessions", json={"platform": "linkedin", "cookies": COOKIES, "user_agent": "UA/1.0"})
    assert r.status_code == 200
    data = r.json()
    assert data["platform"] == "linkedin"
    assert data["valid"] is True
    assert data["cookie_count"] == 2
    assert "cookies" not in data  # SessionRead n'expose pas les cookies


def test_upsert_replaces_existing(client):
    client.post("/api/v1/sessions", json={"platform": "linkedin", "cookies": COOKIES})
    client.post("/api/v1/sessions", json={"platform": "linkedin", "cookies": COOKIES[:1]})
    r = client.get("/api/v1/sessions")
    li = [s for s in r.json() if s["platform"] == "linkedin"]
    assert len(li) == 1
    assert li[0]["cookie_count"] == 1


def test_get_cookies_endpoint_returns_cookies(client):
    client.post("/api/v1/sessions", json={"platform": "linkedin", "cookies": COOKIES})
    r = client.get("/api/v1/sessions/linkedin/cookies")
    assert r.status_code == 200
    assert len(r.json()["cookies"]) == 2
    assert r.json()["cookies"][0]["name"] == "li_at"


def test_invalidate_session(client):
    client.post("/api/v1/sessions", json={"platform": "linkedin", "cookies": COOKIES})
    r = client.post("/api/v1/sessions/linkedin/invalidate?error=login+redirect")
    assert r.status_code == 200
    assert r.json()["valid"] is False
    assert r.json()["last_error"] == "login redirect"


def test_invalid_platform_rejected(client):
    r = client.post("/api/v1/sessions", json={"platform": "myspace", "cookies": []})
    assert r.status_code == 422


def test_get_missing_session_404(client):
    assert client.get("/api/v1/sessions/instagram").status_code == 404


def test_delete_session(client):
    client.post("/api/v1/sessions", json={"platform": "instagram", "cookies": COOKIES})
    assert client.delete("/api/v1/sessions/instagram").status_code == 204
    assert client.get("/api/v1/sessions/instagram").status_code == 404
