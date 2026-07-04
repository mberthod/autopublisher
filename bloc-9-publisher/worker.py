"""Worker de publication côté serveur.

Remplace l'extension Chrome : poll les tâches à publier, rejoue la session
(cookies) via Playwright headless et publie — même PC de l'utilisateur éteint.
"""
import asyncio
import os
import sys

import httpx
from loguru import logger

import ig_publisher

BACKEND = os.environ.get("BACKEND_URL", "http://192.168.0.176:8000")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
API = f"{BACKEND}/api/v1"

# Instagram est publié côté serveur (instagrapi + sessionid). LinkedIn reste géré
# par l'extension (API interne depuis le navigateur, session web valide seulement là).
PUBLISHERS = {"instagram": ig_publisher.publish}

_in_flight: set[str] = set()


async def poll_once(client: httpx.AsyncClient):
    try:
        r = await client.get(f"{API}/tasks/pending", timeout=30)
        r.raise_for_status()
        tasks = r.json().get("tasks", [])
    except Exception as e:
        logger.warning(f"poll failed: {e}")
        return

    for task in tasks:
        tid = task["task_id"]
        route = task.get("publish_via") or task["platform"]
        if tid in _in_flight:
            continue
        if route not in PUBLISHERS:
            logger.info(f"task {tid[:8]} route '{route}' non gérée côté serveur (skip)")
            continue
        _in_flight.add(tid)
        try:
            await process(client, task, route)
        finally:
            _in_flight.discard(tid)


async def process(client: httpx.AsyncClient, task: dict, route: str):
    tid = task["task_id"]
    logger.info(f"publishing {tid[:8]} via {route} (as: {task.get('publish_as_name')})")

    # Récupérer la session (cookies)
    try:
        r = await client.get(f"{API}/sessions/{route}/cookies", timeout=20)
        if r.status_code == 404:
            await callback(client, tid, failed("AUTH_REQUIRED", f"Aucune session {route} — synchronise depuis l'extension"))
            return
        r.raise_for_status()
        sess = r.json()
    except Exception as e:
        await callback(client, tid, failed("UNKNOWN", f"lecture session: {e}"))
        return

    if not sess.get("valid", True):
        await callback(client, tid, failed("AUTH_REQUIRED", f"Session {route} marquée invalide"))
        return

    # Publier
    try:
        result = await PUBLISHERS[route](task, sess.get("cookies", []), sess.get("user_agent"))
    except Exception as e:
        logger.exception("publish crashed")
        result = failed("UNKNOWN", str(e))

    # Session invalide → la marquer pour alerter l'utilisateur
    if result.get("status") == "failed" and result.get("error_code") == "AUTH_REQUIRED":
        try:
            await client.post(f"{API}/sessions/{route}/invalidate", params={"error": result.get("error_message", "")})
        except Exception:
            pass

    await callback(client, tid, result)
    logger.bind(status=result.get("status"), code=result.get("error_code")).info(f"done {tid[:8]}")


def failed(code: str, msg: str) -> dict:
    return {"status": "failed", "error_code": code, "error_message": msg}


async def callback(client: httpx.AsyncClient, task_id: str, result: dict):
    payload = dict(result)
    if payload.get("status") == "success":
        payload.setdefault("post_url", result.get("post_url"))
    try:
        await client.post(f"{API}/tasks/{task_id}/callback", json=payload, timeout=20)
    except Exception as e:
        logger.error(f"callback failed for {task_id[:8]}: {e}")


async def main():
    logger.info(f"Publisher worker démarré — backend={BACKEND}, poll={POLL_INTERVAL}s, routes={list(PUBLISHERS)}")
    async with httpx.AsyncClient() as client:
        while True:
            await poll_once(client)
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
