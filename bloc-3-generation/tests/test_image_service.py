import pytest
from unittest.mock import MagicMock, patch, mock_open

from app.services.image_service import ImageService
from tests.conftest import SAMPLE_CHARTE


def test_text_only_format_returns_none():
    svc = ImageService(fal_key="")
    result = svc.generate("post-1", "angle test", SAMPLE_CHARTE)
    assert result is None


def test_no_fal_key_returns_none():
    svc = ImageService(fal_key="")
    result = svc.generate("post-1", "angle test", SAMPLE_CHARTE)
    assert result is None


def test_generate_calls_fal_with_correct_prompt(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"images": [{"url": "https://fal.media/test.png"}]}
    mock_response.raise_for_status = MagicMock()

    mock_post = mocker.patch("httpx.post", return_value=mock_response)
    mocker.patch.object(ImageService, "_download_image", return_value="./data/posts/post-1.png")

    svc = ImageService(fal_key="test-key")
    result = svc.generate("post-1", "nuisances sonores Airbnb", SAMPLE_CHARTE)

    assert result is not None
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["headers"]["Authorization"] == "Key test-key"
    prompt_sent = call_kwargs["json"]["prompt"]
    assert "nuisances sonores Airbnb" in prompt_sent
    assert "#FF6B35" in prompt_sent


def test_generate_returns_static_url(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"images": [{"url": "https://fal.media/img.png"}]}
    mock_response.raise_for_status = MagicMock()

    mocker.patch("httpx.post", return_value=mock_response)
    mocker.patch.object(ImageService, "_download_image", return_value="./data/posts/post-42.png")

    svc = ImageService(fal_key="test-key")
    result = svc.generate("post-42", "angle", SAMPLE_CHARTE)

    assert result is not None
    assert "post-42.png" in result
    assert "static/posts" in result


def test_generate_returns_none_on_fal_error(mocker):
    import httpx
    mocker.patch("httpx.post", side_effect=httpx.ConnectError("timeout"))

    svc = ImageService(fal_key="test-key")
    result = svc.generate("post-err", "angle", SAMPLE_CHARTE)
    assert result is None
