import json
import os

from fastapi import APIRouter

router = APIRouter()

_CAPTURE_PATH = "./data/li_captures.jsonl"


@router.post("/capture")
def capture(body: dict):
    """Reçoit une requête interne capturée par l'extension (debug format LinkedIn page)."""
    os.makedirs(os.path.dirname(_CAPTURE_PATH), exist_ok=True)
    with open(_CAPTURE_PATH, "a") as f:
        f.write(json.dumps(body)[:40000] + "\n")
    return {"ok": True}
