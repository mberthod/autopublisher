from datetime import datetime, timedelta

import pytest

from app.models import QueueTask
from app.services import queue_service


def test_enqueue_task_creates_pending_task(db):
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "abc"})
    assert task.id is not None
    assert task.status == "pending"
    assert task.attempts == 0
    assert task.task_type == "publish_post"
    assert task.payload == {"post_id": "abc"}


def test_enqueue_task_persisted_in_db(db):
    task = queue_service.enqueue_task(db, "generate_text", {"post_id": "xyz"})
    from_db = db.query(QueueTask).filter(QueueTask.id == task.id).first()
    assert from_db is not None
    assert from_db.status == "pending"


def test_claim_next_task_returns_pending(db):
    queue_service.enqueue_task(db, "publish_post", {"post_id": "p1"})
    task = queue_service.claim_next_task(db)
    assert task is not None
    assert task.status == "running"


def test_claim_next_task_returns_none_when_empty(db):
    task = queue_service.claim_next_task(db)
    assert task is None


def test_claim_next_task_respects_next_retry_at(db):
    # Tâche planifiée dans le futur → pas claimée
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "future"})
    task.next_retry_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    claimed = queue_service.claim_next_task(db)
    assert claimed is None


def test_mark_success(db):
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "ok"})
    task.status = "running"
    db.commit()
    queue_service.mark_success(db, task)
    assert task.status == "success"
    assert task.completed_at is not None


def test_mark_retry_increments_attempts(db):
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "retry"})
    task.status = "running"
    db.commit()
    queue_service.mark_retry(db, task, error="timeout", delay_seconds=1.0)
    assert task.attempts == 1
    assert task.status == "pending"
    assert task.last_error == "timeout"
    assert task.next_retry_at > datetime.utcnow()


def test_mark_failed(db):
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "fail"})
    task.status = "running"
    task.attempts = 2
    db.commit()
    queue_service.mark_failed(db, task, error="Fatal error", error_code="TIMEOUT")
    assert task.status == "failed"
    assert task.last_error_code == "TIMEOUT"
    assert task.completed_at is not None


def test_recover_stuck_tasks(db):
    # Tâche bloquée en 'running' depuis longtemps
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "stuck"})
    task.status = "running"
    task.updated_at = datetime.utcnow() - timedelta(minutes=10)
    db.commit()

    recovered = queue_service.recover_stuck_tasks(db, stuck_threshold_minutes=5)
    assert recovered == 1
    db.refresh(task)
    assert task.status == "pending"


def test_recover_stuck_tasks_ignores_recent(db):
    task = queue_service.enqueue_task(db, "publish_post", {"post_id": "recent"})
    task.status = "running"
    db.commit()  # updated_at = now → pas stuck

    recovered = queue_service.recover_stuck_tasks(db, stuck_threshold_minutes=5)
    assert recovered == 0


def test_get_queue_stats(db):
    queue_service.enqueue_task(db, "publish_post", {"post_id": "a"})
    queue_service.enqueue_task(db, "generate_text", {"post_id": "b"})
    stats = queue_service.get_queue_stats(db)
    assert stats["total"] == 2
    assert stats["pending"] == 2
    assert stats["running"] == 0
    assert stats["success"] == 0
    assert stats["failed"] == 0
