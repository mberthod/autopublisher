"""
Test 1 — GrilledMe → Persona.
Marqué @slow car il implique de vrais appels LLM (Ollama, ~30-60s par question).
"""
import pytest
import httpx


@pytest.mark.slow
@pytest.mark.bloc2
async def test_grillme_session_start(bloc2_url):
    """Démarrer une session → session_id + première question renvoyée."""
    async with httpx.AsyncClient(base_url=bloc2_url, timeout=15.0) as client:
        r = await client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"})
        assert r.status_code == 201
        data = r.json()
        assert "session_id" in data
        assert "first_question" in data
        assert len(data["first_question"]) > 10


@pytest.mark.slow
@pytest.mark.bloc2
async def test_grillme_full_conversation_creates_persona(bloc2_url):
    """
    Conversation simulée (10 réponses courtes) → Persona créé en BDD.
    Utilise le vrai LLM (Ollama) — peut prendre 2-5 min.
    """
    async with httpx.AsyncClient(base_url=bloc2_url, timeout=120.0) as client:
        # 1. Start session
        r = await client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"})
        assert r.status_code == 201
        session_id = r.json()["session_id"]

        # 2. Enchaîner des réponses
        answers = [
            "Propriétaires de locations courte durée en France, 1 à 5 biens Airbnb",
            "Maintenir une note 4.8 étoiles, éviter les plaintes de voisins",
            "Nuisances sonores la nuit, remboursements causés par des locataires bruyants",
            "Solutions acoustiques concrètes, rapides à installer soi-même",
            "Ton chaleureux mais expert, jamais vendeur ni condescendant",
            "Éviter les termes : cheap, disruptif, révolutionnaire",
            "Emojis techniques uniquement : 🔧 ✅ 📊",
            "Posts LinkedIn de 1500 caractères max, phrases courtes",
            "Public cible : propriétaires 35-55 ans, CSP+, sensibles à la rentabilité",
            "C'est parfait, je valide ce profil",
        ]

        is_complete = False
        for answer in answers:
            r = await client.post(
                f"/api/v1/grillme/sessions/{session_id}/messages",
                json={"user_message": answer},
            )
            assert r.status_code == 200, f"Message failed: {r.text}"
            data = r.json()
            if data.get("is_complete"):
                is_complete = True
                break

        # 3. Récupérer le persona
        r = await client.get(f"/api/v1/grillme/sessions/{session_id}/persona")
        assert r.status_code == 200, f"Persona not found: {r.text}"
        persona_data = r.json()
        assert "persona" in persona_data
        persona = persona_data["persona"]

        # 4. Vérifier la qualité minimale
        assert persona["bu"] == "noisyless"
        assert len(persona["besoins"]) > 20, "besoins trop court"
        assert len(persona["frustrations"]) > 20, "frustrations trop court"
        assert len(persona["cible"]) > 20, "cible trop court"
        assert isinstance(persona["charte_branding"], dict)
        assert "ton" in persona["charte_branding"]
