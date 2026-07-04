"""Publie une seule tâche immédiatement (debug), sans attendre le poll.

Usage: .venv/bin/python run_once.py [task_id]
Sans argument : traite la première tâche LinkedIn en attente.
"""
import asyncio
import os
import sys

import httpx
from loguru import logger

import worker

API = worker.API


async def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API}/tasks/pending", timeout=30)
        tasks = r.json().get("tasks", [])
        if not tasks:
            logger.info("Aucune tâche en attente.")
            return
        task = next((t for t in tasks if t["task_id"] == want), None) if want else \
            next((t for t in tasks if (t.get("publish_via") or t["platform"]) == "linkedin"), None)
        if not task:
            logger.info(f"Tâche introuvable (want={want}). Tâches: {[(t['task_id'][:8], t['platform']) for t in tasks]}")
            return
        route = task.get("publish_via") or task["platform"]
        logger.info(f"Traitement {task['task_id'][:8]} via {route}")
        await worker.process(client, task, route)


if __name__ == "__main__":
    asyncio.run(main())
