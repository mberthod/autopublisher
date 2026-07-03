from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.queue_routes import router as queue_router
from app.config import settings
from app.db import get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up resilience service")
    init_db()
    yield
    logger.info("Shutting down resilience service")


app = FastAPI(
    title="SaaS RSE — Résilience",
    version="0.1.0",
    description="Queue + retry + alertes Telegram",
    lifespan=lifespan,
)


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def readyz(db=__import__("fastapi").Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


app.include_router(queue_router, prefix="/api/v1/queue", tags=["queue"])
