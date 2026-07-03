from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models import QueueTask
from app.services import queue_service
from app.workers.queue_worker import process_single_task


def make_failing_handler(exc_message: str = "Simulated failure"):
    def handler(payload):
        raise RuntimeError(exc_message)
    return handler


def make_succeeding_handler():
    def handler(payload):
        return {"ok": True}
    return handler


def test_task_succeeds_on_first_attempt(db, mocker):
    mocker.patch(
        "app.workers.queue_worker.TASK_HANDLERS",
        {"publish_post": make_succeeding_handler()},
    )
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "p1"})

    processed = process_single_task(db)

    assert processed is True
    db.refresh(task)
    assert task.status == "success"
    assert task.attempts == 0
    assert task.completed_at is not None


def test_task_retried_after_first_failure(db, mocker):
    mocker.patch(
        "app.workers.queue_worker.TASK_HANDLERS",
        {"publish_post": make_failing_handler()},
    )
    mocker.patch("app.workers.queue_worker.compute_next_retry_delay", return_value=0.0)
    mocker.patch("app.workers.queue_worker.send_telegram_alert")

    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "p2"}, max_retries=3)

    process_single_task(db)

    db.refresh(task)
    assert task.status == "pending"
    assert task.attempts == 1
    assert task.last_error == "Simulated failure"


def test_task_failed_after_max_retries(db, mocker):
    mocker.patch(
        "app.workers.queue_worker.TASK_HANDLERS",
        {"publish_post": make_failing_handler("Network error")},
    )
    mocker.patch("app.workers.queue_worker.compute_next_retry_delay", return_value=0.0)
    telegram_mock = mocker.patch("app.workers.queue_worker.send_telegram_alert")

    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "p3"}, max_retries=3)

    # 3 tentatives en forçant next_retry_at dans le passé
    for _ in range(3):
        task = db.query(QueueTask).filter(QueueTask.id == task.id).first()
        task.next_retry_at = datetime.utcnow() - timedelta(seconds=1)
        task.status = "pending"
        db.commit()
        process_single_task(db)

    db.refresh(task)
    assert task.status == "failed"
    assert task.attempts == 3
    assert task.last_error == "Network error"
    assert task.completed_at is not None

    telegram_mock.assert_called_once()
    call_kwargs = telegram_mock.call_args[1]
    assert call_kwargs["task_type"] == "publish_post"
    assert call_kwargs["attempts"] == 3


def test_telegram_called_with_correct_payload(db, mocker):
    mocker.patch(
        "app.workers.queue_worker.TASK_HANDLERS",
        {"generate_text": make_failing_handler("LLM timeout")},
    )
    mocker.patch("app.workers.queue_worker.compute_next_retry_delay", return_value=0.0)
    telegram_mock = mocker.patch("app.workers.queue_worker.send_telegram_alert")

    payload = {"post_id": "x", "persona_id": "y"}
    task = queue_service.enqueue_task(db, "generate_text", payload, max_retries=3)

    for _ in range(3):
        task = db.query(QueueTask).filter(QueueTask.id == task.id).first()
        task.next_retry_at = datetime.utcnow() - timedelta(seconds=1)
        task.status = "pending"
        db.commit()
        process_single_task(db)

    telegram_mock.assert_called_once()
    kwargs = telegram_mock.call_args[1]
    assert kwargs["task_id"] == task.id
    assert kwargs["error_message"] == "LLM timeout"
    assert kwargs["payload"] == payload


def test_unknown_task_type_goes_to_failed_immediately(db, mocker):
    telegram_mock = mocker.patch("app.workers.queue_worker.send_telegram_alert")
    task = queue_service.enqueue_task(db, "unknown_type", {"data": "x"})

    process_single_task(db)

    db.refresh(task)
    assert task.status == "failed"
    assert task.last_error_code == "UNKNOWN_TASK_TYPE"
    telegram_mock.assert_called_once()


def test_no_task_returns_false(db):
    result = process_single_task(db)
    assert result is False


def test_queue_stats_via_api(client, db):
    queue_service.enqueue_task(db, "publish_post", {"post_id": "s1"})
    queue_service.enqueue_task(db, "publish_post", {"post_id": "s2"})
    response = client.get("/api/v1/queue/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["pending"] == 2
