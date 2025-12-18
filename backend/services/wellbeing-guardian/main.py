"""
NUCLEUS V2.0 - Wellbeing Guardian

Protects the entity's emotional and cognitive wellbeing through:
1. Cognitive Load Monitoring - Prevents overwhelm
2. Emotional State Tracking - Detects stress/burnout
3. Boundary Protection - Respects work-life balance
4. Intervention Triggers - Suggests breaks/changes
5. Wellbeing Recommendations - Proactive wellness suggestions

Based on:
- GI X Document: "שמירה רגשית וקוגניטיבית"
- NUCLEUS Agent Document: Entity protection and care
- Existing health-wellness-engine: Complements, doesn't duplicate
  (health-wellness-engine focuses on physical metrics,
   wellbeing-guardian focuses on cognitive/emotional protection)
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
from models.dna import Entity, DailyReadiness
from models.memory import CalendarEvent
from models.nucleus_core import WellbeingCheck, BehaviorLog
from llm.gateway import get_llm_gateway
from pubsub.publisher import get_publisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wellbeing Guardian",
    description="Protects entity's emotional and cognitive wellbeing",
    version="2.0.0"
)

llm = get_llm_gateway()
publisher = get_publisher()


# ============================================================================
# WELLBEING THRESHOLDS
# ============================================================================

WELLBEING_THRESHOLDS = {
    "cognitive_load": {
        "low": 0.3,
        "moderate": 0.5,
        "high": 0.7,
        "critical": 0.85
    },
    "stress_level": {
        "low": 0.3,
        "moderate": 0.5,
        "high": 0.7,
        "critical": 0.85
    },
    "work_hours": {
        "healthy": 8,
        "concerning": 10,
        "critical": 12
    },
    "meeting_density": {
        "healthy": 0.4,  # 40% of day
        "concerning": 0.6,
        "critical": 0.8
    }
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class WellbeingCheckRequest(BaseModel):
    """Request to check entity wellbeing"""
    entity_id: str
    include_recommendations: bool = True


class CognitiveLoadRequest(BaseModel):
    """Request to assess cognitive load"""
    entity_id: str
    current_tasks: Optional[List[str]] = None
    context: Optional[str] = None


class InterventionRequest(BaseModel):
    """Request to check if intervention is needed"""
    entity_id: str
    trigger_type: str  # scheduled, real_time, user_request


class WellbeingStatus(BaseModel):
    """Wellbeing status response"""
    entity_id: str
    overall_score: float
    cognitive_load: float
    stress_level: float
    energy_level: float
    status: str  # healthy, concerning, critical
    alerts: List[str]
    recommendations: List[str]


# ============================================================================
# COGNITIVE LOAD MONITOR
# ============================================================================

class CognitiveLoadMonitor:
    """Monitors and assesses cognitive load"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def assess(
        self,
        current_tasks: Optional[List[str]],
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Assess current cognitive load"""
        
        factors = {}
        
        # Factor 1: Calendar density
        calendar_load = await self._assess_calendar_load()
        factors["calendar_density"] = calendar_load
        
        # Factor 2: Active tasks
        task_load = await self._assess_task_load(current_tasks)
        factors["task_load"] = task_load
        
        # Factor 3: Recent activity intensity
        activity_load = await self._assess_activity_intensity()
        factors["activity_intensity"] = activity_load
        
        # Factor 4: Context switching
        context_switching = await self._assess_context_switching()
        factors["context_switching"] = context_switching
        
        # Calculate overall cognitive load
        overall_load = (
            calendar_load * 0.3 +
            task_load * 0.3 +
            activity_load * 0.2 +
            context_switching * 0.2
        )
        
        # Determine status
        if overall_load >= WELLBEING_THRESHOLDS["cognitive_load"]["critical"]:
            status = "critical"
        elif overall_load >= WELLBEING_THRESHOLDS["cognitive_load"]["high"]:
            status = "high"
        elif overall_load >= WELLBEING_THRESHOLDS["cognitive_load"]["moderate"]:
            status = "moderate"
        else:
            status = "low"
        
        return {
            "cognitive_load": overall_load,
            "status": status,
            "factors": factors,
            "recommendations": self._generate_load_recommendations(overall_load, factors)
        }
    
    async def _assess_calendar_load(self) -> float:
        """Assess load from calendar"""
        
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        events = self.db.query(CalendarEvent).filter(
            and_(
                CalendarEvent.entity_id == self.entity_id,
                CalendarEvent.start_time >= datetime.combine(today, datetime.min.time()),
                CalendarEvent.start_time < datetime.combine(tomorrow, datetime.min.time())
            )
        ).all()
        
        if not events:
            return 0.2
        
        # Calculate meeting hours
        total_hours = sum([
            (e.end_time - e.start_time).total_seconds() / 3600
            for e in events if e.end_time
        ])
        
        # Normalize to 0-1 (assuming 8 hour workday)
        return min(1.0, total_hours / 8)
    
    async def _assess_task_load(self, tasks: Optional[List[str]]) -> float:
        """Assess load from tasks"""
        
        if not tasks:
            return 0.3  # Default moderate load
        
        # Simple heuristic: more tasks = higher load
        task_count = len(tasks)
        
        if task_count <= 2:
            return 0.3
        elif task_count <= 5:
            return 0.5
        elif task_count <= 8:
            return 0.7
        else:
            return 0.9
    
    async def _assess_activity_intensity(self) -> float:
        """Assess recent activity intensity"""
        
        # Check recent behavior logs
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        recent_actions = self.db.query(func.count(BehaviorLog.id)).filter(
            and_(
                BehaviorLog.entity_id == self.entity_id,
                BehaviorLog.created_at >= hour_ago
            )
        ).scalar() or 0
        
        # Normalize: 0-10 actions = low, 10-30 = moderate, 30+ = high
        if recent_actions < 10:
            return 0.3
        elif recent_actions < 30:
            return 0.5
        else:
            return min(1.0, recent_actions / 50)
    
    async def _assess_context_switching(self) -> float:
        """Assess context switching frequency"""
        
        # Check variety of action types in last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        action_types = self.db.query(BehaviorLog.action_type).filter(
            and_(
                BehaviorLog.entity_id == self.entity_id,
                BehaviorLog.created_at >= hour_ago
            )
        ).distinct().all()
        
        unique_types = len(action_types)
        
        # More variety = more context switching
        if unique_types <= 2:
            return 0.2
        elif unique_types <= 4:
            return 0.4
        elif unique_types <= 6:
            return 0.6
        else:
            return 0.8
    
    def _generate_load_recommendations(
        self,
        overall_load: float,
        factors: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on load"""
        
        recommendations = []
        
        if overall_load >= 0.7:
            recommendations.append("Consider taking a short break")
            recommendations.append("Prioritize and defer non-urgent tasks")
        
        if factors.get("calendar_density", 0) >= 0.6:
            recommendations.append("Consider declining or rescheduling some meetings")
        
        if factors.get("context_switching", 0) >= 0.6:
            recommendations.append("Try to batch similar tasks together")
        
        if factors.get("activity_intensity", 0) >= 0.7:
            recommendations.append("Slow down - high activity detected")
        
        return recommendations


# ============================================================================
# STRESS DETECTOR
# ============================================================================

class StressDetector:
    """Detects stress and burnout indicators"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def detect(self) -> Dict[str, Any]:
        """Detect current stress level"""
        
        indicators = {}
        
        # Indicator 1: Work hours trend
        work_hours = await self._analyze_work_hours()
        indicators["work_hours_trend"] = work_hours
        
        # Indicator 2: Response patterns
        response_patterns = await self._analyze_response_patterns()
        indicators["response_patterns"] = response_patterns
        
        # Indicator 3: Health metrics (if available)
        health_indicators = await self._check_health_indicators()
        indicators["health_indicators"] = health_indicators
        
        # Calculate stress level
        stress_level = (
            work_hours * 0.4 +
            response_patterns * 0.3 +
            health_indicators * 0.3
        )
        
        # Determine status
        if stress_level >= WELLBEING_THRESHOLDS["stress_level"]["critical"]:
            status = "critical"
            alerts = ["High stress detected - intervention recommended"]
        elif stress_level >= WELLBEING_THRESHOLDS["stress_level"]["high"]:
            status = "high"
            alerts = ["Elevated stress levels detected"]
        elif stress_level >= WELLBEING_THRESHOLDS["stress_level"]["moderate"]:
            status = "moderate"
            alerts = []
        else:
            status = "low"
            alerts = []
        
        return {
            "stress_level": stress_level,
            "status": status,
            "indicators": indicators,
            "alerts": alerts
        }
    
    async def _analyze_work_hours(self) -> float:
        """Analyze work hours trend"""
        
        # Check calendar events for the past week
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        events = self.db.query(CalendarEvent).filter(
            and_(
                CalendarEvent.entity_id == self.entity_id,
                CalendarEvent.start_time >= week_ago
            )
        ).all()
        
        if not events:
            return 0.3
        
        # Calculate average daily hours
        total_hours = sum([
            (e.end_time - e.start_time).total_seconds() / 3600
            for e in events if e.end_time
        ])
        
        avg_daily = total_hours / 7
        
        if avg_daily <= 8:
            return 0.3
        elif avg_daily <= 10:
            return 0.5
        elif avg_daily <= 12:
            return 0.7
        else:
            return 0.9
    
    async def _analyze_response_patterns(self) -> float:
        """Analyze response time patterns"""
        
        # Check behavior logs for response times
        day_ago = datetime.utcnow() - timedelta(days=1)
        
        logs = self.db.query(BehaviorLog).filter(
            and_(
                BehaviorLog.entity_id == self.entity_id,
                BehaviorLog.created_at >= day_ago,
                BehaviorLog.response_time_ms.isnot(None)
            )
        ).all()
        
        if not logs:
            return 0.3
        
        # Calculate average response time
        avg_response = sum(l.response_time_ms for l in logs) / len(logs)
        
        # Longer response times might indicate fatigue
        if avg_response < 500:
            return 0.3
        elif avg_response < 1000:
            return 0.5
        elif avg_response < 2000:
            return 0.7
        else:
            return 0.9
    
    async def _check_health_indicators(self) -> float:
        """Check health indicators if available"""
        
        # Get latest readiness score
        readiness = self.db.query(DailyReadiness).filter(
            DailyReadiness.entity_id == self.entity_id
        ).order_by(DailyReadiness.date.desc()).first()
        
        if not readiness:
            return 0.5  # Unknown
        
        # Invert readiness (low readiness = high stress indicator)
        return 1.0 - readiness.readiness_score


# ============================================================================
# INTERVENTION MANAGER
# ============================================================================

class InterventionManager:
    """Manages wellbeing interventions"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def check_intervention_needed(
        self,
        cognitive_load: float,
        stress_level: float
    ) -> Dict[str, Any]:
        """Check if intervention is needed"""
        
        interventions = []
        
        # Critical cognitive load
        if cognitive_load >= 0.85:
            interventions.append({
                "type": "immediate_break",
                "priority": "high",
                "message": "You've been working intensely. A 10-minute break would help.",
                "action": "suggest_break"
            })
        
        # High stress
        if stress_level >= 0.7:
            interventions.append({
                "type": "stress_relief",
                "priority": "high",
                "message": "Stress levels are elevated. Consider a brief walk or breathing exercise.",
                "action": "suggest_destress"
            })
        
        # Combined high load
        if cognitive_load >= 0.6 and stress_level >= 0.6:
            interventions.append({
                "type": "workload_review",
                "priority": "medium",
                "message": "Your workload seems heavy. Would you like help prioritizing?",
                "action": "offer_prioritization"
            })
        
        return {
            "intervention_needed": len(interventions) > 0,
            "interventions": interventions
        }
    
    async def record_intervention(
        self,
        intervention_type: str,
        accepted: bool,
        outcome: Optional[str]
    ):
        """Record an intervention and its outcome"""
        
        # Store in wellbeing checks
        check = WellbeingCheck(
            entity_id=self.entity_id,
            check_type="intervention",
            overall_score=0.5,  # Neutral
            cognitive_load=0,
            stress_level=0,
            energy_level=0,
            factors={
                "intervention_type": intervention_type,
                "accepted": accepted,
                "outcome": outcome
            },
            recommendations=[]
        )
        self.db.add(check)
        self.db.commit()


# ============================================================================
# WELLBEING ASSESSOR
# ============================================================================

class WellbeingAssessor:
    """Main wellbeing assessment coordinator"""
    
    def __init__(self, db: Session, entity_id: UUID):
        self.db = db
        self.entity_id = entity_id
        
    async def assess(self, include_recommendations: bool) -> Dict[str, Any]:
        """Perform comprehensive wellbeing assessment"""
        
        # Get cognitive load
        load_monitor = CognitiveLoadMonitor(self.db, self.entity_id)
        load_result = await load_monitor.assess(None, None)
        
        # Get stress level
        stress_detector = StressDetector(self.db, self.entity_id)
        stress_result = await stress_detector.detect()
        
        # Get energy level from health data
        readiness = self.db.query(DailyReadiness).filter(
            DailyReadiness.entity_id == self.entity_id
        ).order_by(DailyReadiness.date.desc()).first()
        
        energy_level = readiness.readiness_score if readiness else 0.5
        
        # Calculate overall score
        overall_score = (
            (1 - load_result["cognitive_load"]) * 0.3 +
            (1 - stress_result["stress_level"]) * 0.3 +
            energy_level * 0.4
        )
        
        # Determine status
        if overall_score >= 0.7:
            status = "healthy"
        elif overall_score >= 0.5:
            status = "concerning"
        else:
            status = "critical"
        
        # Collect alerts
        alerts = stress_result.get("alerts", [])
        if load_result["status"] in ["high", "critical"]:
            alerts.append(f"Cognitive load is {load_result['status']}")
        
        # Generate recommendations
        recommendations = []
        if include_recommendations:
            recommendations = load_result.get("recommendations", [])
            
            if stress_result["stress_level"] >= 0.5:
                recommendations.append("Consider stress-reduction activities")
            
            if energy_level < 0.5:
                recommendations.append("Energy is low - prioritize rest")
        
        # Check for interventions
        intervention_mgr = InterventionManager(self.db, self.entity_id)
        intervention_result = await intervention_mgr.check_intervention_needed(
            load_result["cognitive_load"],
            stress_result["stress_level"]
        )
        
        # Record the check
        check = WellbeingCheck(
            entity_id=self.entity_id,
            check_type="comprehensive",
            overall_score=overall_score,
            cognitive_load=load_result["cognitive_load"],
            stress_level=stress_result["stress_level"],
            energy_level=energy_level,
            factors={
                "load_factors": load_result.get("factors", {}),
                "stress_indicators": stress_result.get("indicators", {})
            },
            recommendations=recommendations
        )
        self.db.add(check)
        self.db.commit()
        
        return {
            "overall_score": overall_score,
            "cognitive_load": load_result["cognitive_load"],
            "stress_level": stress_result["stress_level"],
            "energy_level": energy_level,
            "status": status,
            "alerts": alerts,
            "recommendations": recommendations,
            "interventions": intervention_result.get("interventions", [])
        }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/check", response_model=WellbeingStatus)
async def check_wellbeing(
    request: WellbeingCheckRequest,
    db: Session = Depends(get_db)
):
    """Perform comprehensive wellbeing check"""
    try:
        eid = UUID(request.entity_id)
        
        assessor = WellbeingAssessor(db, eid)
        result = await assessor.assess(request.include_recommendations)
        
        return WellbeingStatus(
            entity_id=request.entity_id,
            overall_score=result["overall_score"],
            cognitive_load=result["cognitive_load"],
            stress_level=result["stress_level"],
            energy_level=result["energy_level"],
            status=result["status"],
            alerts=result["alerts"],
            recommendations=result["recommendations"]
        )
        
    except Exception as e:
        logger.error(f"Error checking wellbeing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cognitive-load")
async def assess_cognitive_load(
    request: CognitiveLoadRequest,
    db: Session = Depends(get_db)
):
    """Assess current cognitive load"""
    try:
        eid = UUID(request.entity_id)
        
        monitor = CognitiveLoadMonitor(db, eid)
        result = await monitor.assess(request.current_tasks, request.context)
        
        return {
            "entity_id": request.entity_id,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error assessing cognitive load: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/check-intervention")
async def check_intervention(
    request: InterventionRequest,
    db: Session = Depends(get_db)
):
    """Check if intervention is needed"""
    try:
        eid = UUID(request.entity_id)
        
        # Get current levels
        load_monitor = CognitiveLoadMonitor(db, eid)
        load_result = await load_monitor.assess(None, None)
        
        stress_detector = StressDetector(db, eid)
        stress_result = await stress_detector.detect()
        
        # Check for intervention
        intervention_mgr = InterventionManager(db, eid)
        result = await intervention_mgr.check_intervention_needed(
            load_result["cognitive_load"],
            stress_result["stress_level"]
        )
        
        return {
            "entity_id": request.entity_id,
            "trigger_type": request.trigger_type,
            **result
        }
        
    except Exception as e:
        logger.error(f"Error checking intervention: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{entity_id}")
async def get_wellbeing_history(
    entity_id: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get wellbeing check history"""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        checks = db.query(WellbeingCheck).filter(
            and_(
                WellbeingCheck.entity_id == UUID(entity_id),
                WellbeingCheck.created_at >= cutoff
            )
        ).order_by(WellbeingCheck.created_at.desc()).all()
        
        return {
            "entity_id": entity_id,
            "period_days": days,
            "checks_count": len(checks),
            "history": [
                {
                    "date": c.created_at.isoformat() if c.created_at else None,
                    "type": c.check_type,
                    "overall_score": c.overall_score,
                    "cognitive_load": c.cognitive_load,
                    "stress_level": c.stress_level,
                    "energy_level": c.energy_level
                }
                for c in checks
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "wellbeing-guardian", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
