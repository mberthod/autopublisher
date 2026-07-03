from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.interrogator_agent import InterrogatorAgent, MATRIX_FIELDS
from app.agents.strategist_agent import StrategistAgent
from app.models import GrilledMeSession, Persona
from app.services import persona_service


def start_session(db: Session, bu: str, interrogator: Optional[InterrogatorAgent] = None) -> tuple[str, str]:
    if interrogator is None:
        interrogator = InterrogatorAgent()

    result = interrogator.start_session(bu)
    first_question = result.get("next_question") or "Décrivez votre cible client idéale."

    session = GrilledMeSession(
        bu=bu,
        matrix=result.get("matrix_update", {}),
        transcript=[{"role": "assistant", "content": first_question, "timestamp": datetime.utcnow().isoformat()}],
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

    logger.bind(session_id=session_id).info(f"Handling message: {user_message[:50]}")

    transcript = list(session.transcript)
    transcript.append({"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()})

    matrix = dict(session.matrix)
    result = interrogator.process_message(session.bu, matrix, transcript, user_message)

    matrix_update = result.get("matrix_update", {})
    if isinstance(matrix_update, dict):
        matrix.update(matrix_update)

    next_question = result.get("next_question")
    is_complete = result.get("is_complete", False)
    progress = float(result.get("matrix_progress", _compute_progress(matrix)))
    current_field = _get_current_field(matrix)

    if next_question:
        transcript.append({"role": "assistant", "content": next_question, "timestamp": datetime.utcnow().isoformat()})

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


def _compute_progress(matrix: dict) -> float:
    filled = sum(1 for f in MATRIX_FIELDS if matrix.get(f))
    return round(filled / len(MATRIX_FIELDS), 2)


def _get_current_field(matrix: dict) -> Optional[str]:
    for field in MATRIX_FIELDS:
        if not matrix.get(field):
            return field
    return None
