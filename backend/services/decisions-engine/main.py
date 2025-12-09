"""
NUCLEUS V1.2 - Decisions Engine Service
Makes strategic and tactical decisions based on DNA and context
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import uuid

# Import shared modules
import sys
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Goal, Interest
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Decisions Engine",
    description="Makes strategic and tactical decisions based on DNA and context",
    version="1.0.0"
)

# Initialize Pub/Sub client
project_id = os.getenv("PROJECT_ID", "thrive-system1")
pubsub = get_pubsub_client(project_id)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class DecisionRequest(BaseModel):
    entity_id: str
    context: str
    decision_type: str  # strategic, tactical


class DecisionResponse(BaseModel):
    decision_id: str
    entity_id: str
    decision: str
    rationale: str
    confidence: float


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "decisions-engine",
        "version": "1.0.0"
    }


@app.post("/decide", response_model=DecisionResponse)
async def make_decision(
    request: DecisionRequest,
    db: Session = Depends(get_db)
):
    """Make a decision based on entity DNA and context"""
    logger.info(f"Making {request.decision_type} decision for entity: {request.entity_id}")
    
    # Get entity DNA
    entity = db.query(Entity).filter(Entity.id == uuid.UUID(request.entity_id)).first()
    goals = db.query(Goal).filter(Goal.entity_id == uuid.UUID(request.entity_id)).all()
    interests = db.query(Interest).filter(Interest.entity_id == uuid.UUID(request.entity_id)).all()
    
    # TODO: Implement actual decision-making logic with LLM
    # For now, return a placeholder
    decision_id = str(uuid.uuid4())
    
    decision_response = DecisionResponse(
        decision_id=decision_id,
        entity_id=request.entity_id,
        decision="Placeholder decision - to be implemented with LLM",
        rationale="Based on entity DNA and current context",
        confidence=0.75
    )
    
    # Publish decision event
    await pubsub.publish(
        topic_name="decision-events",
        message_data={
            "event_type": "decision_made",
            "decision_id": decision_id,
            "entity_id": request.entity_id,
            "decision_type": request.decision_type,
            "confidence": 0.75
        }
    )
    
    return decision_response


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Decisions Engine service starting up...")
    # Pub/Sub will be initialized on first use (lazy loading)
    logger.info("Decisions Engine service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Decisions Engine service shutting down...")
    await pubsub.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
