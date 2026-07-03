import json

import httpx
from loguru import logger

from app.config import settings

ALERT_TEMPLATE = """🚨 SaaS RSE — Tâche échouée définitivement

Type: {task_type}
Tentatives: {attempts}/{max_retries}
Erreur: {error_code}
Message: {error_message}

Payload: {payload_preview}
Tâche ID: {task_id}
Échouée à: {completed_at}

→ Voir dashboard: http://192.168.0.176:8000/queue/{task_id}"""


def send_telegram_alert(
    task_id: str,
    task_type: str,
    attempts: int,
    max_retries: int,
    error_code: str,
    error_message: str,
    payload: dict,
    completed_at: str,
) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured — alert skipped")
        return False

    payload_preview = json.dumps(payload, indent=2, ensure_ascii=False)[:500]
    text = ALERT_TEMPLATE.format(
        task_type=task_type,
        attempts=attempts,
        max_retries=max_retries,
        error_code=error_code,
        error_message=error_message[:200],
        payload_preview=payload_preview,
        task_id=task_id,
        completed_at=completed_at,
    )

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        response.raise_for_status()
        logger.bind(task_id=task_id).info("Telegram alert sent")
        return True
    except Exception as exc:
        logger.bind(task_id=task_id).error(f"Telegram alert failed: {exc}")
        return False
