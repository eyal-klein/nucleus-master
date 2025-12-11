"""
Health & Wellness Engine Service

Analyzes health metrics, calculates daily readiness scores, identifies trends,
and generates personalized recommendations based on IOT health data.
"""

import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np
from sqlalchemy import create_engine, select, and_, func, desc
from sqlalchemy.orm import sessionmaker, Session

# Import models
import sys
sys.path.append('/app/backend/shared')
from models.memory import HealthMetric
from models.dna import DailyReadiness, EnergyPattern

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nucleus")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="Health & Wellness Engine",
    description="Analyzes health data and provides personalized recommendations",
    version="1.0.0"
)


class ReadinessLevel(str, Enum):
    """Readiness level categories"""
    EXCELLENT = "excellent"  # 0.8-1.0
    GOOD = "good"            # 0.6-0.8
    MODERATE = "moderate"    # 0.4-0.6
    LOW = "low"              # 0.2-0.4
    POOR = "poor"            # 0.0-0.2


class TrendDirection(str, Enum):
    """Trend direction"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class ActivityType(str, Enum):
    """Optimal activity types"""
    DEEP_WORK = "deep_work"
    MEETINGS = "meetings"
    CREATIVE = "creative"
    EXERCISE = "exercise"
    REST = "rest"
    ROUTINE = "routine"


# API Models
class ReadinessScore(BaseModel):
    """Daily readiness score"""
    entity_id: str
    date: date
    readiness_score: float = Field(..., ge=0, le=1)
    sleep_score: float = Field(..., ge=0, le=1)
    hrv_score: float = Field(..., ge=0, le=1)
    activity_score: float = Field(..., ge=0, le=1)
    recovery_score: float = Field(..., ge=0, le=1)
    level: ReadinessLevel
    recommendations: List[str]
    raw_metrics: Dict[str, Any]


class HealthTrend(BaseModel):
    """Health trend analysis"""
    metric_type: str
    direction: TrendDirection
    change_percent: float
    current_avg: float
    previous_avg: float
    period_days: int


class EnergyPatternData(BaseModel):
    """Energy pattern for a time slot"""
    hour_of_day: int
    day_of_week: Optional[int]
    avg_energy_level: float
    optimal_for: ActivityType
    sample_count: int


# Health Analysis Functions
class HealthAnalyzer:
    """Analyzes health metrics and generates insights"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_readiness(
        self,
        entity_id: str,
        target_date: date
    ) -> Optional[ReadinessScore]:
        """Calculate daily readiness score from health metrics"""
        
        # Get health metrics for the day
        start_time = datetime.combine(target_date, datetime.min.time())
        end_time = datetime.combine(target_date, datetime.max.time())
        
        metrics = self.db.execute(
            select(HealthMetric).where(
                and_(
                    HealthMetric.entity_id == entity_id,
                    HealthMetric.recorded_at >= start_time,
                    HealthMetric.recorded_at <= end_time
                )
            )
        ).scalars().all()
        
        if not metrics:
            logger.warning(f"No health metrics found for {entity_id} on {target_date}")
            return None
        
        # Extract metric values
        metric_values = {}
        for metric in metrics:
            if metric.metric_type not in metric_values:
                metric_values[metric.metric_type] = []
            metric_values[metric.metric_type].append(float(metric.value))
        
        # Calculate component scores
        sleep_score = self._calculate_sleep_score(metric_values)
        hrv_score = self._calculate_hrv_score(metric_values)
        activity_score = self._calculate_activity_score(metric_values)
        recovery_score = self._calculate_recovery_score(metric_values)
        
        # Calculate overall readiness (weighted average)
        readiness = (
            sleep_score * 0.4 +      # Sleep is most important
            hrv_score * 0.3 +        # HRV indicates stress/recovery
            recovery_score * 0.2 +   # Recovery state
            activity_score * 0.1     # Activity balance
        )
        
        # Determine readiness level
        level = self._get_readiness_level(readiness)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            readiness, sleep_score, hrv_score, recovery_score
        )
        
        # Prepare raw metrics
        raw_metrics = {
            "sleep_hours": np.mean(metric_values.get("sleep_duration", [0])),
            "hrv_avg": int(np.mean(metric_values.get("hrv", [0]))),
            "resting_heart_rate": int(np.mean(metric_values.get("resting_heart_rate", [0]))),
            "steps": int(np.sum(metric_values.get("steps", [0]))),
            "calories_burned": int(np.sum(metric_values.get("calories", [0])))
        }
        
        return ReadinessScore(
            entity_id=entity_id,
            date=target_date,
            readiness_score=round(readiness, 2),
            sleep_score=round(sleep_score, 2),
            hrv_score=round(hrv_score, 2),
            activity_score=round(activity_score, 2),
            recovery_score=round(recovery_score, 2),
            level=level,
            recommendations=recommendations,
            raw_metrics=raw_metrics
        )
    
    def _calculate_sleep_score(self, metrics: Dict[str, List[float]]) -> float:
        """Calculate sleep quality score (0-1)"""
        sleep_duration = metrics.get("sleep_duration", [0])
        sleep_quality = metrics.get("sleep_score", [0])
        
        if not sleep_duration:
            return 0.5  # Default neutral score
        
        avg_duration = np.mean(sleep_duration)
        avg_quality = np.mean(sleep_quality) if sleep_quality else 0.7
        
        # Optimal sleep is 7-9 hours
        duration_score = 1.0
        if avg_duration < 6:
            duration_score = avg_duration / 6
        elif avg_duration > 9:
            duration_score = max(0.7, 1.0 - (avg_duration - 9) * 0.1)
        
        # Combine duration and quality
        return (duration_score * 0.5 + avg_quality * 0.5)
    
    def _calculate_hrv_score(self, metrics: Dict[str, List[float]]) -> float:
        """Calculate HRV balance score (0-1)"""
        hrv_values = metrics.get("hrv", [])
        
        if not hrv_values:
            return 0.5  # Default neutral score
        
        avg_hrv = np.mean(hrv_values)
        
        # HRV scoring (higher is generally better, but very individual)
        # Using general guidelines: 20-100ms range
        if avg_hrv < 20:
            return 0.3  # Low HRV indicates stress
        elif avg_hrv < 40:
            return 0.6
        elif avg_hrv < 60:
            return 0.8
        else:
            return 0.95  # Excellent HRV
    
    def _calculate_activity_score(self, metrics: Dict[str, List[float]]) -> float:
        """Calculate activity balance score (0-1)"""
        steps = metrics.get("steps", [0])
        calories = metrics.get("calories", [0])
        
        total_steps = np.sum(steps)
        
        # Optimal steps: 8000-12000 per day
        if total_steps < 5000:
            return 0.4  # Too sedentary
        elif total_steps < 8000:
            return 0.7
        elif total_steps <= 12000:
            return 1.0  # Optimal
        elif total_steps <= 15000:
            return 0.9  # Good but high
        else:
            return 0.7  # Possibly overtraining
    
    def _calculate_recovery_score(self, metrics: Dict[str, List[float]]) -> float:
        """Calculate recovery state score (0-1)"""
        resting_hr = metrics.get("resting_heart_rate", [])
        hrv = metrics.get("hrv", [])
        
        if not resting_hr:
            return 0.5
        
        avg_rhr = np.mean(resting_hr)
        
        # Lower resting HR generally indicates better recovery
        # Typical range: 50-80 bpm
        if avg_rhr < 55:
            rhr_score = 1.0  # Excellent
        elif avg_rhr < 65:
            rhr_score = 0.9
        elif avg_rhr < 75:
            rhr_score = 0.7
        else:
            rhr_score = 0.5  # Elevated
        
        # Combine with HRV if available
        if hrv:
            hrv_score = self._calculate_hrv_score(metrics)
            return (rhr_score * 0.6 + hrv_score * 0.4)
        
        return rhr_score
    
    def _get_readiness_level(self, score: float) -> ReadinessLevel:
        """Determine readiness level from score"""
        if score >= 0.8:
            return ReadinessLevel.EXCELLENT
        elif score >= 0.6:
            return ReadinessLevel.GOOD
        elif score >= 0.4:
            return ReadinessLevel.MODERATE
        elif score >= 0.2:
            return ReadinessLevel.LOW
        else:
            return ReadinessLevel.POOR
    
    def _generate_recommendations(
        self,
        readiness: float,
        sleep: float,
        hrv: float,
        recovery: float
    ) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Overall readiness recommendations
        if readiness >= 0.8:
            recommendations.append("Excellent readiness! Great day for challenging tasks and important meetings.")
        elif readiness >= 0.6:
            recommendations.append("Good readiness. Focus on productive work and maintain your routine.")
        elif readiness >= 0.4:
            recommendations.append("Moderate readiness. Pace yourself and take regular breaks.")
        else:
            recommendations.append("Low readiness. Prioritize rest and recovery today.")
        
        # Sleep-specific recommendations
        if sleep < 0.5:
            recommendations.append("Sleep quality needs improvement. Aim for 7-9 hours tonight.")
        
        # HRV-specific recommendations
        if hrv < 0.5:
            recommendations.append("HRV is low, indicating stress. Consider meditation or light activity.")
        
        # Recovery-specific recommendations
        if recovery < 0.5:
            recommendations.append("Recovery is suboptimal. Avoid intense exercise today.")
        
        return recommendations
    
    def analyze_trends(
        self,
        entity_id: str,
        metric_type: str,
        days: int = 14
    ) -> Optional[HealthTrend]:
        """Analyze trend for a specific health metric"""
        
        # Get metrics for the period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        mid_date = start_date + timedelta(days=days // 2)
        
        # First half metrics
        first_half = self.db.execute(
            select(HealthMetric).where(
                and_(
                    HealthMetric.entity_id == entity_id,
                    HealthMetric.metric_type == metric_type,
                    HealthMetric.recorded_at >= start_date,
                    HealthMetric.recorded_at < mid_date
                )
            )
        ).scalars().all()
        
        # Second half metrics
        second_half = self.db.execute(
            select(HealthMetric).where(
                and_(
                    HealthMetric.entity_id == entity_id,
                    HealthMetric.metric_type == metric_type,
                    HealthMetric.recorded_at >= mid_date,
                    HealthMetric.recorded_at <= end_date
                )
            )
        ).scalars().all()
        
        if not first_half or not second_half:
            return None
        
        # Calculate averages
        first_avg = np.mean([float(m.value) for m in first_half])
        second_avg = np.mean([float(m.value) for m in second_half])
        
        # Calculate change
        change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
        
        # Determine direction
        if abs(change_percent) < 5:
            direction = TrendDirection.STABLE
        elif change_percent > 0:
            direction = TrendDirection.IMPROVING if metric_type in ["hrv", "sleep_score"] else TrendDirection.DECLINING
        else:
            direction = TrendDirection.DECLINING if metric_type in ["hrv", "sleep_score"] else TrendDirection.IMPROVING
        
        return HealthTrend(
            metric_type=metric_type,
            direction=direction,
            change_percent=round(change_percent, 2),
            current_avg=round(second_avg, 2),
            previous_avg=round(first_avg, 2),
            period_days=days
        )
    
    def analyze_energy_patterns(
        self,
        entity_id: str,
        days: int = 30
    ) -> List[EnergyPatternData]:
        """Analyze energy patterns by hour of day"""
        
        # Get health metrics for the period
        start_date = datetime.utcnow() - timedelta(days=days)
        
        metrics = self.db.execute(
            select(HealthMetric).where(
                and_(
                    HealthMetric.entity_id == entity_id,
                    HealthMetric.recorded_at >= start_date
                )
            )
        ).scalars().all()
        
        if not metrics:
            return []
        
        # Group by hour of day
        hourly_data = {}
        for metric in metrics:
            hour = metric.recorded_at.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            
            # Estimate energy level from metrics
            energy = self._estimate_energy_from_metric(metric)
            if energy is not None:
                hourly_data[hour].append(energy)
        
        # Calculate patterns
        patterns = []
        for hour in range(24):
            if hour in hourly_data and hourly_data[hour]:
                avg_energy = np.mean(hourly_data[hour])
                optimal_activity = self._determine_optimal_activity(hour, avg_energy)
                
                patterns.append(EnergyPatternData(
                    hour_of_day=hour,
                    day_of_week=None,  # All days combined
                    avg_energy_level=round(avg_energy, 2),
                    optimal_for=optimal_activity,
                    sample_count=len(hourly_data[hour])
                ))
        
        return patterns
    
    def _estimate_energy_from_metric(self, metric: HealthMetric) -> Optional[float]:
        """Estimate energy level from a health metric"""
        # This is a simplified estimation
        # In production, use more sophisticated models
        
        if metric.metric_type == "heart_rate":
            # Lower resting HR = higher energy potential
            hr = float(metric.value)
            if hr < 60:
                return 0.9
            elif hr < 70:
                return 0.7
            else:
                return 0.5
        
        elif metric.metric_type == "hrv":
            # Higher HRV = better energy
            hrv = float(metric.value)
            if hrv > 60:
                return 0.9
            elif hrv > 40:
                return 0.7
            else:
                return 0.5
        
        return None
    
    def _determine_optimal_activity(self, hour: int, energy: float) -> ActivityType:
        """Determine optimal activity type for time slot"""
        
        # Morning (6-12): Best for deep work if energy is high
        if 6 <= hour < 12:
            if energy > 0.7:
                return ActivityType.DEEP_WORK
            else:
                return ActivityType.ROUTINE
        
        # Afternoon (12-17): Meetings and collaboration
        elif 12 <= hour < 17:
            if energy > 0.6:
                return ActivityType.MEETINGS
            else:
                return ActivityType.ROUTINE
        
        # Evening (17-21): Creative or exercise
        elif 17 <= hour < 21:
            if energy > 0.6:
                return ActivityType.CREATIVE
            else:
                return ActivityType.REST
        
        # Night (21-6): Rest
        else:
            return ActivityType.REST


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "health-wellness-engine",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/calculate-readiness/{entity_id}")
async def calculate_readiness(entity_id: str, target_date: Optional[date] = None):
    """Calculate daily readiness score for entity"""
    db = SessionLocal()
    try:
        analyzer = HealthAnalyzer(db)
        
        if target_date is None:
            target_date = date.today()
        
        readiness = analyzer.calculate_readiness(entity_id, target_date)
        
        if not readiness:
            raise HTTPException(
                status_code=404,
                detail=f"No health metrics found for {entity_id} on {target_date}"
            )
        
        # Store in database
        db_readiness = DailyReadiness(
            entity_id=entity_id,
            date=target_date,
            readiness_score=readiness.readiness_score,
            sleep_score=readiness.sleep_score,
            hrv_score=readiness.hrv_score,
            activity_score=readiness.activity_score,
            recovery_score=readiness.recovery_score,
            sleep_hours=readiness.raw_metrics.get("sleep_hours"),
            hrv_avg=readiness.raw_metrics.get("hrv_avg"),
            resting_heart_rate=readiness.raw_metrics.get("resting_heart_rate"),
            steps=readiness.raw_metrics.get("steps"),
            calories_burned=readiness.raw_metrics.get("calories_burned"),
            recommendations=readiness.recommendations
        )
        
        db.merge(db_readiness)
        db.commit()
        
        return readiness
    
    finally:
        db.close()


@app.get("/readiness/{entity_id}")
async def get_readiness(entity_id: str, target_date: Optional[date] = None):
    """Get daily readiness score for entity"""
    db = SessionLocal()
    try:
        if target_date is None:
            target_date = date.today()
        
        readiness = db.execute(
            select(DailyReadiness).where(
                and_(
                    DailyReadiness.entity_id == entity_id,
                    DailyReadiness.date == target_date
                )
            )
        ).scalar_one_or_none()
        
        if not readiness:
            raise HTTPException(
                status_code=404,
                detail=f"No readiness data found for {entity_id} on {target_date}"
            )
        
        return readiness
    
    finally:
        db.close()


@app.get("/trends/{entity_id}")
async def get_trends(entity_id: str, days: int = 14):
    """Get health trends for entity"""
    db = SessionLocal()
    try:
        analyzer = HealthAnalyzer(db)
        
        # Analyze trends for key metrics
        metric_types = ["sleep_score", "hrv", "resting_heart_rate", "steps"]
        trends = []
        
        for metric_type in metric_types:
            trend = analyzer.analyze_trends(entity_id, metric_type, days)
            if trend:
                trends.append(trend)
        
        return {
            "entity_id": entity_id,
            "period_days": days,
            "trends": trends
        }
    
    finally:
        db.close()


@app.get("/recommendations/{entity_id}")
async def get_recommendations(entity_id: str):
    """Get personalized recommendations for entity"""
    db = SessionLocal()
    try:
        # Get latest readiness
        readiness = db.execute(
            select(DailyReadiness).where(
                DailyReadiness.entity_id == entity_id
            ).order_by(desc(DailyReadiness.date)).limit(1)
        ).scalar_one_or_none()
        
        if not readiness:
            raise HTTPException(
                status_code=404,
                detail=f"No readiness data found for {entity_id}"
            )
        
        return {
            "entity_id": entity_id,
            "date": readiness.date,
            "readiness_score": readiness.readiness_score,
            "recommendations": readiness.recommendations
        }
    
    finally:
        db.close()


@app.post("/analyze-energy/{entity_id}")
async def analyze_energy(entity_id: str, days: int = 30):
    """Analyze and store energy patterns for entity"""
    db = SessionLocal()
    try:
        analyzer = HealthAnalyzer(db)
        
        patterns = analyzer.analyze_energy_patterns(entity_id, days)
        
        if not patterns:
            raise HTTPException(
                status_code=404,
                detail=f"No health metrics found for {entity_id}"
            )
        
        # Store patterns in database
        for pattern in patterns:
            db_pattern = EnergyPattern(
                entity_id=entity_id,
                hour_of_day=pattern.hour_of_day,
                day_of_week=pattern.day_of_week,
                avg_energy_level=pattern.avg_energy_level,
                sample_count=pattern.sample_count,
                optimal_for=pattern.optimal_for.value
            )
            
            db.merge(db_pattern)
        
        db.commit()
        
        return {
            "entity_id": entity_id,
            "patterns_count": len(patterns),
            "patterns": patterns
        }
    
    finally:
        db.close()


@app.get("/energy-patterns/{entity_id}")
async def get_energy_patterns(entity_id: str):
    """Get stored energy patterns for entity"""
    db = SessionLocal()
    try:
        patterns = db.execute(
            select(EnergyPattern).where(
                EnergyPattern.entity_id == entity_id
            ).order_by(EnergyPattern.hour_of_day)
        ).scalars().all()
        
        if not patterns:
            raise HTTPException(
                status_code=404,
                detail=f"No energy patterns found for {entity_id}"
            )
        
        return {
            "entity_id": entity_id,
            "patterns_count": len(patterns),
            "patterns": patterns
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
