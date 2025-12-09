"""
NUCLEUS V1.2 - Agent Evolution Service
Manages agent lifecycle: creation, modification, deletion
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import uuid

# Import shared modules
import sys
sys.path.append("/app/backend")

from shared.models import get_db, Agent, Tool, AgentTool
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Agent Evolution",
    description="Manages agent lifecycle: creation, modification, deletion",
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


class AgentCreate(BaseModel):
    agent_name: str
    agent_type: str  # strategic, tactical
    system_prompt: str
    description: Optional[str] = None
    tool_ids: List[str] = []


class AgentResponse(BaseModel):
    id: str
    agent_name: str
    agent_type: str
    version: int
    is_active: bool


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agent-evolution",
        "version": "1.0.0"
    }


@app.post("/agents", response_model=AgentResponse)
async def create_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db)
):
    """Create a new agent"""
    logger.info(f"Creating agent: {agent.agent_name}")
    
    # Create agent
    new_agent = Agent(
        agent_name=agent.agent_name,
        agent_type=agent.agent_type,
        system_prompt=agent.system_prompt,
        description=agent.description,
        version=1,
        is_active=True
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    # Assign tools
    for tool_id in agent.tool_ids:
        agent_tool = AgentTool(
            agent_id=new_agent.id,
            tool_id=uuid.UUID(tool_id)
        )
        db.add(agent_tool)
    
    db.commit()
    
    # Publish agent created event
    await pubsub.publish(
        topic_name="evolution-events",
        message_data={
            "event_type": "agent_created",
            "agent_id": str(new_agent.id),
            "agent_name": agent.agent_name,
            "agent_type": agent.agent_type
        }
    )
    
    return AgentResponse(
        id=str(new_agent.id),
        agent_name=new_agent.agent_name,
        agent_type=new_agent.agent_type,
        version=new_agent.version,
        is_active=new_agent.is_active
    )


@app.get("/agents", response_model=List[AgentResponse])
async def list_agents(
    db: Session = Depends(get_db)
):
    """List all agents"""
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    
    return [
        AgentResponse(
            id=str(agent.id),
            agent_name=agent.agent_name,
            agent_type=agent.agent_type,
            version=agent.version,
            is_active=agent.is_active
        )
        for agent in agents
    ]


@app.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """Soft delete an agent"""
    agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.is_active = False
    db.commit()
    
    # Publish agent deleted event
    await pubsub.publish(
        topic_name="evolution-events",
        message_data={
            "event_type": "agent_deleted",
            "agent_id": agent_id,
            "agent_name": agent.agent_name
        }
    )
    
    return {"status": "agent_deleted", "agent_id": agent_id}


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Agent Evolution service starting up...")
    # Pub/Sub will be initialized on first use (lazy loading)
    logger.info("Agent Evolution service ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Agent Evolution service shutting down...")
    await pubsub.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
