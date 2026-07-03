import json
import pytest
from unittest.mock import MagicMock

from app.agents.interrogator_agent import InterrogatorAgent
from app.agents.strategist_agent import StrategistAgent
from app.services import grillme_service
from tests.conftest import (
    INTERROGATOR_RESPONSE_IN_PROGRESS,
    INTERROGATOR_RESPONSE_COMPLETE,
    STRATEGIST_RESPONSE,
    FULL_MATRIX,
)


def make_interrogator_mock(response: dict) -> InterrogatorAgent:
    agent = InterrogatorAgent.__new__(InterrogatorAgent)
    agent.start_session = MagicMock(return_value=response)
    agent.process_message = MagicMock(return_value=response)
    return agent


def make_strategist_mock(response: dict) -> StrategistAgent:
    agent = StrategistAgent.__new__(StrategistAgent)
    agent.create_persona = MagicMock(return_value=response)
    return agent


def test_post_sessions_creates_session(client, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    response = client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"})
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert "first_question" in data
    assert len(data["first_question"]) > 0


def test_post_sessions_invalid_bu(client):
    response = client.post("/api/v1/grillme/sessions", json={"bu": "unknown"})
    assert response.status_code == 422


def test_post_message_returns_next_question(client, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    session = client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"}).json()

    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    response = client.post(
        f"/api/v1/grillme/sessions/{session['session_id']}/messages",
        json={"user_message": "Je cible les propriétaires Airbnb en zone urbaine"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "next_question" in data
    assert "matrix_progress" in data
    assert "is_complete" in data
    assert data["is_complete"] is False


def test_post_message_not_found(client):
    response = client.post(
        "/api/v1/grillme/sessions/nonexistent/messages",
        json={"user_message": "hello"},
    )
    assert response.status_code == 404


def test_full_conversation_produces_persona(client, db, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    session = client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"}).json()
    session_id = session["session_id"]

    complete_interrogator = make_interrogator_mock(INTERROGATOR_RESPONSE_COMPLETE)
    complete_strategist = make_strategist_mock(STRATEGIST_RESPONSE)

    mocker.patch("app.services.grillme_service.InterrogatorAgent", return_value=complete_interrogator)
    mocker.patch("app.services.grillme_service.StrategistAgent", return_value=complete_strategist)

    response = client.post(
        f"/api/v1/grillme/sessions/{session_id}/messages",
        json={"user_message": "Tout est complet, voici ma charte finale"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_complete"] is True
    assert data["next_question"] is None


def test_get_persona_after_completion(client, db, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    session = client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"}).json()
    session_id = session["session_id"]

    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_COMPLETE),
    )
    mocker.patch(
        "app.services.grillme_service.StrategistAgent",
        return_value=make_strategist_mock(STRATEGIST_RESPONSE),
    )
    client.post(f"/api/v1/grillme/sessions/{session_id}/messages", json={"user_message": "ok"})

    response = client.get(f"/api/v1/grillme/sessions/{session_id}/persona")
    assert response.status_code == 200
    data = response.json()
    assert "persona" in data
    assert "transcript" in data
    assert data["persona"]["bu"] == "noisyless"
    assert data["persona"]["nom"] == STRATEGIST_RESPONSE["nom"]


def test_get_persona_before_completion(client, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    session = client.post("/api/v1/grillme/sessions", json={"bu": "noisyless"}).json()
    response = client.get(f"/api/v1/grillme/sessions/{session['session_id']}/persona")
    assert response.status_code == 400


def test_matrix_progress_increases_with_messages(client, db, mocker):
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(INTERROGATOR_RESPONSE_IN_PROGRESS),
    )
    session = client.post("/api/v1/grillme/sessions", json={"bu": "afluxo"}).json()

    progressive_response = {
        **INTERROGATOR_RESPONSE_IN_PROGRESS,
        "matrix_update": {"cible": "...", "besoins": "..."},
        "matrix_progress": 0.5,
    }
    mocker.patch(
        "app.services.grillme_service.InterrogatorAgent",
        return_value=make_interrogator_mock(progressive_response),
    )
    response = client.post(
        f"/api/v1/grillme/sessions/{session['session_id']}/messages",
        json={"user_message": "Voici ma cible et mes besoins"},
    )
    assert response.status_code == 200
    assert response.json()["matrix_progress"] >= 0.25
