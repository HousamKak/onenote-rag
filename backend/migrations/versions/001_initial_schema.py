"""
Migration 001: Initial database schema.
 
Creates all tables for OneNote document cache:
- onenote_documents: Store OneNote pages with content
- onenote_images: Store image metadata
- sync_state: Track sync status per entity
- sync_history: Audit trail of all sync operations
- sync_jobs: Active/historical sync jobs
- notebooks: User notebook selection
"""
import sqlite3
from pathlib import Path
 
 
def up(conn: sqlite3.Connection):
    """Create initial schema."""
    cursor = conn.cursor()
   
    # Create schema (inline definition below)
    _create_schema_inline(cursor)
   
    conn.commit()
 
 
def _create_schema_inline(cursor: sqlite3.Cursor):
    """Create schema inline (fallback if SQL file not found)."""
   
    # OneNote documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onenote_documents (
            page_id TEXT PRIMARY KEY NOT NULL,
            html_content TEXT NOT NULL,
            plain_text TEXT,
            notebook_id TEXT NOT NULL,
            notebook_name TEXT,
            section_id TEXT NOT NULL,
            section_name TEXT,
            page_title TEXT NOT NULL,
            author TEXT,
            created_date TIMESTAMP,
            modified_date TIMESTAMP NOT NULL,
            source_url TEXT,
            tags TEXT,
            last_synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sync_version INTEGER NOT NULL DEFAULT 1,
            is_deleted INTEGER DEFAULT 0,
            indexed_at TIMESTAMP,
            chunk_count INTEGER DEFAULT 0,
            image_count INTEGER DEFAULT 0,
            extra_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
   
    # Indexes for onenote_documents
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_modified_date ON onenote_documents(modified_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_last_synced ON onenote_documents(last_synced_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_notebook_section ON onenote_documents(notebook_id, section_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_indexed_status ON onenote_documents(indexed_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_is_deleted ON onenote_documents(is_deleted)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_onenote_page_title ON onenote_documents(page_title)")
   
    # OneNote images table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onenote_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id TEXT NOT NULL,
            image_index INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_size_bytes INTEGER,
            mime_type TEXT,
            alt_text TEXT,
            vision_analysis TEXT,
            analyzed_at TIMESTAMP,
            graph_resource_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES onenote_documents(page_id) ON DELETE CASCADE,
            UNIQUE(page_id, image_index)
        )
    """)
   
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_page_id ON onenote_images(page_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_analyzed ON onenote_images(analyzed_at)")
   
    # Sync state table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            entity_name TEXT,
            last_full_sync_at TIMESTAMP,
            last_incremental_sync_at TIMESTAMP,
            next_sync_due_at TIMESTAMP,
            total_pages_synced INTEGER DEFAULT 0,
            pages_added_last_sync INTEGER DEFAULT 0,
            pages_updated_last_sync INTEGER DEFAULT 0,
            pages_deleted_last_sync INTEGER DEFAULT 0,
            last_sync_duration_seconds INTEGER,
            last_sync_error TEXT,
            api_calls_last_sync INTEGER DEFAULT 0,
            avg_api_latency_ms INTEGER,
            sync_status TEXT DEFAULT 'idle',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entity_type, entity_id)
        )
    """)
   
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_state_entity ON sync_state(entity_type, entity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_state_next_sync ON sync_state(next_sync_due_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_state_status ON sync_state(sync_status)")
   
    # Sync history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            duration_seconds INTEGER,
            notebook_id TEXT,
            section_id TEXT,
            status TEXT NOT NULL,
            pages_fetched INTEGER DEFAULT 0,
            pages_added INTEGER DEFAULT 0,
            pages_updated INTEGER DEFAULT 0,
            pages_deleted INTEGER DEFAULT 0,
            pages_skipped INTEGER DEFAULT 0,
            api_calls_made INTEGER DEFAULT 0,
            errors_encountered INTEGER DEFAULT 0,
            error_details TEXT,
            total_wait_time_seconds INTEGER DEFAULT 0,
            rate_limit_hits INTEGER DEFAULT 0,
            triggered_by TEXT,
            user_id TEXT,
            job_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
   
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_started ON sync_history(started_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_status ON sync_history(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_history_job_id ON sync_history(job_id)")
   
    # Sync jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_jobs (
            job_id TEXT PRIMARY KEY,
            sync_type TEXT NOT NULL,
            notebook_ids TEXT,
            status TEXT NOT NULL,
            progress_percent REAL DEFAULT 0.0,
            current_phase TEXT,
            total_pages INTEGER DEFAULT 0,
            pages_processed INTEGER DEFAULT 0,
            pages_added INTEGER DEFAULT 0,
            pages_updated INTEGER DEFAULT 0,
            pages_deleted INTEGER DEFAULT 0,
            api_calls_made INTEGER DEFAULT 0,
            elapsed_seconds INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
   
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_jobs_created ON sync_jobs(created_at)")
   
    # Notebooks table (for user selection)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            site_id TEXT,
            is_shared INTEGER DEFAULT 0,
            owner_name TEXT,
            is_selected INTEGER DEFAULT 0,
            last_synced_at TIMESTAMP,
            sync_status TEXT,
            page_count INTEGER DEFAULT 0,
            last_modified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, user_id)
        )
    """)
   
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notebooks_selected ON notebooks(user_id, is_selected)")
 
 
def down(conn: sqlite3.Connection):
    """Rollback initial schema (drop all tables)."""
    cursor = conn.cursor()
   
    # Drop tables in reverse order (respecting foreign keys)
    cursor.execute("DROP TABLE IF EXISTS notebooks")
    cursor.execute("DROP TABLE IF EXISTS sync_jobs")
    cursor.execute("DROP TABLE IF EXISTS sync_history")
    cursor.execute("DROP TABLE IF EXISTS sync_state")
    cursor.execute("DROP TABLE IF EXISTS onenote_images")
    cursor.execute("DROP TABLE IF EXISTS onenote_documents")
   
    conn.commit()