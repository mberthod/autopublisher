from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import PostCreate, PostRead, PostUpdate
from app.services import post_service

router = APIRouter()


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, db: Session = Depends(get_db)):
    return post_service.create(db, data)


@router.get("", response_model=list[PostRead])
def list_posts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    persona_id: Optional[str] = Query(None),
    planning_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return post_service.list_all(
        db,
        skip=skip,
        limit=limit,
        status=status,
        persona_id=persona_id,
        planning_id=planning_id,
        platform=platform,
    )


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: str, db: Session = Depends(get_db)):
    return post_service.get_by_id(db, post_id)


@router.patch("/{post_id}", response_model=PostRead)
def update_post(post_id: str, data: PostUpdate, db: Session = Depends(get_db)):
    return post_service.update(db, post_id, data)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: str, db: Session = Depends(get_db)):
    post_service.delete(db, post_id)
