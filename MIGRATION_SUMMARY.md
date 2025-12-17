# NUCLEUS Migration to GCP Project: NUCLEUS MASTER

## Migration Date: December 17, 2025

## Overview
Successfully migrated all NUCLEUS services from `thrive-system1` GCP project to the new dedicated `nucleus-master` GCP project.

## New GCP Project Details
- **Project Name:** NUCLEUS MASTER
- **Project ID:** nucleus-master
- **Project Number:** 960195739164
- **Organization:** globalimpact.co.il
- **Region:** me-west1 (Tel Aviv)

## Migrated Resources

### Cloud Run Services (17)
1. agent-health-monitor
2. apple-watch-connector
3. briefing-agent
4. calendar-connector
5. context-aware-scheduler
6. event-consumer
7. gmail-connector
8. health-wellness-engine
9. intelligent-agent-factory
10. linkedin-connector
11. nucleus-agent-evolution
12. nucleus-decisions-engine
13. nucleus-memory-engine
14. nucleus-orchestrator
15. nucleus-results-analysis
16. nucleus-task-manager
17. oura-connector

### Cloud Run Jobs (10)
1. agent-lifecycle-manager
2. master-prompt-engine
3. nucleus-activation-engine
4. nucleus-dna-engine
5. nucleus-first-interpretation
6. nucleus-med-to-deep
7. nucleus-micro-prompts
8. nucleus-qa-engine
9. nucleus-research-engine
10. nucleus-second-interpretation

### Cloud SQL
- **Instance:** nucleus-db
- **Version:** MySQL 8.0
- **Region:** me-west1

### Secrets
- ANTHROPIC_API_KEY
- DATABASE_URL
- GEMINI_API_KEY
- OPENAI_API_KEY
- nucleus-db-url

### Service Accounts
- nucleus-deployer (CI/CD deployments)
- admin-master (Cloud Run jobs)
- nucleus-sa (Cloud Run services)

## Changes Made
1. Updated all GitHub Actions workflows to use `nucleus-master` project
2. Changed region from `us-central1` to `me-west1`
3. Updated Cloud SQL connection strings
4. Created new Artifact Registry repository
5. Configured IAM permissions for all service accounts

## GitHub Secrets Updated
- GCP_PROJECT_ID → nucleus-master
- GCP_SA_KEY → New service account key

---
*Migration completed successfully*
