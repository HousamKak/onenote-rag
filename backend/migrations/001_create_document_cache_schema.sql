-- Migration: Create OneNote Document Cache Schema
-- Version: 001
-- Description: Local persistence layer for OneNote documents to reduce Graph API dependency
-- Compatible with: SQLite (current) and PostgreSQL (future)

-- =============================================================================
-- Table 1: OneNote Documents (Raw Storage)
-- =============================================================================
CREATE TABLE IF NOT EXISTS onenote_documents (
    page_id TEXT PRIMARY KEY NOT NULL,

    -- Content
    html_content TEXT NOT NULL,
    plain_text TEXT,

    -- Hierarchy
    notebook_id TEXT NOT NULL,
    notebook_name TEXT,
    section_id TEXT NOT NULL,
    section_name TEXT,
    page_title TEXT NOT NULL,

    -- Metadata
    author TEXT,
    created_date TIMESTAMP,
    modified_date TIMESTAMP NOT NULL,
    source_url TEXT,
    tags TEXT,  -- Comma-separated for SQLite, JSON array in PostgreSQL

    -- Sync tracking
    last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_version INTEGER NOT NULL DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,  -- Boolean as INTEGER for SQLite

    -- Indexing status
    indexed_at TIMESTAMP,
    chunk_count INTEGER DEFAULT 0,
    image_count INTEGER DEFAULT 0,

    -- Additional metadata (JSON string)
    extra_metadata TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for onenote_documents
CREATE INDEX IF NOT EXISTS idx_onenote_modified_date ON onenote_documents(modified_date);
CREATE INDEX IF NOT EXISTS idx_onenote_last_synced ON onenote_documents(last_synced_at);
CREATE INDEX IF NOT EXISTS idx_onenote_notebook_section ON onenote_documents(notebook_id, section_id);
CREATE INDEX IF NOT EXISTS idx_onenote_indexed_status ON onenote_documents(indexed_at);
CREATE INDEX IF NOT EXISTS idx_onenote_is_deleted ON onenote_documents(is_deleted);
CREATE INDEX IF NOT EXISTS idx_onenote_page_title ON onenote_documents(page_title);

-- =============================================================================
-- Table 2: OneNote Images (Metadata)
-- =============================================================================
CREATE TABLE IF NOT EXISTS onenote_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL,
    image_index INTEGER NOT NULL,

    -- Storage
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    mime_type TEXT,

    -- Analysis
    alt_text TEXT,
    vision_analysis TEXT,
    analyzed_at TIMESTAMP,

    -- Graph API metadata
    graph_resource_id TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (page_id) REFERENCES onenote_documents(page_id) ON DELETE CASCADE,

    -- Unique constraint
    UNIQUE(page_id, image_index)
);

-- Indexes for onenote_images
CREATE INDEX IF NOT EXISTS idx_images_page_id ON onenote_images(page_id);
CREATE INDEX IF NOT EXISTS idx_images_analyzed ON onenote_images(analyzed_at);

-- =============================================================================
-- Table 3: Sync State (Per Entity Tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Scope
    entity_type TEXT NOT NULL,  -- 'global', 'notebook', 'section'
    entity_id TEXT NOT NULL,
    entity_name TEXT,

    -- Sync metadata
    last_full_sync_at TIMESTAMP,
    last_incremental_sync_at TIMESTAMP,
    next_sync_due_at TIMESTAMP,

    -- Statistics
    total_pages_synced INTEGER DEFAULT 0,
    pages_added_last_sync INTEGER DEFAULT 0,
    pages_updated_last_sync INTEGER DEFAULT 0,
    pages_deleted_last_sync INTEGER DEFAULT 0,
    last_sync_duration_seconds INTEGER,
    last_sync_error TEXT,

    -- Rate limiting stats
    api_calls_last_sync INTEGER DEFAULT 0,
    avg_api_latency_ms INTEGER,

    -- Status
    sync_status TEXT DEFAULT 'idle',  -- idle, syncing, error, paused, completed

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    UNIQUE(entity_type, entity_id)
);

-- Indexes for sync_state
CREATE INDEX IF NOT EXISTS idx_sync_state_entity ON sync_state(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_sync_state_next_sync ON sync_state(next_sync_due_at);
CREATE INDEX IF NOT EXISTS idx_sync_state_status ON sync_state(sync_status);

-- =============================================================================
-- Table 4: Sync History (Audit Trail)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Sync details
    sync_type TEXT NOT NULL,  -- 'full', 'incremental', 'smart'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Scope (nullable for global syncs)
    notebook_id TEXT,
    section_id TEXT,

    -- Results
    status TEXT NOT NULL,  -- success, partial_success, failed, cancelled
    pages_fetched INTEGER DEFAULT 0,
    pages_added INTEGER DEFAULT 0,
    pages_updated INTEGER DEFAULT 0,
    pages_deleted INTEGER DEFAULT 0,
    pages_skipped INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,
    error_details TEXT,

    -- Rate limiting stats
    total_wait_time_seconds REAL DEFAULT 0,
    rate_limit_hits INTEGER DEFAULT 0,

    -- Triggered by
    triggered_by TEXT,  -- 'manual', 'scheduled', 'auto', 'api'
    user_id TEXT,

    -- Job tracking
    job_id TEXT UNIQUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for sync_history
CREATE INDEX IF NOT EXISTS idx_sync_history_time ON sync_history(started_at);
CREATE INDEX IF NOT EXISTS idx_sync_history_status ON sync_history(status);
CREATE INDEX IF NOT EXISTS idx_sync_history_job_id ON sync_history(job_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_type ON sync_history(sync_type);

-- =============================================================================
-- Table 5: Sync Jobs (Active Job Tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_jobs (
    job_id TEXT PRIMARY KEY NOT NULL,

    -- Job configuration
    sync_type TEXT NOT NULL,
    notebook_ids TEXT,  -- JSON array as text for SQLite

    -- Status
    status TEXT NOT NULL,  -- queued, running, paused, completed, failed, cancelled
    progress_percent REAL DEFAULT 0,

    -- Progress tracking
    total_pages INTEGER DEFAULT 0,
    pages_processed INTEGER DEFAULT 0,
    pages_added INTEGER DEFAULT 0,
    pages_updated INTEGER DEFAULT 0,
    pages_deleted INTEGER DEFAULT 0,

    -- Performance
    api_calls_made INTEGER DEFAULT 0,
    elapsed_seconds INTEGER DEFAULT 0,
    estimated_remaining_seconds INTEGER,

    -- Error tracking
    error_count INTEGER DEFAULT 0,
    last_error TEXT,

    -- Control
    can_pause INTEGER DEFAULT 1,  -- Boolean
    can_cancel INTEGER DEFAULT 1,  -- Boolean

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for sync_jobs
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_created ON sync_jobs(created_at);

-- =============================================================================
-- Initial Data: Global Sync State
-- =============================================================================
INSERT OR IGNORE INTO sync_state (entity_type, entity_id, entity_name, sync_status)
VALUES ('global', 'global', 'All OneNote Documents', 'idle');

-- =============================================================================
-- Views for Easy Querying
-- =============================================================================

-- View: Active documents (not deleted)
CREATE VIEW IF NOT EXISTS active_documents AS
SELECT * FROM onenote_documents WHERE is_deleted = 0;

-- View: Documents needing indexing
CREATE VIEW IF NOT EXISTS documents_needing_indexing AS
SELECT
    page_id,
    page_title,
    modified_date,
    last_synced_at,
    indexed_at,
    chunk_count
FROM onenote_documents
WHERE is_deleted = 0
  AND (indexed_at IS NULL OR indexed_at < last_synced_at);

-- View: Recent sync activity
CREATE VIEW IF NOT EXISTS recent_sync_activity AS
SELECT
    sync_type,
    status,
    started_at,
    completed_at,
    duration_seconds,
    pages_fetched,
    pages_added,
    pages_updated,
    pages_deleted,
    api_calls_made
FROM sync_history
ORDER BY started_at DESC
LIMIT 50;

-- View: Sync health dashboard
CREATE VIEW IF NOT EXISTS sync_health_dashboard AS
SELECT
    (SELECT COUNT(*) FROM onenote_documents WHERE is_deleted = 0) as total_documents,
    (SELECT COUNT(*) FROM onenote_images) as total_images,
    (SELECT COUNT(*) FROM onenote_documents WHERE is_deleted = 0 AND indexed_at IS NULL) as unindexed_documents,
    (SELECT COUNT(*) FROM onenote_documents WHERE is_deleted = 0 AND datetime(last_synced_at) < datetime('now', '-24 hours')) as stale_documents,
    (SELECT last_full_sync_at FROM sync_state WHERE entity_type = 'global') as last_full_sync,
    (SELECT last_incremental_sync_at FROM sync_state WHERE entity_type = 'global') as last_incremental_sync,
    (SELECT COUNT(*) FROM sync_history WHERE status = 'failed' AND datetime(started_at) > datetime('now', '-24 hours')) as recent_failures;

-- =============================================================================
-- Triggers for Updated Timestamps
-- =============================================================================

-- Trigger: Update updated_at on onenote_documents
CREATE TRIGGER IF NOT EXISTS update_onenote_documents_timestamp
AFTER UPDATE ON onenote_documents
BEGIN
    UPDATE onenote_documents SET updated_at = CURRENT_TIMESTAMP WHERE page_id = NEW.page_id;
END;

-- Trigger: Update updated_at on onenote_images
CREATE TRIGGER IF NOT EXISTS update_onenote_images_timestamp
AFTER UPDATE ON onenote_images
BEGIN
    UPDATE onenote_images SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: Update updated_at on sync_state
CREATE TRIGGER IF NOT EXISTS update_sync_state_timestamp
AFTER UPDATE ON sync_state
BEGIN
    UPDATE sync_state SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: Update updated_at on sync_jobs
CREATE TRIGGER IF NOT EXISTS update_sync_jobs_timestamp
AFTER UPDATE ON sync_jobs
BEGIN
    UPDATE sync_jobs SET updated_at = CURRENT_TIMESTAMP WHERE job_id = NEW.job_id;
END;

-- =============================================================================
-- Migration Complete
-- =============================================================================
