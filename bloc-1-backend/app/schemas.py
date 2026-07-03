from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime


# --- Persona ---

class PersonaCreate(BaseModel):
    bu: Literal["noisyless", "afluxo", "mbhrep"]
    nom: str = Field(..., min_length=1, max_length=200)
    besoins: str = Field(..., min_length=10)
    frustrations: str = Field(..., min_length=10)
    cible: str = Field(..., min_length=10)
    charte_branding: dict


class PersonaUpdate(BaseModel):
    bu: Optional[Literal["noisyless", "afluxo", "mbhrep"]] = None
    nom: Optional[str] = None
    besoins: Optional[str] = None
    frustrations: Optional[str] = None
    cible: Optional[str] = None
    charte_branding: Optional[dict] = None


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


# --- Planning ---

class PlanningCreate(BaseModel):
    persona_id: str
    date_debut: datetime
    date_fin: datetime


class PlanningUpdate(BaseModel):
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class PlanningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    date_debut: datetime
    date_fin: datetime
    created_at: datetime
    updated_at: datetime


class PlanningWithPostsRead(PlanningRead):
    posts: list["PostRead"] = []


# --- Post ---

class PostCreate(BaseModel):
    planning_id: str
    persona_id: str
    platform: Literal["linkedin", "instagram"]
    angle_editorial: str = Field(..., min_length=10)
    format: Literal["text_only", "image", "carousel"]


class PostUpdate(BaseModel):
    text: Optional[str] = None
    image_url: Optional[str] = None
    carousel_urls: Optional[list[str]] = None
    status: Optional[Literal["draft", "validated", "scheduled", "published", "failed"]] = None
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    planning_id: str
    persona_id: str
    platform: str
    angle_editorial: str
    format: str
    text: Optional[str]
    image_url: Optional[str]
    carousel_urls: Optional[list[str]]
    status: str
    scheduled_for: Optional[datetime]
    published_at: Optional[datetime]
    published_url: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


PlanningWithPostsRead.model_rebuild()
