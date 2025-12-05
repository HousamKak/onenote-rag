"""
Database service for OneNote notebook management.
 
Handles storage and retrieval of notebook metadata including:
- Discovered notebooks (owned and shared)
- User notebook preferences (selected/unselected)
- Sync status per notebook
"""
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
 
from models.notebook import Notebook, NotebookStatus
 
logger = logging.getLogger(__name__)
 
 
class NotebookDB:
    """Database service for notebook management."""
 
    def __init__(self, db_path: str = "data/notebooks.db"):
        """
        Initialize notebook database.
 
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()
        logger.info(f"NotebookDB initialized at {db_path}")
 
    def _ensure_db_exists(self):
        """
        Ensure database file exists.
       
        Note: Schema migrations are now handled by the migration system in main.py
        during application startup. This just ensures the file exists.
        """
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
       
        # Just ensure the file exists (migrations are handled in main.py)
        if not Path(self.db_path).exists():
            logger.info("Creating new database file (schema will be created by migrations)")
            conn = self._get_connection()
            conn.close()
 
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
 
    # =========================================================================
    # NOTEBOOK OPERATIONS
    # =========================================================================
 
    def upsert_notebook(self, notebook: Notebook) -> None:
        """
        Insert or update a notebook.
 
        Args:
            notebook: Notebook object to upsert
        """
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO notebooks (
                    id, user_id, display_name, created_datetime, last_modified_datetime,
                    site_id, is_shared, user_role, shared_by,
                    web_url, sections_url, is_selected, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    last_modified_datetime = excluded.last_modified_datetime,
                    site_id = excluded.site_id,
                    is_shared = excluded.is_shared,
                    user_role = excluded.user_role,
                    shared_by = excluded.shared_by,
                    web_url = excluded.web_url,
                    sections_url = excluded.sections_url,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                notebook.id,
                notebook.user_id,
                notebook.display_name,
                notebook.created_datetime,
                notebook.last_modified_datetime,
                notebook.site_id,
                notebook.is_shared,
                notebook.user_role,
                notebook.shared_by,
                notebook.web_url,
                notebook.sections_url,
                notebook.is_selected
            ))
            conn.commit()
            logger.debug(f"Upserted notebook: {notebook.id} ({notebook.display_name})")
        finally:
            conn.close()
 
    def get_notebook(self, notebook_id: str, user_id: str) -> Optional[Notebook]:
        """
        Get notebook by ID and user.
 
        Args:
            notebook_id: Notebook ID
            user_id: User ID
 
        Returns:
            Notebook if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM notebooks WHERE id = ? AND user_id = ?",
                (notebook_id, user_id)
            )
            row = cursor.fetchone()
 
            if row:
                return self._row_to_notebook(row)
            return None
        finally:
            conn.close()
 
    def get_notebooks_for_user(self, user_id: str, selected_only: bool = False) -> List[Notebook]:
        """
        Get all notebooks for a user.
 
        Args:
            user_id: User ID
            selected_only: If True, only return selected notebooks
 
        Returns:
            List of Notebook objects
        """
        conn = self._get_connection()
        try:
            if selected_only:
                cursor = conn.execute(
                    "SELECT * FROM notebooks WHERE user_id = ? AND is_selected = 1 ORDER BY display_name",
                    (user_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM notebooks WHERE user_id = ? ORDER BY display_name",
                    (user_id,)
                )
 
            rows = cursor.fetchall()
            return [self._row_to_notebook(row) for row in rows]
        finally:
            conn.close()
 
    def update_selection(self, user_id: str, notebook_ids: List[str]) -> None:
        """
        Update which notebooks are selected for sync.
 
        Deselects all notebooks for the user, then selects the specified ones.
 
        Args:
            user_id: User ID
            notebook_ids: List of notebook IDs to select
        """
        conn = self._get_connection()
        try:
            # Deselect all for this user
            conn.execute(
                "UPDATE notebooks SET is_selected = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
 
            # Select specified notebooks
            if notebook_ids:
                placeholders = ','.join('?' * len(notebook_ids))
                conn.execute(
                    f"UPDATE notebooks SET is_selected = 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND id IN ({placeholders})",
                    (user_id, *notebook_ids)
                )
 
            conn.commit()
            logger.info(f"Updated selection for user {user_id}: {len(notebook_ids)} notebooks selected")
        finally:
            conn.close()
 
    def update_sync_status(
        self,
        notebook_id: str,
        user_id: str,
        sync_status: str,
        page_count: Optional[int] = None,
        section_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update sync status for a notebook.
 
        Args:
            notebook_id: Notebook ID
            user_id: User ID
            sync_status: Status: syncing, completed, error
            page_count: Number of pages synced
            section_count: Number of sections
            error_message: Error message if failed
        """
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE notebooks
                SET sync_status = ?,
                    last_synced_at = CURRENT_TIMESTAMP,
                    page_count = COALESCE(?, page_count),
                    section_count = COALESCE(?, section_count),
                    error_message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (sync_status, page_count, section_count, error_message, notebook_id, user_id))
            conn.commit()
            logger.debug(f"Updated sync status for notebook {notebook_id}: {sync_status}")
        finally:
            conn.close()
 
    def get_notebook_status(self, user_id: str) -> List[NotebookStatus]:
        """
        Get sync status for all notebooks of a user.
 
        Args:
            user_id: User ID
 
        Returns:
            List of NotebookStatus objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, display_name, is_selected, sync_status, last_synced_at,
                       page_count, section_count, error_message
                FROM notebooks
                WHERE user_id = ?
                ORDER BY display_name
            """, (user_id,))
 
            rows = cursor.fetchall()
            return [NotebookStatus(
                id=row['id'],
                display_name=row['display_name'],
                is_selected=bool(row['is_selected']),
                sync_status=row['sync_status'],
                last_synced_at=datetime.fromisoformat(row['last_synced_at']) if row['last_synced_at'] else None,
                page_count=row['page_count'] or 0,
                section_count=row['section_count'] or 0,
                error_message=row['error_message']
            ) for row in rows]
        finally:
            conn.close()
 
    def _row_to_notebook(self, row: sqlite3.Row) -> Notebook:
        """Convert database row to Notebook object."""
        return Notebook(
            id=row['id'],
            user_id=row['user_id'],
            display_name=row['display_name'],
            created_datetime=datetime.fromisoformat(row['created_datetime']) if row['created_datetime'] else None,
            last_modified_datetime=datetime.fromisoformat(row['last_modified_datetime']) if row['last_modified_datetime'] else None,
            site_id=row['site_id'],
            is_shared=bool(row['is_shared']),
            user_role=row['user_role'],
            shared_by=row['shared_by'],
            web_url=row['web_url'],
            sections_url=row['sections_url'],
            is_selected=bool(row['is_selected'])
        )
 