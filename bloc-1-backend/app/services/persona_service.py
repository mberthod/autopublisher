from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.models import Persona
from app.schemas import PersonaCreate, PersonaUpdate


def create(db: Session, data: PersonaCreate) -> Persona:
    persona = Persona(**data.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    logger.bind(persona_id=persona.id, bu=persona.bu).info("Persona created")
    return persona


def get_by_id(db: Session, persona_id: str) -> Persona:
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    return persona


def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Persona]:
    return db.query(Persona).offset(skip).limit(limit).all()


def update(db: Session, persona_id: str, data: PersonaUpdate) -> Persona:
    persona = get_by_id(db, persona_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(persona, field, value)
    db.commit()
    db.refresh(persona)
    logger.bind(persona_id=persona.id).info("Persona updated")
    return persona


def delete(db: Session, persona_id: str) -> None:
    persona = get_by_id(db, persona_id)
    db.delete(persona)
    db.commit()
    logger.bind(persona_id=persona_id).info("Persona deleted")
