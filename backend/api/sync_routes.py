"""
API routes for document cache synchronization.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel

from models.document_cache import SyncResult, CacheStats
from services.sync_orchestrator import SyncOrchestrator
from services.document_cache import DocumentCacheService
from middleware.auth import get_current_user
from models.user import UserContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Global instances (will be injected via dependency injection)
_sync_orchestrator: Optional[SyncOrchestrator] = None
_document_cache: Optional[DocumentCacheService] = None


def set_sync_orchestrator(orchestrator: SyncOrchestrator):
    """Set global sync orchestrator instance."""
    global _sync_orchestrator
    _sync_orchestrator = orchestrator


def set_document_cache(cache: DocumentCacheService):
    """Set global document cache instance."""
    global _document_cache
    _document_cache = cache


def get_sync_orchestrator() -> SyncOrchestrator:
    """Get sync orchestrator dependency."""
    if _sync_orchestrator is None:
        raise HTTPException(status_code=500, detail="Sync orchestrator not initialized")
    return _sync_orchestrator


def get_document_cache() -> DocumentCacheService:
    """Get document cache dependency."""
    if _document_cache is None:
        raise HTTPException(status_code=500, detail="Document cache not initialized")
    return _document_cache


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SyncRequest(BaseModel):
    """Request to trigger a sync operation."""
    notebook_ids: Optional[List[str]] = None


class SyncJobResponse(BaseModel):
    """Response with sync job information."""
    job_id: str
    status: str
    message: str
    estimated_duration_minutes: Optional[int] = None


class SyncStatusResponse(BaseModel):
    """Response with sync job status."""
    job_id: str
    sync_type: str
    status: str  # queued, running, paused, completed, failed, cancelled
    progress: dict
    stats: dict
    can_pause: bool
    can_cancel: bool


class SyncResultResponse(BaseModel):
    """Response with sync results."""
    job_id: str
    sync_type: str
    status: str
    summary: dict
    performance: dict
    errors: Optional[dict] = None


# =============================================================================
# SYNC ENDPOINTS
# =============================================================================

@router.post("/full", response_model=SyncJobResponse)
async def trigger_full_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Trigger a full sync from OneNote to local cache.

    Fetches ALL documents from OneNote and updates the local cache.
    This operation runs in the background and returns a job ID for tracking.

    - Use this for initial sync or when data integrity is questioned
    - Takes longer but ensures completeness
    - Respects rate limits automatically
    """
    try:
        logger.info(f"Full sync requested by user {user.user_id}")

        # Estimate duration (rough estimate: 1000 pages ~= 10 minutes)
        estimated_minutes = 10  # Default estimate

        # Start sync in background
        async def run_sync():
            try:
                result = await orchestrator.sync_full(
                    notebook_ids=request.notebook_ids,
                    triggered_by="api",
                    user_id=user.user_id
                )
                logger.info(f"Full sync completed: {result.status}")
            except Exception as e:
                logger.error(f"Full sync failed: {e}", exc_info=True)

        background_tasks.add_task(run_sync)

        # Generate job ID (will be created by orchestrator, but we can peek at next)
        import uuid
        job_id = str(uuid.uuid4())

        return SyncJobResponse(
            job_id=job_id,
            status="started",
            message="Full sync started in background",
            estimated_duration_minutes=estimated_minutes
        )

    except Exception as e:
        logger.error(f"Error triggering full sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incremental", response_model=SyncJobResponse)
async def trigger_incremental_sync(
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Trigger an incremental sync from OneNote to local cache.

    Only fetches documents that changed since the last sync.
    Faster than full sync, runs in the background.

    - Use for regular updates
    - Only syncs changed/new/deleted documents
    - Much faster for large datasets
    """
    try:
        logger.info(f"Incremental sync requested by user {user.user_id}")

        # Start sync in background
        async def run_sync():
            try:
                result = await orchestrator.sync_incremental(
                    triggered_by="api",
                    user_id=user.user_id
                )
                logger.info(f"Incremental sync completed: {result.status}")
            except Exception as e:
                logger.error(f"Incremental sync failed: {e}", exc_info=True)

        background_tasks.add_task(run_sync)

        import uuid
        job_id = str(uuid.uuid4())

        return SyncJobResponse(
            job_id=job_id,
            status="started",
            message="Incremental sync started in background",
            estimated_duration_minutes=2  # Usually much faster
        )

    except Exception as e:
        logger.error(f"Error triggering incremental sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart", response_model=SyncJobResponse)
async def trigger_smart_sync(
    background_tasks: BackgroundTasks,
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Trigger a smart sync that automatically chooses the best strategy.

    Automatically decides between full and incremental sync based on:
    - Time since last sync
    - Last sync status
    - Cache health

    - Recommended for automated/scheduled syncs
    - Balances thoroughness and speed
    """
    try:
        logger.info(f"Smart sync requested by user {user.user_id}")

        # Start sync in background
        async def run_sync():
            try:
                result = await orchestrator.sync_smart(
                    triggered_by="api",
                    user_id=user.user_id
                )
                logger.info(f"Smart sync completed: {result.status}")
            except Exception as e:
                logger.error(f"Smart sync failed: {e}", exc_info=True)

        background_tasks.add_task(run_sync)

        import uuid
        job_id = str(uuid.uuid4())

        return SyncJobResponse(
            job_id=job_id,
            status="started",
            message="Smart sync started in background",
            estimated_duration_minutes=None  # Variable
        )

    except Exception as e:
        logger.error(f"Error triggering smart sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATUS & CONTROL ENDPOINTS
# =============================================================================

@router.get("/status/{job_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    job_id: str,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Get status of a sync job.

    Returns current progress, statistics, and control options.
    """
    try:
        job = orchestrator.get_job_status(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Calculate progress percentage
        progress_percent = 0.0
        if job.total_pages > 0:
            progress_percent = (job.pages_processed / job.total_pages) * 100

        return SyncStatusResponse(
            job_id=job.job_id,
            sync_type=job.sync_type,
            status=job.status,
            progress={
                "pages_processed": job.pages_processed,
                "total_pages": job.total_pages,
                "percent": round(progress_percent, 2)
            },
            stats={
                "pages_added": job.pages_added,
                "pages_updated": job.pages_updated,
                "pages_deleted": job.pages_deleted,
                "api_calls_made": job.api_calls_made,
                "elapsed_seconds": job.elapsed_seconds,
                "estimated_remaining_seconds": job.estimated_remaining_seconds,
                "error_count": job.error_count
            },
            can_pause=job.can_pause and job.status == "running",
            can_cancel=job.can_cancel and job.status in ["running", "paused"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_sync(
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Pause the current sync operation.

    The sync will stop gracefully after completing the current batch.
    Use /resume to continue.
    """
    try:
        orchestrator.pause_sync()
        return {"status": "pausing", "message": "Sync will pause after current batch"}

    except Exception as e:
        logger.error(f"Error pausing sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_sync(
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Resume a paused sync operation.
    """
    try:
        orchestrator.resume_sync()
        return {"status": "resumed", "message": "Sync resumed"}

    except Exception as e:
        logger.error(f"Error resuming sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
async def cancel_sync(
    user: UserContext = Depends(get_current_user),
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Cancel the current sync operation.

    The sync will stop gracefully and mark the job as cancelled.
    """
    try:
        orchestrator.cancel_sync()
        return {"status": "cancelling", "message": "Sync will cancel after current operation"}

    except Exception as e:
        logger.error(f"Error cancelling sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CACHE INFORMATION ENDPOINTS
# =============================================================================

@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats(
    cache: DocumentCacheService = Depends(get_document_cache)
):
    """
    Get statistics about the local document cache.

    Returns information about:
    - Total documents and images cached
    - Last sync timestamps
    - Cache health status
    - Documents needing sync/indexing
    """
    try:
        stats = cache.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_sync_history(
    limit: int = 50,
    orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator)
):
    """
    Get recent sync history.

    Returns up to `limit` recent sync operations with their results.
    """
    try:
        # Get history from database
        from services.document_cache_db import DocumentCacheDB
        cache_db = DocumentCacheDB()
        history = cache_db.get_recent_sync_history(limit=limit)

        return {
            "history": [
                {
                    "id": h.id,
                    "sync_type": h.sync_type,
                    "status": h.status,
                    "started_at": h.started_at.isoformat(),
                    "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                    "duration_seconds": h.duration_seconds,
                    "pages_fetched": h.pages_fetched,
                    "pages_added": h.pages_added,
                    "pages_updated": h.pages_updated,
                    "pages_deleted": h.pages_deleted,
                    "pages_skipped": h.pages_skipped,
                    "api_calls_made": h.api_calls_made,
                    "errors_encountered": h.errors_encountered,
                    "triggered_by": h.triggered_by
                }
                for h in history
            ],
            "total": len(history)
        }

    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_sync_health(
    cache: DocumentCacheService = Depends(get_document_cache)
):
    """
    Get overall sync health status.

    Returns a simple health check with recommendations.
    """
    try:
        stats = cache.get_stats()

        recommendations = []

        if stats.stale_documents > 100:
            recommendations.append("Many documents haven't synced in 24h - consider running an incremental sync")

        if stats.unindexed_documents > 50:
            recommendations.append("Many documents need indexing - consider re-indexing the cache")

        if stats.recent_failures > 5:
            recommendations.append("Multiple recent sync failures - check logs and consider running a full sync")

        if not stats.last_full_sync or (datetime.now() - stats.last_full_sync).days > 7:
            recommendations.append("No full sync in 7 days - consider running a full sync")

        health_status = "healthy"
        if stats.sync_health == "error" or stats.recent_failures > 5:
            health_status = "unhealthy"
        elif stats.sync_health == "needs_sync" or stats.stale_documents > 100:
            health_status = "needs_attention"

        return {
            "status": health_status,
            "last_full_sync": stats.last_full_sync.isoformat() if stats.last_full_sync else None,
            "last_incremental_sync": stats.last_incremental_sync.isoformat() if stats.last_incremental_sync else None,
            "total_documents": stats.total_documents,
            "stale_documents": stats.stale_documents,
            "unindexed_documents": stats.unindexed_documents,
            "recent_failures": stats.recent_failures,
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"Error getting sync health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import for datetime
from datetime import datetime
