"""
NUCLEUS V1.2 - First Interpretation Engine (Cloud Run Job)
Initial interpretation of entity DNA to identify strategic directions
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, List
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Interest, Goal, Value
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirstInterpretationEngine:
    """
    First Interpretation Engine - Strategic interpretation of DNA.
    
    Process:
    1. Read entity DNA (interests, goals, values)
    2. Identify strategic patterns and opportunities
    3. Generate high-level interpretations
    4. Store interpretations for Second Interpretation
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        
    async def interpret(self, entity_id: str) -> Dict[str, Any]:
        """
        Generate first interpretation for entity.
        
        Args:
            entity_id: UUID of the entity
            
        Returns:
            Interpretation results
        """
        logger.info(f"Starting first interpretation for entity: {entity_id}")
        
        db = next(get_db())
        
        try:
            # Get entity and DNA
            entity = db.query(Entity).filter(Entity.id == uuid.UUID(entity_id)).first()
            if not entity:
                raise ValueError(f"Entity {entity_id} not found")
            
            dna = self._collect_dna(db, entity_id)
            
            # Generate interpretation
            interpretation = await self._generate_interpretation(entity, dna)
            
            # Store interpretation (in memory schema as summary)
            from shared.models import Summary
            summary = Summary(
                entity_id=uuid.UUID(entity_id),
                summary_text=interpretation["strategic_direction"],
                summary_type="first_interpretation",
                metadata=interpretation
            )
            db.add(summary)
            db.commit()
            
            # Publish event
            await self.pubsub.publish(
                topic_name="interpretation-events",
                message_data={
                    "event_type": "first_interpretation_complete",
                    "entity_id": entity_id,
                    "strategic_themes": interpretation.get("themes", [])
                }
            )
            
            logger.info(f"First interpretation complete for entity: {entity_id}")
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "interpretation": interpretation
            }
            
        except Exception as e:
            logger.error(f"First interpretation failed: {e}")
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
        ).all()
        
        values = db.query(Value).filter(
            Value.entity_id == uuid.UUID(entity_id)
        ).all()
        
        return {
            "interests": [
                {"name": i.interest_name, "description": i.description}
                for i in interests
            ],
            "goals": [
                {"title": g.goal_title, "description": g.description, "priority": g.priority}
                for g in goals
            ],
            "values": [
                {"name": v.value_name, "description": v.description}
                for v in values
            ]
        }
    
    async def _generate_interpretation(self, entity: Entity, dna: Dict) -> Dict[str, Any]:
        """Generate strategic interpretation using LLM"""
        
        prompt = f"""You are a strategic analyst for NUCLEUS. Analyze the entity's DNA and provide a first-level strategic interpretation.

Entity: {entity.entity_name}

DNA:
Interests ({len(dna['interests'])}):
{self._format_list(dna['interests'], 'name', 'description')}

Goals ({len(dna['goals'])}):
{self._format_list(dna['goals'], 'title', 'description')}

Values ({len(dna['values'])}):
{self._format_list(dna['values'], 'name', 'description')}

Provide a strategic interpretation that identifies:
1. **Strategic Direction**: Overall direction based on DNA
2. **Key Themes**: 3-5 major themes that emerge
3. **Opportunities**: Areas for growth and development
4. **Potential Challenges**: Obstacles or conflicts in DNA

Respond in JSON format:
{{
  "strategic_direction": "One paragraph summary",
  "themes": ["theme1", "theme2", "theme3"],
  "opportunities": ["opportunity1", "opportunity2"],
  "challenges": ["challenge1", "challenge2"]
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a strategic DNA analyst for NUCLEUS."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(messages, temperature=0.4)
        
        # Parse JSON
        import json
        try:
            interpretation = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("LLM response not valid JSON")
            interpretation = {
                "strategic_direction": response[:500],
                "themes": [],
                "opportunities": [],
                "challenges": []
            }
        
        return interpretation
    
    def _format_list(self, items: List[Dict], name_key: str, desc_key: str) -> str:
        """Format list for prompt"""
        if not items:
            return "None"
        return "\n".join([
            f"- {item[name_key]}: {item.get(desc_key, 'N/A')}"
            for item in items[:10]  # Limit to avoid token overflow
        ])


async def main():
    """Main entry point"""
    logger.info("First Interpretation Engine starting...")
    
    entity_id = os.getenv("ENTITY_ID")
    if not entity_id:
        logger.error("ENTITY_ID environment variable not set")
        return
    
    engine = FirstInterpretationEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.interpret(entity_id)
        logger.info(f"First Interpretation complete: {result}")
    except Exception as e:
        logger.error(f"First Interpretation failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
