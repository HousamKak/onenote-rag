# Database Migration System
 
Complete database migration system for the OneNote RAG application with version tracking, auto-migration on startup, and CLI management.
 
---
 
## Quick Start
 
### Check Migration Status
 
```bash
cd backend
python cli.py status
```
 
### Apply All Pending Migrations
 
```bash
cd backend
python cli.py migrate
```
 
### Migrate to Specific Version
 
```bash
cd backend
python cli.py migrate-to --version 2
```
 
---
 
## System Overview
 
### Databases Managed
 
| Database | Migrations | Auto-Applied | Description |
|----------|------------|--------------|-------------|
| **document_cache.db** | ✅ Yes (001, 002) | ✅ On startup | OneNote content cache |
| **notebooks.db** | ✅ Yes (003) | ✅ On startup | Notebook discovery & preferences |
| **settings.db** | ❌ No | Inline schema | Application config (simple, stable) |
| **chroma_db/** | N/A | Managed by ChromaDB | Vector embeddings |
 
### Migration Versions
 
| Version | Database | Description | Status |
|---------|----------|-------------|--------|
| **001** | document_cache.db | Initial schema (documents, images, sync) | ✅ Complete |
| **002** | document_cache.db | Add `needs_resync` column | ✅ Complete |
| **003** | notebooks.db | Initial schema (notebooks table) | ✅ Complete |
 
---
 
## Architecture
 
### Directory Structure
 
```
backend/
├── migrations/
│   ├── __init__.py                              # Package init
│   ├── manager.py                               # MigrationManager class
│   ├── 001_create_document_cache_schema.sql     # Source SQL (document_cache)
│   ├── 002_create_notebooks_schema.sql          # Source SQL (notebooks)
│   └── versions/
│       ├── __init__.py                          # Version registry
│       ├── 001_initial_schema.py                # document_cache initial
│       ├── 002_add_needs_resync.py              # needs_resync column
│       └── 003_initial_notebooks_schema.py      # notebooks initial
│
├── cli.py                                       # CLI interface
└── main.py                                      # Auto-migration on startup
```
 
### Migration Flow
 
```
Application Startup (main.py)
    ↓
Check document_cache.db migrations
    ├─ Version 1: Initial schema
    └─ Version 2: needs_resync column
    ↓
Initialize DocumentCacheDB (schema exists)
    ↓
Check notebooks.db migrations
    └─ Version 3: Initial schema
    ↓
Initialize NotebookDB (schema exists)
    ↓
Initialize DatabaseService (settings.db - inline)
    ↓
Application Ready ✅
```
 
---
 
## Auto-Migration on Startup
 
### How It Works
 
Migrations are **automatically applied** when the application starts:
 
```python
# In main.py lifespan()
 
# 1. Check for pending migrations
migration_manager = get_migration_manager(cache_db_path)
pending_count = len(migration_manager.get_pending_migrations())
 
# 2. Apply if needed
if pending_count > 0:
    migration_manager.migrate()
    logger.info("✅ Migrations applied")
 
# 3. Initialize database services
cache_db = DocumentCacheDB(db_path=cache_db_path)
```
 
### Benefits
 
- ✅ **Zero manual intervention** - Migrations apply automatically
- ✅ **Fail-safe** - App won't start if migrations fail
- ✅ **Idempotent** - Safe to run multiple times
- ✅ **Version tracked** - `schema_migrations` table tracks applied migrations
 
---
 
## CLI Usage
 
### Commands
 
#### 1. Status - Check Migration State
 
```bash
python cli.py status
```
 
**Output:**
```
======================================================================
📊 Database Migration Status
======================================================================
Database: ./data/document_cache.db
Current Version: 3
======================================================================
 
✅ Applied Migrations:
  001 - Initial database schema (document_cache.db)
       Applied: 2025-12-05 10:30:00 (250ms)
  002 - Add needs_resync column for retry logic
       Applied: 2025-12-05 10:30:01 (50ms)
  003 - Initial notebooks schema (notebooks.db)
       Applied: 2025-12-05 10:30:02 (100ms)
 
✅ All migrations up to date!
 
======================================================================
```
 
#### 2. Migrate - Apply Pending Migrations
 
```bash
python cli.py migrate
```
 
**Output:**
```
🔄 Running migrations on: ./data/document_cache.db
 
Found 1 pending migration(s)
Applying migration 2: Add needs_resync column for retry logic
✅ Migration 2 applied successfully (50ms)
✅ All migrations applied. Current version: 2
 
✅ Successfully applied 1 migration(s)
```
 
#### 3. Migrate To - Target Specific Version
 
```bash
python cli.py migrate-to --version 1
```
 
#### 4. Init - Initialize Migration Tracking
 
```bash
python cli.py init
```
 
(Creates `schema_migrations` table - done automatically by `migrate`)
 
---
 
## Creating New Migrations
 
### Step 1: Create Migration File
 
```python
# migrations/versions/004_add_new_feature.py
 
"""
Migration 004: Add new feature.
 
Description of what this migration does.
"""
import sqlite3
 
 
def up(conn: sqlite3.Connection):
    """Apply migration."""
    cursor = conn.cursor()
   
    # Your migration code here
    cursor.execute("""
        ALTER TABLE onenote_documents
        ADD COLUMN new_field TEXT
    """)
   
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_new_field
        ON onenote_documents(new_field)
    """)
   
    conn.commit()
    print("✅ Added new_field column")
 
 
def down(conn: sqlite3.Connection):
    """Rollback migration (optional)."""
    cursor = conn.cursor()
   
    # Rollback code (if possible in SQLite)
    cursor.execute("DROP INDEX IF EXISTS idx_new_field")
   
    # Note: SQLite < 3.35.0 doesn't support DROP COLUMN
    # You may need to recreate the table
   
    conn.commit()
    print("✅ Rolled back new_field")
```
 
### Step 2: Register in versions/__init__.py
 
```python
from migrations.versions import (
    migration_001_initial_schema,
    migration_002_add_needs_resync,
    migration_003_initial_notebooks_schema,
    migration_004_add_new_feature  # ADD THIS
)
 
__all__ = [
    'migration_001_initial_schema',
    'migration_002_add_needs_resync',
    'migration_003_initial_notebooks_schema',
    'migration_004_add_new_feature'  # ADD THIS
]
```
 
### Step 3: Register in CLI
 
```python
# In cli.py get_migration_manager()
 
manager.register_migration(Migration(
    version=4,
    description="Add new feature",
    up_func=migration_004_add_new_feature.up,
    down_func=migration_004_add_new_feature.down
))
```
 
### Step 4: Test
 
```bash
# Check status
python cli.py status
 
# Apply migration
python cli.py migrate
 
# Verify
python cli.py status
```
 
---
 
## Migration Best Practices
 
### ✅ Do's
 
1. **Always version migrations sequentially** - No gaps (001, 002, 003...)
2. **Make migrations idempotent** - Safe to run multiple times
3. **Test on fresh database** - Verify clean install works
4. **Test on existing database** - Verify upgrade path works
5. **Write descriptive comments** - Explain WHY, not just WHAT
6. **Use transactions** - All changes in `up()` commit together
7. **Add indexes** - Create indexes for new columns
 
### ❌ Don'ts
 
1. **Don't modify old migrations** - They may have already been applied
2. **Don't skip versions** - Migrations must be sequential
3. **Don't assume data** - Handle empty tables gracefully
4. **Don't use DROP COLUMN** - Not supported in SQLite < 3.35.0
5. **Don't forget down()** - Provide rollback when possible
 
### SQLite Limitations
 
**No DROP COLUMN** (before 3.35.0):
```sql
-- ❌ Won't work in older SQLite
ALTER TABLE mytable DROP COLUMN mycolumn;
 
-- ✅ Workaround: Recreate table
CREATE TABLE mytable_new (...columns without mycolumn...);
INSERT INTO mytable_new SELECT ...columns... FROM mytable;
DROP TABLE mytable;
ALTER TABLE mytable_new RENAME TO mytable;
```
 
**No RENAME COLUMN** (before 3.25.0):
```sql
-- ❌ Won't work in older SQLite
ALTER TABLE mytable RENAME COLUMN old TO new;
 
-- ✅ Workaround: Recreate table or add new column
```
 
---
 
## Migration Tracking
 
### schema_migrations Table
 
The system tracks applied migrations in a special table:
 
```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER
);
```
 
**Example data:**
 
| version | description | applied_at | execution_time_ms |
|---------|-------------|------------|-------------------|
| 1 | Initial database schema | 2025-12-05 10:30:00 | 250 |
| 2 | Add needs_resync column | 2025-12-05 10:30:01 | 50 |
| 3 | Initial notebooks schema | 2025-12-05 10:30:02 | 100 |
 
### Query Current Version
 
```sql
SELECT MAX(version) FROM schema_migrations;
-- Returns: 3
```
 
### Check Pending Migrations
 
```python
manager = get_migration_manager("./data/document_cache.db")
pending = manager.get_pending_migrations()
print(f"Pending: {len(pending)} migration(s)")
```
 
---
 
## Testing
 
### Test Fresh Installation
 
```bash
# 1. Delete databases
rm backend/data/document_cache.db
rm backend/data/notebooks.db
 
# 2. Start application
cd backend
python main.py
 
# Expected:
# ✅ "Found 3 pending migration(s), applying now..."
# ✅ "✅ Database migrations applied successfully"
# ✅ "✅ Notebooks database migrations applied successfully"
```
 
### Test Existing Installation
 
```bash
# 1. Keep existing databases
 
# 2. Start application
cd backend
python main.py
 
# Expected:
# ✅ "✅ Database is up to date (no pending migrations)"
# ✅ "✅ Notebooks database is up to date"
```
 
### Test Manual Migration
 
```bash
# Check status
python cli.py status
 
# Apply migrations
python cli.py migrate
 
# Check again
python cli.py status
```
 
---
 
## Troubleshooting
 
### Issue: "Migration failed: no such table"
 
**Cause:** Trying to migrate a table that doesn't exist yet
 
**Solution:** Ensure migration 001 (initial schema) is applied first
 
```bash
python cli.py status  # Check current version
python cli.py migrate  # Apply all migrations
```
 
### Issue: "Database is locked"
 
**Cause:** Another process has the database open
 
**Solution:** Close all database connections
 
```bash
# Check what's using the database (Linux/Mac)
lsof | grep document_cache.db
 
# Force close application
pkill -9 python
```
 
### Issue: "duplicate column name"
 
**Cause:** Migration already partially applied
 
**Solution:** Migration is idempotent - will skip if column exists
 
```python
# In migration code:
try:
    cursor.execute("ALTER TABLE mytable ADD COLUMN mycolumn TEXT")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("ℹ️  Column already exists, skipping")
    else:
        raise
```
 
### Issue: "Migration version mismatch"
 
**Cause:** Migration files out of sync with `schema_migrations` table
 
**Solution:** Check migration history
 
```sql
-- In sqlite3
SELECT * FROM schema_migrations ORDER BY version;
```
 
---
 
## Production Deployment
 
### Deployment Checklist
 
- [ ] **Backup database** before deployment
- [ ] **Test migrations** on staging environment
- [ ] **Check migration status** - `python cli.py status`
- [ ] **Apply migrations** - `python cli.py migrate`
- [ ] **Verify application starts** - Check logs
- [ ] **Verify data integrity** - Run queries
- [ ] **Monitor errors** - Check application logs
 
### Backup Strategy
 
```bash
# Before deployment
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz backend/data/
 
# After successful deployment
mv backup-*.tar.gz backups/
```
 
### Rollback Plan
 
```bash
# 1. Stop application
pkill -9 python
 
# 2. Restore backup
tar -xzf backup-20251205-103000.tar.gz
 
# 3. Restart application
python main.py
```
 
---
 
## FAQ
 
### Q: Do I need to run migrations manually?
 
**A: No** - Migrations are automatically applied on application startup. You only need the CLI for checking status or troubleshooting.
 
### Q: What happens if a migration fails?
 
**A:** The application will **fail to start** and log the error. This is intentional - it prevents running with an inconsistent schema.
 
### Q: Can I skip migrations?
 
**A:** No - migrations must be applied sequentially. The system tracks which versions have been applied and only runs pending ones.
 
### Q: How do I rollback a migration?
 
**A:** Currently, rollback is not fully implemented due to SQLite limitations. Best practice is to restore from backup.
 
### Q: Can I modify an applied migration?
 
**A:** **No** - Never modify migrations that have been applied. Instead, create a new migration to make changes.
 
### Q: What about settings.db?
 
**A:** `settings.db` uses a simple inline schema (1 table, stable). It doesn't need migrations. The schema is created on first access.
 
---
 
## Summary
 
✅ **Complete migration system** with version tracking  
✅ **Auto-migration** on application startup  
✅ **CLI tools** for manual management  
✅ **Idempotent** migrations (safe to run multiple times)  
✅ **Production-ready** with proper error handling  
 
**Next Steps:**
1. Test fresh installation
2. Test existing installation upgrade
3. Monitor logs during deployment
4. Create backups before production deployment
 
---
 
**Last Updated:** December 5, 2025  
**Migration System Version:** 1.0  
**Current Schema Version:** 3
 
