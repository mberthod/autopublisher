from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, init_db
from app.schemas import PostGenerateRequest, PostGenerateResponse
from app.services import post_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up generation service")
    init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="SaaS RSE — Génération",
    version="0.1.0",
    description="Pipeline Persona + angle → post draft (texte + image)",
    lifespan=lifespan,
)

app.mount("/static/posts", StaticFiles(directory="./data/posts"), name="posts")


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


@app.post("/api/v1/posts/generate", response_model=PostGenerateResponse, tags=["generation"])
def generate_post(req: PostGenerateRequest, db: Session = Depends(get_db)):
    return post_service.generate(db, req)
