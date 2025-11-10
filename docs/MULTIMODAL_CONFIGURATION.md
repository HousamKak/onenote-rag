# Multimodal RAG Configuration Guide

This guide explains how to configure and use the multimodal RAG features (text + metadata + images).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Variables](#environment-variables)
4. [Service Configuration](#service-configuration)
5. [API Endpoints](#api-endpoints)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

## Overview

The multimodal RAG system extends the text-only RAG with:

- **Image Analysis**: GPT-4o Vision analyzes images during indexing
- **Metadata Enrichment**: Metadata is semantically searchable
- **Visual Query Detection**: Automatically detects and handles image-related questions
- **Document Integrity**: page_id links all document components (text + images)
- **Unified Search**: Single vector index with combined text + metadata + image descriptions

## Prerequisites

### Required

- **OpenAI API Key**: Required for GPT-4o Vision
  - Used for image analysis and visual queries
  - Cost-efficient models: `gpt-4o-mini` for indexing, `gpt-4o` for queries

### Optional

- **OneNote Access**: Required only if indexing from OneNote
  - Microsoft Graph Token or Client ID/Secret
- **S3-Compatible Storage**: Optional for production image storage
  - Default uses local filesystem

## Environment Variables

### Core Configuration (`.env` file)

```bash
# OpenAI Configuration (REQUIRED for multimodal)
OPENAI_API_KEY=sk-...

# Microsoft Graph (for OneNote integration)
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_TENANT_ID=...
MICROSOFT_GRAPH_TOKEN=...  # Optional: Manual token

# Vector Database
VECTOR_DB_PATH=./data/chroma
EMBEDDING_PROVIDER=openai  # or 'huggingface'

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Multimodal-Specific Configuration

These are configured in code (see `backend/main.py`):

```python
# Vision Service
vision_service = GPT4VisionService(
    api_key=openai_key,
    default_model="gpt-4o-mini",  # Cost-efficient for indexing
    max_tokens=1000,
    temperature=0.0  # Deterministic
)

# Image Storage (Local)
image_storage = ImageStorageService(
    storage_type="local",  # or "s3"
    base_path="backend/storage/images"
)

# Image Storage (S3) - Optional
image_storage = ImageStorageService(
    storage_type="s3",
    s3_endpoint="http://localhost:9000",  # MinIO or AWS
    s3_access_key="minioadmin",
    s3_secret_key="minioadmin",
    s3_bucket="onenote-rag-images"
)
```

### Database Configuration (Settings Service)

You can also configure via the settings API:

```bash
# Set OpenAI key via API
curl -X PUT http://localhost:8000/api/settings/openai_api_key \
  -H "Content-Type: application/json" \
  -d '{"value": "sk-..."}'

# Enable startup sync
curl -X PUT http://localhost:8000/api/settings/enable_startup_sync \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'
```

## Service Configuration

### 1. Default Configuration (main.py)

The system auto-initializes multimodal services if OpenAI API key is available:

```python
# From backend/main.py (simplified)
if openai_key:
    vision_service = GPT4VisionService(api_key=openai_key, ...)
    image_storage = ImageStorageService(storage_type="local", ...)
    multimodal_handler = MultimodalQueryHandler(vision_service, image_storage)

    rag_engine = RAGEngine(
        vector_store=vector_store,
        multimodal_handler=multimodal_handler  # Enables multimodal
    )
else:
    rag_engine = RAGEngine(vector_store=vector_store)  # Text-only mode
```

### 2. Custom Configuration

For custom setups, initialize services manually:

```python
from services.vision_service import GPT4VisionService
from services.image_storage import ImageStorageService
from services.multimodal_processor import MultimodalDocumentProcessor
from services.multimodal_query import MultimodalQueryHandler

# Vision service with custom model
vision_service = GPT4VisionService(
    api_key=os.getenv("OPENAI_API_KEY"),
    default_model="gpt-4o",  # Higher quality, higher cost
    max_tokens=2000,
    temperature=0.1
)

# S3 storage for production
image_storage = ImageStorageService(
    storage_type="s3",
    s3_endpoint="https://s3.amazonaws.com",
    s3_access_key=os.getenv("AWS_ACCESS_KEY"),
    s3_secret_key=os.getenv("AWS_SECRET_KEY"),
    s3_bucket="my-rag-images"
)

# Multimodal processor for indexing
processor = MultimodalDocumentProcessor(
    vision_service=vision_service,
    chunk_size=1000,
    chunk_overlap=200,
    max_images_per_document=10  # Limit images per doc
)

# Query handler
query_handler = MultimodalQueryHandler(
    vision_service=vision_service,
    image_storage=image_storage
)
```

## API Endpoints

### 1. Multimodal Query

Query with automatic image detection and retrieval:

```bash
POST /api/query/multimodal
Content-Type: application/json

{
  "question": "Show me the architecture diagram from the design doc",
  "config": null  # Optional RAG config
}

# Response includes images if visual query detected:
{
  "answer": "Here's the architecture diagram...",
  "sources": [...],
  "metadata": {
    "techniques_used": ["basic_rag", "multimodal_visual_query"],
    ...
  },
  "images": [
    {
      "page_id": "ABC123",
      "page_title": "System Design",
      "image_index": 0,
      "image_path": "ABC12345/ABC123_0.png",
      "public_url": "/api/images/ABC123/0"
    }
  ]
}
```

### 2. Image Retrieval

Fetch specific images:

```bash
GET /api/images/{page_id}/{image_index}

# Example:
GET /api/images/ABC123/0

# Returns: PNG image data (binary)
Content-Type: image/png
```

### 3. Standard Query (Text-Only)

Original endpoint still available for backwards compatibility:

```bash
POST /api/query
Content-Type: application/json

{
  "question": "What is the project status?"
}

# Response: Text-only, no images
```

### 4. Document Indexing

Index documents with multimodal support:

```bash
POST /api/index/sync
Content-Type: application/json

{
  "notebook_ids": null,  # null = all notebooks
  "full_sync": false,    # Incremental by default
  "force_reindex": false
}

# Indexes:
# - Text content
# - Metadata (prepended to text)
# - Images (analyzed with GPT-4o Vision)
# All linked by page_id
```

## Usage Examples

### Example 1: Visual Query

```python
import requests

response = requests.post(
    "http://localhost:8000/api/query/multimodal",
    json={"question": "Show me diagrams about the API architecture"}
)

data = response.json()

print(f"Answer: {data['answer']}")

if data['images']:
    print(f"\nFound {len(data['images'])} images:")
    for img in data['images']:
        print(f"  - {img['page_title']}: {img['public_url']}")

        # Download image
        img_response = requests.get(f"http://localhost:8000{img['public_url']}")
        with open(f"image_{img['image_index']}.png", "wb") as f:
            f.write(img_response.content)
```

### Example 2: Text Query with Metadata Search

```python
# Metadata is searchable thanks to enrichment
response = requests.post(
    "http://localhost:8000/api/query/multimodal",
    json={"question": "Find documents by John Doe from the Engineering notebook"}
)

# Searches across:
# - Text content
# - Author metadata (enriched)
# - Notebook/section names (enriched)
# - Tags (enriched)
```

### Example 3: Document Integrity

```python
# Reconstruct complete document from any retrieved chunk

# 1. Query returns chunk
response = requests.post(
    "http://localhost:8000/api/query/multimodal",
    json={"question": "API documentation"}
)

source = response.json()['sources'][0]
page_id = source['document_id']  # e.g., "ABC123"

# 2. Get all images for this document
# (Images automatically included in response if visual query)
# Or fetch manually:
import requests

images = []
for i in range(10):  # Try up to 10 images
    img_url = f"http://localhost:8000/api/images/{page_id}/{i}"
    img_response = requests.get(img_url)
    if img_response.status_code == 200:
        images.append(img_response.content)
    else:
        break  # No more images

print(f"Document {page_id} has {len(images)} images")
```

## Troubleshooting

### Issue: "Multimodal features disabled"

**Cause**: OpenAI API key not configured

**Solution**:
```bash
# Set in .env
OPENAI_API_KEY=sk-...

# Or via API
curl -X PUT http://localhost:8000/api/settings/openai_api_key \
  -H "Content-Type: application/json" \
  -d '{"value": "sk-..."}'

# Restart server
```

### Issue: Images not found (404)

**Cause**: Images not indexed yet or storage path incorrect

**Solution**:
```bash
# 1. Check storage path
ls backend/storage/images/

# 2. Re-index with multimodal support
curl -X POST http://localhost:8000/api/index/sync \
  -H "Content-Type: application/json" \
  -d '{"full_sync": true}'

# 3. Verify images were extracted
ls backend/storage/images/*/
```

### Issue: Visual queries not detecting images

**Cause**: Query doesn't contain visual keywords

**Solution**: Use explicit visual terms:
- ✓ "Show me the diagram"
- ✓ "What images are in..."
- ✓ "Picture of..."
- ✗ "Explain the system" (too generic)

### Issue: High API costs

**Cause**: Using gpt-4o for all image analysis

**Solution**:
```python
# Use gpt-4o-mini for indexing (56% cost reduction)
vision_service = GPT4VisionService(
    default_model="gpt-4o-mini"  # Cheaper
)

# Reserve gpt-4o for important queries:
await vision_service.answer_question_about_images(
    question=query,
    images=images,
    model="gpt-4o"  # Explicit override for quality
)
```

### Issue: SSL certificate errors

**Cause**: Corporate proxy blocking OpenAI API

**Solution**: Already configured in code (see `backend/main.py`)
```python
# SSL verification disabled globally
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
```

## Cost Optimization

### Model Selection

| Model | Use Case | Cost (per 1M tokens) |
|-------|----------|---------------------|
| gpt-4o-mini | Indexing, descriptions | ~$0.15 |
| gpt-4o | Visual Q&A, high quality | ~$2.50 |

**Recommendation**: Use `gpt-4o-mini` for indexing (default), `gpt-4o` for queries.

### Batch Processing

Index documents in batches to amortize API call overhead:

```python
# Good: Process all documents in one session
chunks_all = []
images_all = []
for doc in documents:
    chunks, images = await processor.chunk_document_multimodal(doc)
    chunks_all.extend(chunks)
    images_all.extend(images)

vector_store.add_documents(chunks_all)  # Bulk insert
```

### Image Limits

Limit images per document to control costs:

```python
processor = MultimodalDocumentProcessor(
    max_images_per_document=5  # Default: 10
)
```

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTIMODAL RAG SYSTEM                    │
└─────────────────────────────────────────────────────────────┘

INDEXING FLOW:
OneNote → Extract (text, metadata, images) → GPT-4o Vision
       → Enrich metadata → Combine all → Chunk → Embed
       → Store chunks in ChromaDB + images in storage
       → Link everything with page_id

QUERY FLOW:
User query → Visual detection? → Retrieve text chunks from DB
          → Extract page_ids → Fetch images from storage
          → GPT-4o answers with images → Return combined response

KEY PRINCIPLE:
page_id is the universal linking key connecting:
  - Text chunks (in vector DB)
  - Images (in file/S3 storage)
  - Metadata (embedded in chunks)
  → Document integrity maintained!
```

## Next Steps

1. **Basic Setup**:
   - Set `OPENAI_API_KEY` in `.env`
   - Start server: `uvicorn main:app --reload`
   - Verify: Check logs for "Multimodal query handler initialized"

2. **Index Documents**:
   - Sync OneNote: `POST /api/index/sync`
   - Verify images: `ls backend/storage/images/`

3. **Test Queries**:
   - Text query: `POST /api/query`
   - Visual query: `POST /api/query/multimodal`
   - Check response for `images` field

4. **Production Deployment**:
   - Switch to S3 storage for images
   - Configure cost limits on OpenAI
   - Monitor usage with LangSmith tracing

## Related Documentation

- [Multimodal Implementation Guide](./MULTIMODAL_IMPLEMENTATION_GUIDE.md)
- [Multimodal Architecture](./MULTIMODAL_INDEXING_ARCHITECTURE.md)
- [RAG Techniques Implementation](./RAG_TECHNIQUES_IMPLEMENTATION_PLAN.md)
- [API Documentation](http://localhost:8000/docs)
