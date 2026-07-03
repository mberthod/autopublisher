from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, init_db
from app.schemas import PostGenerateRequest, PostGenerateResponse, IdeaGenerateRequest, IdeaGenerateResponse
from app.services import post_service
from app.services.llm_service import LLMService
from app.services.persona_service import get_by_id as get_persona


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.0.176:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/posts", StaticFiles(directory="./data/posts"), name="posts")


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


@app.post("/api/v1/posts/generate", response_model=PostGenerateResponse, tags=["generation"])
def generate_post(req: PostGenerateRequest, db: Session = Depends(get_db)):
    return post_service.generate(db, req)

@app.post("/api/v1/ideas/generate", response_model=IdeaGenerateResponse, tags=["ideas"])
def generate_ideas(req: IdeaGenerateRequest, db: Session = Depends(get_db)):
    persona = get_persona(db, req.persona_id)
    llm = LLMService()
    ideas_raw = llm.generate_ideas(persona, req.keywords, req.platform, req.n)
    ideas = [
        {"angle": i.get("angle", ""), "rationale": i.get("rationale", ""), "platform": i.get("platform", req.platform)}
        for i in ideas_raw
    ]
    return {"ideas": ideas}
