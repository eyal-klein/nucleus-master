"""
NUCLEUS Phase 3 - Oura Ring Connector Service
Connects to Oura API and publishes events to Google Cloud Pub/Sub
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.append("/app")

from backend.shared.connectors.base import HealthConnector
# Pub/Sub client
from google.cloud import pubsub_v1
import json


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NUCLEUS Oura Connector",
    description="Connects to Oura API and streams health events",
    version="3.0.0"
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SyncRequest(BaseModel):
    entity_id: str
    access_token: str
    since: Optional[datetime] = None


class SyncResponse(BaseModel):
    status: str
    records_processed: int
    events_published: int


class OuraConnector(HealthConnector):
    """Oura Ring API connector"""
    
    def __init__(self, entity_id: str, credentials: Dict[str, str]):
        super().__init__(entity_id, credentials)
        self.access_token = credentials.get("access_token")
        self.api_base_url = "https://api.ouraring.com/v2/usercollection"
    
    @property
    def source_name(self) -> str:
        return "oura"
    
    async def authenticate(self) -> bool:
        """Verify Oura API access token"""
        try:
            # Test API access with a simple request
            response = await self.http_client.get(
                f"{self.api_base_url}/personal_info",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                logger.info(f"Oura authenticated for entity {self.entity_id}")
                return True
            else:
                logger.error(f"Oura authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Oura authentication error: {str(e)}")
            return False
    
    async def fetch_latest_data(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch latest data from Oura API.
        
        Oura provides several data types:
        - Sleep sessions
        - Daily readiness
        - Daily activity
        - Heart rate
        - HRV (Heart Rate Variability)
        """
        if not since:
            since = datetime.utcnow() - timedelta(days=7)  # Default to last 7 days
        
        start_date = since.date().isoformat()
        end_date = date.today().isoformat()
        
        all_data = []
        
        # Fetch sleep data
        sleep_data = await self._fetch_sleep(start_date, end_date)
        all_data.extend([{"type": "sleep", "data": s} for s in sleep_data])
        
        # Fetch readiness data
        readiness_data = await self._fetch_readiness(start_date, end_date)
        all_data.extend([{"type": "readiness", "data": r} for r in readiness_data])
        
        # Fetch daily activity
        activity_data = await self._fetch_activity(start_date, end_date)
        all_data.extend([{"type": "activity", "data": a} for a in activity_data])
        
        logger.info(f"Fetched {len(all_data)} records from Oura")
        return all_data
    
    async def _fetch_sleep(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch sleep sessions"""
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/sleep",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"start_date": start_date, "end_date": end_date}
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"Failed to fetch sleep data: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching sleep data: {str(e)}")
            return []
    
    async def _fetch_readiness(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch daily readiness"""
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/daily_readiness",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"start_date": start_date, "end_date": end_date}
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"Failed to fetch readiness data: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching readiness data: {str(e)}")
            return []
    
    async def _fetch_activity(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetch daily activity"""
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/daily_activity",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"start_date": start_date, "end_date": end_date}
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(f"Failed to fetch activity data: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching activity data: {str(e)}")
            return []
    
    def parse_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Oura data into standardized events"""
        data_type = raw_data["type"]
        data = raw_data["data"]
        
        events = []
        
        if data_type == "sleep":
            events.extend(self._parse_sleep(data))
        elif data_type == "readiness":
            events.extend(self._parse_readiness(data))
        elif data_type == "activity":
            events.extend(self._parse_activity(data))
        
        return events
    
    def _parse_sleep(self, sleep_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse sleep session into events"""
        events = []
        
        # Sleep completed event
        events.append({
            "type": "sleep_completed",
            "payload": {
                "date": sleep_data.get("day"),
                "total_sleep_duration": sleep_data.get("total_sleep_duration"),  # seconds
                "sleep_score": sleep_data.get("score"),
                "efficiency": sleep_data.get("efficiency"),
                "deep_sleep_duration": sleep_data.get("deep_sleep_duration"),
                "rem_sleep_duration": sleep_data.get("rem_sleep_duration"),
                "light_sleep_duration": sleep_data.get("light_sleep_duration"),
                "awake_time": sleep_data.get("awake_time"),
                "bedtime_start": sleep_data.get("bedtime_start"),
                "bedtime_end": sleep_data.get("bedtime_end")
            },
            "metadata": {
                "source_id": sleep_data.get("id")
            }
        })
        
        # Individual metrics
        if sleep_data.get("score"):
            events.append(self.create_health_metric_event(
                metric_type="sleep_score",
                value=sleep_data["score"],
                unit="score",
                recorded_at=datetime.fromisoformat(sleep_data["day"]),
                source_id=sleep_data.get("id")
            ))
        
        if sleep_data.get("average_hrv"):
            events.append(self.create_health_metric_event(
                metric_type="hrv",
                value=sleep_data["average_hrv"],
                unit="ms",
                recorded_at=datetime.fromisoformat(sleep_data["day"]),
                source_id=sleep_data.get("id")
            ))
        
        if sleep_data.get("average_heart_rate"):
            events.append(self.create_health_metric_event(
                metric_type="heart_rate",
                value=sleep_data["average_heart_rate"],
                unit="bpm",
                recorded_at=datetime.fromisoformat(sleep_data["day"]),
                source_id=sleep_data.get("id")
            ))
        
        return events
    
    def _parse_readiness(self, readiness_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse readiness data into events"""
        events = []
        
        # Readiness score
        if readiness_data.get("score"):
            events.append(self.create_health_metric_event(
                metric_type="readiness_score",
                value=readiness_data["score"],
                unit="score",
                recorded_at=datetime.fromisoformat(readiness_data["day"]),
                source_id=readiness_data.get("id")
            ))
        
        # Temperature deviation
        if readiness_data.get("temperature_deviation"):
            events.append(self.create_health_metric_event(
                metric_type="temperature_deviation",
                value=readiness_data["temperature_deviation"],
                unit="celsius",
                recorded_at=datetime.fromisoformat(readiness_data["day"]),
                source_id=readiness_data.get("id")
            ))
        
        return events
    
    def _parse_activity(self, activity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse activity data into events"""
        events = []
        
        # Steps
        if activity_data.get("steps"):
            events.append(self.create_health_metric_event(
                metric_type="steps",
                value=activity_data["steps"],
                unit="steps",
                recorded_at=datetime.fromisoformat(activity_data["day"]),
                source_id=activity_data.get("id")
            ))
        
        # Calories
        if activity_data.get("total_calories"):
            events.append(self.create_health_metric_event(
                metric_type="calories",
                value=activity_data["total_calories"],
                unit="kcal",
                recorded_at=datetime.fromisoformat(activity_data["day"]),
                source_id=activity_data.get("id")
            ))
        
        # Activity score
        if activity_data.get("score"):
            events.append(self.create_health_metric_event(
                metric_type="activity_score",
                value=activity_data["score"],
                unit="score",
                recorded_at=datetime.fromisoformat(activity_data["day"]),
                source_id=activity_data.get("id")
            ))
        
        return events


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "oura-connector",
        "version": "3.0.0"
    }


@app.post("/sync", response_model=SyncResponse)
async def sync_oura(request: SyncRequest):
    """
    Sync Oura Ring data for an entity.
    
    This endpoint:
    1. Authenticates with Oura API
    2. Fetches sleep, readiness, and activity data
    3. Parses data into standardized health metrics
    4. Publishes events to Event Stream
    """
    connector = OuraConnector(
        request.entity_id,
        {"access_token": request.access_token}
    )
    
    try:
        # Default to last 7 days if no since timestamp
        since = request.since or (datetime.utcnow() - timedelta(days=7))
        
        # Sync
        events_published = await connector.sync(since=since)
        
        return {
            "status": "success",
            "records_processed": events_published,
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
