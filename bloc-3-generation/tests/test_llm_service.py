import pytest
from unittest.mock import MagicMock

from app.services.llm_service import LLMService, SYSTEM_PROMPT_TEMPLATE
from tests.conftest import SAMPLE_CHARTE


def make_mock_client(text_response: str, tokens_in: int = 500, tokens_out: int = 300):
    mock = MagicMock()
    mock.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=text_response))
    ]
    mock.chat.completions.create.return_value.usage = MagicMock(
        prompt_tokens=tokens_in, completion_tokens=tokens_out
    )
    return mock


def make_persona(bu="noisyless"):
    p = MagicMock()
    p.bu = bu
    p.id = "persona-test-id"
    p.cible = "Propriétaires Airbnb, 30-55 ans"
    p.besoins = "Réduire les nuisances sonores"
    p.frustrations = "Notes Airbnb en baisse"
    p.charte_branding = SAMPLE_CHARTE
    return p


def test_generate_text_returns_non_empty(db):
    long_text = "A" * 1400
    mock_client = make_mock_client(long_text)
    svc = LLMService(client=mock_client)
    persona = make_persona()
    result = svc.generate_text(persona, "douleur bruit Airbnb", "linkedin", "text_only")
    assert result["text"]
    assert len(result["text"]) > 0


def test_generate_text_linkedin_length_respected(db):
    text = "Votre locataire vous a encore envoyé un message à 2h du matin. " * 20  # ~1300 chars
    mock_client = make_mock_client(text)
    svc = LLMService(client=mock_client)
    result = svc.generate_text(make_persona(), "bruit nocturne", "linkedin", "text_only")
    assert len(result["text"]) < 2500


def test_generate_text_system_prompt_contains_persona_bu():
    mock_client = make_mock_client("Post content")
    svc = LLMService(client=mock_client)
    persona = make_persona(bu="afluxo")
    svc.generate_text(persona, "énergie verte", "linkedin", "text_only")

    call_args = mock_client.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    system = messages[0]["content"]
    assert "afluxo" in system


def test_generate_text_system_prompt_contains_mots_interdits():
    mock_client = make_mock_client("Post content")
    svc = LLMService(client=mock_client)
    svc.generate_text(make_persona(), "angle test", "linkedin", "text_only")

    messages = mock_client.chat.completions.create.call_args[1]["messages"]
    system = messages[0]["content"]
    assert "cheap" in system
    assert "disrupt" in system


def test_generate_text_returns_token_counts():
    mock_client = make_mock_client("Some text", tokens_in=800, tokens_out=250)
    svc = LLMService(client=mock_client)
    result = svc.generate_text(make_persona(), "angle", "instagram", "text_only")
    assert result["tokens_in"] == 800
    assert result["tokens_out"] == 250


def test_generate_text_instagram_uses_shorter_length_prompt():
    mock_client = make_mock_client("Post court")
    svc = LLMService(client=mock_client)
    svc.generate_text(make_persona(), "angle", "instagram", "text_only")

    messages = mock_client.chat.completions.create.call_args[1]["messages"]
    user_msg = messages[1]["content"]
    assert "200" in user_msg or "500" in user_msg
