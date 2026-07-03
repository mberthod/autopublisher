"""
Test 0 — Health checks sur tous les blocs.
Ces tests passent en CI sans dépendances externes.
"""
import pytest
import httpx


@pytest.mark.bloc1
async def test_bloc1_backend_up(bloc1_url):
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=5.0) as client:
        r = await client.get("/api/v1/posts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.bloc2
async def test_bloc2_grillme_up(bloc2_url):
    async with httpx.AsyncClient(base_url=bloc2_url, timeout=5.0) as client:
        # Session creation returns 201 when service is up
        r = await client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"})
        assert r.status_code == 201
        assert "session_id" in r.json()
        assert "first_question" in r.json()


@pytest.mark.bloc7
async def test_bloc7_resilience_up(bloc7_url):
    async with httpx.AsyncClient(base_url=bloc7_url, timeout=5.0) as client:
        r = await client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.bloc7
async def test_bloc7_queue_stats(bloc7_url):
    async with httpx.AsyncClient(base_url=bloc7_url, timeout=5.0) as client:
        r = await client.get("/api/v1/queue/stats")
        assert r.status_code == 200
        stats = r.json()
        assert "total" in stats or "pending" in stats


@pytest.mark.bloc3
async def test_bloc3_generation_up(bloc3_url):
    async with httpx.AsyncClient(base_url=bloc3_url, timeout=5.0) as client:
        r = await client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
