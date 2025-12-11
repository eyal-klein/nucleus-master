"""
Google Calendar Connector Service

Integrates with Google Calendar API to sync calendar events and publish them to NATS.
Provides OAuth authentication, event syncing, and webhook handling.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import base connector
import sys
sys.path.append('/app/backend/shared')
from connectors.base import BaseConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
EVENT_STREAM_URL = os.getenv("EVENT_STREAM_URL", "http://event-stream:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

# FastAPI app
app = FastAPI(
    title="Google Calendar Connector",
    description="Syncs Google Calendar events to NUCLEUS",
    version="1.0.0"
)


class CalendarConnector(BaseConnector):
    """Google Calendar connector implementation"""
    
    def __init__(self):
        super().__init__(
            name="calendar-connector",
            event_stream_url=EVENT_STREAM_URL
        )
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uri = REDIRECT_URI
    
    def get_auth_url(self, entity_id: str) -> str:
        """Generate OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=entity_id,
            prompt='consent'
        )
        
        return auth_url
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens"""
        entity_id = state
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store credentials (in production, store in database)
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        # Store in memory for now (TODO: persist to database)
        self.store_credentials(entity_id, token_data)
        
        return {
            "entity_id": entity_id,
            "status": "authenticated",
            "scopes": SCOPES
        }
    
    def get_credentials(self, entity_id: str) -> Optional[Credentials]:
        """Get stored credentials for entity"""
        token_data = self.retrieve_credentials(entity_id)
        if not token_data:
            return None
        
        return Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes")
        )
    
    async def sync_calendar_events(
        self,
        entity_id: str,
        days_past: int = 7,
        days_future: int = 30
    ) -> List[Dict[str, Any]]:
        """Sync calendar events for entity"""
        credentials = self.get_credentials(entity_id)
        if not credentials:
            raise ValueError(f"No credentials found for entity {entity_id}")
        
        try:
            # Build Calendar API service
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = (now - timedelta(days=days_past)).isoformat() + 'Z'
            time_max = (now + timedelta(days=days_future)).isoformat() + 'Z'
            
            # Fetch events
            logger.info(f"Fetching calendar events for entity {entity_id}")
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Found {len(events)} calendar events")
            
            # Process and publish events
            published_events = []
            for event in events:
                event_data = self._parse_calendar_event(event, entity_id)
                
                # Publish to NATS
                await self.publish_event(
                    stream="DIGITAL",
                    subject="calendar.event",
                    data=event_data
                )
                
                published_events.append(event_data)
            
            return published_events
        
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            raise HTTPException(status_code=500, detail=f"Calendar API error: {str(e)}")
    
    def _parse_calendar_event(self, event: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
        """Parse Google Calendar event into standardized format"""
        start = event.get('start', {})
        end = event.get('end', {})
        
        # Handle all-day events
        start_time = start.get('dateTime', start.get('date'))
        end_time = end.get('dateTime', end.get('date'))
        
        # Extract attendees
        attendees = []
        for attendee in event.get('attendees', []):
            attendees.append({
                "email": attendee.get('email'),
                "response_status": attendee.get('responseStatus'),
                "organizer": attendee.get('organizer', False)
            })
        
        return {
            "event_type": "calendar_event",
            "source": "google_calendar",
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "event_id": event.get('id'),
                "summary": event.get('summary', 'No Title'),
                "description": event.get('description', ''),
                "location": event.get('location', ''),
                "start_time": start_time,
                "end_time": end_time,
                "timezone": start.get('timeZone', 'UTC'),
                "attendees": attendees,
                "organizer": event.get('organizer', {}).get('email'),
                "status": event.get('status', 'confirmed'),
                "html_link": event.get('htmlLink'),
                "created": event.get('created'),
                "updated": event.get('updated')
            }
        }
    
    def store_credentials(self, entity_id: str, token_data: Dict[str, Any]):
        """Store credentials (in-memory for now, TODO: persist to database)"""
        if not hasattr(self, '_credentials_store'):
            self._credentials_store = {}
        self._credentials_store[entity_id] = token_data
    
    def retrieve_credentials(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored credentials"""
        if not hasattr(self, '_credentials_store'):
            return None
        return self._credentials_store.get(entity_id)


# Initialize connector
connector = CalendarConnector()


# API Models
class SyncRequest(BaseModel):
    entity_id: str = Field(..., description="Entity ID to sync calendar for")
    days_past: int = Field(7, description="Number of days in the past to sync")
    days_future: int = Field(30, description="Number of days in the future to sync")


class WebhookNotification(BaseModel):
    """Google Calendar webhook notification"""
    channel_id: str
    resource_id: str
    resource_uri: str
    resource_state: str  # sync, exists, not_exists


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "calendar-connector",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/auth")
async def initiate_auth(entity_id: str):
    """Initiate OAuth flow for Google Calendar"""
    try:
        auth_url = connector.get_auth_url(entity_id)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Error initiating auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback from Google"""
    try:
        result = await connector.handle_oauth_callback(code, state)
        return JSONResponse(content={
            "message": "Successfully authenticated with Google Calendar",
            "entity_id": result["entity_id"],
            "status": result["status"]
        })
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync")
async def sync_calendar(request: SyncRequest, background_tasks: BackgroundTasks):
    """Manually trigger calendar sync"""
    try:
        # Run sync in background
        background_tasks.add_task(
            connector.sync_calendar_events,
            request.entity_id,
            request.days_past,
            request.days_future
        )
        
        return {
            "message": "Calendar sync initiated",
            "entity_id": request.entity_id,
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle Google Calendar webhook notifications"""
    try:
        # Get notification headers
        channel_id = request.headers.get('X-Goog-Channel-ID')
        resource_state = request.headers.get('X-Goog-Resource-State')
        resource_id = request.headers.get('X-Goog-Resource-ID')
        
        logger.info(f"Received webhook: channel={channel_id}, state={resource_state}")
        
        # Handle different resource states
        if resource_state == 'sync':
            # Initial sync notification
            return {"status": "acknowledged"}
        
        elif resource_state in ['exists', 'not_exists']:
            # Calendar changed, trigger sync
            # TODO: Extract entity_id from channel_id and trigger sync
            logger.info(f"Calendar changed, should trigger sync for resource {resource_id}")
            return {"status": "sync_scheduled"}
        
        return {"status": "ignored"}
    
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/{entity_id}")
async def list_events(entity_id: str, days_past: int = 7, days_future: int = 30):
    """List synced calendar events for entity"""
    try:
        events = await connector.sync_calendar_events(entity_id, days_past, days_future)
        return {
            "entity_id": entity_id,
            "event_count": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
