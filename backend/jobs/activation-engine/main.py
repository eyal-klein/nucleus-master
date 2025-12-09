"""
NUCLEUS V1.2 - Activation Engine (Cloud Run Job)
Activates approved agents and registers them in the assembly
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Agent, AgentActivation
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActivationEngine:
    """
    Activation Engine - Activates approved agents.
    
    Process:
    1. Identify agents ready for activation (status='approved')
    2. Register agent in active assembly
    3. Initialize agent resources (if needed)
    4. Update agent status to 'active'
    5. Publish activation event
    """
    
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        
    async def activate_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Activate an approved agent.
        
        Args:
            agent_id: UUID of the agent to activate
            
        Returns:
            Activation results
        """
        logger.info(f"Starting activation for agent: {agent_id}")
        
        db = next(get_db())
        
        try:
            # Get agent
            agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            if agent.status != 'approved':
                logger.warning(f"Agent {agent_id} is not approved (status: {agent.status})")
                return {
                    "status": "skipped",
                    "agent_id": agent_id,
                    "reason": f"Agent status is {agent.status}, not approved"
                }
            
            logger.info(f"Activating agent: {agent.agent_name}")
            
            # Update agent status
            agent.status = 'active'
            agent.activated_at = datetime.utcnow()
            agent.meta_data = agent.meta_data or {}
            agent.meta_data['activation_timestamp'] = datetime.utcnow().isoformat()
            
            # Create activation record
            activation = AgentActivation(
                agent_id=uuid.UUID(agent_id),
                activated_by="activation-engine",
                activation_reason="Passed QA and approved for activation",
                metadata={
                    "agent_name": agent.agent_name,
                    "purpose": agent.purpose
                }
            )
            
            db.add(agent)
            db.add(activation)
            db.commit()
            
            # Publish activation event
            await self.pubsub.publish(
                topic_name="evolution-events",
                message_data={
                    "event_type": "agent_activated",
                    "agent_id": agent_id,
                    "agent_name": agent.agent_name,
                    "purpose": agent.purpose,
                    "activated_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Agent {agent.agent_name} activated successfully")
            
            return {
                "status": "success",
                "agent_id": agent_id,
                "agent_name": agent.agent_name,
                "activated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Activation failed for agent {agent_id}: {e}")
            raise
        finally:
            db.close()
    
    async def activate_all_approved(self) -> Dict[str, Any]:
        """Activate all approved agents"""
        logger.info("Activating all approved agents...")
        
        db = next(get_db())
        
        try:
            # Get all approved agents
            approved_agents = db.query(Agent).filter(Agent.status == 'approved').all()
            
            if not approved_agents:
                logger.info("No approved agents found")
                return {
                    "status": "success",
                    "activated_count": 0,
                    "message": "No approved agents to activate"
                }
            
            logger.info(f"Found {len(approved_agents)} approved agents")
            
            results = []
            for agent in approved_agents:
                try:
                    result = await self.activate_agent(str(agent.id))
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to activate {agent.agent_name}: {e}")
                    results.append({
                        "status": "error",
                        "agent_id": str(agent.id),
                        "agent_name": agent.agent_name,
                        "error": str(e)
                    })
            
            activated_count = sum(1 for r in results if r.get('status') == 'success')
            
            logger.info(f"Activation complete: {activated_count}/{len(approved_agents)} agents activated")
            
            return {
                "status": "success",
                "total_agents": len(approved_agents),
                "activated_count": activated_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Batch activation failed: {e}")
            raise
        finally:
            db.close()


async def main():
    """Main entry point"""
    logger.info("Activation Engine starting...")
    
    engine = ActivationEngine()
    await engine.pubsub.initialize()
    
    try:
        # Check if specific agent ID provided
        agent_id = os.getenv("AGENT_ID")
        
        if agent_id:
            logger.info(f"Activating specific agent: {agent_id}")
            result = await engine.activate_agent(agent_id)
        else:
            logger.info("Activating all approved agents")
            result = await engine.activate_all_approved()
        
        logger.info(f"Activation complete: {result}")
        
    except Exception as e:
        logger.error(f"Activation failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
