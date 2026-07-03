from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.grillme_routes import router as grillme_router
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up GrilledMe service")
    init_db()
    logger.info(f"Database ready at {settings.database_url}")
    yield
    logger.info("Shutting down GrilledMe service")


app = FastAPI(
    title="GrilledMe — Onboarding conversationnel",
    version="0.1.0",
    description="Multi-agents onboarding pour générer des Personas RSE",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.0.176:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grillme_router, prefix="/api/v1/grillme", tags=["grillme"])
