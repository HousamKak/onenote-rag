"""
Database service for OneNote document cache.
Handles all database operations for cached documents, images, and sync tracking.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from models.document_cache import (
    CachedDocument,
    CachedImage,
    SyncState,
    SyncHistory,
    SyncJob,
    CacheStats
)

logger = logging.getLogger(__name__)


class DocumentCacheDB:
    """Database service for OneNote document cache."""

    def __init__(self, db_path: str = "data/document_cache.db"):
        """
        Initialize document cache database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()
        logger.info(f"DocumentCacheDB initialized at {db_path}")

    def _ensure_db_exists(self):
        """Ensure database and schema exist."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Check if migrations need to be run
        if not Path(self.db_path).exists():
            logger.info("Database does not exist, running migrations...")
            self._run_migrations()
        else:
            logger.info("Database exists, checking schema...")
            # TODO: Add schema version checking

    def _run_migrations(self):
        """Run database migrations."""
        migration_file = Path(__file__).parent.parent / "migrations" / "001_create_document_cache_schema.sql"

        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")

        logger.info(f"Running migration: {migration_file}")

        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        conn = self._get_connection()
        try:
            conn.executescript(migration_sql)
            conn.commit()
            logger.info("Migration completed successfully")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================

    def get_document(self, page_id: str) -> Optional[CachedDocument]:
        """
        Get document by page_id.

        Args:
            page_id: OneNote page ID

        Returns:
            CachedDocument if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM onenote_documents WHERE page_id = ? AND is_deleted = 0",
                (page_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_cached_document(row)
            return None
        finally:
            conn.close()

    def get_all_documents(self, include_deleted: bool = False) -> List[CachedDocument]:
        """
        Get all documents from cache.

        Args:
            include_deleted: Whether to include soft-deleted documents

        Returns:
            List of CachedDocument
        """
        conn = self._get_connection()
        try:
            if include_deleted:
                cursor = conn.execute("SELECT * FROM onenote_documents ORDER BY modified_date DESC")
            else:
                cursor = conn.execute(
                    "SELECT * FROM onenote_documents WHERE is_deleted = 0 ORDER BY modified_date DESC"
                )

            rows = cursor.fetchall()
            return [self._row_to_cached_document(row) for row in rows]
        finally:
            conn.close()

    def get_documents_modified_after(
        self,
        timestamp: datetime,
        include_deleted: bool = False
    ) -> List[CachedDocument]:
        """
        Get documents modified after a specific timestamp.

        Args:
            timestamp: Datetime threshold
            include_deleted: Whether to include soft-deleted documents

        Returns:
            List of CachedDocument
        """
        conn = self._get_connection()
        try:
            if include_deleted:
                cursor = conn.execute(
                    "SELECT * FROM onenote_documents WHERE modified_date > ? ORDER BY modified_date DESC",
                    (timestamp.isoformat(),)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM onenote_documents WHERE modified_date > ? AND is_deleted = 0 ORDER BY modified_date DESC",
                    (timestamp.isoformat(),)
                )

            rows = cursor.fetchall()
            return [self._row_to_cached_document(row) for row in rows]
        finally:
            conn.close()

    def get_documents_needing_indexing(self) -> List[CachedDocument]:
        """
        Get documents that need indexing (indexed_at is NULL or < last_synced_at).

        Returns:
            List of CachedDocument
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM onenote_documents
                WHERE is_deleted = 0
                  AND (indexed_at IS NULL OR indexed_at < last_synced_at)
                ORDER BY modified_date DESC
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_cached_document(row) for row in rows]
        finally:
            conn.close()

    def upsert_document(self, document: CachedDocument) -> None:
        """
        Insert or update document in cache.

        Args:
            document: CachedDocument to upsert
        """
        conn = self._get_connection()
        try:
            # Convert tags list to comma-separated string
            tags_str = ",".join(document.tags) if document.tags else None

            # Convert extra_metadata to JSON string
            extra_metadata_str = json.dumps(document.extra_metadata) if document.extra_metadata else None

            conn.execute(
                """
                INSERT INTO onenote_documents (
                    page_id, html_content, plain_text,
                    notebook_id, notebook_name, section_id, section_name, page_title,
                    author, created_date, modified_date, source_url, tags,
                    last_synced_at, sync_version, is_deleted,
                    indexed_at, chunk_count, image_count,
                    extra_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(page_id) DO UPDATE SET
                    html_content = excluded.html_content,
                    plain_text = excluded.plain_text,
                    notebook_id = excluded.notebook_id,
                    notebook_name = excluded.notebook_name,
                    section_id = excluded.section_id,
                    section_name = excluded.section_name,
                    page_title = excluded.page_title,
                    author = excluded.author,
                    created_date = excluded.created_date,
                    modified_date = excluded.modified_date,
                    source_url = excluded.source_url,
                    tags = excluded.tags,
                    last_synced_at = excluded.last_synced_at,
                    sync_version = sync_version + 1,
                    is_deleted = excluded.is_deleted,
                    indexed_at = excluded.indexed_at,
                    chunk_count = excluded.chunk_count,
                    image_count = excluded.image_count,
                    extra_metadata = excluded.extra_metadata
                """,
                (
                    document.page_id, document.html_content, document.plain_text,
                    document.notebook_id, document.notebook_name, document.section_id,
                    document.section_name, document.page_title,
                    document.author,
                    document.created_date.isoformat() if document.created_date else None,
                    document.modified_date.isoformat(),
                    document.source_url, tags_str,
                    document.last_synced_at.isoformat(), document.sync_version,
                    1 if document.is_deleted else 0,
                    document.indexed_at.isoformat() if document.indexed_at else None,
                    document.chunk_count, document.image_count,
                    extra_metadata_str
                )
            )
            conn.commit()
            logger.debug(f"Upserted document: {document.page_id}")
        except Exception as e:
            logger.error(f"Error upserting document {document.page_id}: {e}")
            raise
        finally:
            conn.close()

    def bulk_upsert_documents(self, documents: List[CachedDocument]) -> int:
        """
        Bulk insert/update documents.

        Args:
            documents: List of CachedDocument

        Returns:
            Number of documents upserted
        """
        if not documents:
            return 0

        conn = self._get_connection()
        try:
            count = 0
            for document in documents:
                tags_str = ",".join(document.tags) if document.tags else None
                extra_metadata_str = json.dumps(document.extra_metadata) if document.extra_metadata else None

                conn.execute(
                    """
                    INSERT INTO onenote_documents (
                        page_id, html_content, plain_text,
                        notebook_id, notebook_name, section_id, section_name, page_title,
                        author, created_date, modified_date, source_url, tags,
                        last_synced_at, sync_version, is_deleted,
                        indexed_at, chunk_count, image_count,
                        extra_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(page_id) DO UPDATE SET
                        html_content = excluded.html_content,
                        plain_text = excluded.plain_text,
                        notebook_id = excluded.notebook_id,
                        notebook_name = excluded.notebook_name,
                        section_id = excluded.section_id,
                        section_name = excluded.section_name,
                        page_title = excluded.page_title,
                        author = excluded.author,
                        created_date = excluded.created_date,
                        modified_date = excluded.modified_date,
                        source_url = excluded.source_url,
                        tags = excluded.tags,
                        last_synced_at = excluded.last_synced_at,
                        sync_version = sync_version + 1,
                        is_deleted = excluded.is_deleted,
                        extra_metadata = excluded.extra_metadata
                    """,
                    (
                        document.page_id, document.html_content, document.plain_text,
                        document.notebook_id, document.notebook_name, document.section_id,
                        document.section_name, document.page_title,
                        document.author,
                        document.created_date.isoformat() if document.created_date else None,
                        document.modified_date.isoformat(),
                        document.source_url, tags_str,
                        document.last_synced_at.isoformat(), document.sync_version,
                        1 if document.is_deleted else 0,
                        document.indexed_at.isoformat() if document.indexed_at else None,
                        document.chunk_count, document.image_count,
                        extra_metadata_str
                    )
                )
                count += 1

            conn.commit()
            logger.info(f"Bulk upserted {count} documents")
            return count
        except Exception as e:
            logger.error(f"Error bulk upserting documents: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_document_indexed(self, page_id: str, chunk_count: int, image_count: int) -> None:
        """
        Mark document as indexed.

        Args:
            page_id: OneNote page ID
            chunk_count: Number of chunks created
            image_count: Number of images in document
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE onenote_documents
                SET indexed_at = ?, chunk_count = ?, image_count = ?
                WHERE page_id = ?
                """,
                (datetime.now().isoformat(), chunk_count, image_count, page_id)
            )
            conn.commit()
            logger.debug(f"Marked document as indexed: {page_id}")
        finally:
            conn.close()

    def mark_document_deleted(self, page_id: str) -> None:
        """
        Soft delete document.

        Args:
            page_id: OneNote page ID
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE onenote_documents SET is_deleted = 1 WHERE page_id = ?",
                (page_id,)
            )
            conn.commit()
            logger.debug(f"Marked document as deleted: {page_id}")
        finally:
            conn.close()

    def get_all_page_ids(self, include_deleted: bool = False) -> set:
        """
        Get set of all page IDs in cache.

        Args:
            include_deleted: Whether to include deleted documents

        Returns:
            Set of page_id strings
        """
        conn = self._get_connection()
        try:
            if include_deleted:
                cursor = conn.execute("SELECT page_id FROM onenote_documents")
            else:
                cursor = conn.execute("SELECT page_id FROM onenote_documents WHERE is_deleted = 0")

            return {row["page_id"] for row in cursor.fetchall()}
        finally:
            conn.close()

    # =========================================================================
    # IMAGE OPERATIONS
    # =========================================================================

    def get_images_for_page(self, page_id: str) -> List[CachedImage]:
        """
        Get all images for a document.

        Args:
            page_id: OneNote page ID

        Returns:
            List of CachedImage
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM onenote_images WHERE page_id = ? ORDER BY image_index",
                (page_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_cached_image(row) for row in rows]
        finally:
            conn.close()

    def upsert_image(self, image: CachedImage) -> None:
        """
        Insert or update image metadata.

        Args:
            image: CachedImage to upsert
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO onenote_images (
                    page_id, image_index, file_path, file_size_bytes, mime_type,
                    alt_text, vision_analysis, analyzed_at, graph_resource_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(page_id, image_index) DO UPDATE SET
                    file_path = excluded.file_path,
                    file_size_bytes = excluded.file_size_bytes,
                    mime_type = excluded.mime_type,
                    alt_text = excluded.alt_text,
                    vision_analysis = excluded.vision_analysis,
                    analyzed_at = excluded.analyzed_at,
                    graph_resource_id = excluded.graph_resource_id
                """,
                (
                    image.page_id, image.image_index, image.file_path,
                    image.file_size_bytes, image.mime_type,
                    image.alt_text, image.vision_analysis,
                    image.analyzed_at.isoformat() if image.analyzed_at else None,
                    image.graph_resource_id
                )
            )
            conn.commit()
            logger.debug(f"Upserted image: {image.page_id}_{image.image_index}")
        finally:
            conn.close()

    def delete_images_for_page(self, page_id: str) -> None:
        """
        Delete all images for a document.

        Args:
            page_id: OneNote page ID
        """
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM onenote_images WHERE page_id = ?", (page_id,))
            conn.commit()
            logger.debug(f"Deleted images for page: {page_id}")
        finally:
            conn.close()

    # =========================================================================
    # SYNC STATE OPERATIONS
    # =========================================================================

    def get_sync_state(self, entity_type: str, entity_id: str) -> Optional[SyncState]:
        """
        Get sync state for an entity.

        Args:
            entity_type: 'global', 'notebook', or 'section'
            entity_id: Entity identifier

        Returns:
            SyncState if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM sync_state WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_sync_state(row)
            return None
        finally:
            conn.close()

    def upsert_sync_state(self, sync_state: SyncState) -> None:
        """
        Insert or update sync state.

        Args:
            sync_state: SyncState to upsert
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO sync_state (
                    entity_type, entity_id, entity_name,
                    last_full_sync_at, last_incremental_sync_at, next_sync_due_at,
                    total_pages_synced, pages_added_last_sync, pages_updated_last_sync,
                    pages_deleted_last_sync, last_sync_duration_seconds, last_sync_error,
                    api_calls_last_sync, avg_api_latency_ms, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    entity_name = excluded.entity_name,
                    last_full_sync_at = excluded.last_full_sync_at,
                    last_incremental_sync_at = excluded.last_incremental_sync_at,
                    next_sync_due_at = excluded.next_sync_due_at,
                    total_pages_synced = excluded.total_pages_synced,
                    pages_added_last_sync = excluded.pages_added_last_sync,
                    pages_updated_last_sync = excluded.pages_updated_last_sync,
                    pages_deleted_last_sync = excluded.pages_deleted_last_sync,
                    last_sync_duration_seconds = excluded.last_sync_duration_seconds,
                    last_sync_error = excluded.last_sync_error,
                    api_calls_last_sync = excluded.api_calls_last_sync,
                    avg_api_latency_ms = excluded.avg_api_latency_ms,
                    sync_status = excluded.sync_status
                """,
                (
                    sync_state.entity_type, sync_state.entity_id, sync_state.entity_name,
                    sync_state.last_full_sync_at.isoformat() if sync_state.last_full_sync_at else None,
                    sync_state.last_incremental_sync_at.isoformat() if sync_state.last_incremental_sync_at else None,
                    sync_state.next_sync_due_at.isoformat() if sync_state.next_sync_due_at else None,
                    sync_state.total_pages_synced, sync_state.pages_added_last_sync,
                    sync_state.pages_updated_last_sync, sync_state.pages_deleted_last_sync,
                    sync_state.last_sync_duration_seconds, sync_state.last_sync_error,
                    sync_state.api_calls_last_sync, sync_state.avg_api_latency_ms,
                    sync_state.sync_status
                )
            )
            conn.commit()
            logger.debug(f"Upserted sync state: {sync_state.entity_type}/{sync_state.entity_id}")
        finally:
            conn.close()

    # =========================================================================
    # SYNC HISTORY OPERATIONS
    # =========================================================================

    def create_sync_history(self, history: SyncHistory) -> int:
        """
        Create sync history record.

        Args:
            history: SyncHistory to create

        Returns:
            ID of created record
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO sync_history (
                    sync_type, started_at, completed_at, duration_seconds,
                    notebook_id, section_id, status,
                    pages_fetched, pages_added, pages_updated, pages_deleted, pages_skipped,
                    api_calls_made, errors_encountered, error_details,
                    total_wait_time_seconds, rate_limit_hits,
                    triggered_by, user_id, job_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history.sync_type,
                    history.started_at.isoformat(),
                    history.completed_at.isoformat() if history.completed_at else None,
                    history.duration_seconds,
                    history.notebook_id, history.section_id, history.status,
                    history.pages_fetched, history.pages_added, history.pages_updated,
                    history.pages_deleted, history.pages_skipped,
                    history.api_calls_made, history.errors_encountered, history.error_details,
                    history.total_wait_time_seconds, history.rate_limit_hits,
                    history.triggered_by, history.user_id, history.job_id
                )
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_recent_sync_history(self, limit: int = 50) -> List[SyncHistory]:
        """
        Get recent sync history.

        Args:
            limit: Maximum number of records

        Returns:
            List of SyncHistory
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM sync_history ORDER BY started_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_sync_history(row) for row in rows]
        finally:
            conn.close()

    # =========================================================================
    # SYNC JOB OPERATIONS
    # =========================================================================

    def create_sync_job(self, job: SyncJob) -> None:
        """
        Create sync job.

        Args:
            job: SyncJob to create
        """
        conn = self._get_connection()
        try:
            notebook_ids_str = json.dumps(job.notebook_ids) if job.notebook_ids else None

            conn.execute(
                """
                INSERT INTO sync_jobs (
                    job_id, sync_type, notebook_ids, status, progress_percent,
                    total_pages, pages_processed, pages_added, pages_updated, pages_deleted,
                    api_calls_made, elapsed_seconds, estimated_remaining_seconds,
                    error_count, last_error, can_pause, can_cancel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id, job.sync_type, notebook_ids_str, job.status, job.progress_percent,
                    job.total_pages, job.pages_processed, job.pages_added, job.pages_updated, job.pages_deleted,
                    job.api_calls_made, job.elapsed_seconds, job.estimated_remaining_seconds,
                    job.error_count, job.last_error,
                    1 if job.can_pause else 0, 1 if job.can_cancel else 0
                )
            )
            conn.commit()
            logger.debug(f"Created sync job: {job.job_id}")
        finally:
            conn.close()

    def update_sync_job(self, job: SyncJob) -> None:
        """
        Update sync job.

        Args:
            job: SyncJob to update
        """
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE sync_jobs SET
                    status = ?, progress_percent = ?,
                    total_pages = ?, pages_processed = ?, pages_added = ?, pages_updated = ?, pages_deleted = ?,
                    api_calls_made = ?, elapsed_seconds = ?, estimated_remaining_seconds = ?,
                    error_count = ?, last_error = ?,
                    started_at = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (
                    job.status, job.progress_percent,
                    job.total_pages, job.pages_processed, job.pages_added, job.pages_updated, job.pages_deleted,
                    job.api_calls_made, job.elapsed_seconds, job.estimated_remaining_seconds,
                    job.error_count, job.last_error,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.job_id
                )
            )
            conn.commit()
        finally:
            conn.close()

    def get_sync_job(self, job_id: str) -> Optional[SyncJob]:
        """
        Get sync job by ID.

        Args:
            job_id: Job identifier

        Returns:
            SyncJob if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM sync_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_sync_job(row)
            return None
        finally:
            conn.close()

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_cache_stats(self) -> CacheStats:
        """
        Get cache statistics.

        Returns:
            CacheStats
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM sync_health_dashboard")
            row = cursor.fetchone()

            if row:
                # Calculate cache size
                cursor_size = conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                size_row = cursor_size.fetchone()
                cache_size_mb = size_row["size"] / (1024 * 1024) if size_row else None

                # Determine health
                stale_count = row["stale_documents"] or 0
                recent_failures = row["recent_failures"] or 0

                if recent_failures > 5:
                    health = "error"
                elif stale_count > 100:
                    health = "needs_sync"
                else:
                    health = "healthy"

                return CacheStats(
                    total_documents=row["total_documents"] or 0,
                    total_images=row["total_images"] or 0,
                    unindexed_documents=row["unindexed_documents"] or 0,
                    stale_documents=stale_count,
                    last_full_sync=self._parse_datetime(row["last_full_sync"]),
                    last_incremental_sync=self._parse_datetime(row["last_incremental_sync"]),
                    recent_failures=recent_failures,
                    cache_size_mb=cache_size_mb,
                    sync_health=health
                )
            else:
                return CacheStats(
                    total_documents=0,
                    total_images=0,
                    unindexed_documents=0,
                    stale_documents=0,
                    recent_failures=0,
                    sync_health="unknown"
                )
        finally:
            conn.close()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _row_to_cached_document(self, row: sqlite3.Row) -> CachedDocument:
        """Convert database row to CachedDocument."""
        tags = row["tags"].split(",") if row["tags"] else None
        extra_metadata = json.loads(row["extra_metadata"]) if row["extra_metadata"] else None

        return CachedDocument(
            page_id=row["page_id"],
            html_content=row["html_content"],
            plain_text=row["plain_text"],
            notebook_id=row["notebook_id"],
            notebook_name=row["notebook_name"],
            section_id=row["section_id"],
            section_name=row["section_name"],
            page_title=row["page_title"],
            author=row["author"],
            created_date=self._parse_datetime(row["created_date"]),
            modified_date=self._parse_datetime(row["modified_date"]),
            source_url=row["source_url"],
            tags=tags,
            last_synced_at=self._parse_datetime(row["last_synced_at"]),
            sync_version=row["sync_version"],
            is_deleted=bool(row["is_deleted"]),
            indexed_at=self._parse_datetime(row["indexed_at"]),
            chunk_count=row["chunk_count"],
            image_count=row["image_count"],
            extra_metadata=extra_metadata,
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"])
        )

    def _row_to_cached_image(self, row: sqlite3.Row) -> CachedImage:
        """Convert database row to CachedImage."""
        return CachedImage(
            id=row["id"],
            page_id=row["page_id"],
            image_index=row["image_index"],
            file_path=row["file_path"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"],
            alt_text=row["alt_text"],
            vision_analysis=row["vision_analysis"],
            analyzed_at=self._parse_datetime(row["analyzed_at"]),
            graph_resource_id=row["graph_resource_id"],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"])
        )

    def _row_to_sync_state(self, row: sqlite3.Row) -> SyncState:
        """Convert database row to SyncState."""
        return SyncState(
            id=row["id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            entity_name=row["entity_name"],
            last_full_sync_at=self._parse_datetime(row["last_full_sync_at"]),
            last_incremental_sync_at=self._parse_datetime(row["last_incremental_sync_at"]),
            next_sync_due_at=self._parse_datetime(row["next_sync_due_at"]),
            total_pages_synced=row["total_pages_synced"],
            pages_added_last_sync=row["pages_added_last_sync"],
            pages_updated_last_sync=row["pages_updated_last_sync"],
            pages_deleted_last_sync=row["pages_deleted_last_sync"],
            last_sync_duration_seconds=row["last_sync_duration_seconds"],
            last_sync_error=row["last_sync_error"],
            api_calls_last_sync=row["api_calls_last_sync"],
            avg_api_latency_ms=row["avg_api_latency_ms"],
            sync_status=row["sync_status"],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"])
        )

    def _row_to_sync_history(self, row: sqlite3.Row) -> SyncHistory:
        """Convert database row to SyncHistory."""
        return SyncHistory(
            id=row["id"],
            sync_type=row["sync_type"],
            started_at=self._parse_datetime(row["started_at"]),
            completed_at=self._parse_datetime(row["completed_at"]),
            duration_seconds=row["duration_seconds"],
            notebook_id=row["notebook_id"],
            section_id=row["section_id"],
            status=row["status"],
            pages_fetched=row["pages_fetched"],
            pages_added=row["pages_added"],
            pages_updated=row["pages_updated"],
            pages_deleted=row["pages_deleted"],
            pages_skipped=row["pages_skipped"],
            api_calls_made=row["api_calls_made"],
            errors_encountered=row["errors_encountered"],
            error_details=row["error_details"],
            total_wait_time_seconds=row["total_wait_time_seconds"],
            rate_limit_hits=row["rate_limit_hits"],
            triggered_by=row["triggered_by"],
            user_id=row["user_id"],
            job_id=row["job_id"],
            created_at=self._parse_datetime(row["created_at"])
        )

    def _row_to_sync_job(self, row: sqlite3.Row) -> SyncJob:
        """Convert database row to SyncJob."""
        notebook_ids = json.loads(row["notebook_ids"]) if row["notebook_ids"] else None

        return SyncJob(
            job_id=row["job_id"],
            sync_type=row["sync_type"],
            notebook_ids=notebook_ids,
            status=row["status"],
            progress_percent=row["progress_percent"],
            total_pages=row["total_pages"],
            pages_processed=row["pages_processed"],
            pages_added=row["pages_added"],
            pages_updated=row["pages_updated"],
            pages_deleted=row["pages_deleted"],
            api_calls_made=row["api_calls_made"],
            elapsed_seconds=row["elapsed_seconds"],
            estimated_remaining_seconds=row["estimated_remaining_seconds"],
            error_count=row["error_count"],
            last_error=row["last_error"],
            can_pause=bool(row["can_pause"]),
            can_cancel=bool(row["can_cancel"]),
            created_at=self._parse_datetime(row["created_at"]),
            started_at=self._parse_datetime(row["started_at"]),
            completed_at=self._parse_datetime(row["completed_at"]),
            updated_at=self._parse_datetime(row["updated_at"])
        )

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """Parse datetime from string or return None."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
