from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

Base = declarative_base()


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Persona(Base):
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=gen_uuid)
    bu = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    besoins = Column(Text, nullable=False)
    frustrations = Column(Text, nullable=False)
    cible = Column(Text, nullable=False)
    charte_branding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Deprecies — remplaces par la table accounts (conserves en lecture le temps
    # d'une release, plus exposes en ecriture par l'API)
    linkedin_page_url = Column(String, nullable=True)
    instagram_page_url = Column(String, nullable=True)

    plannings = relationship("Planning", back_populates="persona", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="persona", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    kind = Column(String, default="personal", nullable=False)
    page_url = Column(String, nullable=True)
    identity_name = Column(String, nullable=True)
    asset_id = Column(String, nullable=True)
    enabled = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    persona = relationship("Persona", back_populates="accounts")


class Planning(Base):
    __tablename__ = "plannings"

    id = Column(String, primary_key=True, default=gen_uuid)
    persona_id = Column(String, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    date_debut = Column(DateTime, nullable=False)
    date_fin = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    persona = relationship("Persona", back_populates="plannings")
    posts = relationship("Post", back_populates="planning", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=gen_uuid)
    planning_id = Column(String, ForeignKey("plannings.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(String, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    angle_editorial = Column(Text, nullable=False)
    format = Column(String, nullable=False)
    text = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    carousel_urls = Column(JSON, nullable=True)
    status = Column(String, default="draft", nullable=False)
    scheduled_for = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    published_url = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    account_id = Column(String, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    planning = relationship("Planning", back_populates="posts")
    persona = relationship("Persona")
    account = relationship("Account")
    metrics = relationship("PostMetrics", back_populates="post", cascade="all, delete-orphan")


class Positioning(Base):
    """Positionnement stratégique par BU, éditable, injecté dans les prompts
    de génération (idées + posts) pour produire du contenu pertinent."""
    __tablename__ = "positionings"

    id = Column(String, primary_key=True, default=gen_uuid)
    bu = Column(String, nullable=False, unique=True)  # noisyless|afluxo|mbhrep
    content = Column(Text, nullable=True)             # positionnement (cible, douleur, diff, ton…)
    keywords = Column(Text, nullable=True)            # mots-clés / thèmes pour la génération d'idées
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Session(Base):
    """Session de navigateur (cookies) capturee par l'extension et rejouee
    cote serveur par le publisher Playwright. Une session active par plateforme."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    platform = Column(String, nullable=False, unique=True)  # linkedin|instagram|meta_suite
    cookies = Column(JSON, nullable=False)                  # [{name,value,domain,path,secure,httpOnly,expirationDate,...}]
    user_agent = Column(String, nullable=True)
    valid = Column(Integer, default=1, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    reposts = Column(Integer, default=0)
    views = Column(Integer, default=0)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="metrics")
