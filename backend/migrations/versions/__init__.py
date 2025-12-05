"""
Migration versions package.
"""
# Import migration modules (using importlib since filenames start with numbers)
import importlib
 
# Import each migration module
migration_001_initial_schema = importlib.import_module('.001_initial_schema', package='migrations.versions')
migration_002_add_needs_resync = importlib.import_module('.002_add_needs_resync', package='migrations.versions')
migration_003_initial_notebooks_schema = importlib.import_module('.003_initial_notebooks_schema', package='migrations.versions')
 
__all__ = [
    'migration_001_initial_schema',
    'migration_002_add_needs_resync',
    'migration_003_initial_notebooks_schema'
]
 