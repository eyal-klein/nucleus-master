# NUCLEUS V1.2 - GCP Deployment Architecture (Hybrid Model)

**Version:** 1.2 (Hybrid)
**Date:** December 9, 2025
**Author:** Manus AI

---

## 1. Overview

This document describes the **official Hybrid Deployment Architecture** for NUCLEUS V1.2. This model is optimized for cost, performance, and operational excellence by using a mix of always-on Cloud Run Services and on-demand Cloud Run Jobs.

---

## 2. Deployment Strategy: The Hybrid Model

### 2.1. Always-On Services (5 Core Engine Services)

These services are the real-time, event-driven core of the system. They are always running (with scale-to-zero) to provide immediate responses.

| Service Name | Engine(s) Hosted | Trigger | Justification |
| :--- | :--- | :--- | :--- |
| `nucleus-orchestrator` | Orchestrator | Pub/Sub | Always-on to coordinate all engines. |
| `nucleus-task-manager` | Task Manager | HTTP | Immediate response to user requests. |
| `nucleus-results-analysis` | Results Analysis | Pub/Sub | Real-time analysis of task outcomes. |
| `nucleus-decisions-engine` | Decisions Engine | HTTP/Pub/Sub | Immediate autonomous decisions. |
| `nucleus-agent-evolution` | Agent Evolution | Pub/Sub | Real-time agent creation and modification. |

### 2.2. On-Demand Jobs (8 Engine Jobs)

These are heavy, analytical, or periodic tasks executed as serverless jobs. They run to completion and only incur costs during execution.

| Job Name | Engine Hosted | Trigger | Justification |
| :--- | :--- | :--- | :--- |
| `dna-engine-job` | DNA Engine | Cloud Scheduler (Daily) / Pub/Sub | Heavy analysis, not needed in real-time. |
| `first-interpretation-job` | First Interpretation | Pub/Sub (on `dna_updated`) | Discrete, one-off task. |
| `second-interpretation-job`| Second Interpretation | Pub/Sub (on `feedback_received`) | Discrete, one-off task. |
| `micro-prompts-job` | Micro-Prompts Engine | Pub/Sub (on `prompt_refined`) | Discrete, one-off task. |
| `med-to-deep-job` | MED-to-DEEP Engine | Cloud Scheduler (Nightly) | Perfect for a scheduled batch job. |
| `activation-job` | Activation Engine | Pub/Sub (on `agent_validated`) | Discrete deployment process. |
| `qa-job` | QA Engine | Pub/Sub (on `agent_created`) | Discrete testing process. |
| `research-job` | Research Engine | Pub/Sub / HTTP | Long-running, resource-intensive task. |

### 2.3. Supporting Services

- `nucleus-api-gateway` (Cloud Run Service)
- `nucleus-frontend` (Cloud Run Service)
- `nucleus-nats` (GKE Cluster)
- `nucleus-prometheus` (Cloud Run Service)
- `nucleus-grafana` (Cloud Run Service)

---

## 3. Infrastructure Details

(Database, Storage, Secrets, Networking, and CI/CD details remain the same as V1.1)

---

## 4. Cost & Complexity Impact

- **Estimated Cost Reduction:** 30-50% (due to 8 fewer always-on services).
- **DevOps Complexity:** Reduced. Fewer active services to monitor and manage.
- **Performance:** Improved. Real-time services are isolated from heavy batch jobs.

---

## 5. Conclusion

This Hybrid Model is the official, optimized deployment strategy for NUCLEUS V1.2. It provides the best balance of performance, cost, and operational maturity.

---

**End of Document**
