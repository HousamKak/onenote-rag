"""
Migration 002: Add needs_resync column.
 
Adds support for marking pages that need to be re-synced due to:
- Empty/missing content
- API failures during sync
- Manual resync requests
"""
import sqlite3
 
 
def up(conn: sqlite3.Connection):
    """Add needs_resync column and mark empty pages."""
    cursor = conn.cursor()
   
    # Add needs_resync column (default FALSE)
    try:
        cursor.execute("""
            ALTER TABLE onenote_documents
            ADD COLUMN needs_resync INTEGER DEFAULT 0
        """)
        print("✅ Added needs_resync column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️  Column needs_resync already exists")
        else:
            raise
   
    # Create index for efficient querying
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_needs_resync
        ON onenote_documents(needs_resync)
        WHERE needs_resync = 1
    """)
    print("✅ Created index idx_needs_resync")
   
    # Mark all empty pages for resync
    cursor.execute("""
        UPDATE onenote_documents
        SET needs_resync = 1
        WHERE (html_content = '' OR html_content IS NULL OR length(html_content) = 0)
          AND (plain_text = '' OR plain_text IS NULL OR length(plain_text) = 0)
    """)
    marked_count = cursor.rowcount
    print(f"✅ Marked {marked_count} empty pages for resync")
   
    conn.commit()
 
 
def down(conn: sqlite3.Connection):
    """
    Rollback needs_resync column.
   
    Note: SQLite doesn't support DROP COLUMN before version 3.35.0.
    For a proper rollback, you'd need to recreate the table without the column.
    """
    # This is a simplified rollback - just remove the index
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_needs_resync")
    conn.commit()
   
    # Note: The column itself cannot be easily removed in older SQLite versions
    print("⚠️  Warning: Column 'needs_resync' cannot be removed in SQLite < 3.35.0")
    print("    The column will remain but won't be used.")
 