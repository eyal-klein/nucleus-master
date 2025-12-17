"""
NUCLEUS Phase 3 - Gmail Connector Service
Connects to Gmail API and publishes events to Google Cloud Pub/Sub
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import os
import base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httpx
# Pub/Sub client
from google.cloud import pubsub_v1
import json


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Gmail Connector",
    description="Connects to Gmail API and streams email events",
    version="3.0.0"
)

# Configuration
EVENT_STREAM_URL = os.getenv("EVENT_STREAM_URL", "http://event-stream:8080")
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "5"))
# Pub/Sub Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "thrive-system1")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "nucleus-digital-events")



# Pydantic models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SyncRequest(BaseModel):
    entity_id: str
    credentials: Dict[str, str]  # OAuth credentials
    since: Optional[datetime] = None


class SyncResponse(BaseModel):
    status: str
    emails_processed: int
    events_published: int


class GmailConnector:
    """Gmail API connector"""
    
    def __init__(self, entity_id: str, credentials_dict: Dict[str, str]):
        self.entity_id = entity_id
        self.credentials = Credentials(**credentials_dict)
        self.service = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            # Refresh token if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info(f"Gmail authenticated for entity {self.entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {str(e)}")
            return False
    
    def fetch_messages(self, since: Optional[datetime] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch messages from Gmail.
        
        Args:
            since: Only fetch messages after this timestamp
            max_results: Maximum number of messages to fetch
            
        Returns:
            List of message metadata
        """
        try:
            # Build query
            query = ""
            if since:
                # Gmail uses format: after:YYYY/MM/DD
                date_str = since.strftime("%Y/%m/%d")
                query = f"after:{date_str}"
            
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Fetched {len(messages)} messages from Gmail")
            
            # Fetch full message details
            full_messages = []
            for msg in messages:
                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    full_messages.append(full_msg)
                except HttpError as e:
                    logger.error(f"Error fetching message {msg['id']}: {str(e)}")
            
            return full_messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {str(e)}")
            return []
    
    def parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Gmail message into standardized format.
        
        Args:
            message: Raw Gmail message
            
        Returns:
            Parsed message dict
        """
        # Extract headers
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        # Parse timestamp
        timestamp = datetime.fromtimestamp(int(message['internalDate']) / 1000)
        
        return {
            "message_id": message['id'],
            "thread_id": message['threadId'],
            "from": headers.get('From', ''),
            "to": headers.get('To', ''),
            "subject": headers.get('Subject', ''),
            "body": body[:1000],  # Limit body to 1000 chars
            "timestamp": timestamp.isoformat(),
            "labels": message.get('labelIds', []),
            "snippet": message.get('snippet', '')
        }
    
    async def publish_email_event(self, parsed_message: Dict[str, Any]) -> bool:
        """Publish email event to Event Stream"""
        try:
            event = {
                "source": "gmail",
                "type": "received",
                "entity_id": self.entity_id,
                "payload": parsed_message,
                "timestamp": parsed_message["timestamp"],
                "metadata": {
                    "message_id": parsed_message["message_id"],
                    "thread_id": parsed_message["thread_id"]
                }
            }
            
            # Publish to Pub/Sub
            try:
                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(GCP_PROJECT_ID, "nucleus-digital-events")
                
                message_data = json.dumps(event).encode("utf-8")
                future = publisher.publish(
                    topic_path,
                    data=message_data,
                    event_type=event["event_type"],
                    entity_id=event["entity_id"]
                )
                message_id = future.result(timeout=30)
                logger.info(f"Published to Pub/Sub: {message_id}")
                return True
            except Exception as pub_error:
                logger.error(f"Failed to publish to Pub/Sub: {pub_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing event: {str(e)}")
            return False
    
    async def sync(self, since: Optional[datetime] = None) -> tuple[int, int]:
        """
        Sync Gmail messages.
        
        Returns:
            Tuple of (emails_processed, events_published)
        """
        # Authenticate
        if not self.authenticate():
            return (0, 0)
        
        # Fetch messages
        messages = self.fetch_messages(since=since)
        
        # Parse and publish
        events_published = 0
        for message in messages:
            parsed = self.parse_message(message)
            if await self.publish_email_event(parsed):
                events_published += 1
        
        return (len(messages), events_published)
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "gmail-connector",
        "version": "3.0.0"
    }


@app.post("/sync", response_model=SyncResponse)
async def sync_gmail(request: SyncRequest):
    """
    Sync Gmail messages for an entity.
    
    This endpoint:
    1. Authenticates with Gmail API
    2. Fetches new messages (since last sync or specified timestamp)
    3. Parses messages
    4. Publishes events to Event Stream
    """
    connector = GmailConnector(request.entity_id, request.credentials)
    
    try:
        # Default to last 24 hours if no since timestamp
        since = request.since or (datetime.utcnow() - timedelta(hours=24))
        
        # Sync
        emails_processed, events_published = await connector.sync(since=since)
        
        return {
            "status": "success",
            "emails_processed": emails_processed,
            "events_published": events_published
        }
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    
    finally:
        await connector.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
