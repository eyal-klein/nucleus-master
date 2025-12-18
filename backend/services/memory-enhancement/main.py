"""
NUCLEUS V2.0 - Memory Enhancement

Enhances the memory system with:
1. Proactive Memory Refresh - Surfaces relevant memories at the right time
2. Memory Coherence Loop - Ensures consistency across memory tiers
3. Memory Consolidation - Moves important memories to long-term storage
4. Memory Decay Management - Handles forgetting and archival
5. Contextual Memory Retrieval - Finds relevant memories for current context

Based on:
- GI X Document: "רענון יזום" and "לופ קוהרנטיות"
- NUCLEUS Agent Document: Memory management and coherence
- Existing memory-engine: Extends, doesn't duplicate
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, '/app/shared')

from models.base import get_db
from models.memory import MemoryTier1, MemoryTier2, MemoryTier3, MemoryTier4
from models.dna import Entity
from llm.gateway import get_llm_gateway
from pubsub.publisher import get_publisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Memory Enhancement",
    description="Enhances memory with proactive refresh, coherence, and contextual retrieval",
    version="2.0.0"
)

llm = get_llm_gateway()
publisher = get_publisher()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ContextualRetrievalRequest(BaseModel):
    """Request to retrieve contextually relevant memories"""
    entity_id: str
    context: str
    context_type: Optional[str] = None  # meeting, task, conversation, decision
    max_results: int = Field(default=10, ge=1, le=50)
    include_tiers: List[int] = Field(default=[1, 2, 3])


class MemoryRefreshRequest(BaseModel):
    """Request to refresh memories for an entity"""
    entity_id: str
    trigger_type: str  # scheduled, context_change, user_request
    context: Optional[str] = None


class CoherenceCheckRequest(BaseModel):
    """Request to check memory coherence"""
    entity_id: str
    check_depth: str = Field(default="standard")  # quick, standard, deep


class ConsolidationRequest(BaseModel):
    """Request to consolidate memories"""
    entity_id: str
    days_threshold: int = Field(default=7)  # Consolidate memories older than X days


class MemoryResult(BaseModel):
    """A memory result"""
    id: str
    tier: int
    content: str
    relevance_score: float
    created_at: str
    interaction_type: str


# ============================================================================
# CONTEXTUAL RETRIEVER
# ============================================================================

class ContextualRetriever:
    """Retrieves memories based on context"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def retrieve(
        self,
        context: str,
        context_type: Optional[str],
        max_results: int,
        include_tiers: List[int]
    ) -> List[Dict[str, Any]]:
        """Retrieve contextually relevant memories"""
        
        all_memories = []
        
        # Gather memories from each tier
        if 1 in include_tiers:
            tier1 = self.db.query(MemoryTier1).filter(
                MemoryTier1.entity_id == self.entity_id
            ).order_by(MemoryTier1.created_at.desc()).limit(100).all()
            all_memories.extend([
                {"tier": 1, "id": str(m.id), "content": json.dumps(m.interaction_data), 
                 "type": m.interaction_type, "created": m.created_at}
                for m in tier1
            ])
        
        if 2 in include_tiers:
            tier2 = self.db.query(MemoryTier2).filter(
                MemoryTier2.entity_id == self.entity_id
            ).order_by(MemoryTier2.created_at.desc()).limit(100).all()
            all_memories.extend([
                {"tier": 2, "id": str(m.id), "content": json.dumps(m.interaction_data),
                 "type": m.interaction_type, "created": m.created_at}
                for m in tier2
            ])
        
        if 3 in include_tiers:
            tier3 = self.db.query(MemoryTier3).filter(
                MemoryTier3.entity_id == self.entity_id
            ).order_by(MemoryTier3.created_at.desc()).limit(50).all()
            all_memories.extend([
                {"tier": 3, "id": str(m.id), "content": json.dumps(m.interaction_data),
                 "type": m.interaction_type, "created": m.created_at}
                for m in tier3
            ])
        
        if not all_memories:
            return []
        
        # Use LLM to rank by relevance
        ranked = await self._rank_by_relevance(context, context_type, all_memories)
        
        return ranked[:max_results]
    
    async def _rank_by_relevance(
        self,
        context: str,
        context_type: Optional[str],
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank memories by relevance to context"""
        
        # Prepare memory summaries for ranking
        memory_summaries = []
        for i, m in enumerate(memories[:50]):  # Limit to 50 for LLM
            content = m["content"][:200] if len(m["content"]) > 200 else m["content"]
            memory_summaries.append(f"{i}: [{m['type']}] {content}")
        
        prompt = f"""Rank these memories by relevance to the current context.

Current context: {context}
Context type: {context_type or 'general'}

Memories:
{chr(10).join(memory_summaries)}

Return a JSON array of indices sorted by relevance (most relevant first):
{{"ranked_indices": [index1, index2, ...], "relevance_scores": [score1, score2, ...]}}

Scores should be 0.0-1.0. Only include memories with relevance > 0.3."""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You rank memories by contextual relevance."},
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            ranked_indices = result.get("ranked_indices", [])
            scores = result.get("relevance_scores", [])
            
            ranked_memories = []
            for i, idx in enumerate(ranked_indices):
                if idx < len(memories):
                    m = memories[idx]
                    m["relevance_score"] = scores[i] if i < len(scores) else 0.5
                    ranked_memories.append(m)
            
            return ranked_memories
            
        except Exception as e:
            logger.error(f"Error ranking memories: {e}")
            # Return unranked with default score
            for m in memories:
                m["relevance_score"] = 0.5
            return memories


# ============================================================================
# PROACTIVE REFRESHER
# ============================================================================

class ProactiveRefresher:
    """Proactively surfaces relevant memories"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def refresh(
        self,
        trigger_type: str,
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Proactively refresh and surface relevant memories"""
        
        surfaced_memories = []
        
        # Different strategies based on trigger type
        if trigger_type == "scheduled":
            # Daily refresh - surface important memories that haven't been accessed
            surfaced_memories = await self._scheduled_refresh()
            
        elif trigger_type == "context_change":
            # Context changed - find relevant memories
            if context:
                retriever = ContextualRetriever(self.db, self.entity_id)
                surfaced_memories = await retriever.retrieve(context, None, 5, [1, 2, 3])
                
        elif trigger_type == "user_request":
            # User explicitly asked - comprehensive retrieval
            if context:
                retriever = ContextualRetriever(self.db, self.entity_id)
                surfaced_memories = await retriever.retrieve(context, None, 10, [1, 2, 3, 4])
        
        # Publish refresh event
        if surfaced_memories:
            publisher.publish_event(
                "digital",
                "memory.refresh.completed",
                str(self.entity_id),
                {
                    "trigger": trigger_type,
                    "memories_surfaced": len(surfaced_memories)
                }
            )
        
        return {
            "trigger_type": trigger_type,
            "memories_surfaced": len(surfaced_memories),
            "memories": surfaced_memories
        }
    
    async def _scheduled_refresh(self) -> List[Dict[str, Any]]:
        """Scheduled daily refresh"""
        
        # Find memories that are important but not recently accessed
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Get tier 2 memories (working memory) that might need refresh
        memories = self.db.query(MemoryTier2).filter(
            and_(
                MemoryTier2.entity_id == self.entity_id,
                MemoryTier2.created_at >= cutoff
            )
        ).order_by(func.random()).limit(5).all()
        
        return [
            {
                "tier": 2,
                "id": str(m.id),
                "content": json.dumps(m.interaction_data)[:200],
                "type": m.interaction_type,
                "relevance_score": 0.6
            }
            for m in memories
        ]


# ============================================================================
# COHERENCE CHECKER
# ============================================================================

class CoherenceChecker:
    """Checks and maintains memory coherence"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def check_coherence(self, depth: str) -> Dict[str, Any]:
        """Check memory coherence across tiers"""
        
        issues = []
        
        # Check 1: Tier progression (memories should flow down tiers)
        tier1_count = self.db.query(func.count(MemoryTier1.id)).filter(
            MemoryTier1.entity_id == self.entity_id
        ).scalar() or 0
        
        tier2_count = self.db.query(func.count(MemoryTier2.id)).filter(
            MemoryTier2.entity_id == self.entity_id
        ).scalar() or 0
        
        tier3_count = self.db.query(func.count(MemoryTier3.id)).filter(
            MemoryTier3.entity_id == self.entity_id
        ).scalar() or 0
        
        # Tier 1 should have more than tier 2, tier 2 more than tier 3
        if tier2_count > tier1_count * 0.8:
            issues.append({
                "type": "tier_imbalance",
                "severity": "medium",
                "description": "Tier 2 has too many memories relative to Tier 1"
            })
        
        # Check 2: Memory staleness
        week_ago = datetime.utcnow() - timedelta(days=7)
        stale_tier1 = self.db.query(func.count(MemoryTier1.id)).filter(
            and_(
                MemoryTier1.entity_id == self.entity_id,
                MemoryTier1.created_at < week_ago
            )
        ).scalar() or 0
        
        if stale_tier1 > 100:
            issues.append({
                "type": "stale_memories",
                "severity": "low",
                "description": f"{stale_tier1} memories in Tier 1 older than 7 days"
            })
        
        # Check 3: Deep coherence check (if requested)
        if depth == "deep":
            content_issues = await self._check_content_coherence()
            issues.extend(content_issues)
        
        coherence_score = max(0, 1.0 - (len(issues) * 0.1))
        
        return {
            "coherence_score": coherence_score,
            "tier_counts": {
                "tier1": tier1_count,
                "tier2": tier2_count,
                "tier3": tier3_count
            },
            "issues_found": len(issues),
            "issues": issues,
            "recommendations": self._generate_recommendations(issues)
        }
    
    async def _check_content_coherence(self) -> List[Dict[str, Any]]:
        """Check for content-level coherence issues"""
        
        # Sample memories and check for contradictions
        tier2_samples = self.db.query(MemoryTier2).filter(
            MemoryTier2.entity_id == self.entity_id
        ).order_by(MemoryTier2.created_at.desc()).limit(20).all()
        
        if len(tier2_samples) < 5:
            return []
        
        # Use LLM to check for contradictions
        memory_texts = [
            f"[{m.interaction_type}] {json.dumps(m.interaction_data)[:150]}"
            for m in tier2_samples
        ]
        
        prompt = f"""Check these memories for contradictions or inconsistencies.

Memories:
{chr(10).join(memory_texts)}

Return JSON:
{{
    "contradictions_found": true/false,
    "issues": [
        {{"type": "contradiction", "description": "what contradicts what"}}
    ]
}}"""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You check memories for coherence issues."},
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            return result.get("issues", [])
            
        except:
            return []
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on issues"""
        
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "tier_imbalance":
                recommendations.append("Run memory consolidation to balance tiers")
            elif issue["type"] == "stale_memories":
                recommendations.append("Archive old Tier 1 memories to lower tiers")
            elif issue["type"] == "contradiction":
                recommendations.append("Review and resolve contradictory memories")
        
        return recommendations


# ============================================================================
# MEMORY CONSOLIDATOR
# ============================================================================

class MemoryConsolidator:
    """Consolidates memories across tiers"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def consolidate(self, days_threshold: int) -> Dict[str, Any]:
        """Consolidate memories from Tier 1 to lower tiers"""
        
        cutoff = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Find old Tier 1 memories
        old_memories = self.db.query(MemoryTier1).filter(
            and_(
                MemoryTier1.entity_id == self.entity_id,
                MemoryTier1.created_at < cutoff
            )
        ).all()
        
        if not old_memories:
            return {
                "status": "no_consolidation_needed",
                "memories_processed": 0
            }
        
        # Evaluate importance and move to appropriate tier
        moved_to_tier2 = 0
        moved_to_tier3 = 0
        archived = 0
        
        for memory in old_memories:
            importance = await self._evaluate_importance(memory)
            
            if importance > 0.7:
                # Important - move to Tier 2
                tier2_memory = MemoryTier2(
                    entity_id=self.entity_id,
                    interaction_type=memory.interaction_type,
                    interaction_data=memory.interaction_data,
                    created_at=memory.created_at
                )
                self.db.add(tier2_memory)
                moved_to_tier2 += 1
                
            elif importance > 0.4:
                # Moderately important - move to Tier 3
                tier3_memory = MemoryTier3(
                    entity_id=self.entity_id,
                    interaction_type=memory.interaction_type,
                    interaction_data=memory.interaction_data,
                    created_at=memory.created_at
                )
                self.db.add(tier3_memory)
                moved_to_tier3 += 1
                
            else:
                # Not important - archive or delete
                archived += 1
            
            # Remove from Tier 1
            self.db.delete(memory)
        
        self.db.commit()
        
        return {
            "status": "consolidation_complete",
            "memories_processed": len(old_memories),
            "moved_to_tier2": moved_to_tier2,
            "moved_to_tier3": moved_to_tier3,
            "archived": archived
        }
    
    async def _evaluate_importance(self, memory: MemoryTier1) -> float:
        """Evaluate the importance of a memory"""
        
        # Simple heuristic based on interaction type
        importance_weights = {
            "decision": 0.8,
            "task_execution": 0.6,
            "conversation": 0.5,
            "event": 0.4,
            "action": 0.5
        }
        
        base_importance = importance_weights.get(memory.interaction_type, 0.5)
        
        # Adjust based on content (simplified)
        content = json.dumps(memory.interaction_data)
        if "important" in content.lower() or "critical" in content.lower():
            base_importance += 0.2
        
        return min(1.0, base_importance)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/retrieve")
async def retrieve_contextual_memories(
    request: ContextualRetrievalRequest,
    db: Session = Depends(get_db)
):
    """Retrieve memories relevant to the current context"""
    try:
        eid = UUID(request.entity_id)
        
        retriever = ContextualRetriever(db, eid)
        memories = await retriever.retrieve(
            request.context,
            request.context_type,
            request.max_results,
            request.include_tiers
        )
        
        return {
            "entity_id": request.entity_id,
            "context": request.context,
            "memories_found": len(memories),
            "memories": [
                MemoryResult(
                    id=m["id"],
                    tier=m["tier"],
                    content=m["content"][:500],
                    relevance_score=m.get("relevance_score", 0.5),
                    created_at=str(m.get("created", "")),
                    interaction_type=m.get("type", "unknown")
                ).dict()
                for m in memories
            ]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refresh")
async def refresh_memories(
    request: MemoryRefreshRequest,
    db: Session = Depends(get_db)
):
    """Proactively refresh and surface relevant memories"""
    try:
        eid = UUID(request.entity_id)
        
        refresher = ProactiveRefresher(db, eid)
        result = await refresher.refresh(request.trigger_type, request.context)
        
        return {
            "entity_id": request.entity_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error refreshing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/coherence-check")
async def check_coherence(
    request: CoherenceCheckRequest,
    db: Session = Depends(get_db)
):
    """Check memory coherence across tiers"""
    try:
        eid = UUID(request.entity_id)
        
        checker = CoherenceChecker(db, eid)
        result = await checker.check_coherence(request.check_depth)
        
        return {
            "entity_id": request.entity_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error checking coherence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/consolidate")
async def consolidate_memories(
    request: ConsolidationRequest,
    db: Session = Depends(get_db)
):
    """Consolidate memories from Tier 1 to lower tiers"""
    try:
        eid = UUID(request.entity_id)
        
        consolidator = MemoryConsolidator(db, eid)
        result = await consolidator.consolidate(request.days_threshold)
        
        return {
            "entity_id": request.entity_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error consolidating memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/{entity_id}")
async def get_memory_stats(
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get memory statistics"""
    try:
        eid = UUID(entity_id)
        
        tier1 = db.query(func.count(MemoryTier1.id)).filter(
            MemoryTier1.entity_id == eid
        ).scalar() or 0
        
        tier2 = db.query(func.count(MemoryTier2.id)).filter(
            MemoryTier2.entity_id == eid
        ).scalar() or 0
        
        tier3 = db.query(func.count(MemoryTier3.id)).filter(
            MemoryTier3.entity_id == eid
        ).scalar() or 0
        
        tier4 = db.query(func.count(MemoryTier4.id)).filter(
            MemoryTier4.entity_id == eid
        ).scalar() or 0
        
        return {
            "entity_id": entity_id,
            "total_memories": tier1 + tier2 + tier3 + tier4,
            "by_tier": {
                "tier1_hot": tier1,
                "tier2_working": tier2,
                "tier3_reference": tier3,
                "tier4_archive": tier4
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "memory-enhancement", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
