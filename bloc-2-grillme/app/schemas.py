from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    bu: Literal["noisyless", "afluxo", "mbhrep"]


class SessionStartResponse(BaseModel):
    session_id: str
    first_question: str


class MessageRequest(BaseModel):
    user_message: str


class MessageResponse(BaseModel):
    next_question: Optional[str]
    matrix_progress: float
    current_field: Optional[str]
    is_complete: bool


class PersonaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bu: str
    nom: str
    besoins: str
    frustrations: str
    cible: str
    charte_branding: dict
    created_at: datetime
    updated_at: datetime


class TranscriptEntry(BaseModel):
    role: str
    content: str
    timestamp: str


class SessionPersonaResponse(BaseModel):
    persona: PersonaRead
    transcript: list[dict[str, Any]]


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bu: str
    status: str
    matrix: dict
    transcript: list
    persona_id: Optional[str]
    created_at: datetime
    updated_at: datetime
