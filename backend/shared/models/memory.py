"""
NUCLEUS V1.2 - Memory Schema Models
Conversation history, summaries, vector embeddings
"""

from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from .base import Base


class Conversation(Base):
    """Conversation messages"""
    __tablename__ = "conversations"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    meta_data = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Summary(Base):
    """Conversation and period summaries"""
    __tablename__ = "summaries"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    summary_type = Column(String(100), nullable=False)  # daily, weekly, topic
    summary_content = Column(Text, nullable=False)
    time_period_start = Column(TIMESTAMP(timezone=True))
    time_period_end = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Embedding(Base):
    """Vector embeddings for semantic search"""
    __tablename__ = "embeddings"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    source_type = Column(String(100), nullable=False)  # conversation, document, summary
    source_id = Column(UUID(as_uuid=True), nullable=False)
    content_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI ada-002 dimension
    meta_data = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
