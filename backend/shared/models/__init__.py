"""NUCLEUS V1.2 - SQLAlchemy Models"""

from .base import Base, get_db, init_db, engine, SessionLocal
from .dna import Entity, Interest, Goal, Value, RawData, DailyReadiness, EnergyPattern
from .dna_extended import (
    PersonalityTrait, CommunicationStyle, DecisionPattern, WorkHabit,
    Relationship, Skill, Preference, Constraint, Belief, Experience,
    Emotion, Routine, Context, EvolutionHistory
)
from .memory import (
    Conversation, Summary, Embedding, 
    MemoryTier1, MemoryTier2, MemoryTier3, MemoryTier4, 
    HealthMetric, CalendarEvent, EmailMessage, Briefing
)
from .assembly import Agent, Tool, AgentTool, AgentPerformance, AgentNeed, AgentLifecycleEvent
from .execution import Task, Job, Log
from .integrations import EntityIntegration

__all__ = [
    # Base
    "Base",
    "get_db",
    "init_db",
    "engine",
    "SessionLocal",
    # DNA - Core
    "Entity",
    "Interest",
    "Goal",
    "Value",
    "RawData",
    "DailyReadiness",
    "EnergyPattern",
    # DNA - Extended (V2.0)
    "PersonalityTrait",
    "CommunicationStyle",
    "DecisionPattern",
    "WorkHabit",
    "Relationship",
    "Skill",
    "Preference",
    "Constraint",
    "Belief",
    "Experience",
    "Emotion",
    "Routine",
    "Context",
    "EvolutionHistory",
    # Memory
    "Conversation",
    "Summary",
    "Embedding",
    "MemoryTier1",
    "MemoryTier2",
    "MemoryTier3",
    "MemoryTier4",
    "HealthMetric",
    "CalendarEvent",
    "EmailMessage",
    "Briefing",
    # Assembly
    "Agent",
    "Tool",
    "AgentTool",
    "AgentPerformance",
    "AgentNeed",
    "AgentLifecycleEvent",
    # Execution
    "Task",
    "Job",
    "Log",
    # Integrations
    "EntityIntegration",
]
