"""
SQLite database service for settings management.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing SQLite database operations."""

    def __init__(self, db_path: str = "./data/settings.db"):
        """
        Initialize database service.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_schema()

    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    is_sensitive INTEGER NOT NULL DEFAULT 0,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on key for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_key 
                ON settings(key)
            """)

            logger.info("Database schema initialized")

    def get_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a setting by key.

        Args:
            key: Setting key

        Returns:
            Setting dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM settings WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def get_all_settings(self) -> List[Dict[str, Any]]:
        """
        Get all settings.

        Returns:
            List of setting dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings ORDER BY key")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def set_setting(
        self,
        key: str,
        value: str,
        is_sensitive: bool = False,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a setting.

        Args:
            key: Setting key
            value: Setting value
            is_sensitive: Whether the setting contains sensitive data
            description: Optional description

        Returns:
            Updated setting dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if setting exists
            existing = self.get_setting(key)

            if existing:
                # Update existing setting
                cursor.execute("""
                    UPDATE settings 
                    SET value = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (value, key))
            else:
                # Insert new setting
                cursor.execute("""
                    INSERT INTO settings (key, value, is_sensitive, description)
                    VALUES (?, ?, ?, ?)
                """, (key, value, int(is_sensitive), description))

            # Return the updated setting
            return self.get_setting(key)

    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting.

        Args:
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def clear_all_settings(self) -> int:
        """
        Clear all settings from database.

        Returns:
            Number of settings deleted
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM settings")
            return cursor.rowcount
