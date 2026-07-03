from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from app.models import Planning, Persona
from app.schemas import PlanningCreate, PlanningUpdate


def create(db: Session, data: PlanningCreate) -> Planning:
    if not db.query(Persona).filter(Persona.id == data.persona_id).first():
        raise HTTPException(status_code=404, detail=f"Persona {data.persona_id} not found")
    planning = Planning(**data.model_dump())
    db.add(planning)
    db.commit()
    db.refresh(planning)
    logger.bind(planning_id=planning.id, persona_id=planning.persona_id).info("Planning created")
    return planning


def get_by_id(db: Session, planning_id: str) -> Planning:
    planning = (
        db.query(Planning)
        .options(joinedload(Planning.posts))
        .filter(Planning.id == planning_id)
        .first()
    )
    if not planning:
        raise HTTPException(status_code=404, detail=f"Planning {planning_id} not found")
    return planning


def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Planning]:
    return db.query(Planning).offset(skip).limit(limit).all()


def update(db: Session, planning_id: str, data: PlanningUpdate) -> Planning:
    planning = db.query(Planning).filter(Planning.id == planning_id).first()
    if not planning:
        raise HTTPException(status_code=404, detail=f"Planning {planning_id} not found")
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(planning, field, value)
    db.commit()
    db.refresh(planning)
    logger.bind(planning_id=planning.id).info("Planning updated")
    return planning


def delete(db: Session, planning_id: str) -> None:
    planning = db.query(Planning).filter(Planning.id == planning_id).first()
    if not planning:
        raise HTTPException(status_code=404, detail=f"Planning {planning_id} not found")
    db.delete(planning)
    db.commit()
    logger.bind(planning_id=planning_id).info("Planning deleted")
