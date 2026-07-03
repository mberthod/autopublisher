from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.models import Persona


def get_by_id(db: Session, persona_id: str) -> Persona:
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    return persona
