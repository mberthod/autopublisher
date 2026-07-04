from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.models import Account
from app.schemas import AccountCreate, AccountUpdate


def create(db: Session, data: AccountCreate) -> Account:
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.bind(account_id=account.id, platform=account.platform).info("Account created")
    return account


def get_by_id(db: Session, account_id: str) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account


def list_all(db: Session, persona_id: Optional[str] = None) -> list[Account]:
    q = db.query(Account)
    if persona_id:
        q = q.filter(Account.persona_id == persona_id)
    return q.order_by(Account.created_at).all()


def update(db: Session, account_id: str, data: AccountUpdate) -> Account:
    account = get_by_id(db, account_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    logger.bind(account_id=account.id).info("Account updated")
    return account


def delete(db: Session, account_id: str) -> None:
    account = get_by_id(db, account_id)
    db.delete(account)
    db.commit()
    logger.bind(account_id=account_id).info("Account deleted")
