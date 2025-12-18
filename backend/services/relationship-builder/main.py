"""
NUCLEUS V2.0 - Relationship Builder

Builds deep, authentic relationships between NUCLEUS and the entity through:
1. Private Language Development - Unique terms, references, inside jokes
2. Shared Memory Building - Memorable moments and experiences
3. Trust Progression - Gradual deepening of relationship
4. Communication Style Adaptation - Learning preferred interaction patterns
5. Emotional Attunement - Understanding and responding to emotional cues

Based on:
- GI X Document: "שפה פרטית" - building unique shared language
- NUCLEUS Agent Document: Deep relationship building over time
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, '/app/shared')

from models.base import get_db
from models.dna import Entity, CommunicationStyle
from models.nucleus_core import PrivateLanguage, AutonomyLevel
from llm.gateway import get_llm_gateway
from pubsub.publisher import get_publisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Relationship Builder",
    description="Builds deep, authentic relationships through private language and shared experiences",
    version="2.0.0"
)

llm = get_llm_gateway()
publisher = get_publisher()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class PrivateTermRequest(BaseModel):
    """Request to register a new private term"""
    entity_id: str
    term: str
    meaning: str
    context: str
    origin_story: Optional[str] = None


class SharedMemoryRequest(BaseModel):
    """Request to record a shared memory"""
    entity_id: str
    memory_type: str  # milestone, funny_moment, breakthrough, challenge_overcome
    description: str
    emotional_significance: float = Field(default=0.7, ge=0, le=1)
    participants: Optional[List[str]] = None


class CommunicationStyleUpdate(BaseModel):
    """Update communication style preferences"""
    entity_id: str
    preference_type: str  # formality, humor, detail_level, emoji_use, response_length
    preference_value: str
    confidence: float = Field(default=0.7, ge=0, le=1)


class RelationshipStatusResponse(BaseModel):
    """Current relationship status"""
    entity_id: str
    relationship_depth: float
    trust_level: float
    private_terms_count: int
    shared_memories_count: int
    communication_adaptations: int
    relationship_stage: str


# ============================================================================
# PRIVATE LANGUAGE MANAGER
# ============================================================================

class PrivateLanguageManager:
    """Manages the private language between NUCLEUS and entity"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    def add_term(
        self,
        term: str,
        meaning: str,
        context: str,
        origin_story: Optional[str]
    ) -> PrivateLanguage:
        """Add a new private term to the shared vocabulary"""
        
        # Check if term already exists
        existing = self.db.query(PrivateLanguage).filter(
            and_(
                PrivateLanguage.entity_id == self.entity_id,
                PrivateLanguage.term == term
            )
        ).first()
        
        if existing:
            # Update usage count
            existing.usage_count += 1
            existing.last_used = datetime.utcnow()
            self.db.commit()
            return existing
        
        # Create new term
        new_term = PrivateLanguage(
            entity_id=self.entity_id,
            term=term,
            meaning=meaning,
            context=context,
            origin_story=origin_story,
            usage_count=1,
            last_used=datetime.utcnow()
        )
        self.db.add(new_term)
        self.db.commit()
        
        return new_term
    
    def get_vocabulary(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the current private vocabulary"""
        
        terms = self.db.query(PrivateLanguage).filter(
            PrivateLanguage.entity_id == self.entity_id
        ).order_by(PrivateLanguage.usage_count.desc()).limit(limit).all()
        
        return [
            {
                "term": t.term,
                "meaning": t.meaning,
                "context": t.context,
                "usage_count": t.usage_count,
                "origin": t.origin_story
            }
            for t in terms
        ]
    
    def use_term(self, term: str) -> bool:
        """Record usage of a private term"""
        
        existing = self.db.query(PrivateLanguage).filter(
            and_(
                PrivateLanguage.entity_id == self.entity_id,
                PrivateLanguage.term == term
            )
        ).first()
        
        if existing:
            existing.usage_count += 1
            existing.last_used = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    async def suggest_terms(self, conversation: str) -> List[Dict[str, Any]]:
        """Suggest new private terms based on conversation"""
        
        existing_terms = self.get_vocabulary(20)
        existing_list = [t["term"] for t in existing_terms]
        
        prompt = f"""Analyze this conversation for potential private language development.

Conversation:
{conversation}

Existing private terms: {existing_list}

Identify any:
1. Unique phrases or expressions used
2. Inside references or jokes
3. Nicknames or shorthand
4. Recurring themes that could become terms

Respond with JSON:
{{
    "suggested_terms": [
        {{
            "term": "the term",
            "meaning": "what it means in context",
            "context": "when to use it",
            "confidence": 0.0-1.0
        }}
    ]
}}

Only suggest terms that feel natural and meaningful, not forced."""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You help develop authentic private language between AI and human."},
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            return result.get("suggested_terms", [])
            
        except Exception as e:
            logger.error(f"Error suggesting terms: {e}")
            return []


# ============================================================================
# SHARED MEMORY BUILDER
# ============================================================================

class SharedMemoryBuilder:
    """Builds and maintains shared memories"""
    
    MEMORY_TYPES = {
        "milestone": "Significant achievement or progress",
        "funny_moment": "Humorous interaction or mishap",
        "breakthrough": "Important realization or insight",
        "challenge_overcome": "Difficulty faced and resolved together",
        "first_time": "First occurrence of something meaningful",
        "tradition": "Recurring pattern that became meaningful"
    }
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        # Note: Using a simple approach - in production, create a SharedMemory table
        
    async def record_memory(
        self,
        memory_type: str,
        description: str,
        emotional_significance: float,
        participants: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Record a new shared memory"""
        
        # Generate a memorable summary
        summary = await self._generate_summary(memory_type, description)
        
        # Store in entity's memory (using existing memory system)
        memory_record = {
            "type": "shared_memory",
            "memory_type": memory_type,
            "description": description,
            "summary": summary,
            "emotional_significance": emotional_significance,
            "participants": participants or [],
            "recorded_at": datetime.utcnow().isoformat()
        }
        
        # Publish to memory system
        publisher.publish_event(
            "digital",
            "relationship.memory.created",
            str(self.entity_id),
            memory_record
        )
        
        return memory_record
    
    async def _generate_summary(self, memory_type: str, description: str) -> str:
        """Generate a memorable summary of the experience"""
        
        prompt = f"""Create a brief, memorable summary of this shared experience.

Type: {memory_type}
Description: {description}

The summary should:
1. Be concise (1-2 sentences)
2. Capture the emotional essence
3. Be easy to reference later

Just provide the summary, no explanation."""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You create memorable summaries of shared experiences."},
                {"role": "user", "content": prompt}
            ])
            return response.strip()
        except:
            return description[:100]


# ============================================================================
# COMMUNICATION ADAPTER
# ============================================================================

class CommunicationAdapter:
    """Adapts communication style based on learned preferences"""
    
    PREFERENCE_TYPES = {
        "formality": ["very_formal", "formal", "neutral", "casual", "very_casual"],
        "humor": ["none", "occasional", "moderate", "frequent"],
        "detail_level": ["minimal", "concise", "moderate", "detailed", "comprehensive"],
        "emoji_use": ["never", "rare", "occasional", "frequent"],
        "response_length": ["brief", "moderate", "detailed"],
        "greeting_style": ["formal", "friendly", "minimal", "personalized"]
    }
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    def update_preference(
        self,
        preference_type: str,
        preference_value: str,
        confidence: float
    ) -> Dict[str, Any]:
        """Update a communication preference"""
        
        if preference_type not in self.PREFERENCE_TYPES:
            raise ValueError(f"Unknown preference type: {preference_type}")
        
        valid_values = self.PREFERENCE_TYPES[preference_type]
        if preference_value not in valid_values:
            raise ValueError(f"Invalid value for {preference_type}. Valid: {valid_values}")
        
        # Get or create communication style
        style = self.db.query(CommunicationStyle).filter(
            CommunicationStyle.entity_id == self.entity_id
        ).first()
        
        if not style:
            style = CommunicationStyle(
                entity_id=self.entity_id,
                preferences={},
                confidence_scores={}
            )
            self.db.add(style)
        
        # Update preference
        if not style.preferences:
            style.preferences = {}
        if not style.confidence_scores:
            style.confidence_scores = {}
            
        style.preferences[preference_type] = preference_value
        style.confidence_scores[preference_type] = confidence
        style.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "preference_type": preference_type,
            "value": preference_value,
            "confidence": confidence
        }
    
    def get_style_guide(self) -> Dict[str, Any]:
        """Get the current communication style guide"""
        
        style = self.db.query(CommunicationStyle).filter(
            CommunicationStyle.entity_id == self.entity_id
        ).first()
        
        if not style:
            return {"preferences": {}, "confidence_scores": {}}
        
        return {
            "preferences": style.preferences or {},
            "confidence_scores": style.confidence_scores or {}
        }
    
    async def adapt_message(self, message: str) -> str:
        """Adapt a message to match learned communication style"""
        
        style_guide = self.get_style_guide()
        
        if not style_guide["preferences"]:
            return message  # No adaptations yet
        
        prompt = f"""Adapt this message to match the user's preferred communication style.

Original message:
{message}

Style preferences:
{json.dumps(style_guide['preferences'], indent=2)}

Adapt the message while:
1. Keeping the core content intact
2. Matching the formality level
3. Adjusting humor appropriately
4. Matching the detail level
5. Using emojis as preferred

Just provide the adapted message, no explanation."""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You adapt messages to match communication preferences."},
                {"role": "user", "content": prompt}
            ])
            return response.strip()
        except:
            return message


# ============================================================================
# RELATIONSHIP TRACKER
# ============================================================================

class RelationshipTracker:
    """Tracks overall relationship health and progression"""
    
    RELATIONSHIP_STAGES = {
        1: "Initial Contact",
        2: "Getting Acquainted",
        3: "Building Trust",
        4: "Established Partnership",
        5: "Deep Connection"
    }
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    def get_status(self) -> Dict[str, Any]:
        """Get current relationship status"""
        
        # Count private terms
        terms_count = self.db.query(func.count(PrivateLanguage.id)).filter(
            PrivateLanguage.entity_id == self.entity_id
        ).scalar() or 0
        
        # Get autonomy level (proxy for trust)
        autonomy = self.db.query(AutonomyLevel).filter(
            AutonomyLevel.entity_id == self.entity_id
        ).first()
        
        trust_level = autonomy.trust_score if autonomy else 0.3
        current_level = autonomy.current_level if autonomy else 1
        
        # Calculate relationship depth
        relationship_depth = min(1.0, (
            (terms_count * 0.02) +  # Each term adds 2%
            (trust_level * 0.5) +   # Trust is 50%
            (current_level * 0.1)   # Each autonomy level adds 10%
        ))
        
        # Determine stage
        if relationship_depth < 0.2:
            stage = 1
        elif relationship_depth < 0.4:
            stage = 2
        elif relationship_depth < 0.6:
            stage = 3
        elif relationship_depth < 0.8:
            stage = 4
        else:
            stage = 5
        
        return {
            "relationship_depth": relationship_depth,
            "trust_level": trust_level,
            "private_terms_count": terms_count,
            "shared_memories_count": 0,  # Would need SharedMemory table
            "communication_adaptations": 0,  # Would track from CommunicationStyle
            "relationship_stage": self.RELATIONSHIP_STAGES[stage],
            "stage_number": stage
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/private-language/add")
async def add_private_term(
    request: PrivateTermRequest,
    db: Session = Depends(get_db)
):
    """Add a new term to the private language vocabulary"""
    try:
        eid = UUID(request.entity_id)
        
        manager = PrivateLanguageManager(db, eid)
        term = manager.add_term(
            request.term,
            request.meaning,
            request.context,
            request.origin_story
        )
        
        return {
            "status": "added",
            "term": request.term,
            "usage_count": term.usage_count
        }
        
    except Exception as e:
        logger.error(f"Error adding term: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/private-language/{entity_id}")
async def get_vocabulary(
    entity_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get the private language vocabulary"""
    try:
        eid = UUID(entity_id)
        
        manager = PrivateLanguageManager(db, eid)
        vocabulary = manager.get_vocabulary(limit)
        
        return {
            "entity_id": entity_id,
            "count": len(vocabulary),
            "vocabulary": vocabulary
        }
        
    except Exception as e:
        logger.error(f"Error getting vocabulary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/private-language/suggest")
async def suggest_terms(
    entity_id: str,
    conversation: str,
    db: Session = Depends(get_db)
):
    """Suggest new private terms based on a conversation"""
    try:
        eid = UUID(entity_id)
        
        manager = PrivateLanguageManager(db, eid)
        suggestions = await manager.suggest_terms(conversation)
        
        return {
            "entity_id": entity_id,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Error suggesting terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shared-memory/record")
async def record_shared_memory(
    request: SharedMemoryRequest,
    db: Session = Depends(get_db)
):
    """Record a new shared memory"""
    try:
        eid = UUID(request.entity_id)
        
        builder = SharedMemoryBuilder(db, eid)
        memory = await builder.record_memory(
            request.memory_type,
            request.description,
            request.emotional_significance,
            request.participants
        )
        
        return {
            "status": "recorded",
            "memory": memory
        }
        
    except Exception as e:
        logger.error(f"Error recording memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/communication/update-preference")
async def update_communication_preference(
    request: CommunicationStyleUpdate,
    db: Session = Depends(get_db)
):
    """Update a communication style preference"""
    try:
        eid = UUID(request.entity_id)
        
        adapter = CommunicationAdapter(db, eid)
        result = adapter.update_preference(
            request.preference_type,
            request.preference_value,
            request.confidence
        )
        
        return {
            "status": "updated",
            **result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/communication/style-guide/{entity_id}")
async def get_style_guide(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get the current communication style guide"""
    try:
        eid = UUID(entity_id)
        
        adapter = CommunicationAdapter(db, eid)
        guide = adapter.get_style_guide()
        
        return {
            "entity_id": entity_id,
            **guide
        }
        
    except Exception as e:
        logger.error(f"Error getting style guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/communication/adapt-message")
async def adapt_message(
    entity_id: str,
    message: str,
    db: Session = Depends(get_db)
):
    """Adapt a message to match learned communication style"""
    try:
        eid = UUID(entity_id)
        
        adapter = CommunicationAdapter(db, eid)
        adapted = await adapter.adapt_message(message)
        
        return {
            "original": message,
            "adapted": adapted
        }
        
    except Exception as e:
        logger.error(f"Error adapting message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{entity_id}", response_model=RelationshipStatusResponse)
async def get_relationship_status(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get the current relationship status"""
    try:
        eid = UUID(entity_id)
        
        tracker = RelationshipTracker(db, eid)
        status = tracker.get_status()
        
        return RelationshipStatusResponse(
            entity_id=entity_id,
            **status
        )
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "relationship-builder", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
