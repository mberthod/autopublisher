from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.selector_routes import LATEST_VERSION
from app.db import get_db
from app.models import Account, Post
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
    selectors_version: str = LATEST_VERSION
    page_url: Optional[str] = None
    publish_as_name: Optional[str] = None
    publish_via: Optional[str] = None
    account_kind: Optional[str] = None
    asset_id: Optional[str] = None
    placements: list[str] = []


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
        target = _resolve_target(db, p)

        tasks.append(PendingTask(
            task_id=p.id,
            post_id=p.id,
            platform=p.platform,
            format=p.format,
            text=p.text,
            media_urls=media_urls,
            scheduled_for=p.scheduled_for.isoformat() if p.scheduled_for else None,
            **target,
        ))
    return TasksResponse(tasks=tasks)


# Labels historiques — uniquement pour le fallback des personas d'avant la table
# accounts (les nouvelles cibles portent leur identity_name sur l'Account).
_LEGACY_BU_LABELS = {"noisyless": "Noisyless", "afluxo": "Afluxo", "mbhrep": "MBHREP"}


def _resolve_target(db: Session, post: Post) -> dict:
    """Resout la cible de publication d'un post : Account explicite (post.account_id),
    sinon premier Account actif du persona pour la plateforme, sinon fallback legacy
    sur les anciens champs page_url du persona."""
    account = post.account
    if account is None:
        account = (
            db.query(Account)
            .filter(Account.persona_id == post.persona_id)
            .filter(Account.platform == post.platform)
            .filter(Account.enabled == 1)
            .order_by(Account.created_at)
            .first()
        )

    if account:
        publish_via = post.platform
        placements: list[str] = []
        if post.platform in ("instagram", "facebook") and account.kind != "personal":
            publish_via = "meta_suite"
            placements = [post.platform]
        return {
            "page_url": account.page_url,
            "publish_as_name": account.identity_name,
            "publish_via": publish_via,
            "account_kind": account.kind,
            "asset_id": account.asset_id,
            "placements": placements,
        }

    # Fallback legacy (personas sans Account)
    persona = post.persona
    page_url = None
    publish_as_name = None
    if persona:
        if post.platform == "linkedin":
            page_url = persona.linkedin_page_url
            if page_url:  # n'imposer l'identite que si une page est configuree
                publish_as_name = _LEGACY_BU_LABELS.get(persona.bu)
        elif post.platform == "instagram":
            page_url = persona.instagram_page_url
    return {
        "page_url": page_url,
        "publish_as_name": publish_as_name,
        "publish_via": post.platform,
        "account_kind": None,
        "asset_id": None,
        "placements": [],
    }


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
