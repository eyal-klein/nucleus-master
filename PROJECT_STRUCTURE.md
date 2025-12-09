# NUCLEUS V1.2 - Project Structure

**Date:** December 9, 2025  
**Version:** 1.2 (Hybrid Model)

---

## Directory Structure

```
NUCLEUS-V1/
├── backend/
│   ├── services/          # Always-on Cloud Run Services (5)
│   │   ├── orchestrator/
│   │   ├── task-manager/
│   │   ├── results-analysis/
│   │   ├── decisions-engine/
│   │   └── agent-evolution/
│   ├── jobs/              # On-demand Cloud Run Jobs (8)
│   │   ├── dna-engine/
│   │   ├── first-interpretation/
│   │   ├── second-interpretation/
│   │   ├── micro-prompts/
│   │   ├── med-to-deep/
│   │   ├── activation/
│   │   ├── qa/
│   │   └── research/
│   └── shared/            # Shared libraries and utilities
│       ├── models/        # SQLAlchemy models
│       ├── pubsub/        # Pub/Sub client wrapper
│       ├── llm/           # LLM gateway (LiteLLM)
│       ├── adk/           # ADK utilities
│       └── tools/         # LangChain tools library
├── frontend/
│   └── admin-console/     # React + Vite admin dashboard
├── infrastructure/
│   ├── terraform/         # IaC for all GCP resources
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── cloud-sql.tf
│   │   ├── pubsub.tf
│   │   ├── cloud-run.tf
│   │   └── iam.tf
│   └── kubernetes/        # (Reserved for future use)
├── .github/
│   └── workflows/         # CI/CD pipelines
│       ├── deploy-services.yml
│       ├── deploy-jobs.yml
│       └── terraform.yml
└── docs/                  # All architecture and planning docs
    ├── NUCLEUS_ARCHITECTURE_V1.0_FINAL.md
    ├── NUCLEUS_GCP_DEPLOYMENT_V1.2_HYBRID.md
    └── NUCLEUS_IMPLEMENTATION_PLAN_V1.2_HYBRID.md
```

---

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI 0.116+
- **Agent Framework:** Google ADK 1.19.0
- **Tools:** LangChain 0.3.0+
- **LLM Gateway:** LiteLLM 1.55+
- **Database ORM:** SQLAlchemy 2.0+
- **Message Bus:** Google Cloud Pub/Sub

### Frontend
- **Framework:** React 19
- **Build Tool:** Vite
- **UI Library:** shadcn/ui
- **Styling:** Tailwind CSS 3.4+

### Infrastructure
- **Cloud Platform:** Google Cloud Platform (GCP)
- **Deployment:** Cloud Run (Services + Jobs)
- **Database:** Cloud SQL (PostgreSQL 18+)
- **Storage:** Google Cloud Storage
- **Messaging:** Google Cloud Pub/Sub
- **IaC:** Terraform
- **CI/CD:** GitHub Actions

---

## Database Schemas

| Schema | Purpose |
| :--- | :--- |
| `dna` | Entity identity, values, goals, interests |
| `memory` | Conversation history, summaries, vector embeddings |
| `assembly` | Agent & tool definitions, versions, performance |
| `execution` | Tasks, jobs, logs, operational data |

---

## Deployment Model (Hybrid)

### Always-On Services (5)
- nucleus-orchestrator
- nucleus-task-manager
- nucleus-results-analysis
- nucleus-decisions-engine
- nucleus-agent-evolution

### On-Demand Jobs (8)
- dna-engine-job
- first-interpretation-job
- second-interpretation-job
- micro-prompts-job
- med-to-deep-job
- activation-job
- qa-job
- research-job

---

**End of Document**
