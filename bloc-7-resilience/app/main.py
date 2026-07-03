import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.queue_routes import router as queue_router
from app.db import get_db, init_db
from app.services.queue_service import recover_stuck_tasks
from app.config import settings


async def _worker_loop() -> None:
    from app.db import get_session
    from app.services.queue_service import recover_stuck_tasks
    from app.workers.queue_worker import process_single_task

    logger.info(f"Worker loop started — polling every {settings.queue_poll_interval_seconds}s")
    while True:
        db = get_session()
        try:
            processed = process_single_task(db)
            if not processed:
                await asyncio.sleep(settings.queue_poll_interval_seconds)
        except Exception as exc:
            logger.error(f"Worker loop error: {exc}")
            await asyncio.sleep(settings.queue_poll_interval_seconds)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up resilience service")
    init_db()

    # Recovery au démarrage
    from app.db import get_session
    db = get_session()
    try:
        recovered = recover_stuck_tasks(db, settings.queue_stuck_threshold_minutes)
        if recovered:
            logger.info(f"Recovered {recovered} stuck tasks at startup")
    finally:
        db.close()

    # Worker lancé comme tâche asyncio — non-bloquant
    task = asyncio.create_task(_worker_loop())
    logger.info("Queue worker started as background task")
    yield
    task.cancel()
    logger.info("Shutting down")


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
    return {"status": "ok", "db": "connected", "worker": "embedded"}


app.include_router(queue_router, prefix="/api/v1/queue", tags=["queue"])
