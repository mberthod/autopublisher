from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    MessageRequest,
    MessageResponse,
    SessionCreate,
    SessionPersonaResponse,
    SessionStartResponse,
)
from app.services import grillme_service

router = APIRouter()


@router.post("/sessions", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    session_id, first_question = grillme_service.start_session(db, data.bu)
    return SessionStartResponse(session_id=session_id, first_question=first_question)


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
def send_message(session_id: str, data: MessageRequest, db: Session = Depends(get_db)):
    result = grillme_service.handle_message(db, session_id, data.user_message)
    return MessageResponse(**result)


@router.get("/sessions/{session_id}/persona", response_model=SessionPersonaResponse)
def get_persona(session_id: str, db: Session = Depends(get_db)):
    result = grillme_service.get_session_persona(db, session_id)
    return SessionPersonaResponse(**result)
