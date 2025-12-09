"""
NUCLEUS V1.2 - MED-to-DEEP Engine (Cloud Run Job)
Converts medium-term memory to deep long-term memory through consolidation
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid

# Add backend to path
sys.path.append("/app/backend")

from shared.models import get_db, Entity, Conversation, Summary, Embedding
from shared.llm import get_llm_gateway
from shared.pubsub import get_pubsub_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MEDtoDEEPEngine:
    """
    MED-to-DEEP Engine - Memory consolidation from medium to deep storage.
    
    Process:
    1. Identify conversations older than threshold (e.g., 7 days)
    2. Summarize and extract key insights
    3. Generate embeddings for semantic search
    4. Store in deep memory (Summary + Embedding)
    5. Mark conversations as archived
    """
    
    def __init__(self):
        self.llm = get_llm_gateway()
        self.project_id = os.getenv("PROJECT_ID", "thrive-system1")
        self.pubsub = get_pubsub_client(self.project_id)
        self.consolidation_threshold_days = 7
        
    async def consolidate(self, entity_id: str) -> Dict[str, Any]:
        """
        Consolidate medium-term memory to deep storage.
        
        Args:
            entity_id: UUID of the entity
            
        Returns:
            Consolidation results
        """
        logger.info(f"Starting memory consolidation for entity: {entity_id}")
        
        db = next(get_db())
        
        try:
            # Get entity
            entity = db.query(Entity).filter(Entity.id == uuid.UUID(entity_id)).first()
            if not entity:
                raise ValueError(f"Entity {entity_id} not found")
            
            # Find old conversations to consolidate
            threshold_date = datetime.utcnow() - timedelta(days=self.consolidation_threshold_days)
            
            conversations = db.query(Conversation).filter(
                Conversation.entity_id == uuid.UUID(entity_id),
                Conversation.created_at < threshold_date,
                Conversation.meta_data.op('->>')('archived').is_(None)  # Not already archived
            ).order_by(Conversation.created_at).limit(100).all()
            
            if not conversations:
                logger.info("No conversations to consolidate")
                return {
                    "status": "success",
                    "entity_id": entity_id,
                    "consolidated": 0
                }
            
            logger.info(f"Found {len(conversations)} conversations to consolidate")
            
            # Group conversations by time period (e.g., weekly)
            grouped = self._group_by_period(conversations)
            
            consolidated_count = 0
            
            for period, convs in grouped.items():
                # Summarize period
                summary_text = await self._summarize_conversations(entity, convs)
                
                # Generate embedding
                embedding_vector = await self.llm.embed(summary_text)
                
                # Store summary
                summary = Summary(
                    entity_id=uuid.UUID(entity_id),
                    summary_text=summary_text,
                    summary_type="deep_memory",
                    metadata={
                        "period": period,
                        "conversation_count": len(convs),
                        "date_range": {
                            "start": convs[0].created_at.isoformat(),
                            "end": convs[-1].created_at.isoformat()
                        }
                    }
                )
                db.add(summary)
                db.flush()  # Get summary ID
                
                # Store embedding
                embedding = Embedding(
                    entity_id=uuid.UUID(entity_id),
                    embedding_vector=embedding_vector,
                    source_type="summary",
                    source_id=summary.id,
                    metadata={"period": period}
                )
                db.add(embedding)
                
                # Mark conversations as archived
                for conv in convs:
                    conv.meta_data = conv.meta_data or {}
                    conv.meta_data["archived"] = True
                    conv.meta_data["summary_id"] = str(summary.id)
                    db.add(conv)
                
                consolidated_count += len(convs)
            
            db.commit()
            
            # Publish event
            await self.pubsub.publish(
                topic_name="memory-events",
                message_data={
                    "event_type": "memory_consolidated",
                    "entity_id": entity_id,
                    "conversations_consolidated": consolidated_count,
                    "summaries_created": len(grouped)
                }
            )
            
            logger.info(f"Memory consolidation complete: {consolidated_count} conversations")
            
            return {
                "status": "success",
                "entity_id": entity_id,
                "consolidated": consolidated_count,
                "summaries_created": len(grouped)
            }
            
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            raise
        finally:
            db.close()
    
    def _group_by_period(self, conversations: List[Conversation]) -> Dict[str, List[Conversation]]:
        """Group conversations by weekly periods"""
        grouped = {}
        
        for conv in conversations:
            # Get week number
            week_key = conv.created_at.strftime("%Y-W%W")
            
            if week_key not in grouped:
                grouped[week_key] = []
            
            grouped[week_key].append(conv)
        
        return grouped
    
    async def _summarize_conversations(self, entity: Entity, conversations: List[Conversation]) -> str:
        """Summarize a group of conversations"""
        
        # Build conversation text
        conv_text = "\n\n".join([
            f"[{conv.created_at.strftime('%Y-%m-%d')}]\nUser: {conv.user_message}\nAssistant: {conv.assistant_message}"
            for conv in conversations[:20]  # Limit to avoid token overflow
        ])
        
        prompt = f"""You are summarizing conversations for long-term memory storage in NUCLEUS.

Entity: {entity.entity_name}

Conversations ({len(conversations)} total):
{conv_text}

Create a comprehensive summary that captures:
1. Key topics discussed
2. Important decisions or insights
3. Recurring themes or patterns
4. Notable changes in entity's thinking

The summary should be 2-3 paragraphs, focusing on what's important to remember long-term.
"""
        
        messages = [
            {"role": "system", "content": "You are a memory consolidation specialist for NUCLEUS."},
            {"role": "user", "content": prompt}
        ]
        
        summary = await self.llm.complete(messages, temperature=0.3, max_tokens=500)
        
        return summary.strip()


async def main():
    """Main entry point"""
    logger.info("MED-to-DEEP Engine starting...")
    
    entity_id = os.getenv("ENTITY_ID")
    if not entity_id:
        logger.error("ENTITY_ID environment variable not set")
        return
    
    engine = MEDtoDEEPEngine()
    await engine.pubsub.initialize()
    
    try:
        result = await engine.consolidate(entity_id)
        logger.info(f"MED-to-DEEP consolidation complete: {result}")
    except Exception as e:
        logger.error(f"MED-to-DEEP consolidation failed: {e}")
        raise
    finally:
        await engine.pubsub.close()


if __name__ == "__main__":
    asyncio.run(main())
