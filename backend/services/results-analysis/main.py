"""
NUCLEUS V1.2 - Results Analysis Service
Analyzes task results and agent performance
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging
import os
import uuid

# Import shared modules
import sys
sys.path.append("/app/backend")

from shared.models import get_db, AgentPerformance, Task
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Results Analysis",
    description="Analyzes task results and agent performance",
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


class PerformanceAnalysis(BaseModel):
    task_id: str
    agent_id: str
    success: bool
    execution_time_ms: Optional[int] = None
    feedback_score: Optional[float] = None
    metadata: Optional[dict] = None


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "results-analysis",
        "version": "1.0.0"
    }


@app.post("/analyze")
async def analyze_performance(
    analysis: PerformanceAnalysis,
    db: Session = Depends(get_db)
):
    """Analyze agent performance on a task"""
    logger.info(f"Analyzing performance for task: {analysis.task_id}, agent: {analysis.agent_id}")
    
    # Record performance
    performance = AgentPerformance(
        agent_id=uuid.UUID(analysis.agent_id),
        task_id=uuid.UUID(analysis.task_id),
        success=analysis.success,
        execution_time_ms=analysis.execution_time_ms,
        feedback_score=analysis.feedback_score,
        metadata=analysis.metadata
    )
    
    db.add(performance)
    db.commit()
    
    # Publish analysis event
    await pubsub.publish(
        topic_name="analysis-events",
        message_data={
            "event_type": "performance_analyzed",
            "task_id": analysis.task_id,
            "agent_id": analysis.agent_id,
            "success": analysis.success,
            "feedback_score": analysis.feedback_score
        }
    )
    
    return {
        "status": "analysis_complete",
        "task_id": analysis.task_id,
        "agent_id": analysis.agent_id
    }


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Results Analysis service starting up...")
    # Pub/Sub will be initialized on first use (lazy loading)
    logger.info("Results Analysis service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Results Analysis service shutting down...")
    await pubsub.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
