# NUCLEUS Deployment Validation Guide

**Version:** 1.1.0  
**Last Updated:** December 21, 2025

---

## Overview

This guide provides a comprehensive checklist and testing procedures to validate a new NUCLEUS client deployment. It is designed to be executed after completing the `CLIENT_DEPLOYMENT_GUIDE.md`.

---

## Validation Checklist

### Phase 1: Infrastructure & Configuration

| Item | Status | Notes |
|---|---|---|
| [ ] GCP Project Created | | `gcloud projects describe <project_id>` |
| [ ] Billing Account Linked | | `gcloud billing projects describe <project_id>` |
| [ ] All GCP APIs Enabled | | `gcloud services list --enabled` |
| [ ] Service Account Created | | `gcloud iam service-accounts describe <sa_email>` |
| [ ] IAM Roles Granted | | `gcloud projects get-iam-policy <project_id>` |
| [ ] Artifact Registry Created | | `gcloud artifacts repositories list` |
| [ ] Pub/Sub Topic Created | | `gcloud pubsub topics list` |
| [ ] Firestore Database Initialized | | `gcloud firestore databases describe` |
| [ ] GitHub Secrets Configured | | `gh secret list` |
| [ ] `GCP_PROJECT_ID` is set | | `gh secret list | grep GCP_PROJECT_ID` |
| [ ] `GCP_SA_KEY` is set | | `gh secret list | grep GCP_SA_KEY` |

### Phase 2: Service Deployment

| Item | Status | Notes |
|---|---|---|
| [ ] All Workflows Succeeded | | Check GitHub Actions tab |
| [ ] All Services Deployed | | `gcloud run services list` |
| [ ] All Services `READY` | | `gcloud run services list` |
| [ ] No Startup Errors in Logs | | `gcloud run services logs read <service>` |
| [ ] `PROJECT_ID` Validated in Logs | | `gcloud run services logs read <service> | grep "PROJECT_ID"` |

### Phase 3: Integration & Functionality

| Item | Status | Notes |
|---|---|---|
| [ ] Gmail OAuth Flow Works | | `curl <gmail_url>/auth` |
| [ ] Calendar OAuth Flow Works | | `curl <calendar_url>/auth` |
| [ ] Credentials Persist After Restart | | Redeploy connector and test sync |
| [ ] Gmail Sync Works | | `curl -X POST <gmail_url>/sync` |
| [ ] Calendar Sync Works | | `curl -X POST <calendar_url>/sync` |
| [| [ ] Pub/Sub Messages Received | | `gcloud pubsub subscriptions pull <sub_name>` |
| [ ] Events Stored in Firestore | | Check Firestore console |
| [ ] No Cross-Project Data Leakage | | Verify data is in correct project |

---

## Detailed Testing Procedures

### Test 1: `PROJECT_ID` Misconfiguration (Fail-Fast Validation)

**Objective:** Verify that services fail to start if `GCP_PROJECT_ID` is not set.

1.  **Temporarily rename the secret:**
    ```bash
    gh secret rename GCP_PROJECT_ID -n GCP_PROJECT_ID_DISABLED
    ```
2.  **Redeploy a service:**
    ```bash
    gh workflow run deploy-gmail-connector.yml
    ```
3.  **Observe the deployment:**
    -   The GitHub Actions workflow should **succeed** (build and push).
    -   The Cloud Run deployment should **fail**.
4.  **Check the logs:**
    ```bash
    gcloud run services logs read gmail-connector --limit=50
    ```
    **Expected Log:** `ValueError: GCP_PROJECT_ID environment variable is required...`

5.  **Restore the secret:**
    ```bash
    gh secret rename GCP_PROJECT_ID_DISABLED -n GCP_PROJECT_ID
    ```
6.  **Redeploy again:**
    -   The deployment should now **succeed**.

**Result:** ✅ Pass / ❌ Fail

---

### Test 2: End-to-End Gmail Sync

**Objective:** Verify the full flow from Gmail OAuth to Pub/Sub message.

1.  **Get service URL:**
    ```bash
    GMAIL_URL=$(gcloud run services describe gmail-connector --format="value(status.url)")
    ```
2.  **Initiate OAuth:**
    -   Open `$GMAIL_URL/auth?entity_id=validation-user` in a browser.
    -   Complete the Google authentication flow.
    -   **Expected:** `Successfully authenticated` message.
3.  **Trigger Sync:**
    ```bash
    curl -X POST "$GMAIL_URL/sync" \
      -H "Content-Type: application/json" \
      -d '{"entity_id": "validation-user", "max_results": 5}'
    ```
    **Expected:** `{"message":"Sync triggered for entity validation-user"}`
4.  **Check Logs:**
    ```bash
    gcloud run services logs read gmail-connector --limit=100 | grep "Published to Pub/Sub"
    ```
    **Expected:** `Published to Pub/Sub: <message_id>`
5.  **Verify Pub/Sub Message:**
    ```bash
    gcloud pubsub subscriptions pull nucleus-events-sub --auto-ack --limit=1
    ```
    **Expected:** Message data with `source: "gmail"` and `entity_id: "validation-user"`.

**Result:** ✅ Pass / ❌ Fail

---

### Test 3: Calendar Credential Persistence

**Objective:** Verify that OAuth credentials persist after a service restart.

1.  **Get service URL:**
    ```bash
    CALENDAR_URL=$(gcloud run services describe calendar-connector --format="value(status.url)")
    ```
2.  **Authenticate (if not already done):**
    -   Open `$CALENDAR_URL/auth?entity_id=validation-user` in a browser.
    -   Complete the flow.
3.  **Trigger a sync (to confirm it works):**
    ```bash
    curl -X POST "$CALENDAR_URL/sync" \
      -H "Content-Type: application/json" \
      -d '{"entity_id": "validation-user"}'
    ```
    **Expected:** `{"message":"Sync triggered..."}`
4.  **Redeploy the service (simulates a restart):**
    ```bash
    gcloud run deploy calendar-connector \
      --image $(gcloud run services describe calendar-connector --format="value(spec.template.spec.containers[0].image)") \
      --region $REGION
    ```
5.  **Wait for deployment to complete.**
6.  **Trigger sync AGAIN (without re-authenticating):**
    ```bash
    curl -X POST "$CALENDAR_URL/sync" \
      -H "Content-Type: application/json" \
      -d '{"entity_id": "validation-user"}'
    ```
    **Expected:** `{"message":"Sync triggered..."}` (Should work without needing to auth again).

**Result:** ✅ Pass / ❌ Fail

---

## Common Issues & Solutions

| Issue | Solution |
|---|---|
| `401 Unauthorized` on sync | Credentials not found. Re-run the OAuth flow. If it persists, check Secret Manager permissions. |
| `redirect_uri_mismatch` | The URL in Google Cloud Console OAuth settings does not exactly match the Cloud Run service URL. Update it. |
| `PERMISSION_DENIED` on Pub/Sub | The service account is missing the `roles/pubsub.publisher` role. Grant it via IAM. |
| `PERMISSION_DENIED` on Secret Manager | The service account is missing the `roles/secretmanager.secretAccessor` role. Grant it. |

---

This guide ensures that every client deployment is robust, secure, and correctly configured. Always complete this validation before handing over an instance to a client.
