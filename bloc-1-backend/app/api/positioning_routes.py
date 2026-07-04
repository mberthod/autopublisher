from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models import Positioning
from app.schemas import PositioningRead, PositioningUpsert

router = APIRouter()

BUS = ["noisyless", "afluxo", "mbhrep"]


def _get_or_create(db: DbSession, bu: str) -> Positioning:
    p = db.query(Positioning).filter(Positioning.bu == bu).first()
    if p is None:
        p = Positioning(bu=bu)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@router.get("", response_model=list[PositioningRead])
def list_positioning(db: DbSession = Depends(get_db)):
    return [_get_or_create(db, bu) for bu in BUS]


@router.get("/{bu}", response_model=PositioningRead)
def get_positioning(bu: str, db: DbSession = Depends(get_db)):
    return _get_or_create(db, bu)


@router.put("/{bu}", response_model=PositioningRead)
def upsert_positioning(bu: str, data: PositioningUpsert, db: DbSession = Depends(get_db)):
    p = _get_or_create(db, bu)
    if data.content is not None:
        p.content = data.content
    if data.keywords is not None:
        p.keywords = data.keywords
    db.commit()
    db.refresh(p)
    return p
