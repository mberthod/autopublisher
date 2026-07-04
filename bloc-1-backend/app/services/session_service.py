from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session as DbSession

from app.models import Session
from app.schemas import SessionUpsert


def upsert(db: DbSession, data: SessionUpsert) -> Session:
    """Une session active par plateforme : remplace l'existante."""
    sess = db.query(Session).filter(Session.platform == data.platform).first()
    if sess is None:
        sess = Session(platform=data.platform)
        db.add(sess)
    sess.cookies = data.cookies
    sess.user_agent = data.user_agent
    sess.valid = 1
    sess.last_error = None
    db.commit()
    db.refresh(sess)
    # Ne jamais logguer les valeurs de cookies
    logger.bind(platform=sess.platform, n=len(data.cookies)).info("Session updated")
    return sess


def get(db: DbSession, platform: str) -> Session:
    sess = db.query(Session).filter(Session.platform == platform).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"No session for {platform}")
    return sess


def list_all(db: DbSession) -> list[Session]:
    return db.query(Session).order_by(Session.platform).all()


def mark_invalid(db: DbSession, platform: str, error: Optional[str] = None) -> Session:
    sess = get(db, platform)
    sess.valid = 0
    sess.last_error = error
    db.commit()
    db.refresh(sess)
    logger.bind(platform=platform).warning("Session marked invalid")
    return sess


def delete(db: DbSession, platform: str) -> None:
    sess = get(db, platform)
    db.delete(sess)
    db.commit()
    logger.bind(platform=platform).info("Session deleted")
