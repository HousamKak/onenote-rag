-- Migration 002: Create notebooks schema
-- Created: 2025-11-25
-- Purpose: Support notebook discovery, selection, and shared notebook access

-- Notebooks table
CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_datetime TIMESTAMP,
    last_modified_datetime TIMESTAMP,

    -- Shared notebook support (NEW)
    site_id TEXT NOT NULL,                    -- SharePoint site ID (required for site-scoped API access)
    is_shared BOOLEAN DEFAULT 0,              -- Whether this is a shared notebook
    user_role TEXT,                           -- User's role: Owner, Contributor, Reader
    shared_by TEXT,                           -- Display name of notebook owner (if shared)

    -- Discovery metadata (NEW)
    web_url TEXT,                             -- OneNote web URL
    sections_url TEXT,                        -- API endpoint for sections

    -- User preference (NEW)
    is_selected BOOLEAN DEFAULT 1,            -- Whether user wants to sync this notebook

    -- Sync tracking
    last_synced_at TIMESTAMP,                 -- Last successful sync time
    sync_status TEXT DEFAULT 'never_synced',  -- Status: never_synced, syncing, completed, error
    page_count INTEGER DEFAULT 0,             -- Number of pages synced
    section_count INTEGER DEFAULT 0,          -- Number of sections
    error_message TEXT,                       -- Error message if sync failed

    -- Audit timestamps
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_notebooks_user_id
    ON notebooks(user_id);

CREATE INDEX IF NOT EXISTS idx_notebooks_user_selected
    ON notebooks(user_id, is_selected);

CREATE INDEX IF NOT EXISTS idx_notebooks_shared
    ON notebooks(is_shared);

CREATE INDEX IF NOT EXISTS idx_notebooks_sync_status
    ON notebooks(sync_status);

-- Comments (for documentation)
-- Note: SQLite doesn't support inline comments, but this migration creates:
--
-- The notebooks table stores discovered notebooks with:
-- - Core OneNote metadata (id, display_name, timestamps)
-- - Shared notebook support (site_id, is_shared, user_role)
-- - User preferences (is_selected for sync control)
-- - Sync state tracking (status, counts, errors)
--
-- Key Innovation:
-- The site_id field (extracted from getNotebookFromWebUrl) enables
-- site-scoped API access for both owned and shared notebooks, eliminating
-- the need for special handling of different notebook types.
