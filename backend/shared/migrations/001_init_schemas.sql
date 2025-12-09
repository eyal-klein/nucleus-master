-- NUCLEUS V1.2 - Initial Database Schema Migration
-- Creates the 4 core schemas: dna, memory, assembly, execution

-- ============================================================================
-- SCHEMA: dna
-- Purpose: Entity identity, values, goals, interests
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS dna;

CREATE TABLE IF NOT EXISTS dna.entity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dna.interests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES dna.entity(id) ON DELETE CASCADE,
    interest_name VARCHAR(255) NOT NULL,
    interest_description TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    first_detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_reinforced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS dna.goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES dna.entity(id) ON DELETE CASCADE,
    goal_title VARCHAR(500) NOT NULL,
    goal_description TEXT,
    priority INTEGER DEFAULT 5,
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, archived
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dna.values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES dna.entity(id) ON DELETE CASCADE,
    value_name VARCHAR(255) NOT NULL,
    value_description TEXT,
    importance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dna.raw_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES dna.entity(id) ON DELETE CASCADE,
    data_type VARCHAR(100) NOT NULL,  -- conversation, document, interaction
    data_content TEXT NOT NULL,
    metadata JSONB,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SCHEMA: memory
-- Purpose: Conversation history, summaries, vector embeddings
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS memory;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL,
    session_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory.summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL,
    summary_type VARCHAR(100) NOT NULL,  -- daily, weekly, topic
    summary_content TEXT NOT NULL,
    time_period_start TIMESTAMP WITH TIME ZONE,
    time_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL,
    source_type VARCHAR(100) NOT NULL,  -- conversation, document, summary
    source_id UUID NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON memory.embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- SCHEMA: assembly
-- Purpose: Agent & tool definitions, versions, performance
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS assembly;

CREATE TABLE IF NOT EXISTS assembly.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(255) NOT NULL UNIQUE,
    agent_type VARCHAR(100) NOT NULL,  -- strategic, tactical
    system_prompt TEXT NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assembly.tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(255) NOT NULL UNIQUE,
    tool_description TEXT,
    tool_schema JSONB NOT NULL,  -- LangChain tool schema
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assembly.agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES assembly.agents(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES assembly.tools(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, tool_id)
);

CREATE TABLE IF NOT EXISTS assembly.agent_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES assembly.agents(id) ON DELETE CASCADE,
    task_id UUID NOT NULL,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    feedback_score FLOAT,
    metadata JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SCHEMA: execution
-- Purpose: Tasks, jobs, logs, operational data
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS execution;

CREATE TABLE IF NOT EXISTS execution.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL,
    task_title VARCHAR(500) NOT NULL,
    task_description TEXT,
    assigned_agent_id UUID,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, failed
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS execution.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(255) NOT NULL,
    job_type VARCHAR(100) NOT NULL,  -- dna_analysis, interpretation, qa, etc.
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution.logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR
    service_name VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_entity_id ON execution.tasks(entity_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON execution.tasks(status);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON execution.jobs(status);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON execution.logs(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_entity_id ON memory.conversations(entity_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON memory.conversations(session_id);

-- ============================================================================
-- SEED DATA: Create default entity
-- ============================================================================

INSERT INTO dna.entity (name) VALUES ('Eyal Klein') ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
