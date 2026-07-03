from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import QueueTask


def enqueue_task(
    db: Session,
    task_type: str,
    payload: dict,
    max_retries: int = 3,
) -> QueueTask:
    task = QueueTask(
        task_type=task_type,
        payload=payload,
        status="pending",
        attempts=0,
        max_retries=max_retries,
        next_retry_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.bind(task_id=task.id, task_type=task_type).info("Task enqueued")
    return task


def claim_next_task(db: Session) -> Optional[QueueTask]:
    """Récupère et verrouille la prochaine tâche à traiter."""
    task = (
        db.query(QueueTask)
        .filter(
            and_(
                QueueTask.status == "pending",
                QueueTask.next_retry_at <= datetime.utcnow(),
            )
        )
        .order_by(QueueTask.next_retry_at)
        .first()
    )
    if task:
        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        logger.bind(task_id=task.id, task_type=task.task_type, attempts=task.attempts).info("Task claimed")
    return task


def mark_success(db: Session, task: QueueTask) -> QueueTask:
    task.status = "success"
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    logger.bind(task_id=task.id, task_type=task.task_type).info("Task succeeded")
    return task


def mark_retry(db: Session, task: QueueTask, error: str, delay_seconds: float) -> QueueTask:
    from datetime import timedelta
    task.attempts += 1
    task.status = "pending"
    task.last_error = error
    task.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    logger.bind(task_id=task.id, attempts=task.attempts, delay=delay_seconds).warning("Task scheduled for retry")
    return task


def mark_failed(db: Session, task: QueueTask, error: str, error_code: str = "TASK_FAILED") -> QueueTask:
    task.attempts += 1
    task.status = "failed"
    task.last_error = error
    task.last_error_code = error_code
    task.completed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    logger.bind(task_id=task.id, task_type=task.task_type, attempts=task.attempts).error("Task failed definitively")
    return task


def recover_stuck_tasks(db: Session, stuck_threshold_minutes: int = 5) -> int:
    """Remet en 'pending' les tâches bloquées en 'running' depuis trop longtemps."""
    from datetime import timedelta
    threshold = datetime.utcnow() - timedelta(minutes=stuck_threshold_minutes)
    stuck = (
        db.query(QueueTask)
        .filter(and_(QueueTask.status == "running", QueueTask.updated_at <= threshold))
        .all()
    )
    count = len(stuck)
    for task in stuck:
        task.status = "pending"
        task.next_retry_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        logger.bind(task_id=task.id).warning("Stuck task recovered → pending")
    if count:
        db.commit()
    return count


def get_queue_stats(db: Session) -> dict:
    total = db.query(QueueTask).count()
    by_status = {}
    for status in ("pending", "running", "success", "failed"):
        by_status[status] = db.query(QueueTask).filter(QueueTask.status == status).count()
    return {"total": total, **by_status}
