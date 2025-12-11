# NUCLEUS API Documentation

**Version:** 3.0 (Conscious Organism)  
**Last Updated:** December 11, 2025  
**Base URL Pattern:** `https://{service-name}-xeihvetbja-uc.a.run.app`

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Data Ingestion APIs](#data-ingestion-apis)
3. [Analysis APIs](#analysis-apis)
4. [Intelligence APIs](#intelligence-apis)
5. [Authentication](#authentication)
6. [Error Handling](#error-handling)
7. [Rate Limits](#rate-limits)

---

## API Overview

All NUCLEUS services expose REST APIs following consistent patterns:
- **Health Check:** `GET /health` on every service
- **Authentication:** API keys or OAuth tokens
- **Format:** JSON request/response
- **Versioning:** URL-based (future: `/v1/`, `/v2/`)

---

## Data Ingestion APIs

### Event Stream Service

**Base URL:** `https://ingestion-event-stream-xeihvetbja-uc.a.run.app`

#### POST /publish
Publish an event to a NATS stream.

**Request:**
```json
{
  "stream": "DIGITAL",
  "event_type": "email_received",
  "entity_id": "uuid",
  "data": {...}
}
```

**Response:**
```json
{
  "status": "published",
  "sequence": 12345
}
```

#### GET /streams
List available event streams.

**Response:**
```json
{
  "streams": ["DIGITAL", "HEALTH", "SOCIAL"]
}
```

---

### Gmail Connector

**Base URL:** `https://ingestion-gmail-xeihvetbja-uc.a.run.app`

#### GET /auth
Initiate OAuth 2.0 flow for Gmail.

**Response:** Redirect to Google OAuth consent screen

#### GET /callback?code={auth_code}
OAuth callback endpoint.

#### POST /sync/{entity_id}
Sync emails for entity.

**Request:**
```json
{
  "days_back": 7,
  "labels": ["INBOX", "IMPORTANT"]
}
```

**Response:**
```json
{
  "status": "success",
  "messages_synced": 42
}
```

#### GET /messages/{entity_id}
Get synced messages.

**Query Params:**
- `limit` (default: 50)
- `offset` (default: 0)
- `from_date` (ISO 8601)

**Response:**
```json
{
  "messages": [
    {
      "id": "uuid",
      "from": "sender@example.com",
      "subject": "Meeting",
      "body": "...",
      "received_at": "2025-12-11T10:00:00Z"
    }
  ],
  "total": 42
}
```

---

### Calendar Connector

**Base URL:** `https://ingestion-calendar-xeihvetbja-uc.a.run.app`

#### GET /auth
Initiate OAuth 2.0 flow for Google Calendar.

#### POST /sync/{entity_id}
Sync calendar events.

**Request:**
```json
{
  "days_back": 7,
  "days_forward": 30
}
```

**Response:**
```json
{
  "status": "success",
  "events_synced": 25
}
```

#### GET /events/{entity_id}
Get calendar events.

**Query Params:**
- `start_date` (ISO 8601)
- `end_date` (ISO 8601)

**Response:**
```json
{
  "events": [
    {
      "id": "uuid",
      "title": "Team Meeting",
      "start_time": "2025-12-11T14:00:00Z",
      "end_time": "2025-12-11T15:00:00Z",
      "attendees": ["user@example.com"],
      "location": "Conference Room A"
    }
  ]
}
```

#### POST /webhook
Receive calendar change notifications.

---

### Oura Connector

**Base URL:** `https://ingestion-oura-xeihvetbja-uc.a.run.app`

#### POST /authorize/{entity_id}
Authorize Oura Ring access.

**Request:**
```json
{
  "access_token": "oura_token"
}
```

#### POST /sync/{entity_id}
Sync Oura health data.

**Request:**
```json
{
  "days_back": 7
}
```

**Response:**
```json
{
  "status": "success",
  "metrics_synced": {
    "sleep": 7,
    "readiness": 7,
    "activity": 7
  }
}
```

#### GET /latest/{entity_id}
Get latest Oura metrics.

**Response:**
```json
{
  "sleep_score": 85,
  "readiness_score": 78,
  "hrv": 65.5,
  "resting_heart_rate": 58,
  "date": "2025-12-11"
}
```

---

### LinkedIn Connector

**Base URL:** `https://ingestion-linkedin-xeihvetbja-uc.a.run.app`

#### GET /auth
Initiate OAuth 2.0 flow for LinkedIn.

#### POST /sync-profile/{entity_id}
Sync LinkedIn profile.

**Response:**
```json
{
  "status": "success",
  "profile_synced": true
}
```

#### POST /sync-connections/{entity_id}
Sync LinkedIn connections.

**Response:**
```json
{
  "status": "success",
  "connections_synced": 487
}
```

#### POST /sync-activity/{entity_id}
Sync LinkedIn activity feed.

**Request:**
```json
{
  "days_back": 30
}
```

#### GET /profile/{entity_id}
Get stored LinkedIn profile.

#### GET /connections/{entity_id}
Get LinkedIn connections.

**Query Params:**
- `limit` (default: 50)
- `company` (filter by company)
- `location` (filter by location)

---

### Apple Watch Connector

**Base URL:** `https://ingestion-apple-watch-xeihvetbja-uc.a.run.app`

#### POST /authorize/{entity_id}
Authorize HealthKit access.

#### POST /sync-realtime/{entity_id}
Start real-time health data sync.

**Response:**
```json
{
  "status": "syncing",
  "stream_active": true
}
```

#### POST /sync-historical/{entity_id}
Sync historical health data.

**Request:**
```json
{
  "days_back": 30
}
```

#### GET /latest-metrics/{entity_id}
Get latest Apple Watch metrics.

**Response:**
```json
{
  "heart_rate": 72,
  "hrv": 65.5,
  "steps": 5420,
  "calories": 1850,
  "recorded_at": "2025-12-11T10:30:00Z"
}
```

#### POST /stop-sync/{entity_id}
Stop real-time sync.

---

## Analysis APIs

### Memory Engine

**Base URL:** `https://analysis-memory-xeihvetbja-uc.a.run.app`

#### POST /store
Store a memory.

**Request:**
```json
{
  "entity_id": "uuid",
  "memory_type": "email",
  "content": {...},
  "timestamp": "2025-12-11T10:00:00Z"
}
```

#### GET /retrieve/{entity_id}
Retrieve memories.

**Query Params:**
- `memory_type`
- `from_date`
- `to_date`
- `limit`

#### POST /search
Semantic search across memories.

**Request:**
```json
{
  "entity_id": "uuid",
  "query": "meetings about project X",
  "limit": 10
}
```

#### GET /timeline/{entity_id}
Get timeline of memories.

---

### DNA Engine

**Base URL:** `https://analysis-dna-xeihvetbja-uc.a.run.app`

#### POST /analyze/{entity_id}
Analyze memory and update DNA.

#### GET /profile/{entity_id}
Get complete DNA profile.

**Response:**
```json
{
  "entity_id": "uuid",
  "summary": "...",
  "goals": [...],
  "values": [...],
  "patterns": {...}
}
```

#### POST /update/{entity_id}
Manually update DNA.

#### GET /patterns/{entity_id}
Get detected patterns.

---

### Health & Wellness Engine

**Base URL:** `https://analysis-health-xeihvetbja-uc.a.run.app`

#### POST /calculate-readiness/{entity_id}
Calculate daily readiness score.

**Response:**
```json
{
  "readiness_score": 0.78,
  "sleep_score": 0.85,
  "hrv_score": 0.75,
  "recovery_score": 0.80,
  "activity_score": 0.72,
  "date": "2025-12-11"
}
```

#### GET /energy-patterns/{entity_id}
Get energy patterns by time of day.

**Response:**
```json
{
  "patterns": [
    {"hour": 9, "energy_level": 0.85, "optimal_for": "deep_work"},
    {"hour": 14, "energy_level": 0.65, "optimal_for": "meetings"}
  ]
}
```

#### POST /analyze-trends/{entity_id}
Analyze health trends.

#### GET /recommendations/{entity_id}
Get health recommendations.

---

### Social Context Engine

**Base URL:** `https://analysis-social-context-xeihvetbja-uc.a.run.app`

#### POST /analyze-relationship/{entity_id}/{connection_id}
Analyze specific relationship.

**Response:**
```json
{
  "overall_score": 0.75,
  "interaction_score": 0.80,
  "recency_score": 0.70,
  "mutual_connections_score": 0.75,
  "shared_experience_score": 0.80,
  "sentiment_score": 0.65
}
```

#### GET /relationship-scores/{entity_id}
Get all relationship scores.

#### POST /analyze-interactions/{entity_id}
Analyze interaction patterns.

#### GET /recommendations/{entity_id}
Get networking recommendations.

---

### Real-Time Health Monitor

**Base URL:** `https://analysis-realtime-health-xeihvetbja-uc.a.run.app`

#### POST /analyze-metrics/{entity_id}
Analyze latest health metrics.

#### GET /stress-level/{entity_id}
Get current stress level.

**Response:**
```json
{
  "stress_score": 35,
  "stress_category": "low",
  "heart_rate": 72,
  "hrv_value": 65.5,
  "recommendations": [
    "Maintain current activity level",
    "Stay hydrated"
  ]
}
```

#### GET /anomalies/{entity_id}
Get detected health anomalies.

#### GET /trends/{entity_id}
Get health trends.

**Query Params:**
- `days` (default: 7)

#### POST /calculate-baseline/{entity_id}
Calculate personal health baselines.

#### GET /alerts/{entity_id}
Get active health alerts.

---

## Intelligence APIs

### Orchestrator

**Base URL:** `https://intelligence-orchestrator-xeihvetbja-uc.a.run.app`

#### POST /execute-task
Execute a task across multiple services.

**Request:**
```json
{
  "entity_id": "uuid",
  "task_type": "morning_briefing",
  "parameters": {...}
}
```

#### GET /status
Get system status.

#### POST /coordinate
Coordinate multi-service actions.

---

### Briefing Agent

**Base URL:** `https://intelligence-briefing-xeihvetbja-uc.a.run.app`

#### POST /generate-briefing
Generate AI-powered meeting briefing.

**Request:**
```json
{
  "entity_id": "uuid",
  "meeting_id": "uuid",
  "meeting_time": "2025-12-11T14:00:00Z",
  "attendees": ["user@example.com"]
}
```

**Response:**
```json
{
  "briefing_id": "uuid",
  "meeting_title": "Team Meeting",
  "briefing_markdown": "# Meeting Briefing\n\n...",
  "key_points": [...],
  "recommended_preparation": [...]
}
```

#### GET /briefing/{briefing_id}
Get existing briefing.

---

### Context-Aware Scheduler

**Base URL:** `https://intelligence-scheduler-xeihvetbja-uc.a.run.app`

#### POST /find-optimal-slot
Find optimal time slot for task.

**Request:**
```json
{
  "entity_id": "uuid",
  "task_type": "deep_work",
  "duration_minutes": 120,
  "date_range": {
    "start": "2025-12-11",
    "end": "2025-12-15"
  }
}
```

**Response:**
```json
{
  "recommended_slots": [
    {
      "start_time": "2025-12-11T09:00:00Z",
      "end_time": "2025-12-11T11:00:00Z",
      "score": 0.92,
      "reasons": ["High energy", "No conflicts", "Optimal for deep work"]
    }
  ]
}
```

#### POST /optimize-schedule/{entity_id}
Optimize entire day schedule.

#### GET /recommendations/{entity_id}
Get scheduling recommendations.

---

### Network Intelligence

**Base URL:** `https://intelligence-network-xeihvetbja-uc.a.run.app`

#### GET /network-analysis/{entity_id}
Analyze professional network.

**Response:**
```json
{
  "total_connections": 487,
  "network_growth_rate": 5.2,
  "company_clusters": [...],
  "industry_clusters": [...],
  "location_clusters": [...],
  "top_connectors": [...]
}
```

#### GET /opportunities/{entity_id}
Detect career opportunities.

#### GET /introduction-suggestions/{entity_id}
Suggest valuable introductions.

#### GET /career-insights/{entity_id}
Get career path insights.

#### GET /skill-gaps/{entity_id}
Identify skill gaps.

---

### Wellness Dashboard

**Base URL:** `https://intelligence-wellness-xeihvetbja-uc.a.run.app`

#### GET /dashboard/{entity_id}
Get wellness dashboard data.

**Response:**
```json
{
  "wellness_score": 78,
  "today_overview": {
    "heart_rate": 72,
    "steps": 5420,
    "calories": 1850,
    "sleep_hours": 7.2,
    "stress_level": 35
  },
  "activity_summary": {...},
  "sleep_analysis": {...},
  "stress_recovery": {...}
}
```

#### GET /wellness-score/{entity_id}
Get wellness score breakdown.

#### GET /insights/{entity_id}
Get AI-powered wellness insights.

#### GET /goals/{entity_id}
Get health goals.

#### POST /set-goal/{entity_id}
Set health goal.

**Request:**
```json
{
  "goal_type": "steps",
  "target_value": 10000,
  "frequency": "daily"
}
```

#### GET /recommendations/{entity_id}
Get wellness recommendations.

#### GET /export/{entity_id}
Export health data.

**Query Params:**
- `format` (json, csv)
- `start_date`
- `end_date`

---

## Authentication

### API Key Authentication

Include API key in request header:
```
Authorization: Bearer {api_key}
```

### OAuth 2.0

For external integrations (Gmail, Calendar, LinkedIn):
1. Initiate OAuth flow via `/auth` endpoint
2. User authorizes access
3. Receive authorization code via callback
4. Exchange code for access token
5. Store token securely
6. Use token for API requests

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Entity ID is required",
    "details": {...}
  }
}
```

### HTTP Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Missing/invalid auth
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service down

---

## Rate Limits

### Default Limits

- **Per Service:** 1000 requests/hour
- **Per Entity:** 500 requests/hour
- **Burst:** 100 requests/minute

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1702300800
```

### Handling Rate Limits

When rate limited (429 response):
1. Check `X-RateLimit-Reset` header
2. Wait until reset time
3. Implement exponential backoff
4. Consider caching responses

---

*Last Updated: December 11, 2025*  
*Version: 3.0 - Conscious Organism*  
*For detailed service documentation, see ARCHITECTURE.md*
