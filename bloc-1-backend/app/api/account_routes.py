from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AccountCreate, AccountRead, AccountUpdate
from app.services import account_service

router = APIRouter()


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    return account_service.create(db, data)


@router.get("", response_model=list[AccountRead])
def list_accounts(persona_id: Optional[str] = None, db: Session = Depends(get_db)):
    return account_service.list_all(db, persona_id=persona_id)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: str, db: Session = Depends(get_db)):
    return account_service.get_by_id(db, account_id)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(account_id: str, data: AccountUpdate, db: Session = Depends(get_db)):
    return account_service.update(db, account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: str, db: Session = Depends(get_db)):
    account_service.delete(db, account_id)
