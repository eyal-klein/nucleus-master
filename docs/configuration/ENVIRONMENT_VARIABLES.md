# NUCLEUS Environment Variables

**Version:** 1.1.0  
**Last Updated:** December 21, 2025

---

## Overview

This document details all environment variables required to run NUCLEUS services. Proper configuration is critical for security, functionality, and project isolation.

---

## Global Required Variables

These variables **must** be set for all services and jobs.

| Variable | Description | Example | Required |
|---|---|---|---|
| `GCP_PROJECT_ID` | The GCP project ID for the client deployment. | `abc-corp-nucleus-prod` | **Yes** |
| `REGION` | The GCP region for deployment. | `me-west1` | **Yes** |

**⚠️ CRITICAL:**
- As of v1.1.0, services will **fail to start** if `GCP_PROJECT_ID` is not set.
- This is a security feature to prevent cross-client data leakage.

---

## Service-Specific Variables

### Connectors (Gmail, Calendar)

| Variable | Description | Example | Required |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID for Google APIs. | `12345.apps.googleusercontent.com` | **Yes** |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret. | `GOCSPX-12345` | **Yes** |
| `REDIRECT_URI` | OAuth callback URL for the specific connector. | `https://gmail-connector-<hash>.a.run.app/callback` | **Yes** |
| `PUBSUB_TOPIC` | The Pub/Sub topic for publishing events. | `nucleus-digital-events` | No (defaults to `nucleus-digital-events`) |

### Event Consumer

| Variable | Description | Example | Required |
|---|---|---|---|
| `DNA_ENGINE_URL` | URL of the DNA Engine service. | `http://analysis-dna:8080` | No (defaults to `http://analysis-dna:8080`) |

### Orchestrator

| Variable | Description | Example | Required |
|---|---|---|---|
| `PUBSUB_TOPIC` | The Pub/Sub topic for publishing events. | `nucleus-digital-events` | No (defaults to `nucleus-digital-events`) |

---

## GitHub Actions Secrets

These secrets must be configured in the client repository settings.

| Secret Name | Description | Source |
|---|---|---|
| `GCP_PROJECT_ID` | The client's GCP project ID. | From GCP project creation |
| `GCP_SA_KEY` | JSON key for the GitHub Actions service account. | Generated during setup |
| `GOOGLE_CLIENT_ID` | OAuth Client ID. | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret. | From Google Cloud Console |

---

## Configuration in Cloud Run

When deploying services via `gcloud run deploy`, set variables like this:

```bash
gcloud run deploy gmail-connector \
  --image ... \
  --set-env-vars GCP_PROJECT_ID=abc-corp-nucleus-prod,GOOGLE_CLIENT_ID=12345,GOOGLE_CLIENT_SECRET=GOCSPX-12345,REDIRECT_URI=https://... \
  ...
```

**Note:** The GitHub Actions workflows are already configured to pass `GCP_PROJECT_ID` from secrets.

---

## Local Development (`.env` file)

Create a `.env` file in the root of the repository for local development:

```bash
# .env

GCP_PROJECT_ID=your-local-test-project
REGION=me-west1

# Google OAuth
GOOGLE_CLIENT_ID=your-local-client-id
GOOGLE_CLIENT_SECRET=your-local-client-secret
REDIRECT_URI=http://localhost:8000/callback

# Service URLs
DNA_ENGINE_URL=http://localhost:8081

# Pub/Sub
PUBSUB_TOPIC=nucleus-digital-events
```

---

## Validation

To check environment variables on a running Cloud Run service:

```bash
gcloud run services describe SERVICE_NAME \
  --region $REGION \
  --project $GCP_PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"
```

---

## History

- **v1.1.0:** Made `GCP_PROJECT_ID` mandatory for all services.
- **v1.0.0:** Initial version.
