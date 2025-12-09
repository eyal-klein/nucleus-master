"""
NUCLEUS V1.2 - Second Interpretation Engine (Cloud Run Job)
Deep interpretation that refines first interpretation into actionable insights
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Summary
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecondInterpretationEngine:
    """
    Second Interpretation Engine - Tactical refinement of strategic interpretation.
    
    Process:
    1. Read first interpretation
    2. Refine into specific, actionable insights
    3. Identify concrete next steps
    4. Store second interpretation
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        
    async def interpret(self, entity_id: str) -> Dict[str, Any]:
        """
        Generate second interpretation for entity.
        
        Args:
            entity_id: UUID of the entity
            
        Returns:
            Interpretation results
        """
        logger.info(f"Starting second interpretation for entity: {entity_id}")
        
        db = next(get_db())
        
        try:
            # Get entity
            entity = db.query(Entity).filter(Entity.id == uuid.UUID(entity_id)).first()
            if not entity:
                raise ValueError(f"Entity {entity_id} not found")
            
            # Get first interpretation
            first_interp = db.query(Summary).filter(
                Summary.entity_id == uuid.UUID(entity_id),
                Summary.summary_type == "first_interpretation"
            ).order_by(Summary.created_at.desc()).first()
            
            if not first_interp:
                raise ValueError("First interpretation not found. Run First Interpretation first.")
            
            # Generate second interpretation
            interpretation = await self._generate_interpretation(entity, first_interp)
            
            # Store interpretation
            summary = Summary(
                entity_id=uuid.UUID(entity_id),
                summary_text=interpretation["action_plan"],
                summary_type="second_interpretation",
                metadata=interpretation
            )
            db.add(summary)
            db.commit()
            
            # Publish event
            await self.pubsub.publish(
                topic_name="interpretation-events",
                message_data={
                    "event_type": "second_interpretation_complete",
                    "entity_id": entity_id,
                    "action_items": len(interpretation.get("action_items", []))
                }
            )
            
            logger.info(f"Second interpretation complete for entity: {entity_id}")
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "interpretation": interpretation
            }
            
        except Exception as e:
            logger.error(f"Second interpretation failed: {e}")
            raise
        finally:
            db.close()
    
    async def _generate_interpretation(self, entity: Entity, first_interp: Summary) -> Dict[str, Any]:
        """Generate tactical interpretation using LLM"""
        
        first_data = first_interp.metadata or {}
        
        prompt = f"""You are a tactical analyst for NUCLEUS. Based on the strategic interpretation, create a detailed action plan.

Entity: {entity.entity_name}

Strategic Interpretation:
{first_interp.summary_text}

Strategic Themes: {', '.join(first_data.get('themes', []))}
Opportunities: {', '.join(first_data.get('opportunities', []))}
Challenges: {', '.join(first_data.get('challenges', []))}

Create a tactical interpretation that includes:
1. **Action Plan**: Concrete steps to pursue opportunities
2. **Action Items**: 5-10 specific, actionable tasks
3. **Priority Areas**: Top 3 areas to focus on
4. **Success Metrics**: How to measure progress

Respond in JSON format:
{{
  "action_plan": "Detailed action plan paragraph",
  "action_items": [
    {{"task": "specific task", "priority": 1-10, "rationale": "why this matters"}}
  ],
  "priority_areas": ["area1", "area2", "area3"],
  "success_metrics": ["metric1", "metric2"]
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a tactical DNA analyst for NUCLEUS."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(messages, temperature=0.3)
        
        # Parse JSON
        import json
        try:
            interpretation = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("LLM response not valid JSON")
            interpretation = {
                "action_plan": response[:500],
                "action_items": [],
                "priority_areas": [],
                "success_metrics": []
            }
        
        return interpretation


async def main():
    """Main entry point"""
    logger.info("Second Interpretation Engine starting...")
    
    entity_id = os.getenv("ENTITY_ID")
    if not entity_id:
        logger.error("ENTITY_ID environment variable not set")
        return
    
    engine = SecondInterpretationEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.interpret(entity_id)
        logger.info(f"Second Interpretation complete: {result}")
    except Exception as e:
        logger.error(f"Second Interpretation failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
