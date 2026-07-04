from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Post
from app.services import post_service

router = APIRouter()


class PendingTask(BaseModel):
    task_id: str
    post_id: str
    platform: str
    format: str
    text: Optional[str]
    media_urls: list[str]
    scheduled_for: Optional[str]
    selectors_version: str = "2026-07-04-v3"
    page_url: Optional[str] = None


class TasksResponse(BaseModel):
    tasks: list[PendingTask]


class CallbackSuccess(BaseModel):
    status: Literal["success"]
    post_url: Optional[str] = None
    published_at: Optional[str] = None


class CallbackFailed(BaseModel):
    status: Literal["failed"]
    error_code: str
    error_message: str
    screenshot_url: Optional[str] = None


@router.get("/pending", response_model=TasksResponse)
def get_pending_tasks(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    posts = (
        db.query(Post)
        .filter(Post.status == "scheduled")
        .filter((Post.scheduled_for == None) | (Post.scheduled_for <= now))
        .all()
    )
    tasks = []
    for p in posts:
        media_urls: list[str] = []
        if p.image_url:
            media_urls.append(p.image_url)
        if p.carousel_urls:
            media_urls.extend(p.carousel_urls)
        persona = p.persona
        page_url = None
        if persona:
            if p.platform == "linkedin":
                page_url = persona.linkedin_page_url
            elif p.platform == "instagram":
                page_url = persona.instagram_page_url

        tasks.append(PendingTask(
            task_id=p.id,
            post_id=p.id,
            platform=p.platform,
            format=p.format,
            text=p.text,
            media_urls=media_urls,
            scheduled_for=p.scheduled_for.isoformat() if p.scheduled_for else None,
            page_url=page_url,
        ))
    return TasksResponse(tasks=tasks)


@router.post("/{task_id}/callback")
def task_callback(
    task_id: str,
    body: CallbackSuccess | CallbackFailed,
    db: Session = Depends(get_db),
):
    post = db.query(Post).filter(Post.id == task_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if body.status == "success":
        post.status = "published"
        if body.published_at:
            post.published_at = datetime.fromisoformat(body.published_at.replace("Z", "+00:00"))
        if body.post_url:
            post.published_url = body.post_url
    else:
        post.status = "failed"
        post.error_code = body.error_code
        post.error_message = body.error_message

    db.commit()
    return {"ok": True}
