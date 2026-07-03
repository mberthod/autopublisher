import json
import pytest
from unittest.mock import MagicMock

from app.agents.strategist_agent import StrategistAgent
from tests.conftest import FULL_MATRIX, STRATEGIST_RESPONSE


def make_mock_client(response_json: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps(response_json)))
    ]
    return mock_client


def test_create_persona_returns_structured_persona():
    mock_client = make_mock_client(STRATEGIST_RESPONSE)
    agent = StrategistAgent(client=mock_client)
    result = agent.create_persona("noisyless", FULL_MATRIX)
    assert isinstance(result, dict)


def test_create_persona_has_all_required_fields():
    mock_client = make_mock_client(STRATEGIST_RESPONSE)
    agent = StrategistAgent(client=mock_client)
    result = agent.create_persona("noisyless", FULL_MATRIX)
    required = ["nom", "besoins", "frustrations", "cible", "charte_branding"]
    for field in required:
        assert field in result, f"Missing field: {field}"


def test_create_persona_charte_branding_complete():
    mock_client = make_mock_client(STRATEGIST_RESPONSE)
    agent = StrategistAgent(client=mock_client)
    result = agent.create_persona("noisyless", FULL_MATRIX)
    charte = result["charte_branding"]
    required_branding = ["ton", "mots_interdits", "emojis_autorises", "structure_phrases", "longueur_cible", "couleurs"]
    for field in required_branding:
        assert field in charte, f"Missing branding field: {field}"


def test_create_persona_system_prompt_contains_bu():
    mock_client = make_mock_client(STRATEGIST_RESPONSE)
    agent = StrategistAgent(client=mock_client)
    agent.create_persona("afluxo", FULL_MATRIX)
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][1]
    system_content = messages[0]["content"]
    assert "afluxo" in system_content


def test_create_persona_raises_on_missing_fields():
    incomplete_response = {"nom": "Test", "besoins": "ok"}
    mock_client = make_mock_client(incomplete_response)
    agent = StrategistAgent(client=mock_client)
    with pytest.raises(ValueError, match="missing fields"):
        agent.create_persona("noisyless", FULL_MATRIX)


def test_create_persona_raises_on_missing_branding():
    incomplete_response = {
        **STRATEGIST_RESPONSE,
        "charte_branding": {"ton": "professional_warm"},
    }
    mock_client = make_mock_client(incomplete_response)
    agent = StrategistAgent(client=mock_client)
    with pytest.raises(ValueError, match="charte_branding missing fields"):
        agent.create_persona("noisyless", FULL_MATRIX)


def test_create_persona_saved_to_db(db):
    from app.services import persona_service

    mock_client = make_mock_client(STRATEGIST_RESPONSE)
    agent = StrategistAgent(client=mock_client)
    persona_data = agent.create_persona("noisyless", FULL_MATRIX)

    persona = persona_service.create(
        db=db,
        bu="noisyless",
        nom=persona_data["nom"],
        besoins=persona_data["besoins"],
        frustrations=persona_data["frustrations"],
        cible=persona_data["cible"],
        charte_branding=persona_data["charte_branding"],
    )

    from app.models import Persona
    saved = db.query(Persona).filter(Persona.id == persona.id).first()
    assert saved is not None
    assert saved.nom == STRATEGIST_RESPONSE["nom"]
    assert saved.bu == "noisyless"
