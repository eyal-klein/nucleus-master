"""
Network Intelligence Service

Provides intelligent insights on professional network, detects opportunities,
suggests introductions, and analyzes career paths.
"""

import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from collections import Counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, and_, func, desc
from sqlalchemy.orm import sessionmaker, Session

# Import models
import sys
sys.path.append('/app/backend/shared')
from models.memory import LinkedInProfile, LinkedInConnection, LinkedInActivity
from models.dna import RelationshipScore, NetworkInsights

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
    title="Network Intelligence",
    description="Intelligent insights on professional network",
    version="1.0.0"
)


# API Models
class NetworkAnalysis(BaseModel):
    """Network analysis result"""
    entity_id: str
    total_connections: int
    network_growth_rate: float
    company_clusters: List[Dict[str, Any]]
    industry_clusters: List[Dict[str, Any]]
    location_clusters: List[Dict[str, Any]]
    top_connectors: List[Dict[str, Any]]


class Opportunity(BaseModel):
    """Detected opportunity"""
    opportunity_type: str  # job_opening, career_transition, collaboration
    title: str
    description: str
    related_connections: List[str]
    confidence: float = Field(..., ge=0, le=1)
    detected_at: datetime


class IntroductionSuggestion(BaseModel):
    """Introduction suggestion"""
    person_a_id: str
    person_a_name: str
    person_b_id: str
    person_b_name: str
    reason: str
    mutual_benefit: str
    confidence: float = Field(..., ge=0, le=1)


class CareerInsight(BaseModel):
    """Career path insight"""
    common_paths: List[Dict[str, Any]]
    trending_skills: List[str]
    industry_movements: List[Dict[str, Any]]


# Network Analysis
class NetworkAnalyzer:
    """Analyzes professional network"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_network(self, entity_id: str) -> NetworkAnalysis:
        """Analyze network structure and clusters"""
        
        # Get all connections
        connections = self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.entity_id == entity_id
            )
        ).scalars().all()
        
        total_connections = len(connections)
        
        # Calculate growth rate (compare to 30 days ago)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_connections = [
            c for c in connections 
            if c.connected_at and c.connected_at >= thirty_days_ago
        ]
        growth_rate = (len(recent_connections) / total_connections * 100) if total_connections > 0 else 0
        
        # Cluster by company
        companies = [c.current_company for c in connections if c.current_company]
        company_counts = Counter(companies)
        company_clusters = [
            {"company": company, "count": count}
            for company, count in company_counts.most_common(10)
        ]
        
        # Cluster by location
        locations = [c.location for c in connections if c.location]
        location_counts = Counter(locations)
        location_clusters = [
            {"location": location, "count": count}
            for location, count in location_counts.most_common(10)
        ]
        
        # Industry clusters (would need industry data from LinkedIn)
        industry_clusters = []
        
        # Top connectors (connections with high relationship scores)
        top_scores = self.db.execute(
            select(RelationshipScore).where(
                RelationshipScore.entity_id == entity_id
            ).order_by(desc(RelationshipScore.overall_score)).limit(10)
        ).scalars().all()
        
        top_connectors = []
        for score in top_scores:
            connection = self.db.execute(
                select(LinkedInConnection).where(
                    LinkedInConnection.id == score.connection_id
                )
            ).scalar_one_or_none()
            
            if connection:
                top_connectors.append({
                    "name": f"{connection.first_name} {connection.last_name}",
                    "company": connection.current_company,
                    "score": float(score.overall_score)
                })
        
        # Store insights
        insights = NetworkInsights(
            entity_id=entity_id,
            total_connections=total_connections,
            network_growth_rate=growth_rate,
            company_clusters=company_clusters,
            location_clusters=location_clusters,
            top_connectors=top_connectors,
            analysis_date=date.today()
        )
        
        self.db.merge(insights)
        self.db.commit()
        
        return NetworkAnalysis(
            entity_id=entity_id,
            total_connections=total_connections,
            network_growth_rate=round(growth_rate, 2),
            company_clusters=company_clusters,
            industry_clusters=industry_clusters,
            location_clusters=location_clusters,
            top_connectors=top_connectors
        )
    
    def detect_opportunities(self, entity_id: str) -> List[Opportunity]:
        """Detect career opportunities from network"""
        
        opportunities = []
        
        # Get recent activities
        recent_activities = self.db.execute(
            select(LinkedInActivity).where(
                and_(
                    LinkedInActivity.entity_id == entity_id,
                    LinkedInActivity.posted_at >= datetime.utcnow() - timedelta(days=30)
                )
            ).order_by(desc(LinkedInActivity.posted_at))
        ).scalars().all()
        
        # Detect job changes
        job_change_activities = [
            a for a in recent_activities 
            if a.activity_type == "job_change"
        ]
        
        for activity in job_change_activities:
            opportunities.append(Opportunity(
                opportunity_type="career_transition",
                title=f"Career move at {activity.content}",
                description=f"{activity.author_name} changed jobs",
                related_connections=[activity.author_linkedin_id],
                confidence=0.8,
                detected_at=activity.posted_at
            ))
        
        # Detect collaboration opportunities (simplified)
        # In production, use NLP to analyze post content
        
        return opportunities[:10]  # Limit to top 10
    
    def suggest_introductions(self, entity_id: str) -> List[IntroductionSuggestion]:
        """Suggest valuable introductions"""
        
        suggestions = []
        
        # Get connections
        connections = self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.entity_id == entity_id
            ).limit(100)  # Limit for performance
        ).scalars().all()
        
        # Find connections at same company
        company_map = {}
        for conn in connections:
            if conn.current_company:
                if conn.current_company not in company_map:
                    company_map[conn.current_company] = []
                company_map[conn.current_company].append(conn)
        
        # Suggest introductions within same company
        for company, company_connections in company_map.items():
            if len(company_connections) >= 2:
                # Suggest introducing first two
                conn_a = company_connections[0]
                conn_b = company_connections[1]
                
                suggestions.append(IntroductionSuggestion(
                    person_a_id=str(conn_a.id),
                    person_a_name=f"{conn_a.first_name} {conn_a.last_name}",
                    person_b_id=str(conn_b.id),
                    person_b_name=f"{conn_b.first_name} {conn_b.last_name}",
                    reason=f"Both work at {company}",
                    mutual_benefit="Networking within same company",
                    confidence=0.7
                ))
        
        return suggestions[:5]  # Top 5 suggestions
    
    def analyze_career_paths(self, entity_id: str) -> CareerInsight:
        """Analyze career paths in network"""
        
        # Get connections with experience data
        connections = self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.entity_id == entity_id
            )
        ).scalars().all()
        
        # Extract current titles
        titles = [c.current_title for c in connections if c.current_title]
        title_counts = Counter(titles)
        
        common_paths = [
            {"title": title, "count": count}
            for title, count in title_counts.most_common(10)
        ]
        
        # Trending skills (would need skills data)
        trending_skills = ["Python", "Leadership", "Data Analysis", "Cloud Computing"]
        
        # Industry movements (simplified)
        industry_movements = []
        
        return CareerInsight(
            common_paths=common_paths,
            trending_skills=trending_skills,
            industry_movements=industry_movements
        )


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "network-intelligence",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/network-analysis/{entity_id}")
async def get_network_analysis(entity_id: str):
    """Analyze network structure"""
    db = SessionLocal()
    try:
        analyzer = NetworkAnalyzer(db)
        analysis = analyzer.analyze_network(entity_id)
        return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing network: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


@app.get("/opportunities/{entity_id}")
async def detect_opportunities(entity_id: str):
    """Detect career opportunities"""
    db = SessionLocal()
    try:
        analyzer = NetworkAnalyzer(db)
        opportunities = analyzer.detect_opportunities(entity_id)
        
        return {
            "entity_id": entity_id,
            "opportunities_count": len(opportunities),
            "opportunities": opportunities
        }
    
    finally:
        db.close()


@app.get("/introduction-suggestions/{entity_id}")
async def get_introduction_suggestions(entity_id: str):
    """Get introduction suggestions"""
    db = SessionLocal()
    try:
        analyzer = NetworkAnalyzer(db)
        suggestions = analyzer.suggest_introductions(entity_id)
        
        return {
            "entity_id": entity_id,
            "suggestions_count": len(suggestions),
            "suggestions": suggestions
        }
    
    finally:
        db.close()


@app.get("/career-insights/{entity_id}")
async def get_career_insights(entity_id: str):
    """Get career path insights"""
    db = SessionLocal()
    try:
        analyzer = NetworkAnalyzer(db)
        insights = analyzer.analyze_career_paths(entity_id)
        return insights
    
    finally:
        db.close()


@app.get("/skill-gaps/{entity_id}")
async def identify_skill_gaps(entity_id: str):
    """Identify skill gaps in network"""
    db = SessionLocal()
    try:
        # Get entity profile
        profile = db.execute(
            select(LinkedInProfile).where(
                LinkedInProfile.entity_id == entity_id
            )
        ).scalar_one_or_none()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get network skills (simplified)
        # In production, analyze skills from all connections
        
        entity_skills = profile.skills if isinstance(profile.skills, list) else []
        network_skills = ["Python", "Leadership", "Data Analysis", "Cloud Computing", "AI/ML"]
        
        skill_gaps = [skill for skill in network_skills if skill not in entity_skills]
        
        return {
            "entity_id": entity_id,
            "current_skills": entity_skills,
            "network_trending_skills": network_skills,
            "skill_gaps": skill_gaps,
            "recommendations": [f"Consider learning {skill}" for skill in skill_gaps[:3]]
        }
    
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
