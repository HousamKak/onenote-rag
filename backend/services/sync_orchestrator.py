"""
Sync Orchestrator - Manages synchronization between Graph API and local cache.
Implements full, incremental, and smart sync strategies with rate limiting.
"""
import asyncio
import base64
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import requests

from models.document import Document, DocumentMetadata
from models.document_cache import SyncResult, SyncJob, SyncHistory, SyncState
from services.onenote_service import OneNoteService
from services.document_cache import DocumentCacheService
from services.document_cache_db import DocumentCacheDB
from services.image_storage import ImageStorageService
from services.rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Orchestrates synchronization between Microsoft Graph API and local document cache.
    """

    def __init__(
        self,
        onenote_service: OneNoteService,
        document_cache: DocumentCacheService,
        image_storage: ImageStorageService,
        cache_db: DocumentCacheDB
    ):
        """
        Initialize sync orchestrator.

        Args:
            onenote_service: OneNote Graph API service
            document_cache: Document cache service
            image_storage: Image storage service
            cache_db: Direct database access for sync state
        """
        self.onenote = onenote_service
        self.cache = document_cache
        self.image_storage = image_storage
        self.cache_db = cache_db

        # Use the rate limiter from OneNoteService
        self.rate_limiter = onenote_service.rate_limiter

        # Track active jobs
        self.active_jobs: Dict[str, SyncJob] = {}

        # Control flags
        self._pause_requested = False
        self._cancel_requested = False

        logger.info("SyncOrchestrator initialized")

    # =========================================================================
    # PUBLIC SYNC METHODS
    # =========================================================================

    async def sync_full(
        self,
        notebook_ids: Optional[List[str]] = None,
        triggered_by: str = "manual",
        user_id: Optional[str] = None
    ) -> SyncResult:
        """
        Full sync: Fetch all documents from Graph API and update cache.

        Args:
            notebook_ids: Specific notebook IDs to sync (None = all)
            triggered_by: Who/what triggered this sync
            user_id: User ID if applicable

        Returns:
            SyncResult
        """
        job_id = str(uuid.uuid4())
        logger.info(f"Starting full sync (job_id={job_id})")

        # Create sync job
        job = SyncJob(
            job_id=job_id,
            sync_type="full",
            notebook_ids=notebook_ids,
            status="running"
        )
        self.cache_db.create_sync_job(job)
        self.active_jobs[job_id] = job

        # Track metrics
        start_time = datetime.now()
        pages_fetched = 0
        pages_added = 0
        pages_updated = 0
        api_calls = 0
        errors = 0
        error_details = []

        try:
            # Update sync state
            self._update_sync_state_status("syncing")

            # Step 1: Fetch all notebooks
            logger.info("Fetching notebooks...")
            notebooks = await self._fetch_with_rate_limit(
                self.onenote.list_notebooks
            )
            api_calls += 1

            if notebook_ids:
                notebooks = [nb for nb in notebooks if nb['id'] in notebook_ids]

            logger.info(f"Found {len(notebooks)} notebooks")

            # Step 2: For each notebook, get sections and pages
            for notebook in notebooks:
                if self._should_stop():
                    logger.info("Sync cancelled or paused")
                    break

                notebook_id = notebook['id']
                notebook_name = notebook.get('displayName', 'Unknown')

                logger.info(f"Processing notebook: {notebook_name}")

                try:
                    # Get sections
                    sections = await self._fetch_with_rate_limit(
                        self.onenote.list_sections,
                        notebook_id
                    )
                    api_calls += 1

                    # Process each section
                    for section in sections:
                        if self._should_stop():
                            break

                        section_id = section['id']
                        section_name = section.get('displayName', 'Unknown')

                        logger.info(f"  Processing section: {section_name}")

                        try:
                            # Get pages in section (with pagination support)
                            pages = await self._fetch_with_rate_limit(
                                self.onenote.list_pages,
                                section_id
                            )
                            api_calls += 1

                            logger.info(f"    Found {len(pages)} pages")

                            # Process each page
                            for page in pages:
                                if self._should_stop():
                                    break

                                try:
                                    result = await self._sync_page(
                                        page,
                                        notebook_id,
                                        notebook_name,
                                        section_id,
                                        section_name
                                    )

                                    pages_fetched += 1
                                    api_calls += result['api_calls']

                                    if result['is_new']:
                                        pages_added += 1
                                    else:
                                        pages_updated += 1

                                    # Update job progress
                                    self._update_job_progress(job, pages_fetched, api_calls)

                                except Exception as e:
                                    logger.error(f"Error syncing page {page.get('id')}: {e}")
                                    errors += 1
                                    error_details.append(f"Page {page.get('id')}: {str(e)}")

                        except Exception as e:
                            logger.error(f"Error processing section {section_name}: {e}")
                            errors += 1
                            error_details.append(f"Section {section_name}: {str(e)}")

                except Exception as e:
                    logger.error(f"Error processing notebook {notebook_name}: {e}")
                    errors += 1
                    error_details.append(f"Notebook {notebook_name}: {str(e)}")

            # Calculate duration
            duration = (datetime.now() - start_time).seconds

            # Update sync state
            sync_state = SyncState(
                entity_type="global",
                entity_id="global",
                entity_name="All OneNote Documents",
                last_full_sync_at=datetime.now(),
                total_pages_synced=pages_fetched,
                pages_added_last_sync=pages_added,
                pages_updated_last_sync=pages_updated,
                last_sync_duration_seconds=duration,
                api_calls_last_sync=api_calls,
                sync_status="completed" if errors == 0 else "completed_with_errors"
            )
            self.cache_db.upsert_sync_state(sync_state)

            # Create sync result
            status = "success" if errors == 0 else "partial_success"
            result = SyncResult(
                job_id=job_id,
                sync_type="full",
                status=status,
                pages_fetched=pages_fetched,
                pages_added=pages_added,
                pages_updated=pages_updated,
                pages_deleted=0,
                duration_seconds=duration,
                api_calls_made=api_calls,
                rate_limit_hits=self.rate_limiter.total_waits,
                errors_encountered=errors,
                error_details="; ".join(error_details) if error_details else None,
                started_at=start_time,
                completed_at=datetime.now()
            )

            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now()
            job.total_pages = pages_fetched
            job.pages_processed = pages_fetched
            job.pages_added = pages_added
            job.pages_updated = pages_updated
            job.api_calls_made = api_calls
            job.elapsed_seconds = duration
            self.cache_db.update_sync_job(job)

            # Create history record
            history = SyncHistory(
                sync_type="full",
                started_at=start_time,
                completed_at=datetime.now(),
                duration_seconds=duration,
                status=status,
                pages_fetched=pages_fetched,
                pages_added=pages_added,
                pages_updated=pages_updated,
                api_calls_made=api_calls,
                errors_encountered=errors,
                error_details="; ".join(error_details) if error_details else None,
                total_wait_time_seconds=self.rate_limiter.total_wait_time,
                rate_limit_hits=self.rate_limiter.total_waits,
                triggered_by=triggered_by,
                user_id=user_id,
                job_id=job_id
            )
            self.cache_db.create_sync_history(history)

            logger.info(
                f"Full sync completed: {pages_fetched} pages fetched "
                f"({pages_added} new, {pages_updated} updated), "
                f"{api_calls} API calls, {duration}s duration"
            )

            return result

        except Exception as e:
            logger.error(f"Full sync failed: {e}", exc_info=True)

            # Mark job as failed
            job.status = "failed"
            job.last_error = str(e)
            job.error_count += 1
            self.cache_db.update_sync_job(job)

            # Update sync state
            self._update_sync_state_status("error", str(e))

            raise

        finally:
            # Clean up
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def sync_incremental(
        self,
        triggered_by: str = "manual",
        user_id: Optional[str] = None
    ) -> SyncResult:
        """
        Incremental sync: Only fetch documents modified since last sync.

        Args:
            triggered_by: Who/what triggered this sync
            user_id: User ID if applicable

        Returns:
            SyncResult
        """
        job_id = str(uuid.uuid4())
        logger.info(f"Starting incremental sync (job_id={job_id})")

        # Get last sync timestamp
        last_sync = self.cache.get_last_sync_timestamp()
        if not last_sync:
            logger.warning("No previous sync found, falling back to full sync")
            return await self.sync_full(triggered_by=triggered_by, user_id=user_id)

        logger.info(f"Last sync was at: {last_sync}")

        # Create sync job
        job = SyncJob(
            job_id=job_id,
            sync_type="incremental",
            status="running"
        )
        self.cache_db.create_sync_job(job)
        self.active_jobs[job_id] = job

        # Track metrics
        start_time = datetime.now()
        pages_fetched = 0
        pages_added = 0
        pages_updated = 0
        pages_deleted = 0
        pages_skipped = 0
        api_calls = 0
        errors = 0
        error_details = []

        try:
            # Update sync state
            self._update_sync_state_status("syncing")

            # Step 1: Fetch all page metadata to check for changes
            logger.info("Fetching all page metadata to check for changes...")
            all_pages_metadata = await self._fetch_all_pages_metadata()
            api_calls += all_pages_metadata['api_calls']

            # Step 2: Compare with cached documents
            cached_page_ids = self.cache.get_all_page_ids()

            graph_page_ids = {p['id'] for p in all_pages_metadata['pages']}

            # Find pages that changed
            changed_pages = []
            for page_meta in all_pages_metadata['pages']:
                page_id = page_meta['id']
                modified_date_str = page_meta.get('lastModifiedDateTime')

                if not modified_date_str:
                    continue

                try:
                    modified_date = datetime.fromisoformat(modified_date_str.replace('Z', '+00:00'))
                except ValueError:
                    continue

                # Check if modified after last sync
                if modified_date > last_sync:
                    changed_pages.append(page_meta)
                else:
                    pages_skipped += 1

            # Find deleted pages (in cache but not in Graph API)
            deleted_page_ids = cached_page_ids - graph_page_ids

            logger.info(
                f"Found {len(changed_pages)} changed pages, "
                f"{pages_skipped} unchanged pages, "
                f"{len(deleted_page_ids)} deleted pages"
            )

            # Step 3: Fetch content for changed pages only
            for page_meta in changed_pages:
                if self._should_stop():
                    break

                try:
                    # Determine if new or updated
                    page_id = page_meta['id']
                    is_new = page_id not in cached_page_ids

                    # Sync the page
                    result = await self._sync_page_from_metadata(page_meta)

                    pages_fetched += 1
                    api_calls += result['api_calls']

                    if is_new:
                        pages_added += 1
                    else:
                        pages_updated += 1

                    # Update job progress
                    self._update_job_progress(job, pages_fetched, api_calls)

                except Exception as e:
                    logger.error(f"Error syncing page {page_meta.get('id')}: {e}")
                    errors += 1
                    error_details.append(f"Page {page_meta.get('id')}: {str(e)}")

            # Step 4: Mark deleted pages
            for deleted_id in deleted_page_ids:
                try:
                    self.cache.mark_document_deleted(deleted_id)
                    pages_deleted += 1
                    logger.debug(f"Marked page as deleted: {deleted_id}")
                except Exception as e:
                    logger.error(f"Error marking page as deleted {deleted_id}: {e}")

            # Calculate duration
            duration = (datetime.now() - start_time).seconds

            # Update sync state
            sync_state = SyncState(
                entity_type="global",
                entity_id="global",
                entity_name="All OneNote Documents",
                last_incremental_sync_at=datetime.now(),
                total_pages_synced=pages_fetched,
                pages_added_last_sync=pages_added,
                pages_updated_last_sync=pages_updated,
                pages_deleted_last_sync=pages_deleted,
                last_sync_duration_seconds=duration,
                api_calls_last_sync=api_calls,
                sync_status="completed" if errors == 0 else "completed_with_errors"
            )
            self.cache_db.upsert_sync_state(sync_state)

            # Create sync result
            status = "success" if errors == 0 else "partial_success"
            result = SyncResult(
                job_id=job_id,
                sync_type="incremental",
                status=status,
                pages_fetched=pages_fetched,
                pages_added=pages_added,
                pages_updated=pages_updated,
                pages_deleted=pages_deleted,
                pages_skipped=pages_skipped,
                duration_seconds=duration,
                api_calls_made=api_calls,
                rate_limit_hits=self.rate_limiter.total_waits,
                errors_encountered=errors,
                error_details="; ".join(error_details) if error_details else None,
                started_at=start_time,
                completed_at=datetime.now()
            )

            # Update job status
            job.status = "completed"
            job.completed_at = datetime.now()
            job.total_pages = len(all_pages_metadata['pages'])
            job.pages_processed = pages_fetched
            job.pages_added = pages_added
            job.pages_updated = pages_updated
            job.pages_deleted = pages_deleted
            job.api_calls_made = api_calls
            job.elapsed_seconds = duration
            self.cache_db.update_sync_job(job)

            # Create history record
            history = SyncHistory(
                sync_type="incremental",
                started_at=start_time,
                completed_at=datetime.now(),
                duration_seconds=duration,
                status=status,
                pages_fetched=pages_fetched,
                pages_added=pages_added,
                pages_updated=pages_updated,
                pages_deleted=pages_deleted,
                pages_skipped=pages_skipped,
                api_calls_made=api_calls,
                errors_encountered=errors,
                error_details="; ".join(error_details) if error_details else None,
                total_wait_time_seconds=self.rate_limiter.total_wait_time,
                rate_limit_hits=self.rate_limiter.total_waits,
                triggered_by=triggered_by,
                user_id=user_id,
                job_id=job_id
            )
            self.cache_db.create_sync_history(history)

            logger.info(
                f"Incremental sync completed: {pages_fetched} pages processed "
                f"({pages_added} new, {pages_updated} updated, {pages_deleted} deleted, "
                f"{pages_skipped} skipped), {api_calls} API calls, {duration}s duration"
            )

            return result

        except Exception as e:
            logger.error(f"Incremental sync failed: {e}", exc_info=True)

            # Mark job as failed
            job.status = "failed"
            job.last_error = str(e)
            job.error_count += 1
            self.cache_db.update_sync_job(job)

            # Update sync state
            self._update_sync_state_status("error", str(e))

            raise

        finally:
            # Clean up
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def sync_smart(
        self,
        triggered_by: str = "auto",
        user_id: Optional[str] = None
    ) -> SyncResult:
        """
        Smart sync: Automatically choose between full and incremental.

        Decision logic:
        - If never synced: Full sync
        - If last sync > 7 days: Full sync
        - If last sync had errors: Full sync
        - Otherwise: Incremental sync

        Args:
            triggered_by: Who/what triggered this sync
            user_id: User ID if applicable

        Returns:
            SyncResult
        """
        logger.info("Starting smart sync")

        # Get sync state
        sync_state = self.cache_db.get_sync_state('global', 'global')

        # Decision logic
        if not sync_state or not sync_state.last_full_sync_at:
            logger.info("Never synced before, running full sync")
            return await self.sync_full(triggered_by=triggered_by, user_id=user_id)

        days_since_full = (datetime.now() - sync_state.last_full_sync_at).days

        if days_since_full > 7:
            logger.info(f"Last full sync was {days_since_full} days ago, running full sync")
            return await self.sync_full(triggered_by=triggered_by, user_id=user_id)

        if sync_state.sync_status == "error":
            logger.info("Last sync had errors, running full sync")
            return await self.sync_full(triggered_by=triggered_by, user_id=user_id)

        logger.info("Recent sync is fresh, running incremental sync")
        return await self.sync_incremental(triggered_by=triggered_by, user_id=user_id)

    # =========================================================================
    # CONTROL METHODS
    # =========================================================================

    def pause_sync(self):
        """Request pause of current sync operation."""
        self._pause_requested = True
        logger.info("Sync pause requested")

    def resume_sync(self):
        """Resume paused sync operation."""
        self._pause_requested = False
        logger.info("Sync resumed")

    def cancel_sync(self):
        """Cancel current sync operation."""
        self._cancel_requested = True
        logger.info("Sync cancellation requested")

    def get_job_status(self, job_id: str) -> Optional[SyncJob]:
        """
        Get status of sync job.

        Args:
            job_id: Job identifier

        Returns:
            SyncJob if found, None otherwise
        """
        return self.cache_db.get_sync_job(job_id)

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    async def _sync_page(
        self,
        page: Dict[str, Any],
        notebook_id: str,
        notebook_name: str,
        section_id: str,
        section_name: str
    ) -> Dict[str, Any]:
        """
        Sync a single page from Graph API to cache.

        Args:
            page: Page metadata from Graph API
            notebook_id: Notebook ID
            notebook_name: Notebook name
            section_id: Section ID
            section_name: Section name

        Returns:
            Dict with sync results
        """
        page_id = page['id']
        page_title = page.get('title', 'Untitled')
        page_modified = self._parse_datetime(page.get('lastModifiedDateTime'))
        
        # Check if document exists in cache
        existing_doc = self.cache.get_document(page_id)
        is_new = existing_doc is None

        # Skip if page already cached and note modified
        if existing_doc and existing_doc.metadata.modified_date:
            # Compare modification dates
            if page_modified and existing_doc.metadata.modified_date >= page_modified:
                logger.debug(f"Skipping page {page_id} - already up-to-date in cache")
                return {
                    'page_id': page_id,
                    'is_new': False,
                    'skipped': True,
                    'api_calls': 0
                }
                
                
        # Fetch page content
        html_content = await self._fetch_with_rate_limit(
            self.onenote.get_page_content,
            page_id
        )

        if not html_content:
            logger.warning(f"Failed to fetch content for page {page_id}")
            html_content = ""
            
        # Parse HTML and extract text
        plain_text = self._extract_text_from_html(html_content)

        # Extract images with metadata
        images = self._extract_images_from_html(html_content, page_id)

        # Check for existing cached images
        existing_images = self.cache.get_images_for_document(page_id)
        existing_image_count = len(existing_images)
        
        # Download image data WITH RATE LIMITING (only if needed)
        downloaded_images = []
        
        # If we already have images cached and count matches, skip download
        if not is_new and existing_image_count>0 and existing_image_count == len(images):
            logger.debug(f"Skipping image download for page {page_id} - {existing_image_count} images already cached")
            # Use existing image metadata
            for existing_img in existing_images:
                downloaded_images.append({
                    'data': None,  # No need to re-download
                    'alt_text': existing_img.alt_text,
                    'resource_id': existing_img.graph_resource_id,
                    'cached': True
                })
        else:
            # Download images
            for idx, img_meta in enumerate(images):
                # Add delay between image downloads to avoid rate limits
                # Image resources have MUCH stricter rate limits than pages
                if idx > 0 : # Not first image
                    await asyncio.sleep(3.0) # 3 second delay between image downloads (20 per minute)
                
                image_bytes = await self._download_image(img_meta.get('src'))
                if image_bytes:
                    img_meta['data'] = image_bytes
                    img_meta['cached'] = False
                    downloaded_images.append(img_meta)
                else:
                    logger.debug(f"Failed to download image from {img_meta.get('src')} ")
                    
        # Create document metadata
        metadata = DocumentMetadata(
            page_id=page_id,
            page_title=page_title,
            notebook_name=notebook_name,
            section_name=section_name,
            created_date=self._parse_datetime(page.get('createdDateTime')),
            modified_date=self._parse_datetime(page.get('lastModifiedDateTime')),
            author=page.get('createdBy', {}).get('user', {}).get('displayName', 'Unknown'),
            url=page.get('links', {}).get('oneNoteWebUrl', {}).get('href', ''),
            tags=[],
            has_images=len(downloaded_images) > 0,
            image_count=len(downloaded_images)
        )

        # Create document
        document = Document(
            id=page_id,
            page_id=page_id,
            content=plain_text,
            html_content=html_content,
            metadata=metadata
        )

        # Cache document
        self.cache.cache_document(document)

        # Cache images (skip if already cached)
        for idx, image_data in enumerate(downloaded_images):
            # Skip if this image is already cached
            if image_data.get('cached'):
                continue
            
            # Save image file
            image_path = self.image_storage.generate_image_path(page_id, idx)
            await self.image_storage.upload(image_path, image_data['data'])

            # Cache image metadata
            self.cache.cache_image_metadata(
                page_id=page_id,
                image_index=idx,
                file_path=image_path,
                alt_text=image_data.get('alt_text'),
                graph_resource_id=image_data.get('resource_id')
            )

        return {
            'page_id': page_id,
            'is_new': is_new,
            'api_calls': 1  # One call to get_page_content
        }

    async def _sync_page_from_metadata(self, page_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync a page when only metadata is available.

        Args:
            page_meta: Page metadata

        Returns:
            Dict with sync results
        """
        # Extract hierarchy info from metadata
        parent_section = page_meta.get('parentSection', {})
        parent_notebook = page_meta.get('parentNotebook', {})

        return await self._sync_page(
            page=page_meta,
            notebook_id=parent_notebook.get('id', ''),
            notebook_name=parent_notebook.get('displayName', 'Unknown'),
            section_id=parent_section.get('id', ''),
            section_name=parent_section.get('displayName', 'Unknown')
        )

    async def _fetch_all_pages_metadata(self) -> Dict[str, Any]:
        """
        Fetch metadata for all pages (without content).

        Returns:
            Dict with pages list and API call count
        """
        all_pages = []
        api_calls = 0

        # Fetch notebooks
        notebooks = await self._fetch_with_rate_limit(self.onenote.list_notebooks)
        api_calls += 1

        # For each notebook, get sections and pages
        for notebook in notebooks:
            sections = await self._fetch_with_rate_limit(
                self.onenote.list_sections,
                notebook['id']
            )
            api_calls += 1

            for section in sections:
                pages = await self._fetch_with_rate_limit(
                    self.onenote.list_pages,
                    section['id']
                )
                api_calls += 1

                # Add parent info to each page
                for page in pages:
                    page['parentSection'] = {'id': section['id'], 'displayName': section.get('displayName')}
                    page['parentNotebook'] = {'id': notebook['id'], 'displayName': notebook.get('displayName')}

                all_pages.extend(pages)

        return {
            'pages': all_pages,
            'api_calls': api_calls
        }

    async def _fetch_with_rate_limit(self, func, *args, **kwargs):
        """
        Execute function with rate limiting.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        # Rate limiter is already applied in OneNoteService
        # This just wraps it for async compatibility
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def _should_stop(self) -> bool:
        """Check if sync should stop (paused or cancelled)."""
        return self._pause_requested or self._cancel_requested

    def _update_job_progress(self, job: SyncJob, pages_processed: int, api_calls: int):
        """Update job progress in database."""
        job.pages_processed = pages_processed
        job.api_calls_made = api_calls
        job.elapsed_seconds = (datetime.now() - job.created_at).seconds

        if job.total_pages > 0:
            job.progress_percent = (pages_processed / job.total_pages) * 100

        self.cache_db.update_sync_job(job)

    def _update_sync_state_status(self, status: str, error: Optional[str] = None):
        """Update global sync state status."""
        sync_state = self.cache_db.get_sync_state('global', 'global')
        if sync_state:
            sync_state.sync_status = status
            if error:
                sync_state.last_sync_error = error
            self.cache_db.upsert_sync_state(sync_state)

    @staticmethod
    def _extract_text_from_html(html_content: str) -> str:
        """Extract plain text from HTML."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return ' '.join(chunk for chunk in chunks if chunk)
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
            return ""

    async def _download_image(self, image_url: str) -> Optional[bytes]:
            """
            Download image from URL (Graph API or data URL).
    
            Args:
                image_url: URL of the image
    
            Returns:
                Image data as bytes, or None if download fails
            """
            if not image_url:
                return None
            
            try:
                # Handle data URLs (base64 encoded images)
                if image_url.startswith('data:image'):
                    match = re.search(r'base64,(.+)', image_url)
                    if match:
                        base64_data = match.group(1)
                        return base64.b64decode(base64_data)
                    return None
    
                # Download from Graph API URL with authentication
                # Use the rate limiter's internal mechanism
                loop = asyncio.get_event_loop()
            
                def _download():
                    """Synchronous download wrapped for async."""
                    # This will block until rate limiter allows
                    self.rate_limiter.acquire(wait=True)
                
                    headers = {
                        'Authorization': f'Bearer {self.onenote.access_token}'
                    }
                
                    max_retries = 3
                    for attempt in range(max_retries):
                        response = requests.get(image_url, headers=headers, timeout=30)
                    
                        # Handle rate limit errors with hardcoded 10-minute wait
                        if response.status_code == 429:
                            # Microsoft Graph API image resources require LONG waits
                            wait_time = 600  # Hardcoded 10 minutes (600 seconds)
                        
                            logger.warning(
                                f"⚠️  Rate limit hit on image download (attempt {attempt + 1}/{max_retries}). "
                                f"Waiting {wait_time}s (10 minutes) as required by Microsoft Graph API. "
                                f"Image resource endpoint has very strict limits."
                            )
                            self.rate_limiter.record_error(is_rate_limit=True)
                        
                            if attempt < max_retries - 1:
                                import time
                                logger.info(f"⏰ Pausing image downloads for 10 minutes...")
                                time.sleep(wait_time)
                                logger.info(f"⏰ Resuming after 10-minute wait...")
                                continue
                            else:
                                logger.error(
                                    f"❌ Failed to download image after {max_retries} attempts and "
                                    f"30 minutes of waiting. Skipping this image to continue sync."
                                )
                                return None  # Give up gracefully
                    
                        response.raise_for_status()
                        self.rate_limiter.record_success()
                        return response.content
            
                # Run in thread pool to avoid blocking event loop
                image_data = await loop.run_in_executor(None, _download)
                logger.debug(f"Downloaded image: {len(image_data)} bytes")
                return image_data
    
            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response and e.response.status_code == 429:
                    logger.warning(f"Rate limit error downloading image: {image_url}")
                    self.rate_limiter.record_error(is_rate_limit=True)
                else:
                    logger.warning(f"HTTP error downloading image from {image_url}: {str(e)}")
                return None
            except Exception as e:
                logger.warning(f"Error downloading image from {image_url}: {str(e)}")
                return None
    
    
    @staticmethod
    def _extract_images_from_html(html_content: str, page_id: str) -> List[Dict[str, Any]]:
        """
        Extract images from HTML content.

        Args:
            html_content: HTML string
            page_id: Page ID

        Returns:
            List of image data dicts
        """
        images = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            img_tags = soup.find_all('img')

            for img in img_tags:
                images.append({
                    'src': img.get('src'),
                    'alt_text': img.get('alt', ''),
                    'data-fullres-src': img.get('data-fullres-src'),
                    'resource_id': img.get('src'),  # Graph API resource URL
                    'data': None  # Will be populated when downloading
                })

        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        return images

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """Parse datetime from string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
