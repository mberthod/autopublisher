from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import PlanningCreate, PlanningRead, PlanningUpdate, PlanningWithPostsRead
from app.services import planning_service

router = APIRouter()


@router.post("", response_model=PlanningRead, status_code=status.HTTP_201_CREATED)
def create_planning(data: PlanningCreate, db: Session = Depends(get_db)):
    return planning_service.create(db, data)


@router.get("", response_model=list[PlanningRead])
def list_plannings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return planning_service.list_all(db, skip=skip, limit=limit)


@router.get("/{planning_id}", response_model=PlanningWithPostsRead)
def get_planning(planning_id: str, db: Session = Depends(get_db)):
    return planning_service.get_by_id(db, planning_id)


@router.patch("/{planning_id}", response_model=PlanningRead)
def update_planning(planning_id: str, data: PlanningUpdate, db: Session = Depends(get_db)):
    return planning_service.update(db, planning_id, data)


@router.delete("/{planning_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planning(planning_id: str, db: Session = Depends(get_db)):
    planning_service.delete(db, planning_id)
