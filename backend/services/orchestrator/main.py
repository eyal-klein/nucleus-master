"""
NUCLEUS V1.2 - Orchestrator Service
Central coordinator for all NUCLEUS operations
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
import os

# Import shared modules
import sys
sys.path.append("/app/backend")

from shared.models import get_db, Entity
from shared.pubsub import get_pubsub_client

# Import routers
from .routers import integrations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Orchestrator",
    description="Central coordinator for all NUCLEUS operations",
    version="1.0.0"
)

# Include routers
app.include_router(integrations.router)

# Initialize Pub/Sub client
project_id = os.getenv("PROJECT_ID", "thrive-system1")
pubsub = get_pubsub_client(project_id)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class OrchestrationRequest(BaseModel):
    entity_id: str
    operation: str
    payload: Optional[dict] = None


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0"
    }


@app.post("/orchestrate")
async def orchestrate(
    request: OrchestrationRequest,
    db: Session = Depends(get_db)
):
    """
    Main orchestration endpoint.
    Coordinates operations across all NUCLEUS services.
    """
    logger.info(f"Orchestrating operation: {request.operation} for entity: {request.entity_id}")
    
    # Verify entity exists
    entity = db.query(Entity).filter(Entity.id == request.entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Publish orchestration event to Pub/Sub
    await pubsub.publish(
        topic_name="orchestration-events",
        message_data={
            "entity_id": request.entity_id,
            "operation": request.operation,
            "payload": request.payload or {}
        }
    )
    
    return {
        "status": "orchestration_initiated",
        "entity_id": request.entity_id,
        "operation": request.operation
    }


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Orchestrator service starting up...")
    # Pub/Sub will be initialized on first use (lazy loading)
    logger.info("Orchestrator service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Orchestrator service shutting down...")
    await pubsub.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
