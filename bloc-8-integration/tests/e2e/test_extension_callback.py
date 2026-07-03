"""
Test 5 — Extension → Backend callback.
Simule ce que l'extension Chrome envoie après publication.
"""
import pytest
import httpx


@pytest.mark.bloc1
async def test_callback_success_marks_post_published(test_scheduled_post, bloc1_url):
    """L'extension envoie SUCCESS → post passe en published + URL enregistrée."""
    post_id = test_scheduled_post["id"]

    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post(f"/api/v1/tasks/{post_id}/callback", json={
            "status": "success",
            "post_url": "https://www.linkedin.com/posts/test-mathieu-abc123",
            "published_at": "2026-07-03T09:03:42Z",
        })
        assert r.status_code == 200

        r2 = await client.get(f"/api/v1/posts/{post_id}")
        post = r2.json()
        assert post["status"] == "published"
        assert post["published_url"] == "https://www.linkedin.com/posts/test-mathieu-abc123"
        assert post["published_at"] is not None


@pytest.mark.bloc1
async def test_callback_failed_marks_post_failed(test_scheduled_post, bloc1_url):
    """L'extension envoie FAILED → post passe en failed + code d'erreur."""
    post_id = test_scheduled_post["id"]

    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post(f"/api/v1/tasks/{post_id}/callback", json={
            "status": "failed",
            "error_code": "AUTH_REQUIRED",
            "error_message": "Not logged into LinkedIn",
        })
        assert r.status_code == 200

        r2 = await client.get(f"/api/v1/posts/{post_id}")
        post = r2.json()
        assert post["status"] == "failed"
        assert post["error_code"] == "AUTH_REQUIRED"
        assert "LinkedIn" in post["error_message"]


@pytest.mark.bloc1
async def test_callback_unknown_task_returns_404(bloc1_url):
    """Callback sur un task_id inconnu → 404."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/tasks/nonexistent-id/callback", json={
            "status": "failed",
            "error_code": "UNKNOWN",
            "error_message": "test",
        })
        assert r.status_code == 404


@pytest.mark.bloc1
async def test_pending_tasks_endpoint_structure(bloc1_url):
    """GET /tasks/pending retourne le bon format JSON."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.get("/api/v1/tasks/pending")
        assert r.status_code == 200
        data = r.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)


@pytest.mark.bloc1
async def test_selectors_endpoint(bloc1_url):
    """GET /selectors/latest retourne les sélecteurs DOM valides."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.get("/api/v1/selectors/latest")
        assert r.status_code == 200
        data = r.json()
        assert "platforms" in data
        assert "linkedin" in data["platforms"]
        assert "instagram" in data["platforms"]
        assert "btn_open_compose" in data["platforms"]["linkedin"]
