"""
NUCLEUS V1.2 - DNA Engine (Cloud Run Job)
Analyzes entity data to extract and refine DNA (interests, goals, values)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Interest, Goal, Value, RawData, Conversation
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DNAEngine:
    """
    DNA Engine - Extracts and refines entity DNA from raw data.
    
    Process:
    1. Collect all raw data for entity (conversations, documents, interactions)
    2. Analyze using LLM to extract interests, goals, values
    3. Update DNA tables with new/refined information
    4. Publish DNA updated event
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        
    async def analyze_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        Analyze an entity's data to extract/update DNA.
        
        Args:
            entity_id: UUID of the entity to analyze
            
        Returns:
            Analysis results
        """
        logger.info(f"Starting DNA analysis for entity: {entity_id}")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Get entity
            entity = db.query(Entity).filter(Entity.id == uuid.UUID(entity_id)).first()
            if not entity:
                raise ValueError(f"Entity {entity_id} not found")
            
            # Collect raw data
            raw_data = self._collect_raw_data(db, entity_id)
            logger.info(f"Collected {len(raw_data)} raw data items")
            
            # Analyze with LLM
            analysis = await self._analyze_with_llm(entity, raw_data)
            
            # Update DNA tables
            updated = self._update_dna(db, entity_id, analysis)
            
            # Publish event
            await self.pubsub.publish(
                topic_name="dna-events",
                message_data={
                    "event_type": "dna_updated",
                    "entity_id": entity_id,
                    "interests_count": len(updated.get("interests", [])),
                    "goals_count": len(updated.get("goals", [])),
                    "values_count": len(updated.get("values", []))
                }
            )
            
            logger.info(f"DNA analysis complete for entity: {entity_id}")
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "updated": updated
            }
            
        except Exception as e:
            logger.error(f"DNA analysis failed: {e}")
            raise
        finally:
            db.close()
    
    def _collect_raw_data(self, db, entity_id: str) -> List[Dict[str, Any]]:
        """Collect all raw data for entity"""
        raw_data = []
        
        # Get raw data entries
        raw_entries = db.query(RawData).filter(
            RawData.entity_id == uuid.UUID(entity_id)
        ).order_by(RawData.created_at.desc()).limit(100).all()
        
        for entry in raw_entries:
            raw_data.append({
                "type": "raw_data",
                "content": entry.raw_content,
                "source": entry.data_source,
                "timestamp": entry.created_at.isoformat()
            })
        
        # Get recent conversations
        conversations = db.query(Conversation).filter(
            Conversation.entity_id == uuid.UUID(entity_id)
        ).order_by(Conversation.created_at.desc()).limit(50).all()
        
        for conv in conversations:
            raw_data.append({
                "type": "conversation",
                "content": f"User: {conv.user_message}\nAssistant: {conv.assistant_message}",
                "timestamp": conv.created_at.isoformat()
            })
        
        return raw_data
    
    async def _analyze_with_llm(self, entity: Entity, raw_data: List[Dict]) -> Dict[str, Any]:
        """Analyze raw data with LLM to extract DNA"""
        
        # Build analysis prompt
        data_summary = "\n\n".join([
            f"[{item['type']}] {item['content'][:500]}"
            for item in raw_data[:20]  # Limit to avoid token overflow
        ])
        
        prompt = f"""You are analyzing data for an entity named "{entity.entity_name}" to extract their DNA.

DNA consists of:
1. **Interests**: Topics, domains, activities they care about
2. **Goals**: Objectives, aspirations, things they want to achieve
3. **Values**: Principles, beliefs, what matters to them

Analyze the following data and extract:
- New interests (not already known)
- New goals (not already known)
- New values (not already known)

Current known DNA:
- Entity: {entity.entity_name}
- Description: {entity.description or "None"}

Recent data:
{data_summary}

Respond in JSON format:
{{
  "interests": [
    {{"name": "interest name", "description": "why they care", "confidence": 0.0-1.0}}
  ],
  "goals": [
    {{"goal_title": "goal", "description": "details", "priority": 1-10}}
  ],
  "values": [
    {{"value_name": "value", "description": "what it means to them"}}
  ]
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a DNA analyst for NUCLEUS. Extract interests, goals, and values from entity data."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(messages, temperature=0.3)
        
        # Parse JSON response
        import json
        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("LLM response not valid JSON, using empty analysis")
            analysis = {"interests": [], "goals": [], "values": []}
        
        return analysis
    
    def _update_dna(self, db, entity_id: str, analysis: Dict) -> Dict[str, Any]:
        """Update DNA tables with analysis results"""
        updated = {
            "interests": [],
            "goals": [],
            "values": []
        }
        
        # Add interests
        for interest_data in analysis.get("interests", []):
            interest = Interest(
                entity_id=uuid.UUID(entity_id),
                interest_name=interest_data.get("name"),
                description=interest_data.get("description"),
                confidence_score=interest_data.get("confidence", 0.7)
            )
            db.add(interest)
            updated["interests"].append(interest_data.get("name"))
        
        # Add goals
        for goal_data in analysis.get("goals", []):
            goal = Goal(
                entity_id=uuid.UUID(entity_id),
                goal_title=goal_data.get("goal_title"),
                description=goal_data.get("description"),
                priority=goal_data.get("priority", 5)
            )
            db.add(goal)
            updated["goals"].append(goal_data.get("goal_title"))
        
        # Add values
        for value_data in analysis.get("values", []):
            value = Value(
                entity_id=uuid.UUID(entity_id),
                value_name=value_data.get("value_name"),
                description=value_data.get("description")
            )
            db.add(value)
            updated["values"].append(value_data.get("value_name"))
        
        db.commit()
        
        return updated


async def main():
    """Main entry point for DNA Engine job"""
    logger.info("DNA Engine starting...")
    
    # Get entity_id from environment (passed by Cloud Scheduler or manual trigger)
    entity_id = os.getenv("ENTITY_ID")
    
    if not entity_id:
        logger.error("ENTITY_ID environment variable not set")
        return
    
    engine = DNAEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.analyze_entity(entity_id)
        logger.info(f"DNA Engine completed successfully: {result}")
    except Exception as e:
        logger.error(f"DNA Engine failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
