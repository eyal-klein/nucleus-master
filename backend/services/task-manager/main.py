"""
NUCLEUS V1.2 - Task Manager Service
Manages task creation, assignment, and tracking
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import os
import uuid

# Import shared modules
import sys
sys.path.append("/app/backend")

from shared.models import get_db, Task, Agent
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Task Manager",
    description="Manages task creation, assignment, and tracking",
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


class TaskCreate(BaseModel):
    entity_id: str
    task_title: str
    task_description: Optional[str] = None
    priority: int = 5


class TaskResponse(BaseModel):
    id: str
    entity_id: str
    task_title: str
    status: str
    priority: int
    created_at: datetime


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "task-manager",
        "version": "1.0.0"
    }


@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db)
):
    """Create a new task"""
    logger.info(f"Creating task: {task.task_title} for entity: {task.entity_id}")
    
    # Create task in database
    new_task = Task(
        entity_id=uuid.UUID(task.entity_id),
        task_title=task.task_title,
        task_description=task.task_description,
        priority=task.priority,
        status="pending"
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Publish task created event
    await pubsub.publish(
        topic_name="task-events",
        message_data={
            "event_type": "task_created",
            "task_id": str(new_task.id),
            "entity_id": task.entity_id,
            "task_title": task.task_title,
            "priority": task.priority
        }
    )
    
    return TaskResponse(
        id=str(new_task.id),
        entity_id=str(new_task.entity_id),
        task_title=new_task.task_title,
        status=new_task.status,
        priority=new_task.priority,
        created_at=new_task.created_at
    )


@app.get("/tasks/{entity_id}", response_model=List[TaskResponse])
async def get_tasks(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get all tasks for an entity"""
    tasks = db.query(Task).filter(Task.entity_id == uuid.UUID(entity_id)).all()
    
    return [
        TaskResponse(
            id=str(task.id),
            entity_id=str(task.entity_id),
            task_title=task.task_title,
            status=task.status,
            priority=task.priority,
            created_at=task.created_at
        )
        for task in tasks
    ]


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Task Manager service starting up...")
    # Pub/Sub will be initialized on first use (lazy loading)
    logger.info("Task Manager service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Task Manager service shutting down...")
    await pubsub.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
