from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.schemas import SessionRead, SessionUpsert, SessionWithCookies
from app.services import session_service

router = APIRouter()


def _to_read(sess) -> SessionRead:
    return SessionRead(
        id=sess.id,
        platform=sess.platform,
        user_agent=sess.user_agent,
        valid=bool(sess.valid),
        last_error=sess.last_error,
        cookie_count=len(sess.cookies or []),
        updated_at=sess.updated_at,
    )


@router.post("", response_model=SessionRead)
def upsert_session(data: SessionUpsert, db: DbSession = Depends(get_db)):
    return _to_read(session_service.upsert(db, data))


@router.get("", response_model=list[SessionRead])
def list_sessions(db: DbSession = Depends(get_db)):
    return [_to_read(s) for s in session_service.list_all(db)]


@router.get("/{platform}", response_model=SessionRead)
def get_session(platform: str, db: DbSession = Depends(get_db)):
    return _to_read(session_service.get(db, platform))


# Reservee au publisher serveur : renvoie les cookies pour rejouer la session
@router.get("/{platform}/cookies", response_model=SessionWithCookies)
def get_session_cookies(platform: str, db: DbSession = Depends(get_db)):
    sess = session_service.get(db, platform)
    return SessionWithCookies(
        id=sess.id,
        platform=sess.platform,
        user_agent=sess.user_agent,
        valid=bool(sess.valid),
        last_error=sess.last_error,
        cookie_count=len(sess.cookies or []),
        updated_at=sess.updated_at,
        cookies=sess.cookies or [],
    )


@router.post("/{platform}/invalidate", response_model=SessionRead)
def invalidate_session(platform: str, error: str = "", db: DbSession = Depends(get_db)):
    return _to_read(session_service.mark_invalid(db, platform, error or None))


@router.delete("/{platform}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(platform: str, db: DbSession = Depends(get_db)):
    session_service.delete(db, platform)
