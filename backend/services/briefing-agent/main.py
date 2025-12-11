"""
Briefing Agent Service

Generates intelligent pre-meeting briefings with context from emails,
previous meetings, and entity knowledge using AI.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session
from openai import OpenAI

# Import models
import sys
sys.path.append('/app/backend/shared')
from models.memory import CalendarEvent, EmailMessage, Briefing
from models.dna import DailyReadiness

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/nucleus")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# OpenAI setup
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# FastAPI app
app = FastAPI(
    title="Briefing Agent",
    description="Generates intelligent pre-meeting briefings",
    version="1.0.0"
)


# API Models
class BriefingRequest(BaseModel):
    """Request to generate a briefing"""
    event_id: str = Field(..., description="Calendar event ID")
    entity_id: str = Field(..., description="Entity ID")


class BriefingResponse(BaseModel):
    """Generated briefing response"""
    id: str
    event_id: str
    entity_id: str
    title: str
    content: str
    context_sources: Dict[str, int]
    generated_at: datetime
    status: str


# Briefing Generator
class BriefingGenerator:
    """Generates meeting briefings with AI"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai = openai_client
    
    async def generate_briefing(
        self,
        event_id: str,
        entity_id: str
    ) -> BriefingResponse:
        """Generate comprehensive briefing for a meeting"""
        
        # Get calendar event
        event = self.db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.id == event_id,
                    CalendarEvent.entity_id == entity_id
                )
            )
        ).scalar_one_or_none()
        
        if not event:
            raise ValueError(f"Calendar event {event_id} not found")
        
        logger.info(f"Generating briefing for event: {event.summary}")
        
        # Gather context
        context = await self._gather_context(event, entity_id)
        
        # Generate briefing content with AI
        content = await self._generate_content(event, context, entity_id)
        
        # Create briefing record
        briefing = Briefing(
            entity_id=entity_id,
            event_id=event_id,
            title=f"Meeting Briefing: {event.summary}",
            content=content,
            email_count=context["email_count"],
            previous_meetings_count=context["previous_meetings_count"],
            context_sources=context["sources"],
            status="generated"
        )
        
        self.db.add(briefing)
        self.db.commit()
        self.db.refresh(briefing)
        
        return BriefingResponse(
            id=str(briefing.id),
            event_id=event_id,
            entity_id=entity_id,
            title=briefing.title,
            content=briefing.content,
            context_sources={
                "emails": context["email_count"],
                "previous_meetings": context["previous_meetings_count"]
            },
            generated_at=briefing.generated_at,
            status=briefing.status
        )
    
    async def _gather_context(
        self,
        event: CalendarEvent,
        entity_id: str
    ) -> Dict[str, Any]:
        """Gather context from various sources"""
        
        # Extract attendee emails
        attendees = event.attendees if isinstance(event.attendees, list) else []
        attendee_emails = [
            a.get("email") if isinstance(a, dict) else a
            for a in attendees
        ]
        
        # Get related emails (past 7 days)
        emails = await self._get_related_emails(entity_id, attendee_emails, days=7)
        
        # Get previous meetings with same attendees (past 90 days)
        previous_meetings = await self._get_previous_meetings(
            entity_id, attendee_emails, event.start_time, days=90
        )
        
        # Get current readiness
        readiness = await self._get_current_readiness(entity_id)
        
        return {
            "emails": emails,
            "email_count": len(emails),
            "previous_meetings": previous_meetings,
            "previous_meetings_count": len(previous_meetings),
            "readiness": readiness,
            "sources": {
                "emails": len(emails),
                "previous_meetings": len(previous_meetings),
                "readiness": 1 if readiness else 0
            }
        }
    
    async def _get_related_emails(
        self,
        entity_id: str,
        attendee_emails: List[str],
        days: int = 7
    ) -> List[EmailMessage]:
        """Get emails related to meeting attendees"""
        
        if not attendee_emails:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        emails = self.db.execute(
            select(EmailMessage).where(
                and_(
                    EmailMessage.entity_id == entity_id,
                    EmailMessage.received_at >= cutoff_date,
                    or_(*[EmailMessage.sender.contains(email) for email in attendee_emails])
                )
            ).order_by(desc(EmailMessage.received_at)).limit(10)
        ).scalars().all()
        
        return emails
    
    async def _get_previous_meetings(
        self,
        entity_id: str,
        attendee_emails: List[str],
        current_meeting_time: datetime,
        days: int = 90
    ) -> List[CalendarEvent]:
        """Get previous meetings with same attendees"""
        
        if not attendee_emails:
            return []
        
        cutoff_date = current_meeting_time - timedelta(days=days)
        
        # This is simplified - in production, properly query JSONB array
        meetings = self.db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.entity_id == entity_id,
                    CalendarEvent.start_time >= cutoff_date,
                    CalendarEvent.start_time < current_meeting_time
                )
            ).order_by(desc(CalendarEvent.start_time)).limit(5)
        ).scalars().all()
        
        return meetings
    
    async def _get_current_readiness(
        self,
        entity_id: str
    ) -> Optional[DailyReadiness]:
        """Get current day's readiness score"""
        
        today = datetime.utcnow().date()
        
        readiness = self.db.execute(
            select(DailyReadiness).where(
                and_(
                    DailyReadiness.entity_id == entity_id,
                    DailyReadiness.date == today
                )
            )
        ).scalar_one_or_none()
        
        return readiness
    
    async def _generate_content(
        self,
        event: CalendarEvent,
        context: Dict[str, Any],
        entity_id: str
    ) -> str:
        """Generate briefing content using AI"""
        
        # Prepare context for AI
        attendees_list = ", ".join([
            a.get("email") if isinstance(a, dict) else str(a)
            for a in (event.attendees if isinstance(event.attendees, list) else [])
        ])
        
        # Email summaries
        email_context = ""
        if context["emails"]:
            email_context = "\n\n**Recent Email Context:**\n"
            for email in context["emails"][:5]:
                email_context += f"- From {email.sender}: {email.subject}\n"
                if email.snippet:
                    email_context += f"  {email.snippet[:100]}...\n"
        
        # Previous meetings
        meetings_context = ""
        if context["previous_meetings"]:
            meetings_context = "\n\n**Previous Meetings:**\n"
            for meeting in context["previous_meetings"][:3]:
                meetings_context += f"- {meeting.summary} ({meeting.start_time.strftime('%Y-%m-%d')})\n"
        
        # Readiness context
        readiness_context = ""
        if context["readiness"]:
            r = context["readiness"]
            readiness_context = f"\n\n**Your Current State:**\n"
            readiness_context += f"- Readiness Score: {r.readiness_score:.2f}/1.00\n"
            readiness_context += f"- Sleep Score: {r.sleep_score:.2f}/1.00\n"
            readiness_context += f"- Energy Level: {'High' if r.readiness_score > 0.7 else 'Medium' if r.readiness_score > 0.4 else 'Low'}\n"
            if r.recommendations:
                readiness_context += f"- Recommendation: {r.recommendations[0]}\n"
        
        # Build prompt
        prompt = f"""Generate a comprehensive meeting briefing for the following event:

**Meeting Details:**
- Title: {event.summary}
- Time: {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}
- Location: {event.location or 'Not specified'}
- Attendees: {attendees_list or 'Not specified'}
- Description: {event.description or 'No description provided'}

{email_context}

{meetings_context}

{readiness_context}

Please generate a structured briefing in Markdown format with the following sections:
1. **Meeting Overview** - Brief summary of the meeting
2. **Context** - Key context from emails and previous meetings
3. **Key Points to Cover** - Important topics or questions to address
4. **Recommended Preparation** - What to prepare or review before the meeting
5. **Personal Recommendation** - Based on current readiness, how to approach this meeting

Keep it concise, actionable, and professional.
"""
        
        try:
            # Call OpenAI API
            response = self.openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an executive assistant helping prepare for meetings. Generate concise, actionable briefings."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Add header
            header = f"# Meeting Briefing: {event.summary}\n\n"
            header += f"**Time:** {event.start_time.strftime('%A, %B %d, %Y at %H:%M')}\n"
            header += f"**Duration:** {int((event.end_time - event.start_time).total_seconds() / 60)} minutes\n"
            if event.location:
                header += f"**Location:** {event.location}\n"
            header += f"**Attendees:** {attendees_list or 'Not specified'}\n\n"
            header += "---\n\n"
            
            return header + content
        
        except Exception as e:
            logger.error(f"Error generating content with AI: {e}")
            
            # Fallback to template-based briefing
            return self._generate_template_briefing(event, context)
    
    def _generate_template_briefing(
        self,
        event: CalendarEvent,
        context: Dict[str, Any]
    ) -> str:
        """Generate template-based briefing as fallback"""
        
        attendees_list = ", ".join([
            a.get("email") if isinstance(a, dict) else str(a)
            for a in (event.attendees if isinstance(event.attendees, list) else [])
        ])
        
        content = f"# Meeting Briefing: {event.summary}\n\n"
        content += f"**Time:** {event.start_time.strftime('%A, %B %d, %Y at %H:%M')}\n"
        content += f"**Duration:** {int((event.end_time - event.start_time).total_seconds() / 60)} minutes\n"
        if event.location:
            content += f"**Location:** {event.location}\n"
        content += f"**Attendees:** {attendees_list or 'Not specified'}\n\n"
        content += "---\n\n"
        
        content += "## Meeting Overview\n\n"
        if event.description:
            content += f"{event.description}\n\n"
        else:
            content += "No description provided.\n\n"
        
        if context["emails"]:
            content += "## Recent Email Context\n\n"
            for email in context["emails"][:3]:
                content += f"- **From {email.sender}:** {email.subject}\n"
        
        if context["previous_meetings"]:
            content += "\n## Previous Meetings\n\n"
            for meeting in context["previous_meetings"][:3]:
                content += f"- {meeting.summary} ({meeting.start_time.strftime('%Y-%m-%d')})\n"
        
        if context["readiness"]:
            r = context["readiness"]
            content += "\n## Your Current State\n\n"
            content += f"- Readiness Score: {r.readiness_score:.2f}/1.00\n"
            content += f"- Energy Level: {'High' if r.readiness_score > 0.7 else 'Medium' if r.readiness_score > 0.4 else 'Low'}\n"
            if r.recommendations:
                content += f"- Recommendation: {r.recommendations[0]}\n"
        
        return content


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "briefing-agent",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/generate-briefing/{event_id}")
async def generate_briefing(event_id: str, entity_id: str):
    """Generate briefing for a specific event"""
    db = SessionLocal()
    try:
        generator = BriefingGenerator(db)
        briefing = await generator.generate_briefing(event_id, entity_id)
        return briefing
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


@app.get("/briefing/{event_id}")
async def get_briefing(event_id: str):
    """Get existing briefing for an event"""
    db = SessionLocal()
    try:
        briefing = db.execute(
            select(Briefing).where(Briefing.event_id == event_id)
        ).scalar_one_or_none()
        
        if not briefing:
            raise HTTPException(
                status_code=404,
                detail=f"No briefing found for event {event_id}"
            )
        
        return BriefingResponse(
            id=str(briefing.id),
            event_id=briefing.event_id,
            entity_id=briefing.entity_id,
            title=briefing.title,
            content=briefing.content,
            context_sources=briefing.context_sources or {},
            generated_at=briefing.generated_at,
            status=briefing.status
        )
    
    finally:
        db.close()


@app.get("/upcoming-briefings/{entity_id}")
async def get_upcoming_briefings(entity_id: str, hours: int = 24):
    """Get briefings for upcoming meetings"""
    db = SessionLocal()
    try:
        # Get upcoming events
        now = datetime.utcnow()
        future = now + timedelta(hours=hours)
        
        events = db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.entity_id == entity_id,
                    CalendarEvent.start_time >= now,
                    CalendarEvent.start_time <= future
                )
            ).order_by(CalendarEvent.start_time)
        ).scalars().all()
        
        # Get existing briefings
        event_ids = [str(e.id) for e in events]
        briefings = db.execute(
            select(Briefing).where(
                and_(
                    Briefing.entity_id == entity_id,
                    Briefing.event_id.in_(event_ids)
                )
            )
        ).scalars().all()
        
        briefing_map = {b.event_id: b for b in briefings}
        
        # Prepare response
        upcoming = []
        for event in events:
            event_id = str(event.id)
            briefing = briefing_map.get(event_id)
            
            upcoming.append({
                "event": {
                    "id": event_id,
                    "summary": event.summary,
                    "start_time": event.start_time,
                    "end_time": event.end_time
                },
                "briefing": {
                    "exists": briefing is not None,
                    "id": str(briefing.id) if briefing else None,
                    "status": briefing.status if briefing else None
                }
            })
        
        return {
            "entity_id": entity_id,
            "upcoming_count": len(upcoming),
            "upcoming": upcoming
        }
    
    finally:
        db.close()


@app.post("/schedule-briefings/{entity_id}")
async def schedule_briefings(
    entity_id: str,
    background_tasks: BackgroundTasks,
    hours_ahead: int = 24,
    minutes_before: int = 30
):
    """Schedule automatic briefing generation for upcoming meetings"""
    db = SessionLocal()
    try:
        # Get upcoming events
        now = datetime.utcnow()
        future = now + timedelta(hours=hours_ahead)
        
        events = db.execute(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.entity_id == entity_id,
                    CalendarEvent.start_time >= now,
                    CalendarEvent.start_time <= future
                )
            )
        ).scalars().all()
        
        scheduled_count = 0
        for event in events:
            # Check if briefing already exists
            existing = db.execute(
                select(Briefing).where(Briefing.event_id == str(event.id))
            ).scalar_one_or_none()
            
            if not existing:
                # Schedule briefing generation
                background_tasks.add_task(
                    _generate_briefing_task,
                    str(event.id),
                    entity_id
                )
                scheduled_count += 1
        
        return {
            "entity_id": entity_id,
            "scheduled_count": scheduled_count,
            "total_upcoming": len(events)
        }
    
    finally:
        db.close()


async def _generate_briefing_task(event_id: str, entity_id: str):
    """Background task to generate briefing"""
    db = SessionLocal()
    try:
        generator = BriefingGenerator(db)
        await generator.generate_briefing(event_id, entity_id)
        logger.info(f"Generated briefing for event {event_id}")
    except Exception as e:
        logger.error(f"Error in briefing generation task: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
