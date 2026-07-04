"""Publication Instagram côté serveur via l'API mobile privée (instagrapi),
en réutilisant le sessionid capturé par l'extension — approche Unipile.
Publie une photo + légende sans piloter aucune page. PC de l'utilisateur éteint.
"""
import asyncio

import httpx
from loguru import logger
from instagrapi import Client


def _sessionid(cookies: list[dict]):
    return next((c["value"] for c in cookies if c["name"] == "sessionid"), None)


async def publish(task: dict, cookies: list[dict], user_agent):
    # instagrapi est synchrone → thread dédié pour ne pas bloquer la boucle
    return await asyncio.to_thread(_publish_sync, task, cookies)


def _publish_sync(task: dict, cookies: list[dict]) -> dict:
    sessionid = _sessionid(cookies)
    if not sessionid:
        return {"status": "failed", "error_code": "AUTH_REQUIRED", "error_message": "sessionid Instagram absent — resynchronise la session"}

    media_urls = task.get("media_urls") or []
    if not media_urls:
        return {"status": "failed", "error_code": "UNKNOWN", "error_message": "Instagram requiert une image"}

    path = f"/tmp/ig_{task.get('post_id', 'x')}.jpg"
    try:
        r = httpx.get(media_urls[0], timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    except Exception as e:
        return {"status": "failed", "error_code": "UNKNOWN", "error_message": f"téléchargement image: {e}"}

    cl = Client()
    try:
        cl.login_by_sessionid(sessionid)
    except Exception as e:
        return {"status": "failed", "error_code": "AUTH_REQUIRED", "error_message": f"session invalide: {str(e)[:150]}"}

    try:
        media = cl.photo_upload(path, caption=task.get("text") or "")
        code = getattr(media, "code", None)
        url = f"https://www.instagram.com/p/{code}/" if code else None
        logger.bind(url=url).info("Instagram publié")
        return {"status": "success", "post_url": url}
    except Exception as e:
        logger.warning(f"photo_upload échec: {e}")
        return {"status": "failed", "error_code": "PUBLISH_REJECTED", "error_message": str(e)[:250]}
