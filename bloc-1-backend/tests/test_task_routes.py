import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.main import app
from app.db import get_db, init_db
from app.models import Base, Persona, Planning, Post


_Session = None


@pytest.fixture
def client(tmp_path):
    global _Session
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    _Session = Session

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


@pytest.fixture
def seed_instagram_post(client):
    db = _Session()
    db.add(Post(
        id="post_ig", planning_id="pl1", persona_id="p1",
        platform="instagram", format="image", angle_editorial="test ig",
        text="Hello Instagram!", image_url="http://x/img.png", status="scheduled",
        scheduled_for=datetime(2025, 1, 1),
    ))
    db.commit()
    db.close()


def _set_legacy_page_url(client, persona_id, url):
    db = _Session()
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    persona.linkedin_page_url = url
    db.commit()
    db.close()


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


def test_pending_task_company_page(client):
    # Account page entreprise LinkedIn → la task porte page_url + publish_as_name
    r = client.post("/api/v1/accounts", json={
        "persona_id": "p1",
        "platform": "linkedin",
        "kind": "company_page",
        "page_url": "https://www.linkedin.com/company/noisyless/admin/",
        "identity_name": "Noisyless",
    })
    assert r.status_code == 201
    r2 = client.get("/api/v1/tasks/pending")
    t = r2.json()["tasks"][0]
    assert t["page_url"] == "https://www.linkedin.com/company/noisyless/admin/"
    assert t["publish_as_name"] == "Noisyless"
    assert t["publish_via"] == "linkedin"
    assert t["account_kind"] == "company_page"


def test_pending_task_instagram_business_routes_meta_suite(client, seed_instagram_post):
    r = client.post("/api/v1/accounts", json={
        "persona_id": "p1",
        "platform": "instagram",
        "kind": "business_account",
        "page_url": "https://www.instagram.com/noisyless/",
        "identity_name": "noisyless",
        "asset_id": "1234567890",
    })
    assert r.status_code == 201
    tasks = client.get("/api/v1/tasks/pending").json()["tasks"]
    t = next(x for x in tasks if x["platform"] == "instagram")
    assert t["publish_via"] == "meta_suite"
    assert t["placements"] == ["instagram"]
    assert t["asset_id"] == "1234567890"


def test_pending_task_instagram_personal_stays_on_instagram(client, seed_instagram_post):
    r = client.post("/api/v1/accounts", json={
        "persona_id": "p1",
        "platform": "instagram",
        "kind": "personal",
        "page_url": "https://www.instagram.com/mathieu/",
    })
    assert r.status_code == 201
    tasks = client.get("/api/v1/tasks/pending").json()["tasks"]
    t = next(x for x in tasks if x["platform"] == "instagram")
    assert t["publish_via"] == "instagram"
    assert t["placements"] == []


def test_pending_task_legacy_fallback_without_account(client):
    # Persona sans Account mais avec l'ancien champ linkedin_page_url → fallback
    _set_legacy_page_url(client, "p1", "https://www.linkedin.com/company/legacy/admin/")
    t = client.get("/api/v1/tasks/pending").json()["tasks"][0]
    assert t["page_url"] == "https://www.linkedin.com/company/legacy/admin/"
    assert t["publish_as_name"] == "Noisyless"
    assert t["publish_via"] == "linkedin"


def test_pending_task_selectors_version_is_latest(client):
    from app.api.selector_routes import LATEST_VERSION
    r = client.get("/api/v1/tasks/pending")
    assert r.json()["tasks"][0]["selectors_version"] == LATEST_VERSION


def test_selectors_latest(client):
    r = client.get("/api/v1/selectors/latest")
    assert r.status_code == 200
    data = r.json()
    assert "platforms" in data
    assert "linkedin" in data["platforms"]
    assert "instagram" in data["platforms"]


def test_selectors_v4_identity_keys(client):
    r = client.get("/api/v1/selectors/latest")
    li = r.json()["platforms"]["linkedin"]
    for key in ("identity_picker_trigger", "identity_option", "actor_name", "success_toast_link"):
        assert key in li, f"missing {key} in latest linkedin selectors"


def test_selectors_old_versions_still_served(client):
    for version in ("2026-07-01-v1", "2026-07-04-v2", "2026-07-04-v3", "2026-07-04-v4"):
        assert client.get(f"/api/v1/selectors/{version}").status_code == 200


def test_selectors_v5_meta_suite(client):
    ms = client.get("/api/v1/selectors/latest").json()["platforms"]["meta_suite"]
    for key in ("account_switcher_trigger", "active_account_name", "btn_create_post",
                "placement_option_facebook", "placement_option_instagram",
                "text_editor", "file_input", "btn_publish", "success_indicator"):
        assert key in ms, f"missing {key} in meta_suite selectors"


def test_selectors_by_version(client):
    r = client.get("/api/v1/selectors/2026-07-01-v1")
    assert r.status_code == 200


def test_selectors_unknown_version(client):
    r = client.get("/api/v1/selectors/9999-badversion")
    assert r.status_code == 404
