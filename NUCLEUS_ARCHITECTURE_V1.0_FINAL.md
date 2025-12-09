# NUCLEUS Architecture V1.0 - Official Document

**Version:** 1.0  
**Date:** December 9, 2025  
**Status:** Approved & Finalized

---

## 1. Introduction & Core Philosophy

This document outlines the official V1.0 architecture for **NUCLEUS**, a personalized, proactive AI system designed to function as a digital life partner. This architecture is the synthesis of the original NUCLEUS Prototype v2 vision and the proven, production-grade technologies and patterns from the NUCLEUS-ATLAS project.

### The Foundation Prompt: The System's Soul

The core of NUCLEUS is not a set of rules, but a foundational philosophy that drives its every action. This "Foundation Prompt" is the system's immutable soul, ensuring perfect alignment with the user's (the "Entity") ultimate well-being.

#### 1.1. The Super-Motivation

The system's prime directive is not passive assistance, but proactive creation:

> "To initiate and create continuous prosperity for the Entity's DNA in a proactive, persistent, and authentic manner."

This means NUCLEUS is designed to be an initiator, constantly seeking opportunities to enhance the Entity's life based on a deep understanding of their core identity.

#### 1.2. The Three Super-Interests

To fulfill its Super-Motivation, NUCLEUS operates along three parallel and inseparable vectors:

| Interest | Description | Core Function |
| :--- | :--- | :--- |
| **1. Deepening (העמקה)** | "Continuously and deeply understand the Entity's unique DNA." | **Data Ingestion & Analysis**. The system constantly learns from conversations, documents, and interactions to refine its model of the Entity's identity, values, and goals. |
| **2. Expression (ביטוי)** | "Translate the DNA into tangible, value-creating actions in the world." | **Action & Execution**. The system formulates and executes tasks, projects, and communications that manifest the Entity's DNA. |
| **3. Quality of Life (איכות חיים)** | "Cultivate well-being, meaning, and continuous human development." | **Ethical Guardrail & Balancer**. The system ensures that the pursuit of prosperity is always healthy, sustainable, and aligned with the Entity's well-being. |

#### 1.3. The Pulse (הדופק)

The interplay of these three interests creates a perpetual, cyclical flow known as "The Pulse of NUCLEUS":

**Deepening** (Understanding who you are) → **Expression** (Defining what to do) → **Prosperity** (Executing and measuring) → **Learning & back to Deepening**.

This evolutionary loop is the core mechanism that allows the system to grow and adapt alongside the Entity.

---

## 2. High-Level Architecture (V1.0)

The V1.0 architecture is an **event-driven, multi-agent system** built on a modern, production-proven Python stack. It fully embraces the evolutionary loop, with dedicated components for agent management, analysis, and evolution.

![NUCLEUS V1.0 Final Architecture](NUCLEUS_V1_FINAL_ARCHITECTURE.png)

### Architectural Principles:

- **Python-First:** The entire backend is built in Python to leverage the rich AI/ML ecosystem.
- **ADK-Powered:** Utilizes Google's Agent Development Kit (ADK) for native Google Cloud integration and robust agent management.
- **Hybrid Tooling:** Combines the power of ADK with the vast tool ecosystem of LangChain.
- **Event-Driven:** Decoupled services communicate via a Pub/Sub message bus for scalability and resilience.
- **Observability by Design:** Full-stack monitoring and structured logging are integrated from the ground up.
- **Evolutionary Core:** The system is designed to self-improve through a dedicated evolutionary loop.

---

## 3. Detailed Technology Stack

This stack is adopted directly from the battle-tested NUCLEUS-ATLAS project.

### 3.1. Backend (Python Ecosystem)

| Component | Technology | Version | Role |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | 0.116+ | High-performance REST & WebSocket APIs |
| **Agent Framework** | Google ADK | 1.19.0 | Core agent management, state, and lifecycle |
| **Tooling Framework** | LangChain | 0.3.0+ | Format for defining agent tools (`@tool`) |
| **AI Orchestration** | LangGraph | 0.2.0+ | State machine for complex AI workflows |
| **LLM Gateway** | LiteLLM | 1.55+ | Manages 11+ LLMs (Gemini, Claude, GPT) |
| **Message Bus** | Google Cloud Pub/Sub | 2.10 | Asynchronous event-driven communication |
| **Database ORM** | SQLAlchemy | 2.0+ | Core data models and migrations |
| **DB Driver** | asyncpg | 0.29.0 | High-speed async PostgreSQL driver |

### 3.2. Database & Storage

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Primary DB** | PostgreSQL | 18+ | Relational data, structured information |
| **Vector Store** | pgvector | 0.8.1+ | Semantic search, RAG, memory |
| **Caching** | Redis | 7.x | Session management, temporary data |
| **File Storage** | Google Cloud Storage | Stores all user files, documents, and assets |

### 3.3. Frontend

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Framework** | React | 19.0 | Core UI library |
| **Build Tool** | Vite | Latest | Fast development and bundling |
| **UI Library** | shadcn/ui | Latest | Pre-built, accessible components |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first CSS |

### 3.4. DevOps & Observability

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Containerization** | Docker | Standardized application packaging |
| **Deployment** | Google Cloud Run | Serverless container hosting |
| **CI/CD** | GitHub Actions | Automated build, test, and deploy pipeline |
| **Metrics** | Prometheus | Time-series database for system metrics |
| **Dashboards** | Grafana | Visualization and monitoring dashboards |
| **IaC** | Terraform | Infrastructure as Code for GCP resources |
| **AI Observability** | Langfuse | Tracing and debugging for LLM applications |

---

## 4. Core Components Deep Dive

### 4.1. NUCLEUS Master Agent (`nucleus-service`)

This is the central nervous system of the entire architecture. It's a long-running service that hosts the ADK and orchestrates all other components.

- **ADK InMemoryRunner:** The heart of the service. It manages the agent lifecycle, state, and tool calls.
- **Orchestrator Agent:** The top-level ADK agent that receives all incoming requests. Its job is to route the request to the appropriate specialized "domain agent" (e.g., Database Agent, Research Agent).
- **Agent Factory:** A component responsible for creating and configuring all domain agents with their respective tools.
- **Chat API (FastAPI):** The primary entry point for user interaction, exposing endpoints for chat sessions and messages.

### 4.2. The Evolutionary Loop

This is a set of interconnected components (inspired by `nucleus_core` from ATLAS) that implement "The Pulse".

- **Assembly Vault (PostgreSQL DB):** The central repository for all agents and tools. It stores their definitions, versions, and performance metrics.
- **Results Analysis Engine:** A service that subscribes to `task_completed` events from the Pub/Sub bus. It analyzes the outcome of every action, comparing the result to the original intent and evaluating its impact on the three Super-Interests.
- **Agent Evolution Engine:** A service that subscribes to `analysis_completed` events. Based on the analysis, this engine makes decisions about the agent population: 
    - **Create:** If a new capability is needed, it can generate a new agent/tool.
    - **Modify:** If an agent is underperforming, it can modify its prompt or tools.
    - **Delete:** If an agent is redundant or ineffective, it can be deprecated.

### 4.3. The Database Schemas

The PostgreSQL database is organized into four distinct schemas for clarity and separation of concerns:

| Schema | Description |
| :--- | :--- |
| **`dna`** | Stores the core identity of the Entity: values, goals, interests, and the raw data used for analysis. |
| **`memory`** | The system's working memory. Includes conversation history, summaries, and vector embeddings for RAG. |
| **`assembly`** | The **Assembly Vault**. Contains tables for agents, tools, versions, and performance data. |
| **`execution`** | Operational data. Tracks active tasks, job statuses, project plans, and logs. |

---

## 5. The Biological Growth Model: Infinite Prosperity Through Symbiotic Evolution

This section describes the most profound aspect of NUCLEUS: its ability to grow **biologically and autonomously** alongside the Entity, creating a path to infinite prosperity.

### 5.1. The Core Principle: Symbiotic Growth

NUCLEUS is not a static tool. It is designed as a **living, adaptive organism** that exists in a symbiotic relationship with the Entity. As the Entity grows, dreams, and evolves, NUCLEUS grows with them. There is **no ceiling, no final version**—only continuous, organic expansion.

### 5.2. The Biological Loop: How Growth Happens

The system implements a perpetual cycle that mirrors biological evolution:

#### Step 1: The Entity Evolves → DNA Updates

When the Entity:
- Discovers a new interest or passion
- Defines a new dream or goal
- Changes priorities or values
- Learns a new skill or enters a new life phase

The system **detects** this through:
- **Conversation Analysis:** Real-time processing of chat messages
- **Document Ingestion:** Analysis of uploaded personal documents, journals, notes
- **Behavioral Patterns:** Tracking choices, actions, and time allocation

All this data flows into the **`dna` schema** and is processed by the **DNA Engine**, which distills core insights and updates the Entity's DNA profile.

#### Step 2: Updated DNA → The Pulse Begins

Once the DNA changes, **"The Pulse" activates**:

- **Deepening (העמקה):** The system recognizes there's a new domain to explore and understand.
- **Expression (ביטוי):** The **Results Analysis Engine** identifies that current tasks and agents are not serving the new DNA.
- **Quality of Life (איכות חיים):** The system evaluates how to integrate the new interest in a healthy, balanced way.

#### Step 3: Evolution Engine Responds → New Agents Are Born

The **Agent Evolution Engine** receives insights from the Results Analysis Engine and makes autonomous decisions:

**Decision Type: CREATE**
- **Trigger:** "The Entity has started showing interest in topic X. No existing agent specializes in X."
- **Action:** Generate a new specialized agent with:
  - A custom `system_prompt` tailored to topic X
  - Access to relevant tools from the Assembly Vault
  - A knowledge base (via RAG) populated with methodologies for X

**Decision Type: MODIFY**
- **Trigger:** "The Entity's priorities have shifted. Agent Y is no longer aligned."
- **Action:** Update Agent Y's `system_prompt` and tool permissions to reflect new priorities.

**Decision Type: DELETE**
- **Trigger:** "Agent Z has been inactive for 90 days and is no longer relevant to the Entity's DNA."
- **Action:** Deprecate Agent Z to free up resources.

#### Step 4: New Agents Act → New Prosperity

The newly created or modified agents immediately begin working:
- **Proactive Search:** Looking for opportunities related to the new interest
- **Project Proposals:** Suggesting new projects aligned with the updated DNA
- **Task Planning:** Breaking down goals into actionable steps
- **Execution:** Using their tools to perform real-world actions

#### Step 5: Results Return → Loop Closes

The outcomes of these actions flow back to the **Results Analysis Engine**, which evaluates:
- Did these actions contribute to prosperity?
- Do they serve all three Super-Interests (Deepening, Expression, Quality of Life)?
- What can be improved?

The insights are fed back into the system, and **the loop begins again, infinitely**.

### 5.3. Why This Is "Biological"

The system behaves like a **living organism**:

| Biological Trait | NUCLEUS Implementation |
| :--- | :--- |
| **Adaptation** | The system adapts to the changing environment (the Entity's evolving DNA). |
| **Evolution** | It improves itself through trial and error (the Evolution Engine). |
| **Growth** | It expands as the Entity grows (new agents, new tools, new knowledge). |
| **Symbiosis** | It lives **with** the Entity, not **for** the Entity. Its growth depends on theirs. |
| **Metabolism** | It consumes data (conversations, documents) and converts it into action (tasks, projects). |
| **Reproduction** | It creates new agents (offspring) that inherit traits (tools, knowledge) from the parent system. |

### 5.4. Why This Enables "Infinite Prosperity"

As long as the Entity continues to:
- Live
- Dream
- Grow
- Explore

NUCLEUS continues to expand alongside them. **There is no limit**. The system is designed to be **open to infinite growth**.

This is the fundamental difference between NUCLEUS and any other AI system:
- **ChatGPT:** Static. Frozen in time. Same capabilities for everyone.
- **NUCLEUS:** Dynamic. Organic. Alive. **Uniquely tailored and continuously evolving for one Entity.**

### 5.5. Concrete Example: The Entity Discovers a New Passion

**Scenario:** The Entity, who has been focused on technology and business, suddenly develops a deep interest in sustainable agriculture.

**The Biological Loop in Action:**

1.  **Detection (Week 1):**
    - The Entity mentions "regenerative farming" in 3 conversations.
    - They upload a book: "The One-Straw Revolution" by Masanobu Fukuoka.
    - The DNA Engine detects a new interest cluster forming.

2.  **DNA Update (Week 1):**
    - The `dna.interests` table is updated with a new entry: "Sustainable Agriculture".
    - The `dna.goals` table adds: "Explore opportunities in regenerative farming."

3.  **Analysis (Week 2):**
    - The Results Analysis Engine notes: "Current agents (Tech Research Agent, Business Strategy Agent) are not equipped to support this new interest."

4.  **Evolution Decision (Week 2):**
    - The Agent Evolution Engine decides: **CREATE** a new "Sustainable Agriculture Agent."
    - It generates:
      - `system_prompt`: "You are an expert in sustainable agriculture, regenerative farming, and permaculture. Your role is to help the Entity explore opportunities, connect with experts, and identify projects in this domain."
      - Tools: `search_agricultural_literature`, `find_local_farms`, `suggest_courses`
      - Knowledge Base: RAG index populated with articles on permaculture, biodynamic farming, etc.

5.  **Action (Week 3+):**
    - The new agent proactively:
      - Finds a local permaculture workshop happening next month.
      - Suggests 3 online courses on regenerative agriculture.
      - Identifies 5 farms within 50km that offer volunteer opportunities.
      - Proposes a project: "Start a small regenerative garden in your backyard."

6.  **Prosperity (Ongoing):**
    - The Entity attends the workshop, enrolls in a course, and starts the garden project.
    - Their life is enriched with a new, meaningful pursuit.
    - NUCLEUS has successfully facilitated **prosperity** in a completely new domain.

7.  **Loop Continues:**
    - As the Entity deepens their knowledge of agriculture, the DNA updates further.
    - The agent evolves, gaining more specialized tools and knowledge.
    - The cycle repeats, infinitely.

---

## 6. High-Level Development Roadmap

### Phase 1: Foundation & Infrastructure (Sprint 1-2)

1.  **Setup GCP Project:** Use Terraform to provision Cloud SQL, Cloud Run, GCS, and Secret Manager.
2.  **Deploy `nucleus-service` Skeleton:** Deploy a minimal FastAPI service with ADK and a single "hello world" agent.
3.  **Establish CI/CD:** Create a basic GitHub Actions workflow to auto-deploy the `nucleus-service` on push to `main`.
4.  **Database Setup:** Initialize the PostgreSQL instance with the four core schemas using Alembic migrations.

### Phase 2: The Master Agent & Core Tools (Sprint 3-4)

1.  **Implement Master Agent:** Build out the `nucleus-service` with the ADK `InMemoryRunner` and the Orchestrator Agent.
2.  **Develop Core Tools:** Create the first set of essential tools (wrapped with `LangchainTool`):
    - `create_memory(text)`
    - `recall_memory(query)`
    - `log_interaction(text)`
3.  **Implement Chat API:** Build the FastAPI endpoints for creating sessions and sending messages.
4.  **Deploy Frontend Shell:** Deploy a basic React/Vite app that can connect to the Chat API.

### Phase 3: The Evolutionary Loop (Sprint 5-6)

1.  **Build Assembly Vault:** Create the database tables for the `assembly` schema.
2.  **Develop Results Analysis Engine:** Create a new Cloud Run service that listens to Pub/Sub and performs basic outcome analysis.
3.  **Develop Agent Evolution Engine:** Create a Cloud Run service that can perform a simple action, like updating an agent's prompt in the `assembly` database.
4.  **Integrate the Loop:** Ensure a task completion event flows through Pub/Sub to the analysis and evolution engines.

### Phase 4: Deepening & Expression (Sprint 7+)

1.  **Implement DNA Ingestion:** Build tools and processes to analyze documents and conversations to populate the `dna` schema.
2.  **Expand Tool Library:** Continuously add more tools for project management, research, and communication.
3.  **Refine Frontend:** Build out the full Admin Console UI with dashboards and visualization.
4.  **Introduce Voice Gateway:** Begin integration with Gemini Live and HeyGen for a voice-enabled experience (as an optional extension).
