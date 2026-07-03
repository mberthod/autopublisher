import asyncio
import traceback
from datetime import datetime

from loguru import logger

from app.config import settings
from app.db import get_session, init_db
from app.services import queue_service
from app.services.retry_policy import compute_next_retry_delay
from app.services.telegram_notifier import send_telegram_alert
from app.workers.task_handlers import TASK_HANDLERS


def process_single_task(db) -> bool:
    """
    Traite la prochaine tâche disponible. Retourne True si une tâche a été traitée.
    Fonction synchrone, appelable depuis les tests.
    """
    task = queue_service.claim_next_task(db)
    if not task:
        return False

    log = logger.bind(task_id=task.id, task_type=task.task_type, attempts=task.attempts)
    log.info("Processing task")

    handler = TASK_HANDLERS.get(task.task_type)
    if not handler:
        error = f"Unknown task_type: {task.task_type}"
        log.error(error)
        queue_service.mark_failed(db, task, error=error, error_code="UNKNOWN_TASK_TYPE")
        _maybe_alert(task)
        return True

    try:
        handler(task.payload)
        queue_service.mark_success(db, task)
        log.info("Task processed successfully")

    except Exception as exc:
        error_msg = str(exc)
        tb = traceback.format_exc()
        log.warning(f"Task attempt failed: {error_msg}")

        if task.attempts + 1 >= task.max_retries:
            queue_service.mark_failed(db, task, error=error_msg, error_code=type(exc).__name__)
            _maybe_alert(task)
        else:
            delay = compute_next_retry_delay(task.attempts, settings.queue_jitter_factor)
            queue_service.mark_retry(db, task, error=error_msg, delay_seconds=delay)

    return True


def _maybe_alert(task) -> None:
    send_telegram_alert(
        task_id=task.id,
        task_type=task.task_type,
        attempts=task.attempts,
        max_retries=task.max_retries,
        error_code=task.last_error_code or "UNKNOWN",
        error_message=task.last_error or "",
        payload=task.payload,
        completed_at=str(task.completed_at or datetime.utcnow()),
    )


async def run_worker_loop() -> None:
    logger.info("Queue worker starting")
    init_db()

    # Recovery au démarrage : tâches bloquées en 'running' → 'pending'
    db = get_session()
    try:
        recovered = queue_service.recover_stuck_tasks(db, settings.queue_stuck_threshold_minutes)
        if recovered:
            logger.info(f"Recovered {recovered} stuck tasks")
    finally:
        db.close()

    logger.info(f"Worker loop started — polling every {settings.queue_poll_interval_seconds}s")
    while True:
        db = get_session()
        try:
            processed = process_single_task(db)
            if not processed:
                await asyncio.sleep(settings.queue_poll_interval_seconds)
        except Exception as exc:
            logger.error(f"Worker loop error: {exc}")
            await asyncio.sleep(settings.queue_poll_interval_seconds)
        finally:
            db.close()


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
