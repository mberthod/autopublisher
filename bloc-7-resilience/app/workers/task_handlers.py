import httpx
from typing import Callable
from loguru import logger
from app.config import settings


def handle_publish_post(payload: dict) -> dict:
    """
    Passe le post en status 'scheduled' dans le bloc 1.
    L'extension Chrome le récupère via /api/v1/tasks/pending et publie.
    """
    post_id = payload.get("post_id")
    logger.bind(post_id=post_id).info("handle_publish_post: setting post to scheduled")
    try:
        resp = httpx.patch(
            f"{settings.bloc1_api_url}/api/v1/posts/{post_id}",
            json={"status": "scheduled"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Failed to set post scheduled: {exc}")
        raise
    return {"scheduled": True, "post_id": post_id}


def handle_generate_text(payload: dict) -> dict:
    """Appelle le bloc 3 pour générer le texte d'un post."""
    post_id = payload.get("post_id")
    persona_id = payload.get("persona_id")
    angle = payload.get("angle", "")
    planning_id = payload.get("planning_id", "")
    platform = payload.get("platform", "linkedin")

    logger.bind(post_id=post_id).info("handle_generate_text: calling bloc 3")
    try:
        resp = httpx.post(
            f"{settings.generation_service_url}/api/v1/posts/generate",
            json={
                "planning_id": planning_id,
                "persona_id": persona_id,
                "angle_editorial": angle,
                "format": "text_only",
                "platform": platform,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"generated": True, "post_id": data.get("post_id", post_id), "text": data.get("text", "")}
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Text generation failed: {exc}")
        raise


def handle_generate_image(payload: dict) -> dict:
    """Appelle le bloc 3 pour générer une image + texte."""
    post_id = payload.get("post_id")
    persona_id = payload.get("persona_id")
    angle = payload.get("angle", "")
    planning_id = payload.get("planning_id", "")
    platform = payload.get("platform", "linkedin")

    logger.bind(post_id=post_id).info("handle_generate_image: calling bloc 3")
    try:
        resp = httpx.post(
            f"{settings.generation_service_url}/api/v1/posts/generate",
            json={
                "planning_id": planning_id,
                "persona_id": persona_id,
                "angle_editorial": angle,
                "format": "image",
                "platform": platform,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"generated": True, "post_id": data.get("post_id", post_id), "image_url": data.get("image_url", "")}
    except Exception as exc:
        logger.bind(post_id=post_id).error(f"Image generation failed: {exc}")
        raise


TASK_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "publish_post": handle_publish_post,
    "generate_text": handle_generate_text,
    "generate_image": handle_generate_image,
}
