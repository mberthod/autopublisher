"""Publication LinkedIn côté serveur via Playwright headless.

Rejoue la session de l'utilisateur (cookies capturés par l'extension) pour publier
sur son profil ou une page entreprise, sans navigateur ouvert sur son PC.
"""
import asyncio
import unicodedata
from typing import Optional

import httpx
from loguru import logger
from playwright.async_api import async_playwright

FEED_COMPOSE_URL = "https://www.linkedin.com/feed/?shareActive=true&shareContentType=post"
LOGIN_RE = ("/login", "/checkpoint", "/authwall", "/uas/login", "/signup")

OPEN_COMPOSE = [
    "button[aria-label='Commencer un post']",
    "button[aria-label='Start a post']",
    "button.share-box-feed-entry__trigger",
    "div.share-box-feed-entry__top-bar button",
    "button:has-text('Commencer un post')",
    "button:has-text('Start a post')",
]
EDITOR = "div[role='textbox'][contenteditable='true'], div.ql-editor[contenteditable='true']"
ACTOR_NAME = ".share-creation-state__actor-name, button[class*='actor'] span, .share-box-feed-entry__closed-share-box"
SUBMIT = [
    "button.share-actions__primary-action",
    "button[aria-label='Publier']",
    "button[aria-label='Post']",
    "button:has-text('Publier')",
]


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower().strip()


def _identity_matches(actual: str, expected: str) -> bool:
    a, e = _norm(actual), _norm(expected)
    return bool(a and e and (e in a or a in e))


async def _download(url: str, path: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.get(url)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        return True
    except Exception as e:
        logger.warning(f"media download failed: {e}")
        return False


async def publish(task: dict, cookies: list[dict], user_agent: Optional[str]) -> dict:
    """Retourne {status: success|failed, post_url?, error_code?, error_message?}."""
    from cookies import to_playwright

    page_url = task.get("page_url") or FEED_COMPOSE_URL
    text = task.get("text") or ""
    media_urls = task.get("media_urls") or []
    publish_as = task.get("publish_as_name")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            context = await browser.new_context(
                user_agent=user_agent or None,
                viewport={"width": 1280, "height": 900},
                locale="fr-FR",
            )
            await context.add_cookies(to_playwright(cookies))
            page = await context.new_page()
            await page.goto(page_url, wait_until="domcontentloaded", timeout=45_000)
            await page.wait_for_timeout(3000)

            if any(k in page.url for k in LOGIN_RE):
                return {"status": "failed", "error_code": "AUTH_REQUIRED",
                        "error_message": f"Session invalide (redirige vers {page.url})"}

            # Ouvrir le compositeur
            editor = await _open_composer(page)
            if editor is None:
                return {"status": "failed", "error_code": "SELECTOR_NOT_FOUND",
                        "error_message": "Compositeur LinkedIn introuvable"}

            # Vérifier l'identité de publication (page entreprise) avant de publier
            if publish_as:
                actual = await _read_actor(page)
                if not _identity_matches(actual, publish_as):
                    return {"status": "failed", "error_code": "WRONG_IDENTITY",
                            "error_message": f"Compositeur en tant que '{actual or 'inconnu'}' au lieu de '{publish_as}'"}

            # Saisir le texte
            await editor.click()
            await page.wait_for_timeout(500)
            if text:
                await editor.type(text, delay=15)

            # Média
            if media_urls:
                path = f"/tmp/li_{task.get('post_id', 'x')}.png"
                if await _download(media_urls[0], path):
                    file_input = await page.query_selector("input[type='file']")
                    if file_input:
                        await file_input.set_input_files(path)
                        await page.wait_for_timeout(4000)

            # Publier
            if not await _click_first(page, SUBMIT):
                return {"status": "failed", "error_code": "SELECTOR_NOT_FOUND",
                        "error_message": "Bouton Publier introuvable"}

            # Confirmation (toast) + tentative de récupération de l'URL du post
            post_url = None
            try:
                await page.wait_for_selector("div[role='alert'], div[class*='artdeco-toast']", timeout=30_000)
                link = await page.query_selector("div[class*='artdeco-toast'] a[href*='/feed/update/'], div[role='alert'] a[href*='/feed/update/']")
                if link:
                    post_url = await link.get_attribute("href")
            except Exception:
                pass

            return {"status": "success", "post_url": post_url}
        except Exception as e:
            return {"status": "failed", "error_code": "UNKNOWN", "error_message": str(e)}
        finally:
            await browser.close()


async def _open_composer(page):
    # L'editeur est peut-etre deja la (URL ?shareActive=true)
    ed = await page.query_selector(EDITOR)
    if ed and await ed.is_visible():
        return ed
    await _click_first(page, OPEN_COMPOSE)
    try:
        await page.wait_for_selector(EDITOR, timeout=12_000, state="visible")
        return await page.query_selector(EDITOR)
    except Exception:
        return None


async def _read_actor(page) -> str:
    el = await page.query_selector(ACTOR_NAME)
    if el:
        return (await el.inner_text()).strip()
    return ""


async def _click_first(page, selectors: list[str]) -> bool:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False
