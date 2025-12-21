#!/bin/bash
#
# NUCLEUS Client Deployment Automation Script
# Version: 1.1.0
# 
# This script automates the deployment of a new NUCLEUS instance for a client.
# It handles GCP project setup, service account creation, and initial configuration.
#
# Usage:
#   ./scripts/deploy-new-client.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - gh CLI installed and authenticated (optional)
#   - Billing account ID available
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "============================================================================"
echo "                    NUCLEUS Client Deployment Script                       "
echo "                           Version 1.1.0                                    "
echo "============================================================================"
echo ""

# Step 1: Gather client information
log_info "Step 1: Gathering client information..."
echo ""

read -p "Client Name (e.g., 'ABC Corp'): " CLIENT_NAME
read -p "Client Project ID (e.g., 'abc-corp-nucleus-prod'): " CLIENT_PROJECT_ID
read -p "GCP Billing Account ID: " BILLING_ACCOUNT_ID
read -p "Deployment Region [me-west1]: " REGION
REGION=${REGION:-me-west1}

echo ""
log_info "Configuration Summary:"
echo "  Client Name:       $CLIENT_NAME"
echo "  Project ID:        $CLIENT_PROJECT_ID"
echo "  Billing Account:   $BILLING_ACCOUNT_ID"
echo "  Region:            $REGION"
echo ""

read -p "Continue with this configuration? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    log_error "Deployment cancelled by user"
    exit 1
fi

echo ""

# Step 2: Create GCP Project
log_info "Step 2: Creating GCP project..."

if gcloud projects describe "$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Project $CLIENT_PROJECT_ID already exists. Skipping creation."
else
    gcloud projects create "$CLIENT_PROJECT_ID" \
        --name="$CLIENT_NAME - NUCLEUS" \
        --labels=client=$(echo "$CLIENT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-'),environment=production,managed-by=nucleus

    log_success "Project created: $CLIENT_PROJECT_ID"
fi

# Link billing
log_info "Linking billing account..."
gcloud billing projects link "$CLIENT_PROJECT_ID" \
    --billing-account="$BILLING_ACCOUNT_ID"

log_success "Billing linked"

# Set as active project
gcloud config set project "$CLIENT_PROJECT_ID"

echo ""

# Step 3: Enable APIs
log_info "Step 3: Enabling required GCP APIs..."

APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "secretmanager.googleapis.com"
    "pubsub.googleapis.com"
    "firestore.googleapis.com"
    "cloudscheduler.googleapis.com"
    "artifactregistry.googleapis.com"
)

for api in "${APIS[@]}"; do
    log_info "Enabling $api..."
    gcloud services enable "$api" --project="$CLIENT_PROJECT_ID"
done

log_success "All APIs enabled"
echo ""

# Step 4: Create Service Account
log_info "Step 4: Creating GitHub Actions service account..."

SA_EMAIL="github-actions@${CLIENT_PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Service account already exists. Skipping creation."
else
    gcloud iam service-accounts create github-actions \
        --display-name="GitHub Actions Deployment" \
        --project="$CLIENT_PROJECT_ID"
    
    log_success "Service account created"
fi

# Grant roles
log_info "Granting IAM roles..."

ROLES=(
    "roles/run.admin"
    "roles/storage.admin"
    "roles/artifactregistry.admin"
    "roles/iam.serviceAccountUser"
    "roles/secretmanager.admin"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$CLIENT_PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --quiet
done

log_success "IAM roles granted"

# Create key
log_info "Creating service account key..."
KEY_FILE="${HOME}/${CLIENT_PROJECT_ID}-github-actions-key.json"

gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL"

log_success "Service account key saved to: $KEY_FILE"
log_warning "⚠️  IMPORTANT: Keep this file secure! You'll need it for GitHub Secrets."

echo ""

# Step 5: Create Artifact Registry
log_info "Step 5: Creating Artifact Registry repository..."

if gcloud artifacts repositories describe nucleus \
    --location="$REGION" \
    --project="$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Artifact Registry repository already exists. Skipping."
else
    gcloud artifacts repositories create nucleus \
        --repository-format=docker \
        --location="$REGION" \
        --description="NUCLEUS container images" \
        --project="$CLIENT_PROJECT_ID"
    
    log_success "Artifact Registry repository created"
fi

echo ""

# Step 6: Create Pub/Sub Topics
log_info "Step 6: Creating Pub/Sub topics..."

if gcloud pubsub topics describe nucleus-digital-events \
    --project="$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Pub/Sub topic already exists. Skipping."
else
    gcloud pubsub topics create nucleus-digital-events \
        --project="$CLIENT_PROJECT_ID"
    
    log_success "Pub/Sub topic created"
fi

# Create subscription
if gcloud pubsub subscriptions describe nucleus-events-sub \
    --project="$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Pub/Sub subscription already exists. Skipping."
else
    gcloud pubsub subscriptions create nucleus-events-sub \
        --topic=nucleus-digital-events \
        --project="$CLIENT_PROJECT_ID"
    
    log_success "Pub/Sub subscription created"
fi

echo ""

# Step 7: Initialize Firestore
log_info "Step 7: Initializing Firestore database..."

if gcloud firestore databases describe --project="$CLIENT_PROJECT_ID" &>/dev/null; then
    log_warning "Firestore database already exists. Skipping."
else
    gcloud firestore databases create \
        --location="$REGION" \
        --project="$CLIENT_PROJECT_ID"
    
    log_success "Firestore database created"
fi

echo ""

# Step 8: Generate configuration file
log_info "Step 8: Generating configuration file..."

CONFIG_FILE="${HOME}/${CLIENT_PROJECT_ID}-config.env"

cat > "$CONFIG_FILE" << EOF
# NUCLEUS Configuration for $CLIENT_NAME
# Generated: $(date)

# GCP Configuration
PROJECT_ID=$CLIENT_PROJECT_ID
GCP_PROJECT_ID=$CLIENT_PROJECT_ID
REGION=$REGION

# Pub/Sub
PUBSUB_TOPIC=nucleus-digital-events

# Service Account
SERVICE_ACCOUNT_EMAIL=$SA_EMAIL

# GitHub Secrets Required:
# - GCP_PROJECT_ID: $CLIENT_PROJECT_ID
# - GCP_SA_KEY: (contents of $KEY_FILE)
# - GOOGLE_CLIENT_ID: (from OAuth credentials)
# - GOOGLE_CLIENT_SECRET: (from OAuth credentials)

# Artifact Registry
DOCKER_REGISTRY=${REGION}-docker.pkg.dev/${CLIENT_PROJECT_ID}/nucleus
EOF

log_success "Configuration saved to: $CONFIG_FILE"

echo ""

# Step 9: Summary and Next Steps
echo "============================================================================"
log_success "GCP Infrastructure Setup Complete!"
echo "============================================================================"
echo ""
echo "📋 Summary:"
echo "  ✅ GCP Project created: $CLIENT_PROJECT_ID"
echo "  ✅ APIs enabled"
echo "  ✅ Service account created: $SA_EMAIL"
echo "  ✅ Artifact Registry ready"
echo "  ✅ Pub/Sub configured"
echo "  ✅ Firestore initialized"
echo ""
echo "📁 Files Created:"
echo "  • Service Account Key: $KEY_FILE"
echo "  • Configuration File:  $CONFIG_FILE"
echo ""
echo "🔐 Security Reminder:"
echo "  ⚠️  Store $KEY_FILE securely"
echo "  ⚠️  Add to GitHub Secrets (do not commit to repository)"
echo "  ⚠️  Delete local copy after adding to GitHub Secrets"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Clone and configure repository:"
echo "   git clone https://github.com/eyal-klein/NUCLEUS-V1.git $CLIENT_PROJECT_ID"
echo "   cd $CLIENT_PROJECT_ID"
echo ""
echo "2. Create new GitHub repository:"
echo "   gh repo create $CLIENT_PROJECT_ID --private --source=. --remote=origin --push"
echo ""
echo "3. Configure GitHub Secrets:"
echo "   gh secret set GCP_PROJECT_ID --body \"$CLIENT_PROJECT_ID\""
echo "   gh secret set GCP_SA_KEY < $KEY_FILE"
echo ""
echo "4. Create OAuth credentials in Google Cloud Console:"
echo "   https://console.cloud.google.com/apis/credentials?project=$CLIENT_PROJECT_ID"
echo ""
echo "5. Deploy services:"
echo "   git push origin main"
echo ""
echo "📖 Full documentation:"
echo "   docs/CLIENT_DEPLOYMENT_GUIDE.md"
echo ""
echo "============================================================================"

# Cleanup prompt
echo ""
read -p "Delete service account key file now? (yes/no): " DELETE_KEY
if [[ "$DELETE_KEY" == "yes" ]]; then
    rm -f "$KEY_FILE"
    log_success "Service account key deleted"
    log_warning "Make sure you've saved it to GitHub Secrets first!"
fi

echo ""
log_success "Deployment script completed successfully! 🎉"
