"""
Test de la chaîne Persona → Planning → Post → PATCH (status).
Valide le schéma de données end-to-end sur bloc-1.
"""
import pytest
import httpx


@pytest.mark.bloc1
async def test_persona_crud_roundtrip(bloc1_url):
    """Persona créé, lu, supprimé — toutes les données sont cohérentes."""
    payload = {
        "bu": "afluxo",
        "nom": "Test Persona Afluxo",
        "besoins": "Mesurer les performances IoT en temps réel, réduire la latence",
        "frustrations": "Dashboards lents, données non fiables en environnement réel",
        "cible": "Ingénieurs R&D en systèmes embarqués, PME industrielles françaises",
        "charte_branding": {
            "ton": "technique et précis",
            "mots_interdits": ["révolutionnaire", "disruptif"],
            "longueur_cible": 1200,
        },
    }
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        # Create
        r = await client.post("/api/v1/personas", json=payload)
        assert r.status_code == 201
        persona = r.json()
        assert persona["bu"] == "afluxo"
        assert persona["id"] is not None

        pid = persona["id"]

        # Read
        r2 = await client.get(f"/api/v1/personas/{pid}")
        assert r2.status_code == 200
        assert r2.json()["nom"] == "Test Persona Afluxo"

        # List
        r3 = await client.get("/api/v1/personas")
        assert r3.status_code == 200
        assert any(p["id"] == pid for p in r3.json())

        # Delete
        r4 = await client.delete(f"/api/v1/personas/{pid}")
        assert r4.status_code == 204

        # Confirm deleted
        r5 = await client.get(f"/api/v1/personas/{pid}")
        assert r5.status_code == 404


@pytest.mark.bloc1
async def test_full_chain_persona_to_post(bloc1_url, test_persona, test_planning):
    """Persona + Planning existants → crée un Post → PATCH status → vérifie."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        # Create post
        r = await client.post("/api/v1/posts", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "platform": "instagram",
            "format": "carousel",
            "angle_editorial": "3 métriques IoT que les retailers sous-estiment",
        })
        assert r.status_code == 201
        post = r.json()
        post_id = post["id"]
        assert post["status"] == "draft"
        assert post["platform"] == "instagram"
        assert post["format"] == "carousel"

        try:
            # PATCH text + schedule
            r2 = await client.patch(f"/api/v1/posts/{post_id}", json={
                "text": "3 métriques IoT clés #Afluxo #IoT #retail",
                "status": "validated",
                "scheduled_for": "2026-07-10T10:00:00",
            })
            assert r2.status_code == 200
            updated = r2.json()
            assert updated["status"] == "validated"
            assert updated["text"] == "3 métriques IoT clés #Afluxo #IoT #retail"

            # Verify via GET
            r3 = await client.get(f"/api/v1/posts/{post_id}")
            assert r3.json()["status"] == "validated"
        finally:
            await client.delete(f"/api/v1/posts/{post_id}")


@pytest.mark.bloc1
async def test_scheduled_for_date_filter(bloc1_url, test_persona, test_planning):
    """GET /posts?scheduled_for_date=YYYY-MM-DD filtre correctement."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/posts", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "platform": "linkedin",
            "format": "text_only",
            "angle_editorial": "Test filtre date",
        })
        post = r.json()
        post_id = post["id"]

        try:
            # Set a specific date
            await client.patch(f"/api/v1/posts/{post_id}", json={
                "scheduled_for": "2026-08-15T08:00:00",
                "status": "scheduled",
            })

            # Filter by that date → should find it
            r2 = await client.get("/api/v1/posts", params={"scheduled_for_date": "2026-08-15"})
            assert r2.status_code == 200
            ids = [p["id"] for p in r2.json()]
            assert post_id in ids

            # Filter by different date → should NOT find it
            r3 = await client.get("/api/v1/posts", params={"scheduled_for_date": "2026-08-16"})
            ids2 = [p["id"] for p in r3.json()]
            assert post_id not in ids2
        finally:
            await client.delete(f"/api/v1/posts/{post_id}")


@pytest.mark.bloc1
async def test_post_delete_cascade(bloc1_url, test_persona, test_planning):
    """Suppression d'un post → 404 sur le get."""
    async with httpx.AsyncClient(base_url=bloc1_url, timeout=10.0) as client:
        r = await client.post("/api/v1/posts", json={
            "planning_id": test_planning["id"],
            "persona_id": test_persona["id"],
            "platform": "linkedin",
            "format": "text_only",
            "angle_editorial": "Test suppression cascade",
        })
        post_id = r.json()["id"]
        await client.delete(f"/api/v1/posts/{post_id}")
        r2 = await client.get(f"/api/v1/posts/{post_id}")
        assert r2.status_code == 404
