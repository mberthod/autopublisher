from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.models import Persona


def create(db: Session, bu: str, nom: str, besoins: str, frustrations: str, cible: str, charte_branding: dict) -> Persona:
    persona = Persona(
        bu=bu,
        nom=nom,
        besoins=besoins,
        frustrations=frustrations,
        cible=cible,
        charte_branding=charte_branding,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    logger.bind(persona_id=persona.id, bu=bu).info("Persona created via GrilledMe")
    return persona


def get_by_id(db: Session, persona_id: str) -> Persona:
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    return persona
