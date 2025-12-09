"""
NUCLEUS V1.2 - DNA Schema Models
Entity identity, values, goals, interests
"""

from sqlalchemy import Column, String, Text, Float, Boolean, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Entity(Base):
    """Main entity (user) table"""
    __tablename__ = "entity"
    __table_args__ = {"schema": "dna"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interests = relationship("Interest", back_populates="entity", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="entity", cascade="all, delete-orphan")
    values = relationship("Value", back_populates="entity", cascade="all, delete-orphan")
    raw_data = relationship("RawData", back_populates="entity", cascade="all, delete-orphan")


class Interest(Base):
    """Entity interests discovered from interactions"""
    __tablename__ = "interests"
    __table_args__ = {"schema": "dna"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"))
    interest_name = Column(String(255), nullable=False)
    interest_description = Column(Text)
    confidence_score = Column(Float, default=0.0)
    first_detected_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_reinforced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    entity = relationship("Entity", back_populates="interests")


class Goal(Base):
    """Entity goals and objectives"""
    __tablename__ = "goals"
    __table_args__ = {"schema": "dna"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"))
    goal_title = Column(String(500), nullable=False)
    goal_description = Column(Text)
    priority = Column(Integer, default=5)
    status = Column(String(50), default="active")  # active, completed, archived
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    entity = relationship("Entity", back_populates="goals")


class Value(Base):
    """Entity core values"""
    __tablename__ = "values"
    __table_args__ = {"schema": "dna"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"))
    value_name = Column(String(255), nullable=False)
    value_description = Column(Text)
    importance_score = Column(Float, default=0.5)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    entity = relationship("Entity", back_populates="values")


class RawData(Base):
    """Raw data ingested for DNA analysis"""
    __tablename__ = "raw_data"
    __table_args__ = {"schema": "dna"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("dna.entity.id", ondelete="CASCADE"))
    data_type = Column(String(100), nullable=False)  # conversation, document, interaction
    data_content = Column(Text, nullable=False)
    meta_data = Column(JSONB)
    ingested_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    entity = relationship("Entity", back_populates="raw_data")
