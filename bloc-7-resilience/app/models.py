import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class QueueTask(Base):
    __tablename__ = "queue_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", nullable=False)
    # "pending" | "running" | "success" | "failed"
    attempts = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
