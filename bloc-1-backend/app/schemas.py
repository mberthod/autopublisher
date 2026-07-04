from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime

# Alias centralises — seul point de changement pour ajouter une plateforme
Platform = Literal["linkedin", "instagram", "facebook", "tiktok"]
AccountKind = Literal["personal", "company_page", "business_account"]


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
    linkedin_page_url: Optional[str] = None
    instagram_page_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# --- Account (cible de publication : page entreprise, compte pro, profil) ---

class AccountCreate(BaseModel):
    persona_id: str
    platform: Platform
    kind: AccountKind = "personal"
    page_url: Optional[str] = None
    identity_name: Optional[str] = None
    asset_id: Optional[str] = None
    enabled: bool = True


class AccountUpdate(BaseModel):
    platform: Optional[Platform] = None
    kind: Optional[AccountKind] = None
    page_url: Optional[str] = None
    identity_name: Optional[str] = None
    asset_id: Optional[str] = None
    enabled: Optional[bool] = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    persona_id: str
    platform: str
    kind: str
    page_url: Optional[str] = None
    identity_name: Optional[str] = None
    asset_id: Optional[str] = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


# --- Session (cookies navigateur pour publication serveur) ---

class SessionUpsert(BaseModel):
    platform: Platform
    cookies: list[dict]
    user_agent: Optional[str] = None


class SessionRead(BaseModel):
    """Etat de session SANS exposer les cookies (pour dashboard/popup)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    user_agent: Optional[str] = None
    valid: bool
    last_error: Optional[str] = None
    cookie_count: int = 0
    updated_at: datetime


class SessionWithCookies(SessionRead):
    """Reservee au publisher serveur : inclut les cookies."""
    cookies: list[dict]


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
    platform: Platform
    angle_editorial: str = Field(..., min_length=10)
    format: Literal["text_only", "image", "carousel"]
    account_id: Optional[str] = None


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
    account_id: Optional[str] = None


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
    account_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


PlanningWithPostsRead.model_rebuild()
