import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.services.telegram_notifier import send_telegram_alert


SAMPLE_ALERT_KWARGS = dict(
    task_id="task-123",
    task_type="publish_post",
    attempts=3,
    max_retries=3,
    error_code="TIMEOUT",
    error_message="Connection timed out after 30s",
    payload={"post_id": "post-abc"},
    completed_at="2026-07-03T10:00:00",
)


def test_send_telegram_alert_posts_to_api(mocker):
    mocker.patch("app.config.settings.telegram_bot_token", "bot_test123")
    mocker.patch("app.config.settings.telegram_chat_id", "12345")

    mock_post = mocker.patch("httpx.post")
    mock_post.return_value.raise_for_status = MagicMock()

    result = send_telegram_alert(**SAMPLE_ALERT_KWARGS)

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("url") or call_kwargs[1].get("url") or mock_post.call_args[0][0]
    assert "sendMessage" in url
    assert "bot_test123" in url


def test_send_telegram_alert_message_contains_task_info(mocker):
    mocker.patch("app.config.settings.telegram_bot_token", "bot_test123")
    mocker.patch("app.config.settings.telegram_chat_id", "12345")

    mock_post = mocker.patch("httpx.post")
    mock_post.return_value.raise_for_status = MagicMock()

    send_telegram_alert(**SAMPLE_ALERT_KWARGS)

    json_body = mock_post.call_args[1]["json"]
    text = json_body["text"]
    assert "publish_post" in text
    assert "task-123" in text
    assert "TIMEOUT" in text
    assert "3/3" in text


def test_send_telegram_alert_skipped_when_not_configured(mocker):
    mocker.patch("app.config.settings.telegram_bot_token", "")
    mocker.patch("app.config.settings.telegram_chat_id", "")

    mock_post = mocker.patch("httpx.post")
    result = send_telegram_alert(**SAMPLE_ALERT_KWARGS)

    assert result is False
    mock_post.assert_not_called()


def test_send_telegram_alert_returns_false_on_http_error(mocker):
    mocker.patch("app.config.settings.telegram_bot_token", "bot_test123")
    mocker.patch("app.config.settings.telegram_chat_id", "12345")

    mock_post = mocker.patch("httpx.post")
    mock_post.side_effect = httpx.ConnectError("Connection refused")

    result = send_telegram_alert(**SAMPLE_ALERT_KWARGS)
    assert result is False
