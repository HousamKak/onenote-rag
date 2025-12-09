# Automatic Resync for Failed Content Fetches
 
## Problem
During sync, some pages fail to fetch content due to:
- Rate limiting (429 errors)
- Token expiration
- Network issues
- API temporary failures
 
Previously, these pages would be saved with empty content and silently ignored on subsequent syncs.
 
## Solution
Added a `needs_resync` flag to automatically retry failed pages without requiring a full resync.
 
## How It Works
 
### 1. Automatic Marking
Pages are automatically marked with `needs_resync=1` when:
- Content fetch returns empty/null
- Both HTML and text content are < 10 bytes (suspiciously empty)
- Any warning is logged during content fetch
 
### 2. Smart Sync Processing
During **Smart Sync** or **Incremental Sync**:
1. API fetches only recently modified pages (normal incremental behavior)
2. **After** API fetch, system checks database for pages with `needs_resync=1`
3. These pages are re-fetched regardless of modification date
4. Flag is cleared only if content fetch succeeds
 
### 3. Database Schema
```sql
ALTER TABLE onenote_documents
ADD COLUMN needs_resync INTEGER DEFAULT 0;
 
CREATE INDEX idx_needs_resync
ON onenote_documents(needs_resync)
WHERE needs_resync = 1;
```
 
## Usage
 
### Check Status
```bash
python check_resync_status.py
```
 
Shows:
- Total pages needing resync
- List of pages with empty content
- Breakdown by section
 
### Trigger Resync
1. Run **Smart Sync** in the UI
2. System will:
   - Do normal incremental sync for modified pages
   - **Additionally** retry all pages with `needs_resync=1`
3. Monitor backend logs for:
   - `🔄 Force re-syncing: <title> (needs_resync=True)`
   - `✅ Successfully re-synced: <title>`
 
### Manual Marking (if needed)
```bash
python mark_for_resync_v2.py
```
 
## Benefits
 
1. **No Full Sync Required**: Only retries failed pages, not all 1000+ pages
2. **Automatic Recovery**: System self-heals from temporary failures
3. **Transparent**: All resync activity is logged
4. **Efficient**: Minimal API calls (only failed pages)
 
## Code Changes
 
### sync_orchestrator.py
```python
# Detect empty content and mark for resync
if not html_content:
    logger.warning(f"Failed to fetch content for page {page_id}")
    if existing_doc:
        self.cache.mark_documents_need_resync([page_id])
    html_content = ""
 
# Check if content is suspiciously empty
if len(html_content) < 10 and len(plain_text) < 5:
    logger.warning(f"Page '{page_title}' has empty/minimal content - marking for resync")
    self.cache.mark_documents_need_resync([page_id])
```
 
### Database-level Filtering Bypass
```python
# Skip cached pages UNLESS they need resync
needs_resync = existing_doc.needs_resync if existing_doc else False
 
if existing_doc and existing_doc.metadata.modified_date and not needs_resync:
    if page_modified and existing_doc.metadata.modified_date >= page_modified:
        logger.info(f"⏭️  Skipped: {page_title} (cached version up-to-date)")
        return {'skipped': True}
 
if needs_resync:
    logger.info(f"🔄 Force re-syncing: {page_title} (needs_resync=True)")
```
 
### Post-API Resync Check
```python
# After normal incremental sync, check for pages needing resync
if incremental_mode:
    resync_page_ids = self.cache.get_documents_needing_resync()
   
    for page_id in resync_page_ids:
        cached_doc = self.cache.get_document(page_id)
        # Re-sync page with cached metadata
        result = await self._sync_page(...)
```
 
## Migration
```bash
python apply_migration.py
```
 
This will:
1. Add `needs_resync` column
2. Create index for efficient queries
3. Automatically mark all existing empty pages (193 found)
 
## Current Status (2025-12-03)
- 193 pages marked for resync (19.1% of total)
- Mostly in sections: TGNA (78.2%), K (39.1%)
- All marked pages have 0 bytes HTML/text
- Ready for Smart Sync to retry
 
## Future Enhancements
1. Track retry count and give up after N failures
2. Exponential backoff for repeated failures
3. Email notification for persistent failures
4. UI indicator showing resync progress
 
 