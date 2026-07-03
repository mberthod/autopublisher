from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api import health_routes, persona_routes, planning_routes, post_routes
from app.config import settings
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up SaaS RSE backend")
    init_db()
    logger.info(f"Database initialized at {settings.database_url}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="SaaS RSE Backend",
    version="0.1.0",
    description="API pour automation de publications RSE",
    lifespan=lifespan,
)

app.include_router(health_routes.router, tags=["health"])
app.include_router(persona_routes.router, prefix="/api/v1/personas", tags=["personas"])
app.include_router(planning_routes.router, prefix="/api/v1/plannings", tags=["plannings"])
app.include_router(post_routes.router, prefix="/api/v1/posts", tags=["posts"])
