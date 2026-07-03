from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Session

from app.agents.interrogator_agent import InterrogatorAgent, MATRIX_FIELDS, FIELD_QUESTIONS
from app.agents.strategist_agent import StrategistAgent
from app.models import GrilledMeSession, Persona
from app.services import persona_service


def _next_field(matrix: dict) -> Optional[str]:
    for f in MATRIX_FIELDS:
        if not matrix.get(f):
            return f
    return None


def _progress(matrix: dict) -> float:
    filled = sum(1 for f in MATRIX_FIELDS if matrix.get(f))
    return round(filled / len(MATRIX_FIELDS), 2)


def start_session(db: Session, bu: str, interrogator: Optional[InterrogatorAgent] = None) -> tuple[str, str]:
    if interrogator is None:
        interrogator = InterrogatorAgent()

    first_question = interrogator.get_first_question(bu)

    session = GrilledMeSession(
        bu=bu,
        matrix={},
        transcript=[{
            "role": "assistant",
            "content": first_question,
            "field": "cible",
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

    # Determine which field the last assistant question was about
    current_field = _next_field(matrix)
    if not current_field:
        raise HTTPException(status_code=400, detail="All fields already filled")

    logger.bind(session_id=session_id, field=current_field).info(f"Handling message: {user_message[:50]}")

    # Extract and store the value for the current field
    value = interrogator.extract_field_value(session.bu, current_field, user_message)
    matrix[current_field] = value

    transcript.append({"role": "user", "content": user_message, "timestamp": datetime.utcnow().isoformat()})

    # Determine next field
    next_field = _next_field(matrix)
    is_complete = next_field is None
    progress = _progress(matrix)

    next_question = None
    if not is_complete:
        next_question = FIELD_QUESTIONS[next_field]
        transcript.append({
            "role": "assistant",
            "content": next_question,
            "field": next_field,
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
