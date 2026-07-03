from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import PersonaCreate, PersonaRead, PersonaUpdate
from app.services import persona_service

router = APIRouter()


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(data: PersonaCreate, db: Session = Depends(get_db)):
    return persona_service.create(db, data)


@router.get("", response_model=list[PersonaRead])
def list_personas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return persona_service.list_all(db, skip=skip, limit=limit)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: str, db: Session = Depends(get_db)):
    return persona_service.get_by_id(db, persona_id)


@router.patch("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: str, data: PersonaUpdate, db: Session = Depends(get_db)):
    return persona_service.update(db, persona_id, data)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: str, db: Session = Depends(get_db)):
    persona_service.delete(db, persona_id)
