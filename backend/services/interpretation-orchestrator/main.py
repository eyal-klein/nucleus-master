"""
NUCLEUS V2.0 - Interpretation Orchestrator

Manages and coordinates 10 interpretation engines that work together
to understand the entity's world from multiple perspectives:

1. Intent Interpreter - What does the entity want to achieve?
2. Emotion Interpreter - What is the entity feeling?
3. Context Interpreter - What is the current situation?
4. Relationship Interpreter - Who is involved and how?
5. Priority Interpreter - What matters most right now?
6. Risk Interpreter - What could go wrong?
7. Opportunity Interpreter - What possibilities exist?
8. Energy Interpreter - What is the entity's capacity?
9. Value Interpreter - Does this align with core values?
10. Time Interpreter - What are the temporal considerations?

Based on:
- GI X Document: "10 מנועי פרשנות" working in coherence
- NUCLEUS Agent Document: Multi-dimensional understanding
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import asyncio

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, Field

import sys
sys.path.insert(0, '/app/shared')

from models.base import get_db
from models.dna import Entity, Interest, Goal, Value
from models.memory import CalendarEvent, EmailMessage
from models.nucleus_core import AutonomyLevel, Domain
from llm.gateway import get_llm_gateway
from pubsub.publisher import get_publisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Interpretation Orchestrator",
    description="Coordinates 10 interpretation engines for multi-dimensional understanding",
    version="2.0.0"
)

llm = get_llm_gateway()
publisher = get_publisher()


# ============================================================================
# INTERPRETATION ENGINE DEFINITIONS
# ============================================================================

INTERPRETATION_ENGINES = {
    "intent": {
        "name": "Intent Interpreter",
        "question": "What is the entity trying to achieve?",
        "focus": ["goals", "actions", "requests", "implicit_needs"]
    },
    "emotion": {
        "name": "Emotion Interpreter",
        "question": "What emotional state is the entity in?",
        "focus": ["tone", "word_choice", "context_clues", "history"]
    },
    "context": {
        "name": "Context Interpreter",
        "question": "What is the current situation and environment?",
        "focus": ["time", "location", "recent_events", "ongoing_tasks"]
    },
    "relationship": {
        "name": "Relationship Interpreter",
        "question": "Who is involved and what are the relationship dynamics?",
        "focus": ["people_mentioned", "relationship_history", "social_context"]
    },
    "priority": {
        "name": "Priority Interpreter",
        "question": "What matters most right now?",
        "focus": ["urgency", "importance", "deadlines", "dependencies"]
    },
    "risk": {
        "name": "Risk Interpreter",
        "question": "What could go wrong or cause harm?",
        "focus": ["potential_issues", "conflicts", "resource_constraints"]
    },
    "opportunity": {
        "name": "Opportunity Interpreter",
        "question": "What possibilities or benefits exist?",
        "focus": ["potential_gains", "synergies", "timing_advantages"]
    },
    "energy": {
        "name": "Energy Interpreter",
        "question": "What is the entity's current capacity?",
        "focus": ["health_data", "schedule_load", "recent_activity"]
    },
    "value": {
        "name": "Value Interpreter",
        "question": "Does this align with the entity's core values?",
        "focus": ["values", "principles", "long_term_goals"]
    },
    "time": {
        "name": "Time Interpreter",
        "question": "What are the temporal considerations?",
        "focus": ["deadlines", "duration", "scheduling", "time_sensitivity"]
    }
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class InterpretationRequest(BaseModel):
    """Request to interpret a situation"""
    entity_id: str
    situation: str
    context: Optional[Dict[str, Any]] = None
    engines: Optional[List[str]] = None  # If None, use all engines
    depth: str = Field(default="standard")  # quick, standard, deep


class SingleInterpretation(BaseModel):
    """Result from a single interpretation engine"""
    engine: str
    engine_name: str
    interpretation: str
    confidence: float
    key_insights: List[str]
    recommendations: List[str]


class InterpretationResponse(BaseModel):
    """Combined interpretation from all engines"""
    entity_id: str
    situation: str
    interpretations: List[SingleInterpretation]
    synthesis: str
    overall_confidence: float
    action_recommendations: List[str]
    warnings: List[str]


class QuickInterpretRequest(BaseModel):
    """Request for quick interpretation (subset of engines)"""
    entity_id: str
    situation: str
    focus: str  # intent, emotion, priority, risk


# ============================================================================
# INTERPRETATION ENGINE
# ============================================================================

class InterpretationEngine:
    """Individual interpretation engine"""
    
    def __init__(self, engine_id: str, db: Session, entity_id: UUID):
        self.engine_id = engine_id
        self.config = INTERPRETATION_ENGINES[engine_id]
        self.db = db
        self.entity_id = entity_id
        
    async def interpret(
        self,
        situation: str,
        context: Dict[str, Any],
        depth: str
    ) -> Dict[str, Any]:
        """Run interpretation for this engine"""
        
        # Gather relevant data based on focus areas
        entity_data = await self._gather_entity_data()
        
        prompt = f"""You are the {self.config['name']} for an AI assistant.

Your question to answer: {self.config['question']}

Focus areas: {', '.join(self.config['focus'])}

Situation to interpret:
{situation}

Additional context:
{json.dumps(context or {}, indent=2)}

Entity data:
{json.dumps(entity_data, indent=2)}

Depth level: {depth}

Provide your interpretation as JSON:
{{
    "interpretation": "Your detailed interpretation",
    "confidence": 0.0-1.0,
    "key_insights": ["insight 1", "insight 2"],
    "recommendations": ["recommendation 1", "recommendation 2"],
    "flags": ["any warnings or concerns"]
}}

Be specific and actionable."""

        try:
            response = await llm.complete([
                {"role": "system", "content": f"You are the {self.config['name']}, specialized in understanding {self.config['question']}"},
                {"role": "user", "content": prompt}
            ])
            
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            return result
            
        except Exception as e:
            logger.error(f"Error in {self.engine_id} interpreter: {e}")
            return {
                "interpretation": f"Error: {str(e)}",
                "confidence": 0.0,
                "key_insights": [],
                "recommendations": [],
                "flags": ["Interpretation failed"]
            }
    
    async def _gather_entity_data(self) -> Dict[str, Any]:
        """Gather relevant entity data for interpretation"""
        
        data = {}
        
        # Get entity
        entity = self.db.query(Entity).filter(Entity.id == self.entity_id).first()
        if entity:
            data["entity_name"] = entity.name
        
        # Get data based on engine focus
        if self.engine_id == "intent":
            goals = self.db.query(Goal).filter(
                and_(Goal.entity_id == self.entity_id, Goal.is_active == True)
            ).limit(5).all()
            data["active_goals"] = [{"title": g.title, "priority": g.priority} for g in goals]
            
        elif self.engine_id == "value":
            values = self.db.query(Value).filter(
                Value.entity_id == self.entity_id
            ).limit(5).all()
            data["core_values"] = [{"name": v.value_name, "importance": v.importance_score} for v in values]
            
        elif self.engine_id == "energy":
            autonomy = self.db.query(AutonomyLevel).filter(
                AutonomyLevel.entity_id == self.entity_id
            ).first()
            if autonomy:
                data["autonomy_level"] = autonomy.current_level
                data["trust_score"] = autonomy.trust_score
                
        elif self.engine_id == "context":
            # Get recent calendar events
            now = datetime.utcnow()
            events = self.db.query(CalendarEvent).filter(
                and_(
                    CalendarEvent.entity_id == self.entity_id,
                    CalendarEvent.start_time >= now,
                    CalendarEvent.start_time <= now + timedelta(days=1)
                )
            ).limit(5).all()
            data["upcoming_events"] = [{"title": e.title, "start": str(e.start_time)} for e in events]
        
        return data


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class InterpretationOrchestrator:
    """Orchestrates all interpretation engines"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def interpret(
        self,
        situation: str,
        context: Optional[Dict[str, Any]],
        engines: Optional[List[str]],
        depth: str
    ) -> Dict[str, Any]:
        """Run interpretation across all or selected engines"""
        
        # Determine which engines to use
        engine_ids = engines if engines else list(INTERPRETATION_ENGINES.keys())
        
        # Run interpretations in parallel
        tasks = []
        for engine_id in engine_ids:
            if engine_id in INTERPRETATION_ENGINES:
                engine = InterpretationEngine(engine_id, self.db, self.entity_id)
                tasks.append(self._run_engine(engine, situation, context or {}, depth))
        
        results = await asyncio.gather(*tasks)
        
        # Collect interpretations
        interpretations = []
        all_insights = []
        all_recommendations = []
        all_warnings = []
        total_confidence = 0
        
        for engine_id, result in zip(engine_ids, results):
            config = INTERPRETATION_ENGINES.get(engine_id, {})
            interpretations.append({
                "engine": engine_id,
                "engine_name": config.get("name", engine_id),
                "interpretation": result.get("interpretation", ""),
                "confidence": result.get("confidence", 0.5),
                "key_insights": result.get("key_insights", []),
                "recommendations": result.get("recommendations", [])
            })
            
            all_insights.extend(result.get("key_insights", []))
            all_recommendations.extend(result.get("recommendations", []))
            all_warnings.extend(result.get("flags", []))
            total_confidence += result.get("confidence", 0.5)
        
        # Synthesize all interpretations
        synthesis = await self._synthesize(situation, interpretations)
        
        return {
            "interpretations": interpretations,
            "synthesis": synthesis,
            "overall_confidence": total_confidence / len(engine_ids) if engine_ids else 0,
            "action_recommendations": list(set(all_recommendations))[:5],
            "warnings": list(set(all_warnings))
        }
    
    async def _run_engine(
        self,
        engine: InterpretationEngine,
        situation: str,
        context: Dict[str, Any],
        depth: str
    ) -> Dict[str, Any]:
        """Run a single engine with error handling"""
        try:
            return await engine.interpret(situation, context, depth)
        except Exception as e:
            logger.error(f"Engine {engine.engine_id} failed: {e}")
            return {"interpretation": "Failed", "confidence": 0, "key_insights": [], "recommendations": [], "flags": [str(e)]}
    
    async def _synthesize(
        self,
        situation: str,
        interpretations: List[Dict[str, Any]]
    ) -> str:
        """Synthesize all interpretations into a coherent understanding"""
        
        interp_summary = "\n".join([
            f"- {i['engine_name']}: {i['interpretation'][:200]}..."
            for i in interpretations
        ])
        
        synthesis_prompt = f"""Synthesize these 10 interpretations into a coherent understanding.

Situation: {situation}

Interpretations:
{interp_summary}

Provide a unified synthesis that:
1. Identifies the most important insights
2. Resolves any contradictions
3. Provides a clear action path

Keep it concise (2-3 paragraphs)."""

        try:
            response = await llm.complete([
                {"role": "system", "content": "You synthesize multiple perspectives into coherent understanding."},
                {"role": "user", "content": synthesis_prompt}
            ])
            return response.strip()
        except Exception as e:
            return f"Synthesis failed: {str(e)}"


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/interpret", response_model=InterpretationResponse)
async def interpret_situation(
    request: InterpretationRequest,
    db: Session = Depends(get_db)
):
    """
    Interpret a situation using all or selected interpretation engines.
    
    The 10 engines provide multi-dimensional understanding:
    - Intent, Emotion, Context, Relationship, Priority
    - Risk, Opportunity, Energy, Value, Time
    """
    try:
        eid = UUID(request.entity_id)
        
        orchestrator = InterpretationOrchestrator(db, eid)
        result = await orchestrator.interpret(
            request.situation,
            request.context,
            request.engines,
            request.depth
        )
        
        return InterpretationResponse(
            entity_id=request.entity_id,
            situation=request.situation,
            interpretations=[SingleInterpretation(**i) for i in result["interpretations"]],
            synthesis=result["synthesis"],
            overall_confidence=result["overall_confidence"],
            action_recommendations=result["action_recommendations"],
            warnings=result["warnings"]
        )
        
    except Exception as e:
        logger.error(f"Error interpreting situation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quick-interpret")
async def quick_interpret(
    request: QuickInterpretRequest,
    db: Session = Depends(get_db)
):
    """
    Quick interpretation using a single focused engine.
    
    Useful for real-time decisions where speed matters.
    """
    try:
        eid = UUID(request.entity_id)
        
        if request.focus not in INTERPRETATION_ENGINES:
            raise HTTPException(status_code=400, detail=f"Unknown engine: {request.focus}")
        
        engine = InterpretationEngine(request.focus, db, eid)
        result = await engine.interpret(request.situation, {}, "quick")
        
        return {
            "entity_id": request.entity_id,
            "engine": request.focus,
            "interpretation": result.get("interpretation", ""),
            "confidence": result.get("confidence", 0.5),
            "key_insights": result.get("key_insights", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick interpret: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/engines")
async def list_engines():
    """List all available interpretation engines"""
    return {
        "count": len(INTERPRETATION_ENGINES),
        "engines": [
            {
                "id": eid,
                "name": config["name"],
                "question": config["question"],
                "focus": config["focus"]
            }
            for eid, config in INTERPRETATION_ENGINES.items()
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "interpretation-orchestrator", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
