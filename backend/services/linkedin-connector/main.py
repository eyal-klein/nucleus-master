"""
LinkedIn Connector Service

Integrates with LinkedIn API to monitor profile, connections, and activity.
Publishes events to NATS SOCIAL stream for processing.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
import httpx
import asyncio
from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback")
EVENT_STREAM_URL = os.getenv("EVENT_STREAM_URL", "http://ingestion-event-stream:8000")
NATS_URL = os.getenv("NATS_URL", "nats://infra-nats:4222")

# LinkedIn API endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"

# FastAPI app
app = FastAPI(
    title="LinkedIn Connector",
    description="LinkedIn API integration for NUCLEUS",
    version="1.0.0"
)

# In-memory token storage (in production, use database)
tokens = {}

# NATS client
nats_client = None


# Models
class LinkedInProfile(BaseModel):
    """LinkedIn profile data"""
    linkedin_id: str
    first_name: str
    last_name: str
    headline: Optional[str]
    summary: Optional[str]
    profile_url: str
    profile_picture_url: Optional[str]
    current_company: Optional[str]
    current_title: Optional[str]
    location: Optional[str]
    connections_count: Optional[int]


class LinkedInConnection(BaseModel):
    """LinkedIn connection data"""
    connection_linkedin_id: str
    first_name: str
    last_name: str
    headline: Optional[str]
    profile_url: str
    current_company: Optional[str]
    current_title: Optional[str]
    location: Optional[str]


class LinkedInActivity(BaseModel):
    """LinkedIn activity data"""
    activity_id: str
    activity_type: str  # post, comment, share, like, job_change
    author_linkedin_id: str
    author_name: str
    content: Optional[str]
    posted_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0


# NATS Connection
async def connect_nats():
    """Connect to NATS server"""
    global nats_client
    if nats_client is None:
        try:
            nats_client = NATS()
            await nats_client.connect(NATS_URL)
            logger.info(f"Connected to NATS at {NATS_URL}")
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}. Service will continue without NATS.")
            nats_client = None


async def publish_event(event_type: str, entity_id: str, data: Dict[str, Any]):
    """Publish event to NATS SOCIAL stream"""
    try:
        if nats_client is None:
            await connect_nats()
        
        event = {
            "event_type": event_type,
            "source": "linkedin",
            "entity_id": entity_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Publish to SOCIAL stream
        await nats_client.publish("SOCIAL.linkedin", str(event).encode())
        logger.info(f"Published {event_type} event for entity {entity_id}")
    
    except Exception as e:
        logger.error(f"Error publishing event: {e}")


# LinkedIn API Helper Functions
async def get_linkedin_access_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get access token: {response.text}"
            )
        
        return response.json()


async def get_linkedin_profile(access_token: str) -> Dict[str, Any]:
    """Get user's LinkedIn profile"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        # Get basic profile
        response = await client.get(
            f"{LINKEDIN_API_BASE}/me",
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get profile: {response.text}"
            )
        
        profile = response.json()
        
        # Get profile picture (if available)
        try:
            pic_response = await client.get(
                f"{LINKEDIN_API_BASE}/me?projection=(id,profilePicture(displayImage~:playableStreams))",
                headers=headers
            )
            if pic_response.status_code == 200:
                pic_data = pic_response.json()
                if "profilePicture" in pic_data:
                    profile["profilePicture"] = pic_data["profilePicture"]
        except Exception as e:
            logger.warning(f"Could not fetch profile picture: {e}")
        
        return profile


async def get_linkedin_connections(access_token: str, start: int = 0, count: int = 50) -> Dict[str, Any]:
    """Get user's LinkedIn connections"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LINKEDIN_API_BASE}/connections",
            headers=headers,
            params={"start": start, "count": count}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get connections: {response.text}"
            )
        
        return response.json()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize NATS connection on startup"""
    await connect_nats()


@app.on_event("shutdown")
async def shutdown_event():
    """Close NATS connection on shutdown"""
    if nats_client:
        await nats_client.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "linkedin-connector",
        "timestamp": datetime.utcnow().isoformat(),
        "nats_connected": nats_client is not None and nats_client.is_connected
    }


@app.get("/auth")
async def initiate_auth(entity_id: str):
    """Initiate LinkedIn OAuth flow"""
    
    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "state": entity_id,  # Pass entity_id as state
        "scope": "r_liteprofile r_emailaddress r_basicprofile r_network"
    }
    
    auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "message": "Redirect user to auth_url to authorize"
    }


@app.get("/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback from LinkedIn"""
    
    entity_id = state  # entity_id was passed as state
    
    try:
        # Exchange code for access token
        token_data = await get_linkedin_access_token(code)
        access_token = token_data["access_token"]
        
        # Store token (in production, store in database)
        tokens[entity_id] = {
            "access_token": access_token,
            "expires_in": token_data.get("expires_in", 3600),
            "obtained_at": datetime.utcnow()
        }
        
        logger.info(f"Successfully authenticated entity {entity_id}")
        
        # Trigger initial sync
        asyncio.create_task(sync_profile(entity_id))
        
        return {
            "status": "success",
            "message": "LinkedIn account connected successfully",
            "entity_id": entity_id
        }
    
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync-profile/{entity_id}")
async def sync_profile(entity_id: str):
    """Sync user's LinkedIn profile"""
    
    if entity_id not in tokens:
        raise HTTPException(
            status_code=401,
            detail="Entity not authenticated. Please authenticate first."
        )
    
    access_token = tokens[entity_id]["access_token"]
    
    try:
        # Get profile from LinkedIn
        profile_data = await get_linkedin_profile(access_token)
        
        # Parse profile data
        linkedin_id = profile_data.get("id")
        first_name = profile_data.get("localizedFirstName", "")
        last_name = profile_data.get("localizedLastName", "")
        
        # Build profile object
        profile = {
            "linkedin_id": linkedin_id,
            "first_name": first_name,
            "last_name": last_name,
            "headline": profile_data.get("localizedHeadline"),
            "profile_url": f"https://www.linkedin.com/in/{linkedin_id}",
            "profile_picture_url": None,  # Extract from profilePicture if available
        }
        
        # Publish profile update event
        await publish_event(
            "linkedin_profile_update",
            entity_id,
            profile
        )
        
        return {
            "status": "success",
            "message": "Profile synced successfully",
            "profile": profile
        }
    
    except Exception as e:
        logger.error(f"Error syncing profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync-connections/{entity_id}")
async def sync_connections(entity_id: str, max_connections: int = 500):
    """Sync user's LinkedIn connections"""
    
    if entity_id not in tokens:
        raise HTTPException(
            status_code=401,
            detail="Entity not authenticated. Please authenticate first."
        )
    
    access_token = tokens[entity_id]["access_token"]
    
    try:
        all_connections = []
        start = 0
        count = 50
        
        # Paginate through connections
        while start < max_connections:
            connections_data = await get_linkedin_connections(access_token, start, count)
            
            if "elements" not in connections_data:
                break
            
            connections = connections_data["elements"]
            all_connections.extend(connections)
            
            if len(connections) < count:
                break  # No more connections
            
            start += count
        
        # Publish connection events
        for connection in all_connections:
            connection_data = {
                "connection_linkedin_id": connection.get("id"),
                "first_name": connection.get("localizedFirstName", ""),
                "last_name": connection.get("localizedLastName", ""),
                "headline": connection.get("localizedHeadline"),
                "profile_url": f"https://www.linkedin.com/in/{connection.get('id')}",
            }
            
            await publish_event(
                "linkedin_new_connection",
                entity_id,
                connection_data
            )
        
        return {
            "status": "success",
            "message": f"Synced {len(all_connections)} connections",
            "connections_count": len(all_connections)
        }
    
    except Exception as e:
        logger.error(f"Error syncing connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync-activity/{entity_id}")
async def sync_activity(entity_id: str, days: int = 7):
    """Sync LinkedIn activity feed"""
    
    if entity_id not in tokens:
        raise HTTPException(
            status_code=401,
            detail="Entity not authenticated. Please authenticate first."
        )
    
    access_token = tokens[entity_id]["access_token"]
    
    try:
        # Note: LinkedIn API has limited activity feed access
        # This is a simplified implementation
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            # Get user's posts (if available)
            response = await client.get(
                f"{LINKEDIN_API_BASE}/ugcPosts",
                headers=headers,
                params={"q": "authors", "authors": "urn:li:person:CURRENT"}
            )
            
            if response.status_code == 200:
                posts_data = response.json()
                
                if "elements" in posts_data:
                    for post in posts_data["elements"]:
                        activity_data = {
                            "activity_id": post.get("id"),
                            "activity_type": "post",
                            "author_linkedin_id": entity_id,
                            "content": post.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("shareCommentary", {}).get("text"),
                            "posted_at": datetime.fromtimestamp(post.get("created", {}).get("time", 0) / 1000).isoformat(),
                        }
                        
                        await publish_event(
                            "linkedin_activity",
                            entity_id,
                            activity_data
                        )
        
        return {
            "status": "success",
            "message": "Activity synced successfully"
        }
    
    except Exception as e:
        logger.error(f"Error syncing activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/{entity_id}")
async def get_profile(entity_id: str):
    """Get stored profile for entity"""
    # In production, query from database
    return {
        "message": "Profile retrieval from database not implemented yet",
        "entity_id": entity_id
    }


@app.get("/connections/{entity_id}")
async def get_connections(entity_id: str):
    """Get stored connections for entity"""
    # In production, query from database
    return {
        "message": "Connections retrieval from database not implemented yet",
        "entity_id": entity_id
    }


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle webhooks from LinkedIn (if available)"""
    # LinkedIn webhook support is limited
    # This is a placeholder for future implementation
    
    body = await request.json()
    logger.info(f"Received webhook: {body}")
    
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
