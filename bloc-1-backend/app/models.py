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

    linkedin_page_url = Column(String, nullable=True)
    instagram_page_url = Column(String, nullable=True)

    plannings = relationship("Planning", back_populates="persona", cascade="all, delete-orphan")


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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    planning = relationship("Planning", back_populates="posts")
    persona = relationship("Persona")
    metrics = relationship("PostMetrics", back_populates="post", cascade="all, delete-orphan")


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
