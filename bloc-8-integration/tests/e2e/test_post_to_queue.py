"""
Test 3 — Post → Queue (bloc-7).
Valide que la queue accepte des tâches et retourne des stats cohérentes.
"""
import pytest
import httpx


@pytest.mark.bloc7
async def test_queue_enqueue_task(bloc7_url):
    """Enqueue une tâche → id retourné + status pending."""
    async with httpx.AsyncClient(base_url=bloc7_url, timeout=10.0) as client:
        r = await client.post(
            "/api/v1/queue/tasks",
            params={
                "task_type": "publish_post",
                "max_retries": 3,
            },
            json={"post_id": "test-post-id-e2e", "platform": "linkedin"},
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["task_type"] == "publish_post"


@pytest.mark.bloc7
async def test_queue_stats_structure(bloc7_url):
    """GET /queue/stats retourne un objet avec les compteurs attendus."""
    async with httpx.AsyncClient(base_url=bloc7_url, timeout=10.0) as client:
        r = await client.get("/api/v1/queue/stats")
        assert r.status_code == 200
        stats = r.json()
        # stats doit avoir au moins "total" ou des compteurs par statut
        assert isinstance(stats, dict)
        assert len(stats) > 0


@pytest.mark.bloc7
async def test_queue_worker_embedded(bloc7_url):
    """Le readyz indique que le worker est embedded (pas de second process)."""
    async with httpx.AsyncClient(base_url=bloc7_url, timeout=5.0) as client:
        r = await client.get("/readyz")
        assert r.status_code == 200
        data = r.json()
        assert data.get("worker") == "embedded"
        assert data.get("db") == "connected"
