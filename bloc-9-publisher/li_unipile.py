"""Publication LinkedIn (page entreprise) via l'API Unipile.

Unipile gère la session LinkedIn côté serveur (connexion une fois via leur dashboard)
et expose une API propre. On publie en tant que page avec `as_organization`.
Config via .env : UNIPILE_DSN, UNIPILE_API_KEY, UNIPILE_LINKEDIN_ACCOUNT_ID.
"""
import os

import httpx
from loguru import logger

DSN = os.environ.get("UNIPILE_DSN", "").rstrip("/")
API_KEY = os.environ.get("UNIPILE_API_KEY", "")
ACCOUNT_ID = os.environ.get("UNIPILE_LINKEDIN_ACCOUNT_ID", "")


def configured() -> bool:
    return bool(DSN and API_KEY and ACCOUNT_ID)


def _org_id(page_url):
    if page_url and "/company/" in page_url:
        ident = page_url.split("/company/")[1].strip("/").split("/")[0].split("?")[0]
        return ident if ident.isdigit() else None
    return None


async def publish(task: dict, *_args) -> dict:
    if not configured():
        return {"status": "failed", "error_code": "CONFIG",
                "error_message": "Unipile non configuré (UNIPILE_DSN/API_KEY/ACCOUNT_ID)"}

    text = task.get("text") or ""
    org = _org_id(task.get("page_url"))
    media_urls = task.get("media_urls") or []

    data = {"account_id": ACCOUNT_ID, "text": text}
    if org:
        data["as_organization"] = org

    files = None
    img_bytes = None
    if media_urls:
        try:
            r = httpx.get(media_urls[0], timeout=30)
            r.raise_for_status()
            img_bytes = r.content
        except Exception as e:
            logger.warning(f"Unipile: téléchargement image échoué: {e}")

    if img_bytes:
        files = {"attachments": (f"post_{task.get('post_id', 'x')}.jpg", img_bytes, "image/jpeg")}

    headers = {"X-API-KEY": API_KEY, "accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=90) as cli:
            r = await cli.post(f"{DSN}/api/v1/posts", headers=headers, data=data, files=files)
    except Exception as e:
        return {"status": "failed", "error_code": "UNKNOWN", "error_message": f"requête Unipile: {e}"}

    if r.status_code in (200, 201):
        post_url = None
        try:
            d = r.json()
            post_url = d.get("post_url") or d.get("share_url") or d.get("post_id")
        except Exception:
            pass
        logger.bind(as_org=bool(org)).info("LinkedIn publié via Unipile")
        return {"status": "success", "post_url": post_url}

    return {"status": "failed", "error_code": "PUBLISH_REJECTED",
            "error_message": f"Unipile HTTP {r.status_code}: {r.text[:250]}"}
