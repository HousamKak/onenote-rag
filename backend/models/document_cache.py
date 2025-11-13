"""
Data models for OneNote document cache.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CachedDocument(BaseModel):
    """Model for cached OneNote document."""

    page_id: str
    html_content: str
    plain_text: Optional[str] = None

    # Hierarchy
    notebook_id: str
    notebook_name: Optional[str] = None
    section_id: str
    section_name: Optional[str] = None
    page_title: str

    # Metadata
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: datetime
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None

    # Sync tracking
    last_synced_at: datetime
    sync_version: int = 1
    is_deleted: bool = False

    # Indexing status
    indexed_at: Optional[datetime] = None
    chunk_count: int = 0
    image_count: int = 0

    # Additional metadata
    extra_metadata: Optional[dict] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class CachedImage(BaseModel):
    """Model for cached OneNote image metadata."""

    id: Optional[int] = None
    page_id: str
    image_index: int

    # Storage
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = "image/png"

    # Analysis
    alt_text: Optional[str] = None
    vision_analysis: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    # Graph API metadata
    graph_resource_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SyncState(BaseModel):
    """Model for sync state tracking."""

    id: Optional[int] = None

    # Scope
    entity_type: str  # 'global', 'notebook', 'section'
    entity_id: str
    entity_name: Optional[str] = None

    # Sync metadata
    last_full_sync_at: Optional[datetime] = None
    last_incremental_sync_at: Optional[datetime] = None
    next_sync_due_at: Optional[datetime] = None

    # Statistics
    total_pages_synced: int = 0
    pages_added_last_sync: int = 0
    pages_updated_last_sync: int = 0
    pages_deleted_last_sync: int = 0
    last_sync_duration_seconds: Optional[int] = None
    last_sync_error: Optional[str] = None

    # Rate limiting stats
    api_calls_last_sync: int = 0
    avg_api_latency_ms: Optional[int] = None

    # Status
    sync_status: str = "idle"  # idle, syncing, error, paused, completed

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SyncHistory(BaseModel):
    """Model for sync history audit trail."""

    id: Optional[int] = None

    # Sync details
    sync_type: str  # 'full', 'incremental', 'smart'
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    # Scope
    notebook_id: Optional[str] = None
    section_id: Optional[str] = None

    # Results
    status: str  # success, partial_success, failed, cancelled
    pages_fetched: int = 0
    pages_added: int = 0
    pages_updated: int = 0
    pages_deleted: int = 0
    pages_skipped: int = 0
    api_calls_made: int = 0
    errors_encountered: int = 0
    error_details: Optional[str] = None

    # Rate limiting stats
    total_wait_time_seconds: float = 0.0
    rate_limit_hits: int = 0

    # Triggered by
    triggered_by: Optional[str] = None  # 'manual', 'scheduled', 'auto', 'api'
    user_id: Optional[str] = None

    # Job tracking
    job_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)


class SyncJob(BaseModel):
    """Model for active sync job tracking."""

    job_id: str

    # Job configuration
    sync_type: str
    notebook_ids: Optional[List[str]] = None

    # Status
    status: str  # queued, running, paused, completed, failed, cancelled
    progress_percent: float = 0.0

    # Progress tracking
    total_pages: int = 0
    pages_processed: int = 0
    pages_added: int = 0
    pages_updated: int = 0
    pages_deleted: int = 0

    # Performance
    api_calls_made: int = 0
    elapsed_seconds: int = 0
    estimated_remaining_seconds: Optional[int] = None

    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None

    # Control
    can_pause: bool = True
    can_cancel: bool = True

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class CacheStats(BaseModel):
    """Statistics about the document cache."""

    total_documents: int
    total_images: int
    unindexed_documents: int
    stale_documents: int  # Not synced in 24h

    last_full_sync: Optional[datetime] = None
    last_incremental_sync: Optional[datetime] = None
    recent_failures: int

    cache_size_mb: Optional[float] = None
    sync_health: str  # 'healthy', 'needs_sync', 'error'


class SyncResult(BaseModel):
    """Result of a sync operation."""

    job_id: str
    sync_type: str
    status: str

    # Counts
    pages_fetched: int = 0
    pages_added: int = 0
    pages_updated: int = 0
    pages_deleted: int = 0
    pages_skipped: int = 0

    # Performance
    duration_seconds: Optional[int] = None
    api_calls_made: int = 0
    rate_limit_hits: int = 0

    # Errors
    errors_encountered: int = 0
    error_details: Optional[str] = None

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None
