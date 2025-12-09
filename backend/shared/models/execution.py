"""
NUCLEUS V1.2 - Execution Schema Models
Tasks, jobs, logs, operational data
"""

from sqlalchemy import Column, String, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from .base import Base


class Task(Base):
    """Tasks assigned to agents"""
    __tablename__ = "tasks"
    __table_args__ = {"schema": "execution"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    task_title = Column(String(500), nullable=False)
    task_description = Column(Text)
    assigned_agent_id = Column(UUID(as_uuid=True))
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    priority = Column(Integer, default=5)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    meta_data = Column(JSONB)


class Job(Base):
    """Cloud Run Jobs execution records"""
    __tablename__ = "jobs"
    __table_args__ = {"schema": "execution"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String(255), nullable=False)
    job_type = Column(String(100), nullable=False)  # dna_analysis, interpretation, qa, etc.
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    result = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Log(Base):
    """System logs"""
    __tablename__ = "logs"
    __table_args__ = {"schema": "execution"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    service_name = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
