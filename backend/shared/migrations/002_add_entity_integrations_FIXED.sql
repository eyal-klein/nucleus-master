-- ============================================================================
-- NUCLEUS V1.2 - Migration 002: Add Entity Integrations
-- FIXED VERSION - Works with existing migrations table structure
-- ============================================================================
-- Description: Adds entity_integrations table for third-party service credentials
-- Author: NUCLEUS Development Team
-- Date: December 9, 2025
-- ============================================================================

-- Prerequisites Check
DO $$
BEGIN
    -- Check if dna schema exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'dna') THEN
        RAISE EXCEPTION 'Schema "dna" does not exist. Please run migration 001 first.';
    END IF;
    
    -- Check if entity table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'dna' AND table_name = 'entity') THEN
        RAISE EXCEPTION 'Table "dna.entity" does not exist. Please run migration 001 first.';
    END IF;
END $$;

-- ============================================================================
-- Create entity_integrations table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dna.entity_integrations (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entity reference
    entity_id UUID NOT NULL REFERENCES dna.entity(id) ON DELETE CASCADE,
    
    -- Service information
    service_name VARCHAR(100) NOT NULL,  -- e.g., 'gmail', 'github', 'notion'
    service_type VARCHAR(50) NOT NULL,   -- e.g., 'email', 'code', 'docs'
    display_name VARCHAR(255),           -- User-friendly name
    description TEXT,                    -- Optional description
    
    -- Credentials reference (NOT the actual credentials!)
    secret_path VARCHAR(500) NOT NULL,   -- Path to secret in Secret Manager
    credential_type VARCHAR(50) NOT NULL, -- e.g., 'oauth2', 'api_key', 'basic_auth'
    
    -- OAuth specific fields
    scopes TEXT[],                       -- OAuth scopes granted
    token_expires_at TIMESTAMP WITH TIME ZONE, -- When OAuth token expires
    
    -- Sync information
    status VARCHAR(50) DEFAULT 'active', -- active, inactive, expired, error
    last_sync_at TIMESTAMP WITH TIME ZONE, -- Last successful sync
    sync_frequency_hours INTEGER DEFAULT 24, -- How often to sync
    
    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,    -- Service-specific configuration
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_entity_service UNIQUE (entity_id, service_name),
    CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'expired', 'error')),
    CONSTRAINT valid_credential_type CHECK (credential_type IN ('oauth2', 'api_key', 'basic_auth', 'bearer_token'))
);

-- ============================================================================
-- Create indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_entity_integrations_entity_id 
ON dna.entity_integrations(entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_integrations_service_name 
ON dna.entity_integrations(service_name);

CREATE INDEX IF NOT EXISTS idx_entity_integrations_status 
ON dna.entity_integrations(status);

CREATE INDEX IF NOT EXISTS idx_entity_integrations_last_sync 
ON dna.entity_integrations(last_sync_at);

-- ============================================================================
-- Create trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_entity_integrations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_entity_integrations_updated_at
    BEFORE UPDATE ON dna.entity_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_entity_integrations_updated_at();

-- ============================================================================
-- Record migration in existing migrations table
-- ============================================================================

-- Insert using the EXISTING migrations table structure
-- (id, migration_name, applied_at)
INSERT INTO public.migrations (migration_name, applied_at)
VALUES ('002_add_entity_integrations', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
BEGIN
    -- Check table exists
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'dna' AND table_name = 'entity_integrations';
    
    IF table_count = 0 THEN
        RAISE EXCEPTION 'Failed to create entity_integrations table';
    END IF;
    
    -- Check indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'dna' AND tablename = 'entity_integrations';
    
    IF index_count < 4 THEN
        RAISE WARNING 'Expected 4 indexes, found %', index_count;
    END IF;
    
    RAISE NOTICE '✅ Migration 002 completed successfully!';
    RAISE NOTICE '   - Table: dna.entity_integrations created';
    RAISE NOTICE '   - Indexes: % created', index_count;
    RAISE NOTICE '   - Trigger: update_entity_integrations_updated_at created';
END $$;

-- ============================================================================
-- END OF MIGRATION 002
-- ============================================================================
