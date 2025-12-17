"""
Social Context Engine Service

Analyzes social relationships and interactions to understand context,
calculate relationship strength, and provide networking recommendations.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, and_, func, desc
from sqlalchemy.orm import sessionmaker, Session
import numpy as np

# Import models
import sys
sys.path.append('/app/backend/shared')
from models.memory import LinkedInProfile, LinkedInConnection, LinkedInActivity
from models.dna import RelationshipScore

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
    title="Social Context Engine",
    description="Analyzes social relationships and context",
    version="1.0.0"
)


class RelationshipStrength(str, Enum):
    """Relationship strength levels"""
    STRONG = "strong"          # 0.7-1.0
    MODERATE = "moderate"      # 0.4-0.7
    WEAK = "weak"              # 0.0-0.4


# API Models
class RelationshipScoreResponse(BaseModel):
    """Relationship score response"""
    entity_id: str
    connection_id: str
    overall_score: float = Field(..., ge=0, le=1)
    interaction_score: float
    recency_score: float
    mutual_connections_score: float
    shared_experience_score: float
    sentiment_score: float
    strength: RelationshipStrength
    recommendations: List[str]


class InteractionPattern(BaseModel):
    """Interaction pattern analysis"""
    connection_id: str
    connection_name: str
    interaction_count: int
    last_interaction: Optional[datetime]
    frequency: str  # daily, weekly, monthly, rare
    quality_score: float


# Relationship Analysis
class RelationshipAnalyzer:
    """Analyzes relationships and calculates scores"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_relationship_score(
        self,
        entity_id: str,
        connection_id: str
    ) -> RelationshipScoreResponse:
        """Calculate comprehensive relationship score"""
        
        # Get connection
        connection = self.db.execute(
            select(LinkedInConnection).where(
                and_(
                    LinkedInConnection.entity_id == entity_id,
                    LinkedInConnection.id == connection_id
                )
            )
        ).scalar_one_or_none()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Calculate component scores
        interaction_score = self._calculate_interaction_score(entity_id, connection)
        recency_score = self._calculate_recency_score(entity_id, connection)
        mutual_score = self._calculate_mutual_connections_score(entity_id, connection)
        shared_score = self._calculate_shared_experience_score(entity_id, connection)
        sentiment_score = 0.7  # Placeholder for sentiment analysis
        
        # Calculate overall score (weighted average)
        overall_score = (
            interaction_score * 0.3 +
            recency_score * 0.2 +
            mutual_score * 0.2 +
            shared_score * 0.2 +
            (sentiment_score + 1) / 2 * 0.1  # Normalize sentiment to 0-1
        )
        
        # Determine strength
        if overall_score >= 0.7:
            strength = RelationshipStrength.STRONG
        elif overall_score >= 0.4:
            strength = RelationshipStrength.MODERATE
        else:
            strength = RelationshipStrength.WEAK
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_score, interaction_score, recency_score, connection
        )
        
        # Store in database
        db_score = RelationshipScore(
            entity_id=entity_id,
            connection_id=connection_id,
            overall_score=overall_score,
            interaction_score=interaction_score,
            recency_score=recency_score,
            mutual_connections_score=mutual_score,
            shared_experience_score=shared_score,
            sentiment_score=sentiment_score
        )
        
        self.db.merge(db_score)
        self.db.commit()
        
        return RelationshipScoreResponse(
            entity_id=entity_id,
            connection_id=connection_id,
            overall_score=round(overall_score, 2),
            interaction_score=round(interaction_score, 2),
            recency_score=round(recency_score, 2),
            mutual_connections_score=round(mutual_score, 2),
            shared_experience_score=round(shared_score, 2),
            sentiment_score=round(sentiment_score, 2),
            strength=strength,
            recommendations=recommendations
        )
    
    def _calculate_interaction_score(
        self,
        entity_id: str,
        connection: LinkedInConnection
    ) -> float:
        """Calculate interaction frequency score"""
        
        # Count interactions (activities involving this connection)
        interaction_count = self.db.execute(
            select(func.count(LinkedInActivity.id)).where(
                and_(
                    LinkedInActivity.entity_id == entity_id,
                    LinkedInActivity.author_linkedin_id == connection.connection_linkedin_id
                )
            )
        ).scalar()
        
        # Score based on interaction count
        if interaction_count >= 20:
            return 1.0
        elif interaction_count >= 10:
            return 0.8
        elif interaction_count >= 5:
            return 0.6
        elif interaction_count >= 2:
            return 0.4
        elif interaction_count >= 1:
            return 0.2
        else:
            return 0.1  # Connected but no interactions
    
    def _calculate_recency_score(
        self,
        entity_id: str,
        connection: LinkedInConnection
    ) -> float:
        """Calculate recency score based on last interaction"""
        
        # Get last interaction
        last_activity = self.db.execute(
            select(LinkedInActivity).where(
                and_(
                    LinkedInActivity.entity_id == entity_id,
                    LinkedInActivity.author_linkedin_id == connection.connection_linkedin_id
                )
            ).order_by(desc(LinkedInActivity.posted_at)).limit(1)
        ).scalar_one_or_none()
        
        if not last_activity:
            # No interactions, use connection date
            if connection.connected_at:
                days_since = (datetime.utcnow() - connection.connected_at).days
            else:
                return 0.3  # Default for unknown
        else:
            days_since = (datetime.utcnow() - last_activity.posted_at).days
        
        # Score based on recency
        if days_since <= 7:
            return 1.0  # Very recent
        elif days_since <= 30:
            return 0.8  # Recent
        elif days_since <= 90:
            return 0.6  # Moderate
        elif days_since <= 180:
            return 0.4  # Somewhat old
        elif days_since <= 365:
            return 0.2  # Old
        else:
            return 0.1  # Very old
    
    def _calculate_mutual_connections_score(
        self,
        entity_id: str,
        connection: LinkedInConnection
    ) -> float:
        """Calculate mutual connections score"""
        
        # This would require mutual connections data from LinkedIn
        # Placeholder implementation
        return 0.5
    
    def _calculate_shared_experience_score(
        self,
        entity_id: str,
        connection: LinkedInConnection
    ) -> float:
        """Calculate shared experience score (companies, schools)"""
        
        # Get entity profile
        entity_profile = self.db.execute(
            select(LinkedInProfile).where(
                LinkedInProfile.entity_id == entity_id
            )
        ).scalar_one_or_none()
        
        if not entity_profile:
            return 0.5
        
        score = 0.0
        
        # Check current company
        if (entity_profile.current_company and 
            connection.current_company and
            entity_profile.current_company.lower() == connection.current_company.lower()):
            score += 0.5  # Same company is strong signal
        
        # In production, check past companies and schools from experience/education JSONB
        
        return min(score, 1.0)
    
    def _generate_recommendations(
        self,
        overall_score: float,
        interaction_score: float,
        recency_score: float,
        connection: LinkedInConnection
    ) -> List[str]:
        """Generate networking recommendations"""
        
        recommendations = []
        
        if overall_score >= 0.7:
            recommendations.append(f"Strong relationship with {connection.first_name}. Consider collaboration opportunities.")
        elif overall_score >= 0.4:
            recommendations.append(f"Moderate relationship. Increase engagement with {connection.first_name}.")
        else:
            recommendations.append(f"Weak relationship. Reach out to {connection.first_name} to reconnect.")
        
        if recency_score < 0.4:
            recommendations.append(f"Haven't interacted recently. Send a message to catch up.")
        
        if interaction_score < 0.3:
            recommendations.append(f"Low interaction frequency. Engage more with their content.")
        
        return recommendations
    
    def analyze_interactions(
        self,
        entity_id: str,
        days: int = 30
    ) -> List[InteractionPattern]:
        """Analyze interaction patterns"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all connections with activities
        activities = self.db.execute(
            select(LinkedInActivity).where(
                and_(
                    LinkedInActivity.entity_id == entity_id,
                    LinkedInActivity.posted_at >= cutoff_date
                )
            ).order_by(desc(LinkedInActivity.posted_at))
        ).scalars().all()
        
        # Group by author
        interaction_map = {}
        for activity in activities:
            author_id = activity.author_linkedin_id
            if author_id not in interaction_map:
                interaction_map[author_id] = []
            interaction_map[author_id].append(activity)
        
        # Build patterns
        patterns = []
        for author_id, author_activities in interaction_map.items():
            # Get connection info
            connection = self.db.execute(
                select(LinkedInConnection).where(
                    and_(
                        LinkedInConnection.entity_id == entity_id,
                        LinkedInConnection.connection_linkedin_id == author_id
                    )
                )
            ).scalar_one_or_none()
            
            if not connection:
                continue
            
            interaction_count = len(author_activities)
            last_interaction = max(a.posted_at for a in author_activities)
            
            # Determine frequency
            if interaction_count >= days:
                frequency = "daily"
            elif interaction_count >= days / 7:
                frequency = "weekly"
            elif interaction_count >= days / 30:
                frequency = "monthly"
            else:
                frequency = "rare"
            
            # Quality score (placeholder)
            quality_score = min(interaction_count / 10, 1.0)
            
            patterns.append(InteractionPattern(
                connection_id=str(connection.id),
                connection_name=f"{connection.first_name} {connection.last_name}",
                interaction_count=interaction_count,
                last_interaction=last_interaction,
                frequency=frequency,
                quality_score=round(quality_score, 2)
            ))
        
        # Sort by interaction count
        patterns.sort(key=lambda x: x.interaction_count, reverse=True)
        
        return patterns


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "social-context-engine",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/analyze-relationship/{entity_id}")
async def analyze_relationship(entity_id: str, connection_id: str):
    """Analyze specific relationship"""
    db = SessionLocal()
    try:
        analyzer = RelationshipAnalyzer(db)
        score = analyzer.calculate_relationship_score(entity_id, connection_id)
        return score
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


@app.get("/relationship-scores/{entity_id}")
async def get_relationship_scores(entity_id: str, min_score: float = 0.0):
    """Get all relationship scores for entity"""
    db = SessionLocal()
    try:
        scores = db.execute(
            select(RelationshipScore).where(
                and_(
                    RelationshipScore.entity_id == entity_id,
                    RelationshipScore.overall_score >= min_score
                )
            ).order_by(desc(RelationshipScore.overall_score))
        ).scalars().all()
        
        return {
            "entity_id": entity_id,
            "scores_count": len(scores),
            "scores": scores
        }
    
    finally:
        db.close()


@app.post("/analyze-interactions/{entity_id}")
async def analyze_interactions(entity_id: str, days: int = 30):
    """Analyze interaction patterns"""
    db = SessionLocal()
    try:
        analyzer = RelationshipAnalyzer(db)
        patterns = analyzer.analyze_interactions(entity_id, days)
        
        return {
            "entity_id": entity_id,
            "period_days": days,
            "patterns_count": len(patterns),
            "patterns": patterns
        }
    
    finally:
        db.close()


@app.get("/recommendations/{entity_id}")
async def get_recommendations(entity_id: str):
    """Get networking recommendations"""
    db = SessionLocal()
    try:
        # Get top relationships
        top_scores = db.execute(
            select(RelationshipScore).where(
                RelationshipScore.entity_id == entity_id
            ).order_by(desc(RelationshipScore.overall_score)).limit(10)
        ).scalars().all()
        
        recommendations = []
        for score in top_scores:
            if score.overall_score >= 0.7:
                recommendations.append(f"Maintain strong relationship (score: {score.overall_score:.2f})")
            elif score.overall_score < 0.4:
                recommendations.append(f"Reconnect with weak connection (score: {score.overall_score:.2f})")
        
        return {
            "entity_id": entity_id,
            "recommendations": recommendations
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
