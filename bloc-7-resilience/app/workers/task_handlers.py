from typing import Callable

from loguru import logger


def handle_publish_post(payload: dict) -> dict:
    """
    Phase A stub — sera remplacé par l'intégration bloc-5 (extension Chrome).
    payload: {"post_id": "uuid", ...}
    """
    post_id = payload.get("post_id")
    logger.bind(post_id=post_id).info("handle_publish_post called (stub)")
    # Phase B: appel HTTP vers l'extension ou callback SSE
    return {"published": True, "post_id": post_id}


def handle_generate_text(payload: dict) -> dict:
    """
    Phase A stub — sera remplacé par l'intégration bloc-3 (génération LLM).
    payload: {"post_id": "uuid", "persona_id": "uuid", "angle": "..."}
    """
    post_id = payload.get("post_id")
    logger.bind(post_id=post_id).info("handle_generate_text called (stub)")
    # Phase B: import depuis bloc-3 génération
    return {"generated": True, "post_id": post_id}


def handle_generate_image(payload: dict) -> dict:
    """
    Phase A stub — sera remplacé par l'intégration bloc-3 (FAL.ai Flux.1).
    payload: {"post_id": "uuid", "prompt": "..."}
    """
    post_id = payload.get("post_id")
    logger.bind(post_id=post_id).info("handle_generate_image called (stub)")
    # Phase B: import depuis bloc-3 génération image
    return {"generated": True, "post_id": post_id}


TASK_HANDLERS: dict[str, Callable[[dict], dict]] = {
    "publish_post": handle_publish_post,
    "generate_text": handle_generate_text,
    "generate_image": handle_generate_image,
}
