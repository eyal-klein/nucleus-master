"""
NUCLEUS V1.2 - SQLAlchemy Base Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import os
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)

# Database connection string from environment
# Handle both undefined and empty string cases
_db_url = os.getenv("DATABASE_URL", "")
DATABASE_URL = _db_url if _db_url else "postgresql://nucleus:password@localhost:5432/nucleus"

# Lazy initialization - engine and session will be created on first use
_engine = None
_SessionLocal = None

# Base class for all models
Base = declarative_base()


def get_engine():
    """Get or create the database engine (lazy initialization)"""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=10,
                max_overflow=20,
                echo=False  # Set to True for SQL logging
            )
            logger.info(f"Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    return _engine


def get_session_local():
    """Get or create the session factory (lazy initialization)"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


# For backward compatibility - these will trigger lazy initialization when accessed
@property
def engine():
    return get_engine()


# Session factory - use get_session_local() for lazy initialization
def SessionLocal():
    return get_session_local()()


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
