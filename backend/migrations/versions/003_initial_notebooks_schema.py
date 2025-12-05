"""
Migration 003: Initial notebooks database schema.
 
Creates notebooks table for:
- Notebook discovery (owned + shared)
- User preferences (selection)
- Sync state tracking
"""
import sqlite3
from pathlib import Path
 
 
def up(conn: sqlite3.Connection):
    """Create notebooks schema."""
    cursor = conn.cursor()
   
    # Create schema (inline definition below)
    _create_notebooks_schema_inline(cursor)
   
    conn.commit()
    print("✅ Created notebooks schema")
 
 
def _create_notebooks_schema_inline(cursor: sqlite3.Cursor):
    """Create notebooks schema inline (fallback)."""
   
    # Notebooks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created_datetime TIMESTAMP,
            last_modified_datetime TIMESTAMP,
 
            -- Shared notebook support (critical for site-scoped API access)
            site_id TEXT NOT NULL,
            is_shared BOOLEAN DEFAULT 0,
            user_role TEXT,
            shared_by TEXT,
 
            -- Discovery metadata
            web_url TEXT,
            sections_url TEXT,
 
            -- User preference (sync control)
            is_selected BOOLEAN DEFAULT 1,
 
            -- Sync tracking
            last_synced_at TIMESTAMP,
            sync_status TEXT DEFAULT 'never_synced',
            page_count INTEGER DEFAULT 0,
            section_count INTEGER DEFAULT 0,
            error_message TEXT,
 
            -- Audit timestamps
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
   
    # Indexes for query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notebooks_user_id
            ON notebooks(user_id)
    """)
   
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notebooks_user_selected
            ON notebooks(user_id, is_selected)
    """)
   
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notebooks_shared
            ON notebooks(is_shared)
    """)
   
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notebooks_sync_status
            ON notebooks(sync_status)
    """)
 
 
def down(conn: sqlite3.Connection):
    """Rollback notebooks schema."""
    cursor = conn.cursor()
   
    # Drop indexes first
    cursor.execute("DROP INDEX IF EXISTS idx_notebooks_sync_status")
    cursor.execute("DROP INDEX IF EXISTS idx_notebooks_shared")
    cursor.execute("DROP INDEX IF EXISTS idx_notebooks_user_selected")
    cursor.execute("DROP INDEX IF EXISTS idx_notebooks_user_id")
   
    # Drop table
    cursor.execute("DROP TABLE IF EXISTS notebooks")
   
    conn.commit()
    print("✅ Rolled back notebooks schema")
 