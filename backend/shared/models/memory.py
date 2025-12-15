"""
NUCLEUS V1.2 - Memory Schema Models
Conversation history, summaries, vector embeddings
"""

from sqlalchemy import Column, String, Text, TIMESTAMP, Integer, Float, ForeignKey
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


# ============================================================================
# Phase 1 - V2.0: 4-Tier Memory Architecture
# ============================================================================

class MemoryTier1(Base):
    """
    Tier 1: Ultra-fast memory (< 10ms latency)
    Storage: Redis/In-Memory Cache
    Retention: Last 24 hours of interactions
    """
    __tablename__ = "memory_tier1"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(100), nullable=False)  # conversation, action, event
    interaction_data = Column(JSONB, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    ttl_hours = Column(Integer, default=24, comment="Time to live in hours before moving to Tier 2")


class MemoryTier2(Base):
    """
    Tier 2: Fast memory (< 100ms latency)
    Storage: PostgreSQL (hot data)
    Retention: Last 7-30 days
    """
    __tablename__ = "memory_tier2"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(100), nullable=False)
    interaction_data = Column(JSONB, nullable=False)
    summary = Column(Text, nullable=True, comment="LLM-generated summary for quick retrieval")
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    moved_from_tier1_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    ttl_days = Column(Integer, default=30, comment="Time to live in days before moving to Tier 3")


class MemoryTier3(Base):
    """
    Tier 3: Semantic memory (< 500ms latency)
    Storage: PostgreSQL + pgvector (vector search)
    Retention: 30-365 days
    """
    __tablename__ = "memory_tier3"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False, comment="Condensed summary of the interaction")
    embedding = Column(Vector(1536), comment="Vector embedding for semantic search")
    importance_score = Column(Float, default=0.5, comment="0-1 score indicating importance")
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    moved_from_tier2_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    ttl_days = Column(Integer, default=365, comment="Time to live in days before archiving to Tier 4")


class MemoryTier4(Base):
    """
    Tier 4: Long-term archive (> 1s latency acceptable)
    Storage: Google Cloud Storage (JSON files)
    Retention: Indefinite (compressed, cold storage)
    Note: This table stores metadata only; actual data is in GCS
    """
    __tablename__ = "memory_tier4"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    gcs_bucket = Column(String(255), nullable=False, comment="GCS bucket name")
    gcs_path = Column(String(500), nullable=False, comment="Full path to the archived file in GCS")
    time_period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    time_period_end = Column(TIMESTAMP(timezone=True), nullable=False)
    record_count = Column(Integer, nullable=False, comment="Number of interactions in this archive")
    file_size_bytes = Column(Integer, nullable=True)
    archived_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# ============================================================================
# Phase 3: Health & Wellness Data
# ============================================================================

class HealthMetric(Base):
    """
    Raw health and wellness data from IOT devices.
    Stores individual measurements from devices like Oura Ring, Apple Watch, etc.
    """
    __tablename__ = "health_metrics"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    
    # Metric details
    metric_type = Column(String(50), nullable=False)  # sleep_score, hrv, heart_rate, steps
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # bpm, steps, hours
    
    # Source tracking
    source = Column(String(50), nullable=False)  # oura, apple_health, garmin
    source_id = Column(String(255))  # External ID
    
    # Temporal
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Metadata
    meta_data = Column(JSONB, default={})


# ============================================================================
# Phase 4: Calendar & Email Integration
# ============================================================================

class CalendarEvent(Base):
    """
    Calendar events from connected calendar services.
    Stores events from Google Calendar, Outlook, etc.
    """
    __tablename__ = "calendar_events"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    
    # Event details
    external_id = Column(String(255), nullable=True, comment="External calendar event ID")
    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    
    # Temporal
    start_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False)
    all_day = Column(Integer, default=0)
    
    # Attendees and organizer
    organizer = Column(String(255), nullable=True)
    attendees = Column(JSONB, default=[])
    
    # Source tracking
    source = Column(String(50), nullable=False, default="google")  # google, outlook, apple
    calendar_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(50), default="confirmed")  # confirmed, tentative, cancelled
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Metadata
    meta_data = Column(JSONB, default={})


class EmailMessage(Base):
    """
    Email messages from connected email services.
    Stores emails from Gmail, Outlook, etc.
    """
    __tablename__ = "email_messages"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    
    # Email identifiers
    external_id = Column(String(255), nullable=True, comment="External email message ID")
    thread_id = Column(String(255), nullable=True)
    
    # Email content
    subject = Column(String(1000), nullable=True)
    snippet = Column(Text, nullable=True, comment="Short preview of email content")
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    
    # Sender and recipients
    sender = Column(String(500), nullable=False)
    recipients_to = Column(JSONB, default=[])
    recipients_cc = Column(JSONB, default=[])
    recipients_bcc = Column(JSONB, default=[])
    
    # Temporal
    received_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Source tracking
    source = Column(String(50), nullable=False, default="gmail")  # gmail, outlook
    
    # Status
    is_read = Column(Integer, default=0)
    is_starred = Column(Integer, default=0)
    labels = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Metadata
    meta_data = Column(JSONB, default={})


class Briefing(Base):
    """
    AI-generated briefings for meetings and events.
    Contains pre-meeting context and recommendations.
    """
    __tablename__ = "briefings"
    __table_args__ = {"schema": "memory"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"), nullable=False)
    
    # Related event
    event_id = Column(UUID(as_uuid=True), ForeignKey("memory.calendar_events.id", ondelete="CASCADE"), nullable=True)
    
    # Briefing content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    
    # Context sources
    email_count = Column(Integer, default=0)
    previous_meetings_count = Column(Integer, default=0)
    context_sources = Column(JSONB, default={})
    
    # Status
    status = Column(String(50), default="draft")  # draft, generated, sent, viewed
    
    # Timestamps
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    viewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Metadata
    meta_data = Column(JSONB, default={})
