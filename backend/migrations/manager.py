"""
Database migration manager with version tracking.
"""
import sqlite3
import logging
from typing import List, Callable
from datetime import datetime
 
logger = logging.getLogger(__name__)
 
 
class Migration:
    """Represents a single migration."""
   
    def __init__(self, version: int, description: str, up_func: Callable, down_func: Callable = None):
        """
        Initialize migration.
       
        Args:
            version: Migration version number (must be unique)
            description: Human-readable description
            up_func: Function to apply migration (receives sqlite3.Connection)
            down_func: Optional function to rollback migration
        """
        self.version = version
        self.description = description
        self.up_func = up_func
        self.down_func = down_func
   
    def apply(self, conn: sqlite3.Connection):
        """Apply the migration."""
        self.up_func(conn)
   
    def rollback(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        if self.down_func:
            self.down_func(conn)
        else:
            raise NotImplementedError(f"Migration {self.version} has no rollback function")
 
 
class MigrationManager:
    """Manages database schema migrations with version tracking."""
   
    def __init__(self, db_path: str):
        """
        Initialize migration manager.
       
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations: List[Migration] = []
   
    def register_migration(self, migration: Migration):
        """
        Register a migration.
       
        Args:
            migration: Migration to register
        """
        # Check for duplicate version
        if any(m.version == migration.version for m in self.migrations):
            raise ValueError(f"Migration version {migration.version} already registered")
       
        self.migrations.append(migration)
        # Keep sorted by version
        self.migrations.sort(key=lambda m: m.version)
   
    def init_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER
            )
        """)
       
        conn.commit()
        conn.close()
        logger.debug("Migration tracking table initialized")
   
    def get_current_version(self) -> int:
        """
        Get the current schema version.
       
        Returns:
            Current version number (0 if no migrations applied)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
       
        try:
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            result = cursor.fetchone()[0]
            return result or 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0
        finally:
            conn.close()
   
    def get_applied_migrations(self) -> List[tuple]:
        """
        Get list of applied migrations.
       
        Returns:
            List of (version, description, applied_at, execution_time_ms) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
       
        try:
            cursor.execute("""
                SELECT version, description, applied_at, execution_time_ms
                FROM schema_migrations
                ORDER BY version
            """)
            return cursor.fetchall()
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return []
        finally:
            conn.close()
   
    def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations.
       
        Returns:
            List of Migration objects that haven't been applied yet
        """
        current_version = self.get_current_version()
        return [m for m in self.migrations if m.version > current_version]
   
    def apply_migration(self, migration: Migration):
        """
        Apply a single migration.
       
        Args:
            migration: Migration to apply
           
        Raises:
            Exception: If migration fails
        """
        start_time = datetime.now()
       
        conn = sqlite3.connect(self.db_path)
        try:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
           
            # Apply migration
            migration.apply(conn)
           
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
           
            # Record migration
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO schema_migrations (version, description, execution_time_ms)
                   VALUES (?, ?, ?)""",
                (migration.version, migration.description, execution_time)
            )
           
            conn.commit()
            logger.info(f"✅ Migration {migration.version} applied successfully ({execution_time}ms)")
           
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Migration {migration.version} failed: {e}")
            raise
        finally:
            conn.close()
   
    def migrate(self, target_version: int = None):
        """
        Apply all pending migrations up to target_version.
       
        Args:
            target_version: Optional target version. If None, apply all pending migrations.
           
        Returns:
            Number of migrations applied
        """
        self.init_migration_table()
       
        pending = self.get_pending_migrations()
       
        if target_version:
            pending = [m for m in pending if m.version <= target_version]
       
        if not pending:
            logger.info("No pending migrations")
            return 0
       
        logger.info(f"Found {len(pending)} pending migration(s)")
       
        for migration in pending:
            self.apply_migration(migration)
       
        current_version = self.get_current_version()
        logger.info(f"✅ All migrations applied. Current version: {current_version}")
       
        return len(pending)
   
    def show_status(self):
        """Print migration status to console."""
        current_version = self.get_current_version()
        pending = self.get_pending_migrations()
        applied = self.get_applied_migrations()
       
        print(f"\n{'='*70}")
        print(f"📊 Database Migration Status")
        print(f"{'='*70}")
        print(f"Database: {self.db_path}")
        print(f"Current Version: {current_version}")
        print(f"{'='*70}\n")
       
        # Show applied migrations
        if applied:
            print("✅ Applied Migrations:")
            for version, desc, applied_at, exec_time in applied:
                print(f"  {version:03d} - {desc}")
                print(f"       Applied: {applied_at} ({exec_time}ms)")
        else:
            print("No migrations applied yet")
       
        # Show pending migrations
        if pending:
            print(f"\n⏳ Pending Migrations ({len(pending)}):")
            for migration in pending:
                print(f"  {migration.version:03d} - {migration.description}")
        else:
            print("\n✅ All migrations up to date!")
       
        print(f"\n{'='*70}\n")
 