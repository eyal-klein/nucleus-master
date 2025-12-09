"""
NUCLEUS V1.2 - Micro-Prompts Engine (Cloud Run Job)
Generates customized system prompts for each agent based on entity DNA
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, List
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Agent, Interest, Goal, Value, Summary
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MicroPromptsEngine:
    """
    Micro-Prompts Engine - Generates personalized prompts for agents.
    
    Process:
    1. Read entity DNA and interpretations
    2. For each active agent, generate a customized system prompt
    3. Update agent's system_prompt field
    4. Publish prompt updated events
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        
    async def generate_prompts(self, entity_id: str) -> Dict[str, Any]:
        """
        Generate micro-prompts for all agents of an entity.
        
        Args:
            entity_id: UUID of the entity
            
        Returns:
            Generation results
        """
        logger.info(f"Starting micro-prompts generation for entity: {entity_id}")
        
        db = next(get_db())
        
        try:
            # Get entity and DNA
            entity = db.query(Entity).filter(Entity.id == uuid.UUID(entity_id)).first()
            if not entity:
                raise ValueError(f"Entity {entity_id} not found")
            
            dna = self._collect_dna(db, entity_id)
            interpretations = self._collect_interpretations(db, entity_id)
            
            # Get all active agents
            agents = db.query(Agent).filter(Agent.is_active == True).all()
            
            updated_agents = []
            
            for agent in agents:
                # Generate customized prompt
                new_prompt = await self._generate_prompt(entity, dna, interpretations, agent)
                
                # Update agent
                agent.system_prompt = new_prompt
                agent.version += 1
                db.add(agent)
                
                updated_agents.append({
                    "agent_id": str(agent.id),
                    "agent_name": agent.agent_name,
                    "version": agent.version
                })
            
            db.commit()
            
            # Publish events
            for agent_info in updated_agents:
                await self.pubsub.publish(
                    topic_name="evolution-events",
                    message_data={
                        "event_type": "agent_prompt_updated",
                        "entity_id": entity_id,
                        "agent_id": agent_info["agent_id"],
                        "agent_name": agent_info["agent_name"],
                        "version": agent_info["version"]
                    }
                )
            
            logger.info(f"Micro-prompts generated for {len(updated_agents)} agents")
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "updated_agents": updated_agents
            }
            
        except Exception as e:
            logger.error(f"Micro-prompts generation failed: {e}")
            raise
        finally:
            db.close()
    
    def _collect_dna(self, db, entity_id: str) -> Dict[str, List]:
        """Collect entity DNA"""
        interests = db.query(Interest).filter(
            Interest.entity_id == uuid.UUID(entity_id)
        ).all()
        
        goals = db.query(Goal).filter(
            Goal.entity_id == uuid.UUID(entity_id)
        ).order_by(Goal.priority.desc()).limit(5).all()
        
        values = db.query(Value).filter(
            Value.entity_id == uuid.UUID(entity_id)
        ).all()
        
        return {
            "interests": [i.interest_name for i in interests],
            "goals": [g.goal_title for g in goals],
            "values": [v.value_name for v in values]
        }
    
    def _collect_interpretations(self, db, entity_id: str) -> Dict[str, str]:
        """Collect interpretations"""
        first = db.query(Summary).filter(
            Summary.entity_id == uuid.UUID(entity_id),
            Summary.summary_type == "first_interpretation"
        ).order_by(Summary.created_at.desc()).first()
        
        second = db.query(Summary).filter(
            Summary.entity_id == uuid.UUID(entity_id),
            Summary.summary_type == "second_interpretation"
        ).order_by(Summary.created_at.desc()).first()
        
        return {
            "strategic": first.summary_text if first else "Not available",
            "tactical": second.summary_text if second else "Not available"
        }
    
    async def _generate_prompt(
        self,
        entity: Entity,
        dna: Dict,
        interpretations: Dict,
        agent: Agent
    ) -> str:
        """Generate customized prompt for an agent"""
        
        prompt = f"""You are creating a customized system prompt for an AI agent in the NUCLEUS system.

Entity: {entity.entity_name}
Entity Description: {entity.description or "N/A"}

Entity DNA:
- Interests: {', '.join(dna['interests'][:10])}
- Goals: {', '.join(dna['goals'][:5])}
- Values: {', '.join(dna['values'][:5])}

Strategic Direction: {interpretations['strategic'][:300]}
Tactical Plan: {interpretations['tactical'][:300]}

Agent to customize:
- Name: {agent.agent_name}
- Type: {agent.agent_type}
- Current Prompt: {agent.system_prompt[:200]}

Generate a NEW system prompt for this agent that:
1. Aligns with the entity's DNA (interests, goals, values)
2. Reflects the strategic and tactical interpretations
3. Maintains the agent's core purpose ({agent.agent_type})
4. Is personalized to serve {entity.entity_name} specifically

The prompt should be 2-3 paragraphs, clear and actionable.
"""
        
        messages = [
            {"role": "system", "content": "You are a prompt engineer for NUCLEUS agents."},
            {"role": "user", "content": prompt}
        ]
        
        new_prompt = await self.llm.complete(messages, temperature=0.5, max_tokens=500)
        
        return new_prompt.strip()


async def main():
    """Main entry point"""
    logger.info("Micro-Prompts Engine starting...")
    
    entity_id = os.getenv("ENTITY_ID")
    if not entity_id:
        logger.error("ENTITY_ID environment variable not set")
        return
    
    engine = MicroPromptsEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.generate_prompts(entity_id)
        logger.info(f"Micro-Prompts generation complete: {result}")
    except Exception as e:
        logger.error(f"Micro-Prompts generation failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
