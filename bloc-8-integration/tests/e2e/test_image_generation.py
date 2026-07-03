"""
Test 4 — Génération d'image réelle via FAL.ai.
Skippé par défaut. Coût : ~$0.003 par appel.
"""
import os
import pytest
import httpx


@pytest.mark.integration
async def test_fal_ai_image_generation_real(bloc3_url, test_persona, test_planning):
    """Génère une vraie image via FAL.ai et vérifie qu'elle est accessible."""
    if not os.getenv("RUN_INTEGRATION_TESTS"):
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to enable (costs ~$0.003)")

    async with httpx.AsyncClient(base_url=bloc3_url, timeout=180.0) as client:
        r = await client.post("/api/v1/posts/generate", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "angle_editorial": "Photo minimaliste appartement silencieux",
            "format": "image",
            "platform": "linkedin",
        })
        assert r.status_code == 200
        post = r.json()

        if post.get("image_url") is None:
            pytest.skip("FAL_KEY not configured on server — image generation skipped")

        assert post["image_url"].startswith("http")
        async with httpx.AsyncClient(timeout=15.0) as img_client:
            img_r = await img_client.get(post["image_url"])
            assert img_r.status_code == 200
            assert len(img_r.content) > 10_000, "Image trop petite (<10KB)"

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=5.0) as c1:
            await c1.delete(f"/api/v1/posts/{post['id']}")


@pytest.mark.integration
async def test_carousel_generation_png(bloc3_url):
    """Vérifie que le bloc-4 CLI peut générer des PNGs (intégration locale)."""
    import subprocess
    import json
    from pathlib import Path

    spec = {
        "bu": "noisyless",
        "theme": "modern",
        "slides": [
            {"index": 0, "title": "Test E2E", "body": "Corps du slide de test.", "background_color": "#0D0D0D", "text_color": "#F5F5F5"},
            {"index": 1, "title": "Slide 2", "body": "Deuxième slide.", "background_color": "#0D0D0D", "text_color": "#F5F5F5"},
        ],
        "output_dir": "/tmp/e2e_carousel_test",
    }

    spec_path = "/tmp/e2e_carousel_spec.json"
    Path(spec_path).write_text(json.dumps(spec))

    result = subprocess.run(
        ["/data/home-mathieu/saas-rse/bloc-4-carrousels/.venv/bin/python",
         "-m", "app.main", "--spec", spec_path],
        cwd="/data/home-mathieu/saas-rse/bloc-4-carrousels",
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        p = Path(line.strip())
        assert p.exists()
        assert p.stat().st_size > 5_000
