import json
import pytest
from unittest.mock import MagicMock, patch

from app.agents.interrogator_agent import InterrogatorAgent, MATRIX_FIELDS
from tests.conftest import (
    FULL_MATRIX,
    INTERROGATOR_RESPONSE_IN_PROGRESS,
    INTERROGATOR_RESPONSE_COMPLETE,
)


def make_mock_client(response_json: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps(response_json)))
    ]
    return mock_client


def test_start_session_returns_first_question():
    mock_client = make_mock_client(INTERROGATOR_RESPONSE_IN_PROGRESS)
    agent = InterrogatorAgent(client=mock_client)
    result = agent.start_session("noisyless")
    assert "next_question" in result
    assert result["next_question"] is not None
    assert len(result["next_question"]) > 0


def test_start_session_system_prompt_contains_bu():
    mock_client = make_mock_client(INTERROGATOR_RESPONSE_IN_PROGRESS)
    agent = InterrogatorAgent(client=mock_client)
    agent.start_session("afluxo")
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"] if call_args.kwargs else call_args[1]["messages"]
    system_content = messages[0]["content"]
    assert "afluxo" in system_content


def test_process_message_partial_matrix():
    mock_client = make_mock_client(INTERROGATOR_RESPONSE_IN_PROGRESS)
    agent = InterrogatorAgent(client=mock_client)
    matrix = {"cible": "Propriétaires Airbnb"}
    transcript = [{"role": "assistant", "content": "Décrivez votre cible ?", "timestamp": "2026-07-03T10:00:00"}]
    result = agent.process_message("noisyless", matrix, transcript, "Les propriétaires de courte durée")
    assert result["is_complete"] is False
    assert result["next_question"] is not None
    assert 0 <= result["matrix_progress"] <= 1.0


def test_process_message_complete_matrix():
    mock_client = make_mock_client(INTERROGATOR_RESPONSE_COMPLETE)
    agent = InterrogatorAgent(client=mock_client)
    result = agent.process_message("noisyless", FULL_MATRIX, [], "Oui c'est bon")
    assert result["is_complete"] is True
    assert result["next_question"] is None


def test_output_is_valid_json_parseable():
    mock_client = make_mock_client(INTERROGATOR_RESPONSE_IN_PROGRESS)
    agent = InterrogatorAgent(client=mock_client)
    result = agent.start_session("noisyless")
    assert isinstance(result, dict)
    for key in ["matrix_update", "next_question", "is_complete", "reasoning"]:
        assert key in result


def test_extract_json_from_markdown_block():
    agent = InterrogatorAgent(client=MagicMock())
    text = '```json\n{"key": "value", "num": 42}\n```'
    result = agent.extract_json(text)
    assert result == {"key": "value", "num": 42}


def test_extract_json_raises_on_unparseable():
    agent = InterrogatorAgent(client=MagicMock())
    with pytest.raises(ValueError):
        agent.extract_json("this is not json at all")
