"""
Sync System Integration Module

This module contains the initialization code for integrating the document cache
and sync orchestrator into the main application.

Add these imports and code snippets to main.py to enable the sync system.
"""

# =============================================================================
# IMPORTS TO ADD TO main.py
# =============================================================================

"""
Add these imports after the existing imports in main.py:

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from services.document_cache import DocumentCacheService
from services.document_cache_db import DocumentCacheDB
from services.sync_orchestrator import SyncOrchestrator
import api.sync_routes as sync_routes
"""

# =============================================================================
# INITIALIZATION CODE TO ADD TO lifespan() FUNCTION
# =============================================================================

"""
Add this code in the lifespan() function after the vector store initialization
(after line ~194 in main.py):

    # ========================================================================= # Initialize Document Cache & Sync System
    # =========================================================================
    logger.info("Initializing document cache and sync system...")

    # Initialize document cache database
    cache_db_path = "./data/document_cache.db"
    os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)

    cache_db = DocumentCacheDB(db_path=cache_db_path)
    logger.info(f"Document cache database initialized at: {cache_db_path}")

    # Initialize document cache service
    routes.document_cache = DocumentCacheService(db_path=cache_db_path)
    logger.info("Document cache service initialized")

    # Initialize sync orchestrator (will be created per-user request)
    # We'll create a factory function that uses the user's access token
    routes.sync_orchestrator = None  # Created per-user like OneNoteService
    routes.cache_db = cache_db  # Store for global access

    # Set sync services for API routes
    sync_routes.set_document_cache(routes.document_cache)
    # Note: SyncOrchestrator is created per-request with user's token

    logger.info("✅ Document cache and sync system initialized")

    # =========================================================================
    # Background Sync Scheduler (Optional - for automated syncs)
    # =========================================================================

    # Initialize APScheduler for background sync
    scheduler = AsyncIOScheduler()

    # Note: Background syncs are disabled with user-delegated auth by default
    # Users trigger sync manually after login
    # Uncomment below to enable scheduled syncs (requires service account)

    if False:  # Disabled - requires service account or specific user token
        logger.info("Setting up background sync scheduler...")

        # Incremental sync every 6 hours
        scheduler.add_job(
            func=lambda: logger.info("Scheduled sync would run here (disabled with user auth)"),
            trigger=CronTrigger(hour="*/6"),  # Every 6 hours: 0, 6, 12, 18
            id="incremental_sync",
            name="Incremental OneNote Sync",
            replace_existing=True
        )

        # Full sync every Sunday at 2 AM
        scheduler.add_job(
            func=lambda: logger.info("Scheduled full sync would run here (disabled with user auth)"),
            trigger=CronTrigger(day_of_week="sun", hour=2),
            id="full_sync",
            name="Full OneNote Sync",
            replace_existing=True
        )

        scheduler.start()
        logger.info("Background sync scheduler started")
    else:
        logger.info("Background sync scheduler disabled (user-delegated auth mode)")
        logger.info("Users will trigger sync manually via /api/sync endpoints")

    # Store scheduler for shutdown
    routes.scheduler = scheduler if 'scheduler' in locals() else None
"""

# =============================================================================
# SHUTDOWN CODE TO ADD TO lifespan() FUNCTION
# =============================================================================

"""
Add this code in the shutdown section of lifespan() (after line ~351):

    # Shutdown scheduler if running
    if hasattr(routes, 'scheduler') and routes.scheduler:
        logger.info("Shutting down background scheduler...")
        routes.scheduler.shutdown(wait=False)
"""

# =============================================================================
# ROUTER INCLUSION TO ADD AFTER app.include_router(routes.router...)
# =============================================================================

"""
Add this line after app.include_router(routes.router, prefix="/api"):

# Include sync routes
app.include_router(sync_routes.router)
"""

# =============================================================================
# HELPER FUNCTION TO CREATE SYNC ORCHESTRATOR PER-REQUEST
# =============================================================================

"""
Add this helper function to api/routes.py to create SyncOrchestrator per-request:

from services.sync_orchestrator import SyncOrchestrator
from services.onenote_service import OneNoteService

def create_sync_orchestrator_for_user(access_token: str) -> SyncOrchestrator:
    \"\"\"
    Create a SyncOrchestrator instance for a specific user.

    Args:
        access_token: User's Microsoft Graph access token

    Returns:
        SyncOrchestrator configured for the user
    \"\"\"
    # Create OneNoteService with user's token
    onenote_service = OneNoteService(access_token=access_token)

    # Create SyncOrchestrator
    orchestrator = SyncOrchestrator(
        onenote_service=onenote_service,
        document_cache=document_cache,
        image_storage=image_storage,
        cache_db=cache_db
    )

    return orchestrator
"""

# =============================================================================
# MODIFIED /api/onenote/sync ENDPOINT
# =============================================================================

"""
Update the existing /api/onenote/sync endpoint in api/routes.py to use the new cache:

@router.post("/onenote/sync")
async def sync_onenote(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    user: UserContext = Depends(get_current_user)
):
    \"\"\"
    Sync OneNote documents to local cache.

    This endpoint triggers a sync operation that:
    1. Fetches documents from OneNote (respecting rate limits)
    2. Stores them in the local document cache
    3. Queues them for indexing into the vector store

    Args:
        full_sync: If True, performs full sync; if False, incremental sync
        user: Current authenticated user

    Returns:
        Sync job information
    \"\"\"
    try:
        # Create sync orchestrator for this user
        orchestrator = create_sync_orchestrator_for_user(user.access_token)

        # Determine sync type
        sync_type = "full" if full_sync else "incremental"

        # Trigger sync in background
        async def run_sync():
            try:
                if full_sync:
                    result = await orchestrator.sync_full(
                        triggered_by="manual",
                        user_id=user.user_id
                    )
                else:
                    result = await orchestrator.sync_incremental(
                        triggered_by="manual",
                        user_id=user.user_id
                    )

                # After sync, trigger indexing of new documents
                documents_to_index = document_cache.get_documents_needing_indexing()

                if documents_to_index:
                    logger.info(f"Indexing {len(documents_to_index)} documents from cache...")

                    # Chunk and embed documents
                    chunks = document_processor.chunk_documents(
                        documents_to_index,
                        enrich_with_metadata=True
                    )

                    # Add to vector store
                    vector_store.add_documents(chunks)

                    # Mark as indexed in cache
                    for doc in documents_to_index:
                        doc_chunks = [c for c in chunks if c.metadata.get('page_id') == doc.page_id]
                        document_cache.mark_document_indexed(
                            page_id=doc.page_id,
                            chunk_count=len(doc_chunks),
                            image_count=doc.metadata.image_count
                        )

                    logger.info(f"✅ Indexed {len(documents_to_index)} documents ({len(chunks)} chunks)")

                logger.info(f"{sync_type.capitalize()} sync and indexing completed")

            except Exception as e:
                logger.error(f"Sync/indexing failed: {e}", exc_info=True)

        background_tasks.add_task(run_sync)

        return {
            "status": "started",
            "message": f"{sync_type.capitalize()} sync started in background",
            "sync_type": sync_type
        }

    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""

print("""
=============================================================================
INTEGRATION INSTRUCTIONS FOR DOCUMENT CACHE & SYNC SYSTEM
=============================================================================

This file contains all the code snippets needed to integrate the new document
cache and sync system into the existing application.

Follow these steps:

1. ADD IMPORTS to main.py (see IMPORTS section above)

2. ADD INITIALIZATION CODE to lifespan() function in main.py
   - Add after vector store initialization (around line 194)
   - This initializes document cache and optional scheduler

3. ADD SHUTDOWN CODE to lifespan() function
   - Add in the shutdown section (after line 351)
   - This gracefully shuts down the scheduler

4. INCLUDE SYNC ROUTER in main.py
   - Add after app.include_router(routes.router, prefix="/api")
   - This exposes the new /api/sync/* endpoints

5. ADD HELPER FUNCTION to api/routes.py
   - This creates SyncOrchestrator per-user request

6. UPDATE EXISTING SYNC ENDPOINT in api/routes.py
   - Replace /api/onenote/sync with new implementation
   - This uses the cache instead of direct OneNote access

After these changes:
- /api/sync/full - Trigger full sync
- /api/sync/incremental - Trigger incremental sync
- /api/sync/smart - Trigger smart sync
- /api/sync/status/{job_id} - Check sync status
- /api/sync/cache/stats - Get cache statistics
- /api/sync/health - Get sync health
- RAG queries will read from cache (faster, no rate limits)
- Sync runs in background (respects rate limits)

=============================================================================
""")
