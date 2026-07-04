import time
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.models import Persona, Planning, Post
from app.schemas import PostGenerateRequest, PostGenerateResponse
from app.services.image_service import ImageService
from app.services.llm_service import LLMService
from app.services.persona_service import get_by_id as get_persona


def generate(
    db: Session,
    req: PostGenerateRequest,
    llm: Optional[LLMService] = None,
    image_svc: Optional[ImageService] = None,
) -> PostGenerateResponse:
    if llm is None:
        llm = LLMService()
    if image_svc is None:
        image_svc = ImageService()

    persona = get_persona(db, req.persona_id)

    if not db.query(Planning).filter(Planning.id == req.planning_id).first():
        raise HTTPException(status_code=404, detail=f"Planning {req.planning_id} not found")

    t0 = time.monotonic()

    llm_result = llm.generate_text(
        persona=persona,
        angle_editorial=req.angle_editorial,
        platform=req.platform,
        format=req.format,
    )

    post = Post(
        planning_id=req.planning_id,
        persona_id=req.persona_id,
        platform=req.platform,
        angle_editorial=req.angle_editorial,
        format=req.format,
        text=llm_result["text"],
        status="draft",
    )
    db.add(post)
    db.flush()  # get post.id before image generation

    image_url: Optional[str] = None
    image_provider: Optional[str] = None

    if req.format == "image":
        image_url = image_svc.generate(
            post_id=post.id,
            angle_editorial=req.angle_editorial,
            charte=persona.charte_branding or {},
        )
        if image_url:
            image_provider = "fal.ai"
            post.image_url = image_url
    elif req.format == "carousel":
        image_provider = "playwright"
        logger.bind(post_id=post.id).info("Carousel format — delegated to bloc 4")

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    metadata = {
        "llm_model": llm_result["model"],
        "llm_tokens_in": llm_result["tokens_in"],
        "llm_tokens_out": llm_result["tokens_out"],
        "image_provider": image_provider,
        "generation_time_ms": elapsed_ms,
    }
    post.generation_metadata = metadata
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)

    logger.bind(post_id=post.id, format=req.format, ms=elapsed_ms).info("Post draft generated")

    visual_headline = llm_result.get("visual_headline", "")
    return PostGenerateResponse(
        post_id=post.id,
        status=post.status,
        text=post.text,
        image_url=post.image_url,
        carousel_urls=post.carousel_urls,
        visual_headline=visual_headline,
        generation_metadata=metadata,
    )
