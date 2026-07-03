import pytest
from unittest.mock import MagicMock

from app.models import Post
from app.services.image_service import ImageService
from app.services.llm_service import LLMService
from tests.conftest import SAMPLE_CHARTE


def make_llm_mock(text="Voici un post LinkedIn sur les nuisances sonores. " * 20):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=text))
    ]
    mock_client.chat.completions.create.return_value.usage = MagicMock(
        prompt_tokens=600, completion_tokens=280
    )
    return LLMService(client=mock_client)


def make_image_mock(url="http://192.168.0.176:8003/static/posts/test.png"):
    svc = ImageService.__new__(ImageService)
    svc.generate = MagicMock(return_value=url)
    return svc


def test_generate_text_only_post(client, sample_persona, sample_planning, mocker):
    mocker.patch("app.services.post_service.LLMService", return_value=make_llm_mock())
    mocker.patch("app.services.post_service.ImageService", return_value=make_image_mock(None))

    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances sonores nocturnes",
        "format": "text_only",
        "platform": "linkedin",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
    assert len(data["text"]) > 0
    assert data["image_url"] is None
    assert "post_id" in data
    assert "generation_metadata" in data


def test_generate_image_post(client, sample_persona, sample_planning, mocker):
    mocker.patch("app.services.post_service.LLMService", return_value=make_llm_mock())
    mocker.patch("app.services.post_service.ImageService", return_value=make_image_mock())

    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances sonores nocturnes",
        "format": "image",
        "platform": "instagram",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
    assert data["image_url"] is not None
    assert data["generation_metadata"]["image_provider"] == "fal.ai"


def test_post_draft_persisted_in_db(client, db, sample_persona, sample_planning, mocker):
    mocker.patch("app.services.post_service.LLMService", return_value=make_llm_mock())
    mocker.patch("app.services.post_service.ImageService", return_value=make_image_mock(None))

    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances sonores nocturnes",
        "format": "text_only",
        "platform": "linkedin",
    })
    assert response.status_code == 200
    post_id = response.json()["post_id"]

    post = db.query(Post).filter(Post.id == post_id).first()
    assert post is not None
    assert post.status == "draft"
    assert post.text is not None
    assert post.created_at is not None
    assert post.generation_metadata is not None
    assert "llm_model" in post.generation_metadata


def test_generation_metadata_contains_required_fields(client, sample_persona, sample_planning, mocker):
    mocker.patch("app.services.post_service.LLMService", return_value=make_llm_mock())
    mocker.patch("app.services.post_service.ImageService", return_value=make_image_mock(None))

    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances sonores nocturnes",
        "format": "text_only",
        "platform": "linkedin",
    })
    meta = response.json()["generation_metadata"]
    assert "llm_model" in meta
    assert "llm_tokens_in" in meta
    assert "llm_tokens_out" in meta
    assert "generation_time_ms" in meta
    assert meta["generation_time_ms"] >= 0


def test_invalid_persona_returns_404(client, sample_planning, mocker):
    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": "nonexistent",
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances",
        "format": "text_only",
        "platform": "linkedin",
    })
    assert response.status_code == 404


def test_invalid_planning_returns_404(client, sample_persona, mocker):
    response = client.post("/api/v1/posts/generate", json={
        "planning_id": "nonexistent",
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances",
        "format": "text_only",
        "platform": "linkedin",
    })
    assert response.status_code == 404


def test_carousel_format_sets_provider_playwright(client, sample_persona, sample_planning, mocker):
    mocker.patch("app.services.post_service.LLMService", return_value=make_llm_mock())
    mocker.patch("app.services.post_service.ImageService", return_value=make_image_mock(None))

    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances sonores nocturnes",
        "format": "carousel",
        "platform": "linkedin",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["generation_metadata"]["image_provider"] == "playwright"


def test_invalid_platform_returns_422(client, sample_persona, sample_planning):
    response = client.post("/api/v1/posts/generate", json={
        "planning_id": sample_planning.id,
        "persona_id": sample_persona.id,
        "angle_editorial": "douleur des propriétaires Airbnb face aux nuisances",
        "format": "text_only",
        "platform": "twitter",
    })
    assert response.status_code == 422
