# Multimodal Sync Integration Guide

## Overview

The sync/indexing process is now **fully integrated with the multimodal workflow**. When documents are synced from OneNote, they are automatically processed with multimodal capabilities (text + metadata + images) if available.

## How It Works

### Automatic Multimodal Processing

When you call the sync endpoint, the system now:

1. **Checks for multimodal availability** - Looks for OpenAI API key and multimodal services
2. **Selects appropriate processor**:
   - **Multimodal mode** (default): Uses `MultimodalDocumentProcessor` if available
   - **Text-only mode** (fallback): Uses standard `DocumentProcessor` if multimodal unavailable
3. **Processes documents accordingly**:
   - Extracts text content
   - Enriches with metadata
   - **Analyzes images with GPT-4o Vision** (multimodal only)
   - **Stores images in image storage** (multimodal only)
   - Creates unified chunks with page_id linking

### API Changes

#### Sync Request (Enhanced)

```json
POST /api/index/sync
{
  "notebook_ids": null,           // null = all notebooks
  "full_sync": false,             // Incremental by default
  "force_reindex": false,         // Don't force reindex
  "multimodal": true              // NEW: Enable multimodal processing (default: true)
}
```

**New Parameter: `multimodal`**
- `true` (default): Use multimodal processing if available
- `false`: Force text-only processing even if multimodal available

#### Sync Behavior

```
IF multimodal=true AND multimodal_processor available:
  → Use MultimodalDocumentProcessor
  → Extract and analyze images with GPT-4o Vision
  → Store images in backend/storage/images/
  → Link everything with page_id
  → Log: "Using MULTIMODAL processing (text + images)"

ELSE:
  → Use standard DocumentProcessor
  → Text-only indexing (original behavior)
  → Log: "Using TEXT-ONLY processing"
```

## Usage Examples

### Example 1: Full Multimodal Sync

```bash
# Sync all notebooks with multimodal support (default)
curl -X POST http://localhost:8000/api/index/sync \
  -H "Content-Type: application/json" \
  -d '{
    "full_sync": true,
    "multimodal": true
  }'

# Response:
# {
#   "status": "success",
#   "documents_processed": 25,
#   "documents_added": 25,
#   "documents_updated": 0,
#   "documents_skipped": 0,
#   "chunks_created": 150,
#   "message": "Successfully synced: 25 added (150 chunks)"
# }

# Logs will show:
# INFO - Using MULTIMODAL processing (text + images)
# INFO - Analyzed image 1/3
# INFO - Analyzed image 2/3
# INFO - Analyzed image 3/3
# INFO - Stored 3 images for document ABC123
```

### Example 2: Text-Only Sync (Forced)

```bash
# Sync without images (force text-only)
curl -X POST http://localhost:8000/api/index/sync \
  -H "Content-Type: application/json" \
  -d '{
    "full_sync": false,
    "multimodal": false
  }'

# Logs will show:
# INFO - Using TEXT-ONLY processing
```

### Example 3: Incremental Multimodal Sync

```bash
# Incremental sync with multimodal (only changed docs)
curl -X POST http://localhost:8000/api/index/sync \
  -H "Content-Type: application/json" \
  -d '{
    "notebook_ids": ["notebook-123"],
    "full_sync": false,
    "force_reindex": false,
    "multimodal": true
  }'

# Only modified/new documents will be processed with images
```

## Technical Details

### Service Initialization (main.py)

The multimodal services are now initialized and exposed to the API routes:

```python
# In main.py startup:
if openai_key:
    # 1. Initialize vision service
    vision_service = GPT4VisionService(...)

    # 2. Initialize image storage
    image_storage = ImageStorageService(...)

    # 3. Initialize multimodal processor (NEW!)
    multimodal_processor = MultimodalDocumentProcessor(
        vision_service=vision_service,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        max_images_per_document=10,
        access_token=access_token
    )

    # 4. Initialize query handler
    multimodal_handler = MultimodalQueryHandler(...)

    # 5. Expose to routes (NEW!)
    routes.vision_service = vision_service
    routes.image_storage = image_storage
    routes.multimodal_processor = multimodal_processor
```

### Sync Endpoint Logic (routes.py)

```python
@router.post("/index/sync")
async def sync_documents(request: SyncRequest, ...):
    # Check if multimodal available
    use_multimodal = request.multimodal and multimodal_processor is not None

    if use_multimodal:
        logger.info("Using MULTIMODAL processing (text + images)")
    else:
        logger.info("Using TEXT-ONLY processing")

    for doc in documents:
        if use_multimodal:
            # Multimodal: text + metadata + images
            chunks, image_data_list = await multimodal_processor.chunk_document_multimodal(
                document=doc,
                enrich_with_metadata=True,
                include_images=True
            )

            # Store images
            for img_data in image_data_list:
                image_path = image_storage.generate_image_path(
                    page_id=img_data["page_id"],
                    image_index=img_data["position"]
                )
                await image_storage.upload(
                    image_path=image_path,
                    image_data=img_data["data"],
                    ...
                )
        else:
            # Text-only: original behavior
            chunks = processor.chunk_documents([doc])

        # Add to vector store
        store.add_documents(chunks)
```

### Image Storage Structure

Images are stored with page_id-based naming:

```
backend/storage/images/
├── ABC12345/              # Subfolder: first 8 chars of page_id
│   ├── ABC123_0.png       # Image 0 for document ABC123
│   ├── ABC123_0.json      # Metadata for image 0
│   ├── ABC123_1.png       # Image 1 for document ABC123
│   └── ABC123_1.json      # Metadata for image 1
├── DEF67890/
│   ├── DEF678_0.png
│   └── DEF678_0.json
...
```

## Document Integrity

The multimodal sync maintains perfect document integrity through page_id:

```
Document ABC123 (OneNote)
  ↓ Sync with multimodal=true

Vector Database (ChromaDB):
  - Chunk 0: {page_id: "ABC123", chunk_index: 0, has_images: true, image_count: 3}
  - Chunk 1: {page_id: "ABC123", chunk_index: 1, has_images: true, image_count: 3}
  - Chunk 2: {page_id: "ABC123", chunk_index: 2, has_images: true, image_count: 3}

Image Storage:
  - ABC12345/ABC123_0.png
  - ABC12345/ABC123_1.png
  - ABC12345/ABC123_2.png

All linked by page_id = "ABC123" !
```

## Graceful Fallback

The system gracefully handles missing multimodal services:

| Scenario | Behavior |
|----------|----------|
| OpenAI key set + multimodal=true | ✅ Multimodal processing |
| OpenAI key NOT set + multimodal=true | ⚠️ Fallback to text-only |
| OpenAI key set + multimodal=false | ✅ Force text-only |
| OpenAI key NOT set + multimodal=false | ✅ Text-only |

Logs clearly indicate which mode is being used:
```
INFO - Using MULTIMODAL processing (text + images)
```
or
```
WARNING - Multimodal processing requested but not available - falling back to text-only
INFO - Using TEXT-ONLY processing
```

## Monitoring & Debugging

### Check Multimodal Status

```bash
# Check if multimodal services initialized
# Look for these logs on startup:

✓ Vision service initialized
✓ Image storage initialized
✓ Multimodal document processor initialized
✓ Multimodal query handler initialized
✓ Multimodal services exposed to API routes
✓ RAG engine initialized with multimodal support
```

### Verify Images Stored

```bash
# Check image storage directory
ls -la backend/storage/images/

# Should see subfolders with page_id prefixes
# Example:
# ABC12345/
# DEF67890/
# etc.
```

### Test Multimodal Sync

```python
import requests

# Test sync endpoint
response = requests.post(
    "http://localhost:8000/api/index/sync",
    json={
        "full_sync": True,
        "multimodal": True
    }
)

print(response.json())

# Check server logs for:
# - "Using MULTIMODAL processing (text + images)"
# - "Analyzed image X/Y"
# - "Stored N images for document PAGE_ID"
```

## Cost Implications

### Multimodal Sync Costs

When `multimodal=true`, images are analyzed with GPT-4o Vision:

| Component | Cost | Notes |
|-----------|------|-------|
| Text extraction | Free | BeautifulSoup parsing |
| Text embedding | ~$0.0001/1K tokens | text-embedding-ada-002 |
| Image analysis | ~$0.15/1M tokens | gpt-4o-mini (default) |
| Image storage | Free (local) | Or S3 costs if using S3 |

**Example Cost Calculation:**
- 100 documents
- 3 images per document = 300 images
- ~500 tokens per image analysis = 150,000 tokens
- **Cost: ~$0.02 for all image analysis**

Using `gpt-4o-mini` for indexing is **56% cheaper** than gpt-4o!

### Cost Optimization Tips

1. **Use incremental sync** (default) - Only processes changed documents
2. **Limit images per document** - Set `max_images_per_document` in config
3. **Use gpt-4o-mini** (default) - Much cheaper than gpt-4o for indexing
4. **Text-only for non-visual documents** - Set `multimodal=false` for text-heavy notebooks

## Troubleshooting

### Issue: "Multimodal processing requested but not available"

**Cause**: OpenAI API key not configured

**Solution**:
```bash
# Set in .env
OPENAI_API_KEY=sk-...

# Or via settings API
curl -X PUT http://localhost:8000/api/settings/openai_api_key \
  -H "Content-Type: application/json" \
  -d '{"value": "sk-..."}'

# Restart server
```

### Issue: Images not found after sync

**Cause**: Image storage path incorrect or permissions issue

**Solution**:
```bash
# Check storage directory exists and is writable
mkdir -p backend/storage/images
chmod 755 backend/storage/images

# Check logs for image upload errors
grep "Error storing image" backend.log
```

### Issue: Sync is slow

**Cause**: Image analysis takes time (GPT-4o Vision API calls)

**Expected Performance**:
- ~2-3 seconds per image (GPT-4o-mini)
- 3 images per document = ~6-9 seconds per document
- Can be slower with network latency

**Optimization**:
```python
# In multimodal_processor initialization:
MultimodalDocumentProcessor(
    max_images_per_document=5,  # Reduce from 10 to 5
    ...
)
```

### Issue: Want to re-sync with images after text-only sync

**Solution**:
```bash
# Force reindex with multimodal
curl -X POST http://localhost:8000/api/index/sync \
  -H "Content-Type: application/json" \
  -d '{
    "full_sync": true,
    "force_reindex": true,
    "multimodal": true
  }'
```

## Migration Path

### Existing Text-Only Index → Multimodal

If you have an existing text-only index and want to add images:

1. **Full resync with multimodal**:
   ```bash
   POST /api/index/sync
   {
     "full_sync": true,
     "multimodal": true
   }
   ```

2. **Images will be analyzed and stored**
3. **Chunks will be updated with `has_images` and `image_count` metadata**
4. **Old text-only chunks will be replaced**

### Multimodal → Text-Only

To remove images and go back to text-only:

1. **Clear image storage**:
   ```bash
   rm -rf backend/storage/images/*
   ```

2. **Resync without multimodal**:
   ```bash
   POST /api/index/sync
   {
     "full_sync": true,
     "multimodal": false
   }
   ```

## Summary

✅ **Sync process is now multimodal-aware**
- Automatically uses multimodal processing if available
- Graceful fallback to text-only
- Controlled via `multimodal` parameter
- Full document integrity via page_id
- Cost-efficient with gpt-4o-mini
- Comprehensive logging for debugging

🚀 **Ready to use**: Just sync your documents and images will be automatically processed and stored!
