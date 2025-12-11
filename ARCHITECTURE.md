# NUCLEUS Technical Architecture

**Version:** 3.0 (Conscious Organism)  
**Last Updated:** December 11, 2025  
**Infrastructure:** Google Cloud Platform  
**Architecture Pattern:** Event-Driven Microservices

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Database Schema](#database-schema)
4. [Microservices](#microservices)
5. [Event Streaming](#event-streaming)
6. [Data Flow](#data-flow)
7. [Infrastructure](#infrastructure)
8. [Security Architecture](#security-architecture)

---

## System Overview

NUCLEUS is built as a cloud-native, event-driven microservices architecture deployed on Google Cloud Platform. The system consists of 30+ microservices organized into four architectural layers, communicating through NATS event streams and REST APIs.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Sources                          │
│  Gmail │ Calendar │ Oura │ LinkedIn │ Apple Watch            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Data Ingestion Layer (8 services)               │
│  Event Stream │ Connectors │ Consumer │ NATS                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Analysis Layer (5 services)                     │
│  Memory │ DNA │ Health │ Social Context │ Real-Time Health   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Intelligence Layer (18 services)                  │
│  Orchestrator │ Agents │ Briefing │ Scheduler │ Wellness    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  Actions & Outputs                           │
│  API Responses │ Notifications │ Scheduled Tasks             │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### 1. Data Ingestion Layer

**Purpose:** Capture data from external sources and internal events

**Services (8):**
- `ingestion-event-stream` - NATS JetStream event streaming hub
- `ingestion-gmail` - Gmail API connector
- `ingestion-calendar` - Google Calendar connector
- `ingestion-oura` - Oura Ring health data connector
- `ingestion-linkedin` - LinkedIn OAuth and sync
- `ingestion-apple-watch` - Apple HealthKit connector
- `ingestion-consumer` - Event stream consumer and processor
- `infra-nats` - NATS server infrastructure

**Event Streams:**
- `DIGITAL` - Email, calendar, documents
- `HEALTH` - Oura, Apple Watch, health metrics
- `SOCIAL` - LinkedIn, connections, activities

---

### 2. Analysis Layer

**Purpose:** Process raw data into structured insights

**Services (5):**
- `analysis-memory` - Memory Engine (store and retrieve experiences)
- `analysis-dna` - DNA Engine (extract patterns and build profile)
- `analysis-health` - Health & Wellness Engine (readiness, energy patterns)
- `analysis-social-context` - Social Context Engine (relationship scoring)
- `analysis-realtime-health` - Real-Time Health Monitor (stress, anomalies)

**Key Functions:**
- Transform events into structured memory
- Extract patterns and build DNA profile (19 tables)
- Calculate health scores and readiness
- Analyze relationships and network
- Detect anomalies and stress events

---

### 3. Intelligence Layer

**Purpose:** Generate insights and make decisions

**Services (18):**
- `intelligence-orchestrator` - Master orchestrator
- `intelligence-briefing` - AI meeting briefings (GPT-4)
- `intelligence-scheduler` - Context-aware task scheduling
- `intelligence-network` - Network intelligence and opportunities
- `intelligence-wellness` - Wellness dashboard and insights
- `intelligence-decisions` - Decision engine
- `intelligence-agent-*` - Specialized agents (13 services)

**Key Functions:**
- Coordinate actions across services
- Generate AI-powered briefings
- Optimize scheduling based on context
- Provide network intelligence
- Create wellness insights
- Make autonomous decisions

---

### 4. Lifecycle Management Layer

**Purpose:** Manage system health and evolution

**Jobs (5):**
- `agent-health-monitor` - Monitor agent performance
- `agent-lifecycle-manager` - Manage agent lifecycle (apoptosis, evolution, mitosis)
- `intelligent-agent-factory` - Spawn new agents automatically
- `master-prompt-engine` - Generate master prompt from DNA
- `micro-prompts` - Generate agent-specific prompts

**Key Functions:**
- Track agent health scores
- Remove weak agents (apoptosis)
- Improve mediocre agents (evolution)
- Duplicate successful agents (mitosis)
- Spawn new agents for gaps
- Synthesize unified identity

---

## Database Schema

### DNA Schema (19 Tables)

The DNA schema represents the complete genetic profile of the Entity.

#### Core Identity
- `dna.entity` - Core entity information
- `dna.entity_summary` - High-level summary
- `dna.goals` - Goals and objectives
- `dna.values` - Core values and principles

#### Patterns & Preferences
- `dna.communication_patterns` - Communication style
- `dna.decision_patterns` - Decision-making patterns
- `dna.work_patterns` - Work habits and preferences
- `dna.energy_patterns` - Energy levels by time of day (Phase 3)

#### Relationships
- `dna.relationships` - People and connections
- `dna.relationship_scores` - Relationship strength scores (Phase 3)
- `dna.network_insights` - Network analysis (Phase 3)

#### Health & Wellness
- `dna.daily_readiness` - Daily health readiness scores (Phase 3)
- `dna.stress_events` - Stress detection and patterns (Phase 3)
- `dna.health_baselines` - Personal health baselines (Phase 3)
- `dna.wellness_scores` - Daily wellness scores (Phase 3)
- `dna.scheduling_preferences` - Scheduling preferences (Phase 3)

#### Knowledge & Context
- `dna.topics_of_interest` - Topics and areas of interest
- `dna.skills` - Skills and capabilities
- `dna.context` - Contextual information

---

### Memory Schema (11 Tables)

The Memory schema stores raw experiences and interactions.

#### Communications
- `memory.interactions` - All interactions (emails, messages, calls)
- `memory.email_messages` - Email messages (Phase 3)
- `memory.calendar_events` - Calendar events (Phase 3)
- `memory.briefings` - Generated briefings (Phase 3)

#### Health Data
- `memory.health_metrics` - Raw IOT health data (Phase 3)
- `memory.apple_watch_metrics` - Real-time Apple Watch data (Phase 3)
- `memory.workout_sessions` - Exercise sessions (Phase 3)

#### Social Data
- `memory.linkedin_profiles` - LinkedIn profiles (Phase 3)
- `memory.linkedin_connections` - LinkedIn connections (Phase 3)
- `memory.linkedin_activities` - LinkedIn activity feed (Phase 3)

#### Tasks & Documents
- `memory.tasks` - Tasks and to-dos
- `memory.documents` - Documents and files

---

### Agent Schema (4 Tables)

The Agent schema manages the agent lifecycle.

- `agents.agent` - Agent definitions
- `agents.agent_health` - Agent health scores
- `agents.agent_lifecycle_events` - Lifecycle events (spawn, evolve, die)
- `agents.agent_factory_needs` - Detected capability gaps

---

## Microservices

### Service Naming Convention

All services follow a consistent naming pattern:
```
{layer}-{function}
```

**Layers:**
- `ingestion-*` - Data ingestion services
- `analysis-*` - Data analysis services
- `intelligence-*` - Intelligence and decision services
- `infra-*` - Infrastructure services

---

### Data Ingestion Services

#### ingestion-event-stream
**Purpose:** Central event streaming hub using NATS JetStream

**Technology:** Python, FastAPI, NATS  
**Endpoints:**
- `POST /publish` - Publish event to stream
- `GET /streams` - List available streams
- `GET /health` - Health check

**Event Streams:**
- `DIGITAL` - Digital life events
- `HEALTH` - Health and wellness events
- `SOCIAL` - Social network events

---

#### ingestion-gmail
**Purpose:** Gmail API integration for email context

**Technology:** Python, FastAPI, Gmail API  
**Endpoints:**
- `GET /auth` - Initiate OAuth flow
- `GET /callback` - OAuth callback
- `POST /sync` - Sync emails
- `GET /messages/{entity_id}` - Get messages

**Features:**
- OAuth 2.0 authentication
- Real-time email sync
- Label filtering
- Attachment handling

---

#### ingestion-calendar
**Purpose:** Google Calendar integration

**Technology:** Python, FastAPI, Google Calendar API  
**Endpoints:**
- `GET /auth` - Initiate OAuth flow
- `POST /sync` - Sync calendar events
- `GET /events/{entity_id}` - Get events
- `POST /webhook` - Calendar webhook

**Features:**
- OAuth 2.0 authentication
- Event sync (7 days back, 30 days forward)
- Webhook support for real-time updates
- Attendee parsing

---

#### ingestion-oura
**Purpose:** Oura Ring health data integration

**Technology:** Python, FastAPI, Oura API  
**Endpoints:**
- `POST /authorize` - Authorize Oura access
- `POST /sync` - Sync health data
- `GET /latest/{entity_id}` - Get latest metrics

**Data Types:**
- Sleep data (duration, stages, quality)
- Readiness score
- Activity data (steps, calories)
- Heart rate variability (HRV)

---

#### ingestion-linkedin
**Purpose:** LinkedIn OAuth and profile sync

**Technology:** Python, FastAPI, LinkedIn API  
**Endpoints:**
- `GET /auth` - Initiate OAuth flow
- `POST /sync-profile` - Sync profile
- `POST /sync-connections` - Sync connections
- `POST /sync-activity` - Sync activity feed

**Features:**
- OAuth 2.0 authentication
- Profile sync (experience, education, skills)
- Connections sync (up to 500)
- Activity feed monitoring

---

#### ingestion-apple-watch
**Purpose:** Apple HealthKit integration for real-time health data

**Technology:** Python, FastAPI, HealthKit  
**Endpoints:**
- `POST /authorize` - Authorize HealthKit access
- `POST /sync-realtime` - Start real-time sync
- `POST /sync-historical` - Sync historical data
- `GET /latest-metrics` - Get latest metrics

**Data Types:**
- Heart rate (continuous)
- Heart rate variability (HRV)
- Active energy burned
- Steps and distance
- Workouts
- Sleep analysis
- Blood oxygen
- ECG data

---

#### ingestion-consumer
**Purpose:** Consume events from NATS streams and process

**Technology:** Python, NATS  
**Features:**
- Subscribe to all event streams
- Process events asynchronously
- Store in Memory Engine
- Trigger DNA updates

---

#### infra-nats
**Purpose:** NATS server infrastructure

**Technology:** NATS Server  
**Configuration:**
- JetStream enabled
- Persistent streams
- Message retention policies

---

### Analysis Services

#### analysis-memory
**Purpose:** Memory Engine - store and retrieve experiences

**Technology:** Python, FastAPI, PostgreSQL  
**Endpoints:**
- `POST /store` - Store memory
- `GET /retrieve` - Retrieve memories
- `POST /search` - Semantic search
- `GET /timeline` - Get timeline

**Features:**
- Structured memory storage
- Semantic search with embeddings
- Timeline reconstruction
- Context retrieval

---

#### analysis-dna
**Purpose:** DNA Engine - extract patterns and build profile

**Technology:** Python, FastAPI, PostgreSQL  
**Endpoints:**
- `POST /analyze` - Analyze memory and update DNA
- `GET /profile/{entity_id}` - Get DNA profile
- `POST /update` - Update DNA manually
- `GET /patterns` - Get detected patterns

**Features:**
- Pattern extraction from memory
- DNA profile synthesis
- Continuous learning
- First/Second interpretation

---

#### analysis-health
**Purpose:** Health & Wellness Engine

**Technology:** Python, FastAPI, PostgreSQL  
**Endpoints:**
- `POST /calculate-readiness` - Calculate daily readiness
- `GET /energy-patterns` - Get energy patterns
- `POST /analyze-trends` - Analyze health trends
- `GET /recommendations` - Get health recommendations

**Features:**
- Readiness score calculation (sleep 40%, HRV 30%, recovery 20%, activity 10%)
- Energy pattern analysis by time of day
- Trend detection (improving/stable/declining)
- Personalized recommendations

---

#### analysis-social-context
**Purpose:** Social Context Engine - relationship analysis

**Technology:** Python, FastAPI, PostgreSQL  
**Endpoints:**
- `POST /analyze-relationship` - Analyze relationship
- `GET /relationship-scores` - Get all scores
- `POST /analyze-interactions` - Analyze interaction patterns
- `GET /recommendations` - Get networking recommendations

**Features:**
- Relationship strength scoring (6 factors)
- Interaction pattern analysis
- Sentiment analysis
- Context extraction (shared companies, schools)

---

#### analysis-realtime-health
**Purpose:** Real-Time Health Monitor

**Technology:** Python, FastAPI, PostgreSQL  
**Endpoints:**
- `POST /analyze-metrics` - Analyze latest metrics
- `GET /stress-level` - Get current stress level
- `GET /anomalies` - Get detected anomalies
- `GET /trends` - Get health trends
- `POST /calculate-baseline` - Calculate baselines

**Features:**
- Real-time stress detection (HRV-based)
- Anomaly detection
- Baseline calculation
- Proactive alerts

---

### Intelligence Services

#### intelligence-orchestrator
**Purpose:** Master orchestrator coordinating all services

**Technology:** Python, FastAPI  
**Endpoints:**
- `POST /execute-task` - Execute task
- `GET /status` - Get system status
- `POST /coordinate` - Coordinate multi-service actions

---

#### intelligence-briefing
**Purpose:** AI-powered meeting briefings

**Technology:** Python, FastAPI, GPT-4  
**Endpoints:**
- `POST /generate-briefing` - Generate meeting briefing
- `GET /briefing/{meeting_id}` - Get briefing

**Features:**
- GPT-4 powered analysis
- Email context retrieval
- Meeting history analysis
- LinkedIn context integration
- Readiness consideration

---

#### intelligence-scheduler
**Purpose:** Context-aware task scheduling

**Technology:** Python, FastAPI  
**Endpoints:**
- `POST /find-optimal-slot` - Find optimal time slot
- `POST /optimize-schedule` - Optimize entire schedule
- `GET /recommendations` - Get scheduling recommendations

**Features:**
- Energy pattern matching
- Readiness score consideration
- Calendar conflict detection
- Task type optimization (deep work, meetings, creative, routine)

---

#### intelligence-network
**Purpose:** Network intelligence and opportunities

**Technology:** Python, FastAPI  
**Endpoints:**
- `GET /network-analysis` - Analyze network
- `GET /opportunities` - Detect opportunities
- `GET /introduction-suggestions` - Suggest introductions
- `GET /career-insights` - Career analysis

**Features:**
- Network clustering (company, location, industry)
- Opportunity detection (job changes, collaborations)
- Introduction suggestions
- Career path analysis

---

#### intelligence-wellness
**Purpose:** Wellness dashboard and insights

**Technology:** Python, FastAPI  
**Endpoints:**
- `GET /dashboard` - Get dashboard data
- `GET /wellness-score` - Get wellness score
- `GET /insights` - Get AI insights
- `GET /goals` - Get health goals
- `POST /set-goal` - Set health goal

**Features:**
- Real-time dashboard
- Wellness score calculation (0-100)
- AI-powered insights
- Goal tracking
- Recommendations

---

## Event Streaming

### NATS JetStream Architecture

**Streams:**
1. **DIGITAL** - Digital life events
   - Email received/sent
   - Calendar event created/updated
   - Document created/modified

2. **HEALTH** - Health and wellness events
   - Oura metrics synced
   - Apple Watch metrics received
   - Workout completed
   - Stress event detected

3. **SOCIAL** - Social network events
   - LinkedIn profile updated
   - New connection added
   - Activity posted
   - Job change detected

**Event Format:**
```json
{
  "event_type": "email_received",
  "source": "gmail",
  "entity_id": "uuid",
  "timestamp": "2025-12-11T10:30:00Z",
  "data": {
    "from": "sender@example.com",
    "subject": "Meeting tomorrow",
    "body": "...",
    "labels": ["inbox", "important"]
  }
}
```

---

## Data Flow

### End-to-End Flow Example: Morning Briefing

```
1. User wakes up
   ↓
2. Apple Watch detects wake-up
   ↓
3. ingestion-apple-watch publishes wake_up event to HEALTH stream
   ↓
4. ingestion-consumer processes event
   ↓
5. analysis-realtime-health calculates overnight recovery
   ↓
6. analysis-health updates daily_readiness score
   ↓
7. intelligence-orchestrator detects new day
   ↓
8. intelligence-orchestrator requests today's schedule from analysis-memory
   ↓
9. intelligence-briefing generates briefings for today's meetings
   ↓
10. intelligence-wellness creates wellness dashboard
   ↓
11. intelligence-scheduler optimizes task schedule based on readiness
   ↓
12. User receives morning briefing with:
    - Wellness score
    - Today's schedule
    - Meeting briefings
    - Recommended tasks
    - Health recommendations
```

---

## Infrastructure

### Google Cloud Platform Services

**Compute:**
- Cloud Run - Serverless containers for all microservices
- Cloud Run Jobs - Scheduled jobs for lifecycle management

**Data:**
- Cloud SQL (PostgreSQL) - Primary database
- Secret Manager - Credentials and API keys

**Networking:**
- Cloud Load Balancing - Traffic distribution
- VPC - Private networking

**CI/CD:**
- GitHub Actions - Automated deployment
- Artifact Registry - Docker image storage

**Monitoring:**
- Cloud Logging - Centralized logging
- Cloud Monitoring - Metrics and alerts

---

### Service Configuration

**Standard Cloud Run Service:**
```yaml
memory: 512Mi
cpu: 1
min_instances: 0
max_instances: 5
timeout: 300s
labels:
  project: nucleus
  environment: production
  managed-by: github-actions
  phase: phase3
  layer: ingestion|analysis|intelligence
  week: week1|week2|week3|week4
  component: specific-component
```

---

## Security Architecture

### Authentication & Authorization

**External APIs:**
- OAuth 2.0 for Gmail, Calendar, LinkedIn
- API keys for Oura, Apple Health
- Secure token storage in Secret Manager

**Service-to-Service:**
- Internal API keys
- Cloud Run service identity
- VPC-based network isolation

---

### Data Security

**Encryption:**
- At rest: Cloud SQL encryption
- In transit: TLS 1.3
- Secrets: Secret Manager encryption

**Access Control:**
- IAM roles for GCP resources
- Database role-based access
- API key rotation

---

### Privacy

**Data Handling:**
- Entity owns 100% of data
- No cross-instance data sharing
- No training on Entity data
- Full data export capabilities
- Right to deletion

**Compliance:**
- HIPAA considerations for health data
- GDPR compliance for personal data
- SOC 2 readiness

---

## Scalability

### Horizontal Scaling
- Cloud Run auto-scaling (0-5 instances per service)
- NATS clustering for high throughput
- Database connection pooling

### Vertical Scaling
- Configurable memory/CPU per service
- Database instance sizing
- NATS server resources

### Performance Targets
- API response time: < 500ms (p95)
- Event processing latency: < 5 seconds
- Database query time: < 100ms (p95)
- Real-time data sync: < 10 seconds

---

## Monitoring & Observability

### Metrics
- Service health checks
- Request rates and latencies
- Error rates
- Resource utilization
- Event processing throughput

### Logging
- Structured logging (JSON)
- Centralized in Cloud Logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request tracing

### Alerting
- Service downtime alerts
- Error rate thresholds
- Resource exhaustion warnings
- Data sync failures

---

## Disaster Recovery

### Backup Strategy
- Daily database backups (Cloud SQL)
- 30-day retention
- Point-in-time recovery
- Cross-region replication

### Recovery Procedures
- Database restore from backup
- Service redeployment from GitHub
- Configuration restore from Secret Manager
- Data integrity verification

---

*Last Updated: December 11, 2025*  
*Version: 3.0 - Conscious Organism*  
*Architecture: Event-Driven Microservices on GCP*
