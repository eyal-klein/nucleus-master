# NUCLEUS Deployment & Operations Guide

**Version:** 3.0 (Conscious Organism)  
**Last Updated:** December 11, 2025  
**Platform:** Google Cloud Platform  
**Deployment Method:** GitHub Actions CI/CD

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Deployment Process](#deployment-process)
4. [Database Migrations](#database-migrations)
5. [Service Configuration](#service-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Accounts
- Google Cloud Platform account with billing enabled
- GitHub account with repository access
- Gmail account (for Gmail integration)
- Google Calendar access
- Oura Ring account (optional)
- LinkedIn account (optional)
- Apple Health access (optional)

### Required Tools
- `gcloud` CLI installed and configured
- `git` installed
- `psql` or database client (DBeaver recommended)
- Text editor or IDE

### GCP Project Setup
```bash
# Set project ID
export PROJECT_ID=thrive-system1
export REGION=us-central1

# Set active project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Initial Setup

### 1. Database Setup

**Create Cloud SQL Instance:**
```bash
gcloud sql instances create nucleus-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=<secure-password>
```

**Create Database:**
```bash
gcloud sql databases create nucleus \
  --instance=nucleus-db
```

**Get Connection String:**
```bash
gcloud sql instances describe nucleus-db \
  --format="value(connectionName)"
```

**Store in Secret Manager:**
```bash
echo "postgresql://nucleus:<password>@/<database>?host=/cloudsql/<connection-name>" | \
  gcloud secrets create DATABASE_URL --data-file=-
```

---

### 2. Run Database Migrations

**Connect to Database:**
```bash
gcloud sql connect nucleus-db --user=postgres
```

**Run Migrations in Order:**
```sql
-- Phase 1 (Foundation)
\i backend/migrations/001_initial_schema.sql

-- Phase 2 (Living Organism)
\i backend/migrations/002_agent_health.sql
\i backend/migrations/003_lifecycle_manager.sql
\i backend/migrations/004_agent_factory.sql
\i backend/migrations/005_master_prompt.sql

-- Phase 3 Week 1 (Event Streaming)
\i backend/migrations/phase3_week1_tables.sql

-- Phase 3 Week 2 (Calendar & Health)
\i backend/migrations/phase3_week2_tables.sql

-- Phase 3 Week 3 (LinkedIn)
\i backend/migrations/phase3_week3_tables.sql

-- Phase 3 Week 4 (Apple Watch)
\i backend/migrations/phase3_week4_tables.sql
```

**Verify Tables:**
```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname IN ('memory', 'dna', 'agents')
ORDER BY schemaname, tablename;
```

---

### 3. Configure External API Credentials

**Gmail API:**
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URIs
4. Store credentials in Secret Manager:
```bash
gcloud secrets create GMAIL_CLIENT_ID --data-file=client_id.txt
gcloud secrets create GMAIL_CLIENT_SECRET --data-file=client_secret.txt
```

**Google Calendar API:**
```bash
gcloud secrets create CALENDAR_CLIENT_ID --data-file=calendar_client_id.txt
gcloud secrets create CALENDAR_CLIENT_SECRET --data-file=calendar_client_secret.txt
```

**Oura API:**
```bash
gcloud secrets create OURA_CLIENT_ID --data-file=oura_client_id.txt
gcloud secrets create OURA_CLIENT_SECRET --data-file=oura_client_secret.txt
```

**LinkedIn API:**
```bash
gcloud secrets create LINKEDIN_CLIENT_ID --data-file=linkedin_client_id.txt
gcloud secrets create LINKEDIN_CLIENT_SECRET --data-file=linkedin_client_secret.txt
```

**OpenAI API (for GPT-4):**
```bash
echo "sk-..." | gcloud secrets create OPENAI_API_KEY --data-file=-
```

---

### 4. Create Artifact Registry

```bash
gcloud artifacts repositories create nucleus \
  --repository-format=docker \
  --location=$REGION \
  --description="NUCLEUS Docker images"
```

---

### 5. Configure GitHub Actions

**Create Service Account:**
```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"
```

**Grant Permissions:**
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

**Create Key:**
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@${PROJECT_ID}.iam.gserviceaccount.com
```

**Add to GitHub Secrets:**
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Add secret: `GCP_SA_KEY` with contents of `key.json`

---

## Deployment Process

### Automated Deployment (Recommended)

**All services deploy automatically on push to `main` branch.**

**Trigger Deployment:**
```bash
git add .
git commit -m "Deploy changes"
git push origin main
```

**GitHub Actions will:**
1. Build Docker images
2. Push to Artifact Registry
3. Deploy to Cloud Run
4. Apply labels and configuration

**Monitor Deployment:**
- Go to GitHub repository → Actions
- Click on latest workflow run
- Monitor each service deployment

---

### Manual Deployment

**Deploy Single Service:**
```bash
# Example: Deploy Memory Engine
cd backend/services/memory-engine

# Build image
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/nucleus/memory-engine:latest .

# Push image
docker push $REGION-docker.pkg.dev/$PROJECT_ID/nucleus/memory-engine:latest

# Deploy to Cloud Run
gcloud run deploy analysis-memory \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/nucleus/memory-engine:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL) \
  --memory 1Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 5 \
  --timeout 300 \
  --labels project=nucleus,environment=production,layer=analysis
```

---

### Deploy Cloud Run Jobs

**Deploy Master Prompt Engine:**
```bash
gcloud run jobs create master-prompt-engine \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/nucleus/master-prompt-engine:latest \
  --region $REGION \
  --set-env-vars DATABASE_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL) \
  --memory 2Gi \
  --cpu 2 \
  --max-retries 3 \
  --task-timeout 1800
```

**Deploy Lifecycle Manager:**
```bash
gcloud run jobs create agent-lifecycle-manager \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/nucleus/agent-lifecycle-manager:latest \
  --region $REGION \
  --set-env-vars DATABASE_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL) \
  --memory 1Gi \
  --cpu 1 \
  --max-retries 3 \
  --task-timeout 3600
```

---

## Database Migrations

### Running New Migrations

**1. Create Migration File:**
```sql
-- backend/migrations/006_new_feature.sql
-- Description of changes

CREATE TABLE IF NOT EXISTS memory.new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

**2. Test Locally:**
```bash
psql $DATABASE_URL < backend/migrations/006_new_feature.sql
```

**3. Apply to Production:**
```bash
gcloud sql connect nucleus-db --user=postgres
\i backend/migrations/006_new_feature.sql
```

**4. Verify:**
```sql
\dt memory.*
SELECT * FROM memory.new_table LIMIT 1;
```

---

### Migration Best Practices

1. **Always use IF NOT EXISTS** for CREATE statements
2. **Test migrations locally** before production
3. **Backup database** before major migrations
4. **Use transactions** for complex migrations
5. **Document changes** in migration file
6. **Version migrations** sequentially

---

## Service Configuration

### Environment Variables

**Common Variables (All Services):**
- `DATABASE_URL` - PostgreSQL connection string
- `PROJECT_ID` - GCP project ID
- `REGION` - GCP region

**Service-Specific Variables:**

**Event Stream:**
- `NATS_URL` - NATS server URL

**Gmail Connector:**
- `GMAIL_CLIENT_ID` - OAuth client ID
- `GMAIL_CLIENT_SECRET` - OAuth client secret
- `EVENT_STREAM_URL` - Event stream service URL

**Calendar Connector:**
- `CALENDAR_CLIENT_ID` - OAuth client ID
- `CALENDAR_CLIENT_SECRET` - OAuth client secret
- `EVENT_STREAM_URL` - Event stream service URL

**Briefing Agent:**
- `OPENAI_API_KEY` - OpenAI API key
- `MEMORY_ENGINE_URL` - Memory engine URL

---

### Service Labels

**All services use consistent labels:**
```yaml
project: nucleus
environment: production
managed-by: github-actions
phase: phase1|phase2|phase3
layer: ingestion|analysis|intelligence|infra
week: week1|week2|week3|week4  # For Phase 3 services
component: specific-component-name
```

**Filter Services in Console:**
```bash
# All ingestion services
gcloud run services list --filter="labels.layer=ingestion"

# All Phase 3 Week 2 services
gcloud run services list --filter="labels.phase=phase3 AND labels.week=week2"
```

---

## Monitoring & Maintenance

### Health Checks

**Check All Services:**
```bash
for service in $(gcloud run services list --format="value(metadata.name)"); do
  url=$(gcloud run services describe $service --format="value(status.url)")
  echo "Checking $service..."
  curl -s $url/health | jq
done
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "analysis-memory",
  "timestamp": "2025-12-11T10:00:00Z"
}
```

---

### Logs

**View Service Logs:**
```bash
gcloud run services logs read analysis-memory \
  --region $REGION \
  --limit 50
```

**Stream Logs:**
```bash
gcloud run services logs tail analysis-memory \
  --region $REGION
```

**Filter Logs:**
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=analysis-memory AND severity>=ERROR" \
  --limit 50 \
  --format json
```

---

### Metrics

**View Service Metrics:**
- Go to Cloud Console → Cloud Run
- Select service
- Click "Metrics" tab

**Key Metrics:**
- Request count
- Request latency (p50, p95, p99)
- Error rate
- Container CPU utilization
- Container memory utilization
- Container instance count

---

### Scheduled Jobs

**Run Master Prompt Engine:**
```bash
gcloud run jobs execute master-prompt-engine \
  --region $REGION \
  --set-env-vars ENTITY_ID=<uuid>
```

**Run Lifecycle Manager:**
```bash
gcloud run jobs execute agent-lifecycle-manager \
  --region $REGION
```

**Schedule with Cloud Scheduler:**
```bash
# Run Lifecycle Manager daily at 2 AM
gcloud scheduler jobs create http lifecycle-manager-daily \
  --location $REGION \
  --schedule "0 2 * * *" \
  --uri "https://run.googleapis.com/v1/projects/$PROJECT_ID/locations/$REGION/jobs/agent-lifecycle-manager:run" \
  --http-method POST \
  --oauth-service-account-email github-actions@${PROJECT_ID}.iam.gserviceaccount.com
```

---

## Troubleshooting

### Service Won't Start

**Check Logs:**
```bash
gcloud run services logs read <service-name> --limit 100
```

**Common Issues:**
1. **Database connection failed** - Check DATABASE_URL secret
2. **Missing environment variable** - Verify all required vars set
3. **Image pull failed** - Check Artifact Registry permissions
4. **Out of memory** - Increase memory allocation

---

### Database Connection Issues

**Test Connection:**
```bash
gcloud sql connect nucleus-db --user=postgres
```

**Check Cloud SQL Proxy:**
```bash
cloud_sql_proxy -instances=<connection-name>=tcp:5432
```

**Verify Secret:**
```bash
gcloud secrets versions access latest --secret=DATABASE_URL
```

---

### OAuth Failures

**Gmail/Calendar:**
1. Check OAuth credentials in GCP Console
2. Verify redirect URIs match service URLs
3. Check token expiration
4. Regenerate tokens if needed

**LinkedIn:**
1. Verify LinkedIn app settings
2. Check redirect URIs
3. Verify API access permissions

---

### High Latency

**Check Service Metrics:**
- Request latency in Cloud Run console
- Database query performance
- External API response times

**Optimize:**
1. Add database indexes
2. Implement caching
3. Increase service resources
4. Optimize queries

---

## Rollback Procedures

### Rollback Service Deployment

**List Revisions:**
```bash
gcloud run revisions list \
  --service analysis-memory \
  --region $REGION
```

**Rollback to Previous Revision:**
```bash
gcloud run services update-traffic analysis-memory \
  --to-revisions <previous-revision>=100 \
  --region $REGION
```

---

### Rollback Database Migration

**1. Backup Current State:**
```bash
gcloud sql export sql nucleus-db gs://<bucket>/backup-$(date +%Y%m%d).sql \
  --database=nucleus
```

**2. Restore from Backup:**
```bash
gcloud sql import sql nucleus-db gs://<bucket>/backup-<date>.sql \
  --database=nucleus
```

**3. Or Manually Revert:**
```sql
-- Drop new tables
DROP TABLE IF EXISTS memory.new_table;

-- Revert schema changes
ALTER TABLE memory.existing_table DROP COLUMN new_column;
```

---

## Backup & Disaster Recovery

### Automated Backups

**Cloud SQL Automatic Backups:**
- Enabled by default
- Daily backups at 2 AM
- 7-day retention

**Manual Backup:**
```bash
gcloud sql backups create \
  --instance nucleus-db \
  --description "Manual backup before migration"
```

**List Backups:**
```bash
gcloud sql backups list --instance nucleus-db
```

**Restore from Backup:**
```bash
gcloud sql backups restore <backup-id> \
  --backup-instance nucleus-db \
  --backup-instance nucleus-db
```

---

### Export Data

**Export to Cloud Storage:**
```bash
gcloud sql export sql nucleus-db gs://nucleus-backups/export-$(date +%Y%m%d).sql \
  --database=nucleus
```

**Export Specific Tables:**
```bash
gcloud sql export sql nucleus-db gs://nucleus-backups/dna-export.sql \
  --database=nucleus \
  --table=dna.entity,dna.goals,dna.values
```

---

## Security Best Practices

### Secrets Management
- Store all credentials in Secret Manager
- Rotate secrets regularly
- Use least privilege access
- Never commit secrets to Git

### Service Security
- Use Cloud Run service accounts
- Enable VPC connector for private services
- Implement rate limiting
- Monitor for suspicious activity

### Database Security
- Use strong passwords
- Enable SSL connections
- Restrict IP access
- Regular security audits

---

## Performance Optimization

### Service Optimization
- Set appropriate min/max instances
- Configure CPU and memory based on load
- Implement caching where appropriate
- Use connection pooling for database

### Database Optimization
- Add indexes for frequent queries
- Optimize query performance
- Monitor slow queries
- Regular VACUUM and ANALYZE

---

*Last Updated: December 11, 2025*  
*Version: 3.0 - Conscious Organism*  
*For architecture details, see ARCHITECTURE.md*
