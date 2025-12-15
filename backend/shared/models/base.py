"""
NUCLEUS V1.2 - SQLAlchemy Base Configuration

This module provides lazy database initialization to support Cloud Run deployments
where DATABASE_URL may not be available at import time.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import os
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

# Base class for all models - this is safe to create at import time
Base = declarative_base()

# Private storage for lazy initialization
_engine = None
_session_local = None
_database_url = None


def _get_database_url() -> str:
    """Get the database URL, with fallback for development."""
    global _database_url
    if _database_url is None:
        url = os.getenv("DATABASE_URL", "")
        if url:
            _database_url = url
        else:
            # Fallback for local development only
            _database_url = "postgresql://nucleus:password@localhost:5432/nucleus"
            logger.warning("DATABASE_URL not set, using local fallback")
    return _database_url


def get_engine():
    """
    Get or create the database engine (lazy initialization).
    
    This function is safe to call even if DATABASE_URL is not set at import time.
    The engine will be created on first actual use.
    """
    global _engine
    if _engine is None:
        try:
            db_url = _get_database_url()
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=10,
                max_overflow=20,
                echo=False  # Set to True for SQL logging
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    return _engine


def get_session_local():
    """
    Get or create the session factory (lazy initialization).
    """
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _session_local


# For backward compatibility - these are functions/properties that delay initialization
# IMPORTANT: Do NOT use these at module level - use get_engine() and get_session_local() instead
engine = None  # Placeholder - will be set on first use via get_engine()
SessionLocal = None  # Placeholder - will be set on first use via get_session_local()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    session_class = get_session_local()
    db = session_class()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create all tables)"""
    Base.metadata.create_all(bind=get_engine())


# Lazy accessor class for backward compatibility
class LazyEngine:
    """Wrapper that delays engine creation until actually accessed."""
    
    def __getattr__(self, name):
        return getattr(get_engine(), name)
    
    def __call__(self, *args, **kwargs):
        return get_engine()(*args, **kwargs)


class LazySessionLocal:
    """Wrapper that delays session factory creation until actually accessed."""
    
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)
    
    def __getattr__(self, name):
        return getattr(get_session_local(), name)


# Override the placeholders with lazy wrappers
engine = LazyEngine()
SessionLocal = LazySessionLocal()
