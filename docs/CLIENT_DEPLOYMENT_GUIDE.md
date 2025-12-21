# NUCLEUS Client Deployment Guide

**Version:** 1.1.0  
**Last Updated:** December 21, 2025  
**Template:** NUCLEUS-V1

---

## Overview

This guide walks you through deploying a new NUCLEUS instance for a client. The process takes approximately **2-3 hours** for the first deployment and **30-45 minutes** for subsequent deployments.

---

## Prerequisites

### Required Access
- [ ] GitHub account with repository creation permissions
- [ ] GCP project with Owner or Editor role
- [ ] GCP billing account linked
- [ ] GitHub Actions enabled

### Required Tools
- [ ] Git CLI installed
- [ ] Google Cloud SDK (`gcloud`) installed
- [ ] GitHub CLI (`gh`) installed (optional but recommended)
- [ ] Docker installed (for local testing)

### Required Information
- [ ] Client name (e.g., "ABC Corp")
- [ ] Client GCP project ID (e.g., "abc-corp-nucleus-prod")
- [ ] Deployment region (default: `me-west1`)
- [ ] Client domain (if custom domain needed)

---

## Deployment Process

### Step 1: Create Client GCP Project

```bash
# Set variables
export CLIENT_NAME="ABC Corp"
export CLIENT_PROJECT_ID="abc-corp-nucleus-prod"
export BILLING_ACCOUNT_ID="YOUR-BILLING-ACCOUNT-ID"
export REGION="me-west1"

# Create project
gcloud projects create $CLIENT_PROJECT_ID \
  --name="$CLIENT_NAME - NUCLEUS" \
  --labels=client=$(echo $CLIENT_NAME | tr '[:upper:]' '[:lower:]' | tr ' ' '-'),environment=production,managed-by=nucleus

# Link billing
gcloud billing projects link $CLIENT_PROJECT_ID \
  --billing-account=$BILLING_ACCOUNT_ID

# Set as active project
gcloud config set project $CLIENT_PROJECT_ID
```

**Validation:**
```bash
gcloud projects describe $CLIENT_PROJECT_ID
```

---

### Step 2: Enable Required GCP APIs

```bash
# Enable all required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$CLIENT_PROJECT_ID
```

**Validation:**
```bash
gcloud services list --enabled --project=$CLIENT_PROJECT_ID
```

---

### Step 3: Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployment" \
  --project=$CLIENT_PROJECT_ID

# Grant necessary roles
gcloud projects add-iam-policy-binding $CLIENT_PROJECT_ID \
  --member="serviceAccount:github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $CLIENT_PROJECT_ID \
  --member="serviceAccount:github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $CLIENT_PROJECT_ID \
  --member="serviceAccount:github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding $CLIENT_PROJECT_ID \
  --member="serviceAccount:github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create and download key
gcloud iam service-accounts keys create ~/github-actions-key.json \
  --iam-account=github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com
```

**⚠️ IMPORTANT:** Save `github-actions-key.json` securely. You'll need it for GitHub Secrets.

---

### Step 4: Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create nucleus \
  --repository-format=docker \
  --location=$REGION \
  --description="NUCLEUS container images" \
  --project=$CLIENT_PROJECT_ID
```

**Validation:**
```bash
gcloud artifacts repositories list --project=$CLIENT_PROJECT_ID
```

---

### Step 5: Create Pub/Sub Topics

```bash
# Create main event topic
gcloud pubsub topics create nucleus-digital-events \
  --project=$CLIENT_PROJECT_ID

# Create subscriptions (if needed)
gcloud pubsub subscriptions create nucleus-events-sub \
  --topic=nucleus-digital-events \
  --project=$CLIENT_PROJECT_ID
```

**Validation:**
```bash
gcloud pubsub topics list --project=$CLIENT_PROJECT_ID
```

---

### Step 6: Initialize Firestore Database

```bash
# Create Firestore database in native mode
gcloud firestore databases create \
  --location=$REGION \
  --project=$CLIENT_PROJECT_ID
```

**Validation:**
```bash
gcloud firestore databases describe --project=$CLIENT_PROJECT_ID
```

---

### Step 7: Clone and Configure Repository

```bash
# Clone the master template
git clone https://github.com/eyal-klein/NUCLEUS-V1.git ${CLIENT_PROJECT_ID}
cd ${CLIENT_PROJECT_ID}

# Create new repository on GitHub
gh repo create ${CLIENT_PROJECT_ID} --private --source=. --remote=origin --push

# Or manually:
# 1. Create repo on GitHub: https://github.com/new
# 2. Update remote:
git remote set-url origin https://github.com/YOUR-ORG/${CLIENT_PROJECT_ID}.git
git push -u origin main
```

---

### Step 8: Configure GitHub Secrets

```bash
# Navigate to: https://github.com/YOUR-ORG/${CLIENT_PROJECT_ID}/settings/secrets/actions

# Add the following secrets:
```

| Secret Name | Value | Source |
|------------|-------|--------|
| `GCP_PROJECT_ID` | `abc-corp-nucleus-prod` | Your client project ID |
| `GCP_SA_KEY` | Contents of `github-actions-key.json` | Service account key |
| `GOOGLE_CLIENT_ID` | OAuth client ID | Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | Google Cloud Console |

**Using GitHub CLI:**
```bash
gh secret set GCP_PROJECT_ID --body "$CLIENT_PROJECT_ID"
gh secret set GCP_SA_KEY < ~/github-actions-key.json
```

---

### Step 9: Update Configuration Files

#### Update `.github/workflows/*.yml`

**⚠️ CRITICAL:** Verify all workflow files have correct project ID:

```bash
# Check all workflows reference the secret correctly
grep -r "GCP_PROJECT_ID" .github/workflows/

# Should see:
# PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
```

#### Update Environment-Specific Configs

Create `config/production.env`:
```bash
# GCP Configuration
PROJECT_ID=${CLIENT_PROJECT_ID}
GCP_PROJECT_ID=${CLIENT_PROJECT_ID}
REGION=${REGION}

# Pub/Sub
PUBSUB_TOPIC=nucleus-digital-events

# Service URLs (will be updated after first deployment)
EVENT_STREAM_URL=https://ingestion-event-stream-<hash>.a.run.app
ORCHESTRATOR_URL=https://orchestrator-<hash>.a.run.app
```

---

### Step 10: Deploy Services

#### Option A: Deploy All Services (Recommended for first deployment)

```bash
# Trigger all workflows manually
gh workflow run deploy-orchestrator.yml
gh workflow run deploy-event-consumer.yml
gh workflow run deploy-gmail-connector.yml
gh workflow run deploy-calendar-connector.yml
# ... (repeat for all services)
```

#### Option B: Deploy via Git Push

```bash
# Push to main branch to trigger deployments
git push origin main
```

#### Option C: Deploy Specific Service

```bash
# Deploy only one service
gh workflow run deploy-gmail-connector.yml
```

---

### Step 11: Verify Deployments

```bash
# List all Cloud Run services
gcloud run services list --project=$CLIENT_PROJECT_ID --region=$REGION

# Check service status
gcloud run services describe gmail-connector \
  --project=$CLIENT_PROJECT_ID \
  --region=$REGION \
  --format="value(status.url,status.conditions)"

# View logs
gcloud run services logs read gmail-connector \
  --project=$CLIENT_PROJECT_ID \
  --region=$REGION \
  --limit=50
```

**Expected Output:**
```
✅ All services show status: READY
✅ No error logs
✅ Services respond to health checks
```

---

### Step 12: Configure OAuth (Gmail & Calendar)

#### Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select client project: `abc-corp-nucleus-prod`
3. Navigate to: **APIs & Services** → **Credentials**
4. Click: **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Name: `NUCLEUS Gmail Connector`
7. Authorized redirect URIs:
   ```
   https://gmail-connector-<hash>.a.run.app/callback
   https://calendar-connector-<hash>.a.run.app/callback
   ```
8. Click **Create**
9. Copy **Client ID** and **Client Secret**

#### Update GitHub Secrets

```bash
gh secret set GOOGLE_CLIENT_ID --body "YOUR-CLIENT-ID"
gh secret set GOOGLE_CLIENT_SECRET --body "YOUR-CLIENT-SECRET"
```

#### Redeploy Connectors

```bash
gh workflow run deploy-gmail-connector.yml
gh workflow run deploy-calendar-connector.yml
```

---

### Step 13: Test End-to-End Flow

#### Test Gmail Connector

```bash
# Get service URL
GMAIL_URL=$(gcloud run services describe gmail-connector \
  --project=$CLIENT_PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

# Initiate OAuth
curl "$GMAIL_URL/auth?entity_id=test-user-001"

# Follow OAuth flow in browser
# After auth, trigger sync
curl -X POST "$GMAIL_URL/sync" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "test-user-001", "max_results": 10}'
```

#### Test Calendar Connector

```bash
# Get service URL
CALENDAR_URL=$(gcloud run services describe calendar-connector \
  --project=$CLIENT_PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

# Initiate OAuth
curl "$CALENDAR_URL/auth?entity_id=test-user-001"

# After auth, trigger sync
curl -X POST "$CALENDAR_URL/sync" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "test-user-001", "days_past": 7, "days_future": 30}'
```

#### Verify Pub/Sub Messages

```bash
# Pull messages from subscription
gcloud pubsub subscriptions pull nucleus-events-sub \
  --project=$CLIENT_PROJECT_ID \
  --limit=10 \
  --auto-ack
```

**Expected:** Messages with `event_type`, `entity_id`, `source` attributes

---

## Post-Deployment Checklist

### Infrastructure
- [ ] All GCP APIs enabled
- [ ] Service account created with correct permissions
- [ ] Artifact Registry repository created
- [ ] Pub/Sub topics and subscriptions created
- [ ] Firestore database initialized

### GitHub
- [ ] Repository cloned and pushed
- [ ] All secrets configured
- [ ] Workflows validated
- [ ] Branch protection rules set (optional)

### Services
- [ ] All Cloud Run services deployed
- [ ] All services show status: READY
- [ ] No errors in logs
- [ ] Health checks passing

### Integration
- [ ] OAuth credentials created
- [ ] Gmail connector authenticated
- [ ] Calendar connector authenticated
- [ ] Pub/Sub messages flowing
- [ ] Events stored in Firestore

### Security
- [ ] Service account key stored securely
- [ ] GitHub secrets configured
- [ ] OAuth credentials restricted to correct URLs
- [ ] No hardcoded credentials in code

---

## Troubleshooting

### Service Won't Start

**Error:** `ValueError: PROJECT_ID environment variable is required`

**Solution:**
```bash
# Verify secret is set
gh secret list | grep GCP_PROJECT_ID

# If missing, set it:
gh secret set GCP_PROJECT_ID --body "$CLIENT_PROJECT_ID"

# Redeploy service
gh workflow run deploy-SERVICE-NAME.yml
```

---

### OAuth Callback Error

**Error:** `redirect_uri_mismatch`

**Solution:**
1. Get actual Cloud Run URL:
   ```bash
   gcloud run services describe gmail-connector \
     --project=$CLIENT_PROJECT_ID \
     --region=$REGION \
     --format="value(status.url)"
   ```
2. Update OAuth credentials in Google Cloud Console
3. Add exact URL with `/callback` suffix

---

### Pub/Sub Messages Not Flowing

**Solution:**
```bash
# Check topic exists
gcloud pubsub topics list --project=$CLIENT_PROJECT_ID

# Check service has permissions
gcloud projects get-iam-policy $CLIENT_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com"

# View service logs
gcloud run services logs read gmail-connector \
  --project=$CLIENT_PROJECT_ID \
  --region=$REGION \
  --limit=100
```

---

## Maintenance

### Updating to New Template Version

```bash
# Add upstream remote (one-time)
git remote add upstream https://github.com/eyal-klein/NUCLEUS-V1.git

# Fetch latest changes
git fetch upstream

# Merge changes (review carefully!)
git merge upstream/main

# Resolve conflicts if any
# Test thoroughly
# Push to client repo
git push origin main
```

---

## Cost Estimation

### Typical Monthly Costs (Single User)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run | 100K requests | $5-10 |
| Firestore | 10GB storage | $1-2 |
| Pub/Sub | 1M messages | $0.40 |
| Secret Manager | 10 secrets | $0.30 |
| Artifact Registry | 5GB images | $0.50 |
| **Total** | | **~$10-15/month** |

### Scaling (100 Users)

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run | 10M requests | $50-100 |
| Firestore | 100GB storage | $10-20 |
| Pub/Sub | 100M messages | $40 |
| **Total** | | **~$100-160/month** |

---

## Support

### Issues
Report bugs: https://github.com/eyal-klein/NUCLEUS-V1/issues

### Documentation
Full docs: `docs/` directory in repository

### Contact
Technical support: support@nucleus.dev

---

**Deployment Complete! 🎉**

Your NUCLEUS instance is now running for **${CLIENT_NAME}**.

Next steps:
1. Share OAuth URLs with client for authentication
2. Monitor logs for first 24 hours
3. Set up alerting (optional)
4. Schedule regular backups (recommended)
