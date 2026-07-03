"""
Test 2 — Persona → génération de Post (bloc-3).
Marqué @slow car il implique le LLM (Ollama) et optionnellement FAL.ai.
"""
import pytest
import httpx


@pytest.mark.slow
@pytest.mark.bloc3
async def test_post_generation_text_only(bloc3_url, test_persona, test_planning):
    """Génère un post text_only via le LLM → texte cohérent renvoyé."""
    async with httpx.AsyncClient(base_url=bloc3_url, timeout=120.0) as client:
        r = await client.post("/api/v1/posts/generate", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "angle_editorial": "Les 5 sources de bruit les plus sous-estimées en location courte durée",
            "format": "text_only",
            "platform": "linkedin",
        })
        assert r.status_code == 200, f"Generate failed: {r.text}"
        post = r.json()

        assert post["text"] is not None
        assert 100 < len(post["text"]) < 4000
        assert post["status"] == "draft"
        assert post["platform"] == "linkedin"
        assert post["format"] == "text_only"

        # Cleanup
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as c1:
            await c1.delete(f"/api/v1/posts/{post['id']}")


@pytest.mark.slow
@pytest.mark.bloc3
async def test_post_generation_respects_persona_bu(bloc3_url, test_persona, test_planning):
    """Le texte généré doit être cohérent avec le BU noisyless."""
    async with httpx.AsyncClient(base_url=bloc3_url, timeout=120.0) as client:
        r = await client.post("/api/v1/posts/generate", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "angle_editorial": "Pourquoi le silence augmente les étoiles sur Airbnb",
            "format": "text_only",
            "platform": "linkedin",
        })
        assert r.status_code == 200
        post = r.json()

        # Le texte doit mentionner des concepts liés à la location ou bruit
        text_lower = post["text"].lower()
        keywords = ["bruit", "silence", "location", "airbnb", "voisin", "acoustique", "locataire"]
        assert any(kw in text_lower for kw in keywords), (
            f"Text doesn't seem relevant to noisyless: {post['text'][:200]}"
        )

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as c1:
            await c1.delete(f"/api/v1/posts/{post['id']}")


@pytest.mark.integration
@pytest.mark.bloc3
async def test_post_generation_with_real_image(bloc3_url, test_persona, test_planning):
    """Génère un post avec image via FAL.ai (coût ~$0.003 par appel)."""
    import os
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run real FAL.ai calls")

    async with httpx.AsyncClient(base_url=bloc3_url, timeout=180.0) as client:
        r = await client.post("/api/v1/posts/generate", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "angle_editorial": "Appartement silencieux = locataires heureux",
            "format": "image",
            "platform": "linkedin",
        })
        assert r.status_code == 200
        post = r.json()

        assert post["text"] is not None
        assert post["image_url"] is not None
        assert post["image_url"].startswith("http")

        # L'image doit être accessible
        async with httpx.AsyncClient(timeout=10.0) as img_client:
            img_r = await img_client.get(post["image_url"])
            assert img_r.status_code == 200
            assert len(img_r.content) > 10_000

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as c1:
            await c1.delete(f"/api/v1/posts/{post['id']}")
