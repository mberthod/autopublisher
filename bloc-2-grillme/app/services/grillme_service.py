from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.interrogator_agent import InterrogatorAgent
from app.agents.strategist_agent import StrategistAgent
from app.models import GrilledMeSession, Persona
from app.services import persona_service

MAX_EXCHANGES = 12


def start_session(db: Session, bu: str, interrogator: Optional[InterrogatorAgent] = None) -> tuple[str, str]:
    if interrogator is None:
        interrogator = InterrogatorAgent()

    result = interrogator.start_session(bu)
    first_question = result["next_question"]

    session = GrilledMeSession(
        bu=bu,
        matrix={},
        transcript=[{
            "role": "assistant",
            "content": first_question,
            "timestamp": datetime.utcnow().isoformat(),
        }],
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.bind(session_id=session.id, bu=bu).info("GrilledMe session started")
    return session.id, first_question


def handle_message(
    db: Session,
    session_id: str,
    user_message: str,
    interrogator: Optional[InterrogatorAgent] = None,
    strategist: Optional[StrategistAgent] = None,
) -> dict:
    session = db.query(GrilledMeSession).filter(GrilledMeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Session is {session.status}, not in_progress")

    if interrogator is None:
        interrogator = InterrogatorAgent()
    if strategist is None:
        strategist = StrategistAgent()

    matrix = dict(session.matrix)
    transcript = list(session.transcript)

    # Hard cap on exchanges
    exchange_count = sum(1 for t in transcript if t.get("role") == "user")
    if exchange_count >= MAX_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum de {MAX_EXCHANGES} échanges atteint. Démarrez une nouvelle session."
        )

    # Add user message to transcript
    transcript.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Call the LLM agent
    result = interrogator.process_message(session.bu, matrix, transcript, user_message)

    # Update matrix with extracted values
    for field, value in (result.get("matrix_update") or {}).items():
        if value and str(value).strip():
            matrix[field] = value

    is_complete = result.get("is_complete", False)
    next_question = result.get("next_question")
    progress = float(result.get("matrix_progress", 0.0))

    if next_question:
        transcript.append({
            "role": "assistant",
            "content": next_question,
            "timestamp": datetime.utcnow().isoformat(),
        })

    session.matrix = matrix
    session.transcript = transcript
    session.updated_at = datetime.utcnow()

    if is_complete:
        persona_data = strategist.create_persona(session.bu, matrix)
        persona = persona_service.create(
            db=db,
            bu=session.bu,
            nom=persona_data["nom"],
            besoins=persona_data["besoins"],
            frustrations=persona_data["frustrations"],
            cible=persona_data["cible"],
            charte_branding=persona_data["charte_branding"],
        )
        session.persona_id = persona.id
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        logger.bind(session_id=session_id, persona_id=persona.id).info("Session completed, persona saved")

    db.commit()
    db.refresh(session)

    # Determine which field is currently being filled (for UI progress)
    MATRIX_FIELDS = ["cible", "besoins", "frustrations", "charte"]
    current_field = next((f for f in MATRIX_FIELDS if not matrix.get(f)), None)

    return {
        "next_question": next_question,
        "matrix_progress": progress,
        "current_field": current_field,
        "is_complete": is_complete,
    }


def get_session_persona(db: Session, session_id: str) -> dict:
    session = db.query(GrilledMeSession).filter(GrilledMeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session.status != "completed" or not session.persona_id:
        raise HTTPException(status_code=400, detail="Session not completed yet")

    persona = db.query(Persona).filter(Persona.id == session.persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    return {"persona": persona, "transcript": session.transcript}
