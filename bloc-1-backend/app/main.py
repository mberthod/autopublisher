from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import health_routes, persona_routes, planning_routes, post_routes
from app.api import account_routes, task_routes, selector_routes, stats_routes
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://192.168.0.176:5173",
        "http://localhost:5174",
        "http://192.168.0.176:5174",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_routes.router, tags=["health"])
app.include_router(persona_routes.router, prefix="/api/v1/personas", tags=["personas"])
app.include_router(planning_routes.router, prefix="/api/v1/plannings", tags=["plannings"])
app.include_router(post_routes.router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(account_routes.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(task_routes.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(selector_routes.router, prefix="/api/v1/selectors", tags=["selectors"])
app.include_router(stats_routes.router, prefix="/api/v1/stats", tags=["stats"])

