"""Publication LinkedIn via l'API interne "Voyager" (HTTP direct, comme Unipile).

On ne pilote PAS un navigateur : on rejoue la session (cookie li_at + JSESSIONID
qui sert de jeton csrf) et on appelle directement les endpoints internes que le
site LinkedIn utilise. Rapide et sans DOM.

Note : API non documentée + contraire aux CGU LinkedIn. Endpoints susceptibles de
changer — on loggue les réponses en détail pour pouvoir ajuster.
"""
from typing import Optional

import httpx
from loguru import logger

VOYAGER = "https://www.linkedin.com/voyager/api"
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _cookies_by_name(cookies: list[dict]) -> dict:
    return {c["name"]: c["value"] for c in cookies if c.get("name")}


def _cookie_header(cookies: list[dict]) -> str:
    return "; ".join(f'{c["name"]}={c["value"]}' for c in cookies if c.get("name"))


def _headers(cookies: list[dict], user_agent: Optional[str]) -> Optional[dict]:
    by_name = _cookies_by_name(cookies)
    if "li_at" not in by_name:
        return None
    # csrf-token = valeur de JSESSIONID sans les guillemets
    jsession = by_name.get("JSESSIONID", "").strip('"')
    if not jsession:
        return None
    return {
        "cookie": _cookie_header(cookies),
        "csrf-token": jsession,
        "x-restli-protocol-version": "2.0.0",
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "content-type": "application/json; charset=UTF-8",
        "user-agent": user_agent or DEFAULT_UA,
        "x-li-lang": "fr_FR",
        "origin": "https://www.linkedin.com",
        "referer": "https://www.linkedin.com/feed/",
    }


def _org_urn_from_page_url(page_url: Optional[str]) -> Optional[str]:
    """Extrait l'URN d'organisation d'une URL de page admin, ex.
    https://www.linkedin.com/company/115871126/admin/... -> urn:li:organization:115871126"""
    if not page_url or "/company/" not in page_url:
        return None
    tail = page_url.split("/company/", 1)[1].strip("/")
    ident = tail.split("/")[0].split("?")[0]
    return f"urn:li:organization:{ident}" if ident.isdigit() else None


async def publish(task: dict, cookies: list[dict], user_agent: Optional[str]) -> dict:
    text = task.get("text") or ""
    page_url = task.get("page_url")
    org_urn = _org_urn_from_page_url(page_url)

    headers = _headers(cookies, user_agent)
    if headers is None:
        return {"status": "failed", "error_code": "AUTH_REQUIRED",
                "error_message": "Cookies li_at/JSESSIONID absents — resynchronise la session"}

    # Payload de creation de post texte (endpoint interne normShares)
    payload = {
        "visibleToConnectionsOnly": False,
        "externalAudienceProviders": [],
        "commentaryV2": {"text": text, "attributes": []},
        "origin": "FEED",
        "allowedCommentersScope": "ALL",
        "postState": "PUBLISHED",
        "media": [],
    }
    # Publier en tant que page entreprise : attribuer le post a l'organisation
    if org_urn:
        payload["containerEntity"] = org_urn

    url = f"{VOYAGER}/contentcreation/normShares"
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
        except Exception as e:
            return {"status": "failed", "error_code": "UNKNOWN", "error_message": f"requete: {e}"}

    # 401/403 → session invalide ; redirection login idem
    if r.status_code in (401, 403) or (300 <= r.status_code < 400):
        return {"status": "failed", "error_code": "AUTH_REQUIRED",
                "error_message": f"HTTP {r.status_code} (session invalide ?)"}

    if r.status_code not in (200, 201):
        # Loggue le detail pour ajuster l'endpoint/payload au besoin
        body = r.text[:500]
        logger.warning(f"normShares HTTP {r.status_code}: {body}")
        return {"status": "failed", "error_code": "PUBLISH_REJECTED",
                "error_message": f"HTTP {r.status_code}: {body[:200]}"}

    # Succes : tenter d'extraire l'URN de l'activite pour construire l'URL du post
    post_url = None
    try:
        data = r.json()
        urn = _find_activity_urn(data)
        if urn:
            post_url = f"https://www.linkedin.com/feed/update/{urn}/"
    except Exception:
        pass

    logger.bind(as_org=bool(org_urn)).info("post publie via Voyager")
    return {"status": "success", "post_url": post_url}


def _find_activity_urn(data) -> Optional[str]:
    """Cherche un urn:li:activity:... dans la reponse JSON."""
    import json as _json
    blob = _json.dumps(data)
    marker = "urn:li:activity:"
    i = blob.find(marker)
    if i == -1:
        return None
    j = i + len(marker)
    digits = ""
    while j < len(blob) and blob[j].isdigit():
        digits += blob[j]
        j += 1
    return f"{marker}{digits}" if digits else None
