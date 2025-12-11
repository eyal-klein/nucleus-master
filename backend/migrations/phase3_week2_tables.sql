-- Migration: Phase 3 Week 2 - Calendar Integration & Context Awareness
-- Date: 2025-12-11
-- Purpose: Add tables for calendar events, briefings, emails, and scheduling preferences

-- ============================================================================
-- memory.calendar_events - Calendar events from Google Calendar
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory.calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES dna.entity(id) ON DELETE CASCADE,
    
    -- Event details
    event_id VARCHAR(255) NOT NULL,  -- External event ID from Google
    summary VARCHAR(500) NOT NULL,   -- Event title
    description TEXT,                -- Event description
    location VARCHAR(500),           -- Location or meeting link
    
    -- Timing
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    timezone VARCHAR(50),
    
    -- Participants
    organizer VARCHAR(255),
    attendees JSONB DEFAULT '[]'::jsonb,  -- Array of email addresses
    
    -- Status
    status VARCHAR(50),              -- confirmed, tentative, cancelled
    response_status VARCHAR(50),     -- accepted, declined, tentative, needsAction
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'google_calendar',
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    meta_data JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT calendar_events_entity_event_unique UNIQUE (entity_id, event_id, source)
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_entity_id ON memory.calendar_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON memory.calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON memory.calendar_events(status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_attendees ON memory.calendar_events USING GIN (attendees);

COMMENT ON TABLE memory.calendar_events IS 'Calendar events synced from Google Calendar';
COMMENT ON COLUMN memory.calendar_events.event_id IS 'External event ID from Google Calendar API';
COMMENT ON COLUMN memory.calendar_events.attendees IS 'Array of attendee objects with email and response status';

-- ============================================================================
-- memory.email_messages - Email messages from Gmail
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory.email_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES dna.entity(id) ON DELETE CASCADE,
    
    -- Email details
    message_id VARCHAR(255) NOT NULL,  -- External message ID from Gmail
    thread_id VARCHAR(255),            -- Email thread ID
    subject VARCHAR(1000),
    sender VARCHAR(255) NOT NULL,
    recipients JSONB DEFAULT '[]'::jsonb,  -- To, CC, BCC
    
    -- Content
    body_text TEXT,
    body_html TEXT,
    snippet VARCHAR(500),              -- Short preview
    
    -- Timing
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_starred BOOLEAN DEFAULT FALSE,
    labels JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'gmail',
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    meta_data JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT email_messages_entity_message_unique UNIQUE (entity_id, message_id, source)
);

CREATE INDEX IF NOT EXISTS idx_email_messages_entity_id ON memory.email_messages(entity_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_received_at ON memory.email_messages(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_sender ON memory.email_messages(sender);
CREATE INDEX IF NOT EXISTS idx_email_messages_thread_id ON memory.email_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_labels ON memory.email_messages USING GIN (labels);

COMMENT ON TABLE memory.email_messages IS 'Email messages synced from Gmail';
COMMENT ON COLUMN memory.email_messages.message_id IS 'External message ID from Gmail API';
COMMENT ON COLUMN memory.email_messages.snippet IS 'Short preview of email content (first 100-200 chars)';

-- ============================================================================
-- memory.briefings - Generated meeting briefings
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory.briefings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES dna.entity(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES memory.calendar_events(id) ON DELETE CASCADE,
    
    -- Briefing content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,           -- Markdown formatted briefing
    
    -- Context sources
    email_count INTEGER DEFAULT 0,
    previous_meetings_count INTEGER DEFAULT 0,
    context_sources JSONB DEFAULT '[]'::jsonb,
    
    -- Timing
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'generated',  -- generated, sent, read
    
    -- Metadata
    meta_data JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT briefings_event_unique UNIQUE (event_id)
);

CREATE INDEX IF NOT EXISTS idx_briefings_entity_id ON memory.briefings(entity_id);
CREATE INDEX IF NOT EXISTS idx_briefings_generated_at ON memory.briefings(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_briefings_status ON memory.briefings(status);
CREATE INDEX IF NOT EXISTS idx_briefings_event_id ON memory.briefings(event_id);

COMMENT ON TABLE memory.briefings IS 'AI-generated meeting briefings with context';
COMMENT ON COLUMN memory.briefings.content IS 'Markdown formatted briefing content';
COMMENT ON COLUMN memory.briefings.context_sources IS 'Sources used to generate briefing (emails, meetings, etc.)';

-- ============================================================================
-- dna.scheduling_preferences - Entity scheduling preferences
-- ============================================================================

CREATE TABLE IF NOT EXISTS dna.scheduling_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES dna.entity(id) ON DELETE CASCADE,
    
    -- Preferences
    preferred_deep_work_hours JSONB DEFAULT '[]'::jsonb,  -- Array of hour ranges
    preferred_meeting_hours JSONB DEFAULT '[]'::jsonb,
    no_meeting_days JSONB DEFAULT '[]'::jsonb,            -- Array of day names
    
    -- Constraints
    max_meetings_per_day INTEGER DEFAULT 5,
    min_break_between_meetings INTEGER DEFAULT 15,        -- Minutes
    preferred_meeting_duration INTEGER DEFAULT 30,        -- Minutes
    
    -- Work schedule
    work_start_time TIME,
    work_end_time TIME,
    work_days JSONB DEFAULT '["Monday","Tuesday","Wednesday","Thursday","Friday"]'::jsonb,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    meta_data JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT scheduling_preferences_entity_unique UNIQUE (entity_id)
);

CREATE INDEX IF NOT EXISTS idx_scheduling_preferences_entity_id ON dna.scheduling_preferences(entity_id);

COMMENT ON TABLE dna.scheduling_preferences IS 'Entity scheduling preferences and work hours';
COMMENT ON COLUMN dna.scheduling_preferences.preferred_deep_work_hours IS 'Preferred hours for deep work (e.g., [{"start": 9, "end": 12}])';
COMMENT ON COLUMN dna.scheduling_preferences.work_days IS 'Array of work day names (e.g., ["Monday", "Tuesday"])';

-- ============================================================================
-- Update existing models to add calendar and email relationships
-- ============================================================================

-- Add indexes for better query performance on existing tables
CREATE INDEX IF NOT EXISTS idx_health_metrics_entity_type_recorded 
ON memory.health_metrics(entity_id, metric_type, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_daily_readiness_entity_date 
ON dna.daily_readiness(entity_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_energy_patterns_entity_hour 
ON dna.energy_patterns(entity_id, hour_of_day);

-- ============================================================================
-- Grant permissions (if needed)
-- ============================================================================

-- Assuming there's a nucleus_app role
-- GRANT SELECT, INSERT, UPDATE, DELETE ON memory.calendar_events TO nucleus_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON memory.email_messages TO nucleus_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON memory.briefings TO nucleus_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON dna.scheduling_preferences TO nucleus_app;

-- ============================================================================
-- Sample data for testing (optional)
-- ============================================================================

-- Insert default scheduling preferences for existing entities
-- INSERT INTO dna.scheduling_preferences (entity_id, work_start_time, work_end_time)
-- SELECT id, '09:00:00'::TIME, '17:00:00'::TIME
-- FROM dna.entity
-- WHERE NOT EXISTS (
--     SELECT 1 FROM dna.scheduling_preferences WHERE entity_id = dna.entity.id
-- );
