"""
Command-line interface for database management.
 
Usage:
    python cli.py status              # Show migration status
    python cli.py migrate             # Apply all pending migrations
    python cli.py migrate-to --version 1  # Migrate to specific version
"""
import click
import sys
from pathlib import Path
 
# Add backend to path so we can import modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
 
from migrations.manager import MigrationManager, Migration
from migrations.versions import (
    migration_001_initial_schema,
    migration_002_add_needs_resync,
    migration_003_initial_notebooks_schema
)
 
 
def get_migration_manager(db_path: str) -> MigrationManager:
    """
    Create and configure migration manager with all migrations.
   
    Args:
        db_path: Path to SQLite database
       
    Returns:
        Configured MigrationManager instance
    """
    manager = MigrationManager(db_path)
   
    # Register all migrations in order
    manager.register_migration(Migration(
        version=1,
        description="Initial database schema (document_cache.db)",
        up_func=migration_001_initial_schema.up,
        down_func=migration_001_initial_schema.down
    ))
   
    manager.register_migration(Migration(
        version=2,
        description="Add needs_resync column for retry logic",
        up_func=migration_002_add_needs_resync.up,
        down_func=migration_002_add_needs_resync.down
    ))
   
    manager.register_migration(Migration(
        version=3,
        description="Initial notebooks schema (notebooks.db)",
        up_func=migration_003_initial_notebooks_schema.up,
        down_func=migration_003_initial_notebooks_schema.down
    ))
   
    # Add more migrations here as they are created
    # manager.register_migration(Migration(
    #     version=4,
    #     description="...",
    #     up_func=migration_004_xxx.up,
    #     down_func=migration_004_xxx.down
    # ))
   
    return manager
 
 
@click.group()
def cli():
    """OneNote RAG Database Management CLI"""
    pass
 
 
@cli.command()
@click.option('--db', default='./data/document_cache.db', help='Database path')
def migrate(db):
    """Apply all pending migrations."""
    click.echo(f"🔄 Running migrations on: {db}\n")
   
    manager = get_migration_manager(db)
   
    try:
        count = manager.migrate()
        if count > 0:
            click.echo(f"\n✅ Successfully applied {count} migration(s)")
        else:
            click.echo("\n✅ No migrations needed - database is up to date")
    except Exception as e:
        click.echo(f"\n❌ Migration failed: {e}", err=True)
        sys.exit(1)
 
 
@cli.command()
@click.option('--db', default='./data/document_cache.db', help='Database path')
def status(db):
    """Show migration status."""
    manager = get_migration_manager(db)
    manager.show_status()
 
 
@cli.command('migrate-to')
@click.option('--db', default='./data/document_cache.db', help='Database path')
@click.option('--version', type=int, required=True, help='Target version')
def migrate_to(db, version):
    """Migrate to a specific version."""
    click.echo(f"🔄 Migrating to version {version} on: {db}\n")
   
    manager = get_migration_manager(db)
   
    try:
        count = manager.migrate(target_version=version)
        if count > 0:
            click.echo(f"\n✅ Successfully migrated to version {version}")
        else:
            click.echo(f"\n✅ Already at version {version}")
    except Exception as e:
        click.echo(f"\n❌ Migration failed: {e}", err=True)
        sys.exit(1)
 
 
@cli.command()
@click.option('--db', default='./data/document_cache.db', help='Database path')
def init(db):
    """Initialize migration tracking (creates schema_migrations table)."""
    click.echo(f"🔄 Initializing migration tracking on: {db}\n")
   
    manager = get_migration_manager(db)
    manager.init_migration_table()
   
    click.echo("✅ Migration tracking initialized")
 
 
if __name__ == '__main__':
    cli()
 