from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Post, Planning, Persona
from app.schemas import PostCreate, PostUpdate


def create(db: Session, data: PostCreate) -> Post:
    if not db.query(Planning).filter(Planning.id == data.planning_id).first():
        raise HTTPException(status_code=404, detail=f"Planning {data.planning_id} not found")
    if not db.query(Persona).filter(Persona.id == data.persona_id).first():
        raise HTTPException(status_code=404, detail=f"Persona {data.persona_id} not found")
    post = Post(**data.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.bind(post_id=post.id, platform=post.platform, status=post.status).info("Post created")
    return post


def get_by_id(db: Session, post_id: str) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return post


def list_all(
    db: Session,
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    persona_id: Optional[str] = None,
    planning_id: Optional[str] = None,
    platform: Optional[str] = None,
    scheduled_for_date: Optional[str] = None,
) -> list[Post]:
    query = db.query(Post)
    if status:
        query = query.filter(Post.status == status)
    if persona_id:
        query = query.filter(Post.persona_id == persona_id)
    if planning_id:
        query = query.filter(Post.planning_id == planning_id)
    if platform:
        query = query.filter(Post.platform == platform)
    if scheduled_for_date:
        query = query.filter(func.date(Post.scheduled_for) == scheduled_for_date)
    return query.offset(skip).limit(limit).all()


def update(db: Session, post_id: str, data: PostUpdate) -> Post:
    post = get_by_id(db, post_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    logger.bind(post_id=post.id, status=post.status).info("Post updated")
    return post


def update_status(db: Session, post_id: str, status: str, error_code: Optional[str] = None, error_message: Optional[str] = None) -> Post:
    post = get_by_id(db, post_id)
    post.status = status
    if error_code is not None:
        post.error_code = error_code
    if error_message is not None:
        post.error_message = error_message
    db.commit()
    db.refresh(post)
    logger.bind(post_id=post.id, status=status).info("Post status updated")
    return post


def get_pending_to_publish(db: Session) -> list[Post]:
    return db.query(Post).filter(Post.status == "scheduled").all()


def delete(db: Session, post_id: str) -> None:
    post = get_by_id(db, post_id)
    db.delete(post)
    db.commit()
    logger.bind(post_id=post_id).info("Post deleted")
