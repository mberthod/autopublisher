from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.queue_service import enqueue_task, get_queue_stats

router = APIRouter()


@router.get("/stats")
def queue_stats(db: Session = Depends(get_db)):
    return get_queue_stats(db)


@router.post("/tasks", status_code=201)
def create_task(
    task_type: str,
    payload: dict,
    max_retries: int = 3,
    db: Session = Depends(get_db),
):
    task = enqueue_task(db, task_type=task_type, payload=payload, max_retries=max_retries)
    return {"id": task.id, "status": task.status, "task_type": task.task_type}
