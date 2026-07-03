import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.main import app
from app.db import get_db, init_db
from app.models import Base, Persona, Planning, Post


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
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
        # seed: persona + planning + scheduled post
        db = Session()
        persona = Persona(
            id="p1", bu="noisyless", nom="Test", besoins="b", frustrations="f",
            cible="c", charte_branding={}
        )
        db.add(persona)
        planning = Planning(
            id="pl1", persona_id="p1",
            date_debut=datetime(2026, 1, 1), date_fin=datetime(2026, 12, 31)
        )
        db.add(planning)
        post = Post(
            id="post1", planning_id="pl1", persona_id="p1",
            platform="linkedin", format="text_only", angle_editorial="test",
            text="Hello LinkedIn!", status="scheduled",
            scheduled_for=datetime(2025, 1, 1),  # past → due
        )
        db.add(post)
        post2 = Post(
            id="post2", planning_id="pl1", persona_id="p1",
            platform="linkedin", format="text_only", angle_editorial="test",
            text="Draft post", status="draft",
        )
        db.add(post2)
        db.commit()
        db.close()
        yield c

    app.dependency_overrides.clear()


def test_get_pending_tasks_returns_scheduled(client):
    r = client.get("/api/v1/tasks/pending")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tasks"]) == 1
    t = data["tasks"][0]
    assert t["task_id"] == "post1"
    assert t["platform"] == "linkedin"
    assert t["text"] == "Hello LinkedIn!"


def test_get_pending_excludes_drafts(client):
    r = client.get("/api/v1/tasks/pending")
    ids = [t["task_id"] for t in r.json()["tasks"]]
    assert "post2" not in ids


def test_callback_success(client):
    r = client.post("/api/v1/tasks/post1/callback", json={
        "status": "success",
        "post_url": "https://linkedin.com/posts/abc",
        "published_at": "2026-07-03T09:00:00Z",
    })
    assert r.status_code == 200
    # Verify post updated
    r2 = client.get("/api/v1/posts/post1")
    assert r2.json()["status"] == "published"
    assert r2.json()["published_url"] == "https://linkedin.com/posts/abc"


def test_callback_failed(client):
    r = client.post("/api/v1/tasks/post1/callback", json={
        "status": "failed",
        "error_code": "AUTH_REQUIRED",
        "error_message": "Not logged in",
    })
    assert r.status_code == 200
    r2 = client.get("/api/v1/posts/post1")
    assert r2.json()["status"] == "failed"
    assert r2.json()["error_code"] == "AUTH_REQUIRED"


def test_callback_not_found(client):
    r = client.post("/api/v1/tasks/nope/callback", json={
        "status": "failed", "error_code": "UNKNOWN", "error_message": "x"
    })
    assert r.status_code == 404


def test_selectors_latest(client):
    r = client.get("/api/v1/selectors/latest")
    assert r.status_code == 200
    data = r.json()
    assert "platforms" in data
    assert "linkedin" in data["platforms"]
    assert "instagram" in data["platforms"]


def test_selectors_by_version(client):
    r = client.get("/api/v1/selectors/2026-07-01-v1")
    assert r.status_code == 200


def test_selectors_unknown_version(client):
    r = client.get("/api/v1/selectors/9999-badversion")
    assert r.status_code == 404
