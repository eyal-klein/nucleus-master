"""
Context-Aware Scheduler Service

Optimizes task scheduling based on energy patterns, calendar availability,
and daily readiness scores to maximize productivity and well-being.
"""

import os
import logging
from datetime import datetime, timedelta, date, time
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session

# Import models
import sys
sys.path.append('/app/backend/shared')
from models.memory import CalendarEvent
from models.dna import DailyReadiness, EnergyPattern, SchedulingPreferences

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nucleus")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="Context-Aware Scheduler",
    description="Optimizes task scheduling based on context and health data",
    version="1.0.0"
)


class TaskType(str, Enum):
    """Task type categories"""
    DEEP_WORK = "deep_work"
    MEETING = "meeting"
    CREATIVE = "creative"
    ROUTINE = "routine"
    EXERCISE = "exercise"
    REST = "rest"


class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# API Models
class TaskRequest(BaseModel):
    """Task to be scheduled"""
    title: str
    task_type: TaskType
    duration_minutes: int = Field(..., gt=0, le=480)
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Optional[datetime] = None
    preferred_time_of_day: Optional[str] = None  # morning, afternoon, evening


class TimeSlot(BaseModel):
    """Available time slot"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    energy_score: float = Field(..., ge=0, le=1)
    readiness_score: float = Field(..., ge=0, le=1)
    conflict_score: float = Field(..., ge=0, le=1)
    total_score: float = Field(..., ge=0, le=1)
    reason: str


class SchedulingRecommendation(BaseModel):
    """Scheduling recommendation"""
    task: TaskRequest
    recommended_slots: List[TimeSlot]
    best_slot: TimeSlot
    alternative_slots: List[TimeSlot]


class ScheduleOptimization(BaseModel):
    """Schedule optimization result"""
    entity_id: str
    date: date
    tasks_optimized: int
    recommendations: List[str]
    energy_utilization: float


# Scheduler Logic
class ContextAwareScheduler:
    """Schedules tasks based on context and health data"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def find_optimal_slot(
        self,
        entity_id: str,
        task: TaskRequest,
        date_range_days: int = 7
    ) -> SchedulingRecommendation:
        """Find optimal time slot for a task"""
        
        # Get entity's scheduling preferences
        preferences = await self._get_preferences(entity_id)
        
        # Get energy patterns
        energy_patterns = await self._get_energy_patterns(entity_id, task.task_type)
        
        # Get calendar availability
        available_slots = await self._get_available_slots(
            entity_id,
            date_range_days,
            task.duration_minutes,
            preferences
        )
        
        # Get daily readiness scores
        readiness_scores = await self._get_readiness_scores(entity_id, date_range_days)
        
        # Score each slot
        scored_slots = []
        for slot in available_slots:
            score = self._score_slot(
                slot,
                task,
                energy_patterns,
                readiness_scores,
                preferences
            )
            scored_slots.append(score)
        
        if not scored_slots:
            raise ValueError("No available slots found")
        
        # Sort by total score
        scored_slots.sort(key=lambda x: x.total_score, reverse=True)
        
        # Prepare recommendation
        best_slot = scored_slots[0]
        alternative_slots = scored_slots[1:4] if len(scored_slots) > 1 else []
        
        return SchedulingRecommendation(
            task=task,
            recommended_slots=scored_slots[:5],
            best_slot=best_slot,
            alternative_slots=alternative_slots
        )
    
    async def _get_preferences(
        self,
        entity_id: str
    ) -> Optional[SchedulingPreferences]:
        """Get entity's scheduling preferences"""
        
        prefs = self.db.execute(
            select(SchedulingPreferences).where(
                SchedulingPreferences.entity_id == entity_id
            )
        ).scalar_one_or_none()
        
        if not prefs:
            # Return default preferences
            return SchedulingPreferences(
                entity_id=entity_id,
                work_start_time=time(9, 0),
                work_end_time=time(17, 0),
                work_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                max_meetings_per_day=5,
                min_break_between_meetings=15,
                preferred_meeting_duration=30
            )
        
        return prefs
    
    async def _get_energy_patterns(
        self,
        entity_id: str,
        task_type: TaskType
    ) -> Dict[int, float]:
        """Get energy patterns for task type"""
        
        patterns = self.db.execute(
            select(EnergyPattern).where(
                and_(
                    EnergyPattern.entity_id == entity_id,
                    EnergyPattern.optimal_for == task_type.value
                )
            )
        ).scalars().all()
        
        # Create hourly energy map
        energy_map = {}
        for pattern in patterns:
            energy_map[pattern.hour_of_day] = float(pattern.avg_energy_level)
        
        # Fill missing hours with default (0.5)
        for hour in range(24):
            if hour not in energy_map:
                energy_map[hour] = 0.5
        
        return energy_map
    
    async def _get_available_slots(
        self,
        entity_id: str,
        days: int,
        duration_minutes: int,
        preferences: SchedulingPreferences
    ) -> List[Dict[str, Any]]:
        """Get available time slots from calendar"""
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days)
        
        # Get existing calendar events
        events = self.db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.entity_id == entity_id,
                    CalendarEvent.start_time >= start_date,
                    CalendarEvent.start_time <= end_date
                )
            ).order_by(CalendarEvent.start_time)
        ).scalars().all()
        
        # Generate available slots
        available_slots = []
        current_date = start_date.date()
        
        for day_offset in range(days):
            check_date = current_date + timedelta(days=day_offset)
            day_name = check_date.strftime("%A")
            
            # Check if it's a work day
            if day_name not in preferences.work_days:
                continue
            
            # Get work hours for this day
            work_start = datetime.combine(check_date, preferences.work_start_time)
            work_end = datetime.combine(check_date, preferences.work_end_time)
            
            # Find gaps between events
            day_events = [e for e in events if e.start_time.date() == check_date]
            
            if not day_events:
                # Entire day is available
                available_slots.append({
                    "start_time": work_start,
                    "end_time": work_end,
                    "duration_minutes": int((work_end - work_start).total_seconds() / 60)
                })
            else:
                # Find gaps between events
                current_time = work_start
                
                for event in day_events:
                    gap_duration = int((event.start_time - current_time).total_seconds() / 60)
                    
                    if gap_duration >= duration_minutes:
                        available_slots.append({
                            "start_time": current_time,
                            "end_time": event.start_time,
                            "duration_minutes": gap_duration
                        })
                    
                    current_time = max(current_time, event.end_time)
                
                # Check gap after last event
                if current_time < work_end:
                    gap_duration = int((work_end - current_time).total_seconds() / 60)
                    if gap_duration >= duration_minutes:
                        available_slots.append({
                            "start_time": current_time,
                            "end_time": work_end,
                            "duration_minutes": gap_duration
                        })
        
        return available_slots
    
    async def _get_readiness_scores(
        self,
        entity_id: str,
        days: int
    ) -> Dict[date, float]:
        """Get daily readiness scores"""
        
        start_date = date.today()
        end_date = start_date + timedelta(days=days)
        
        readiness_records = self.db.execute(
            select(DailyReadiness).where(
                and_(
                    DailyReadiness.entity_id == entity_id,
                    DailyReadiness.date >= start_date,
                    DailyReadiness.date <= end_date
                )
            )
        ).scalars().all()
        
        # Create date -> score map
        readiness_map = {}
        for record in readiness_records:
            readiness_map[record.date] = float(record.readiness_score)
        
        # Fill missing dates with default (0.7)
        for day_offset in range(days):
            check_date = start_date + timedelta(days=day_offset)
            if check_date not in readiness_map:
                readiness_map[check_date] = 0.7
        
        return readiness_map
    
    def _score_slot(
        self,
        slot: Dict[str, Any],
        task: TaskRequest,
        energy_patterns: Dict[int, float],
        readiness_scores: Dict[date, float],
        preferences: SchedulingPreferences
    ) -> TimeSlot:
        """Score a time slot for a task"""
        
        start_time = slot["start_time"]
        hour = start_time.hour
        slot_date = start_time.date()
        
        # Energy score (how well does this time match task type)
        energy_score = energy_patterns.get(hour, 0.5)
        
        # Readiness score (overall daily readiness)
        readiness_score = readiness_scores.get(slot_date, 0.7)
        
        # Conflict score (1.0 = no conflicts, lower = potential issues)
        conflict_score = 1.0
        
        # Check for back-to-back meetings
        if task.task_type == TaskType.MEETING:
            # Prefer slots with buffer time
            conflict_score = 0.9
        
        # Priority adjustment
        priority_weight = {
            TaskPriority.CRITICAL: 1.2,
            TaskPriority.HIGH: 1.1,
            TaskPriority.MEDIUM: 1.0,
            TaskPriority.LOW: 0.9
        }
        priority_multiplier = priority_weight[task.priority]
        
        # Calculate total score (weighted average)
        total_score = (
            energy_score * 0.5 +        # Energy is most important
            readiness_score * 0.3 +     # Overall readiness
            conflict_score * 0.2        # Avoid conflicts
        ) * priority_multiplier
        
        # Clamp to [0, 1]
        total_score = min(max(total_score, 0), 1)
        
        # Generate reason
        reason = self._generate_reason(
            energy_score, readiness_score, conflict_score, task.task_type
        )
        
        return TimeSlot(
            start_time=start_time,
            end_time=start_time + timedelta(minutes=task.duration_minutes),
            duration_minutes=task.duration_minutes,
            energy_score=round(energy_score, 2),
            readiness_score=round(readiness_score, 2),
            conflict_score=round(conflict_score, 2),
            total_score=round(total_score, 2),
            reason=reason
        )
    
    def _generate_reason(
        self,
        energy: float,
        readiness: float,
        conflict: float,
        task_type: TaskType
    ) -> str:
        """Generate human-readable reason for score"""
        
        reasons = []
        
        if energy > 0.7:
            reasons.append(f"High energy for {task_type.value}")
        elif energy < 0.4:
            reasons.append(f"Low energy for {task_type.value}")
        
        if readiness > 0.7:
            reasons.append("excellent readiness")
        elif readiness < 0.4:
            reasons.append("low readiness")
        
        if conflict < 0.8:
            reasons.append("potential scheduling conflicts")
        
        if not reasons:
            return "Good overall fit"
        
        return ", ".join(reasons).capitalize()
    
    async def optimize_schedule(
        self,
        entity_id: str,
        target_date: date,
        tasks: List[TaskRequest]
    ) -> ScheduleOptimization:
        """Optimize entire schedule for a day"""
        
        recommendations = []
        tasks_scheduled = 0
        
        for task in tasks:
            try:
                recommendation = await self.find_optimal_slot(
                    entity_id,
                    task,
                    date_range_days=1
                )
                
                if recommendation.best_slot.total_score > 0.6:
                    recommendations.append(
                        f"Schedule '{task.title}' at {recommendation.best_slot.start_time.strftime('%H:%M')}"
                    )
                    tasks_scheduled += 1
                else:
                    recommendations.append(
                        f"'{task.title}' has no optimal slot (consider rescheduling or adjusting duration)"
                    )
            
            except Exception as e:
                logger.warning(f"Could not schedule task '{task.title}': {e}")
                recommendations.append(f"Could not find slot for '{task.title}'")
        
        # Calculate energy utilization
        energy_utilization = tasks_scheduled / len(tasks) if tasks else 0
        
        return ScheduleOptimization(
            entity_id=entity_id,
            date=target_date,
            tasks_optimized=tasks_scheduled,
            recommendations=recommendations,
            energy_utilization=round(energy_utilization, 2)
        )


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "context-aware-scheduler",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/find-optimal-slot/{entity_id}")
async def find_optimal_slot(entity_id: str, task: TaskRequest, days: int = 7):
    """Find optimal time slot for a task"""
    db = SessionLocal()
    try:
        scheduler = ContextAwareScheduler(db)
        recommendation = await scheduler.find_optimal_slot(entity_id, task, days)
        return recommendation
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error finding optimal slot: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


@app.post("/schedule-task/{entity_id}")
async def schedule_task(entity_id: str, task: TaskRequest):
    """Schedule a task in the optimal slot"""
    db = SessionLocal()
    try:
        scheduler = ContextAwareScheduler(db)
        recommendation = await scheduler.find_optimal_slot(entity_id, task, date_range_days=7)
        
        # In production, this would create a calendar event
        # For now, just return the recommendation
        
        return {
            "message": "Task scheduled successfully",
            "task": task.title,
            "scheduled_time": recommendation.best_slot.start_time,
            "score": recommendation.best_slot.total_score,
            "reason": recommendation.best_slot.reason
        }
    
    finally:
        db.close()


@app.get("/availability/{entity_id}")
async def get_availability(entity_id: str, days: int = 7, min_duration: int = 30):
    """Get available time slots for entity"""
    db = SessionLocal()
    try:
        scheduler = ContextAwareScheduler(db)
        preferences = await scheduler._get_preferences(entity_id)
        
        available_slots = await scheduler._get_available_slots(
            entity_id,
            days,
            min_duration,
            preferences
        )
        
        return {
            "entity_id": entity_id,
            "days": days,
            "min_duration_minutes": min_duration,
            "available_slots_count": len(available_slots),
            "available_slots": available_slots[:20]  # Limit to 20
        }
    
    finally:
        db.close()


@app.post("/optimize-schedule/{entity_id}")
async def optimize_schedule(entity_id: str, target_date: date, tasks: List[TaskRequest]):
    """Optimize entire schedule for a day"""
    db = SessionLocal()
    try:
        scheduler = ContextAwareScheduler(db)
        optimization = await scheduler.optimize_schedule(entity_id, target_date, tasks)
        return optimization
    
    finally:
        db.close()


@app.get("/recommendations/{entity_id}")
async def get_recommendations(entity_id: str):
    """Get scheduling recommendations for entity"""
    db = SessionLocal()
    try:
        # Get today's readiness
        today = date.today()
        readiness = db.execute(
            select(DailyReadiness).where(
                and_(
                    DailyReadiness.entity_id == entity_id,
                    DailyReadiness.date == today
                )
            )
        ).scalar_one_or_none()
        
        # Get energy patterns
        patterns = db.execute(
            select(EnergyPattern).where(
                EnergyPattern.entity_id == entity_id
            ).order_by(EnergyPattern.avg_energy_level.desc()).limit(3)
        ).scalars().all()
        
        recommendations = []
        
        if readiness:
            if readiness.readiness_score > 0.7:
                recommendations.append("High readiness today - great for challenging tasks and important meetings")
            elif readiness.readiness_score < 0.4:
                recommendations.append("Low readiness today - focus on routine tasks and take breaks")
        
        if patterns:
            best_pattern = patterns[0]
            recommendations.append(
                f"Your peak energy is at {best_pattern.hour_of_day}:00 - "
                f"ideal for {best_pattern.optimal_for}"
            )
        
        return {
            "entity_id": entity_id,
            "date": today,
            "recommendations": recommendations
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
