import os
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

os.makedirs("./data/posts", exist_ok=True)

_connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_generation_metadata()
    logger.info("DB ready")


def _migrate_generation_metadata() -> None:
    """Ajoute la colonne generation_metadata si elle n'existe pas encore (bloc 1 ne l'a pas)."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE posts ADD COLUMN generation_metadata JSON"))
            conn.commit()
            logger.info("Migrated: added generation_metadata column to posts")
        except Exception:
            pass  # Colonne déjà existante


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
