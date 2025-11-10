# Document Integrity in Multimodal RAG

## The Core Principle: Documents Stay Together

**Every chunk knows which document it belongs to, so we can always retrieve the complete document with all its components.**

---

## Visual Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     OneNote Document                         │
│  ID: ABC123                                                  │
│  Title: "Architecture Overview"                              │
│                                                              │
│  ┌──────────────────────┐  ┌───────────────────────────┐   │
│  │ Text Content         │  │ Images                    │   │
│  │                      │  │                           │   │
│  │ "This describes      │  │ [diagram.png]             │   │
│  │  our architecture    │  │ [screenshot.png]          │   │
│  │  with microservices" │  │                           │   │
│  └──────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Metadata                                             │   │
│  │ Notebook: Engineering, Tags: [important]             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    PROCESSING
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED EMBEDDED CHUNKS (Vector DB)             │
│                                                              │
│  Chunk 1 (page_id: ABC123):                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Document: "Architecture Overview"                  │     │
│  │ Notebook: Engineering, Tags: important             │     │
│  │ This describes our architecture with microservices │     │
│  │ [Image 1]: Diagram showing API Gateway and Auth... │     │
│  │ [Image 2]: Screenshot of deployment pipeline...    │     │
│  └────────────────────────────────────────────────────┘     │
│            → Embedding: [0.23, -0.45, 0.18, ...]            │
│                                                              │
│  Chunk 2 (page_id: ABC123):                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │ (continuation of document)                         │     │
│  │ The microservices communicate via message queue... │     │
│  └────────────────────────────────────────────────────┘     │
│            → Embedding: [0.15, 0.32, -0.11, ...]            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│           IMAGE STORAGE (Linked by page_id)                  │
│                                                              │
│  storage/images/ABC123_0.png  ← Image 1 (diagram)           │
│  storage/images/ABC123_1.png  ← Image 2 (screenshot)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Query Examples

### Example 1: Text-based Query

```
User Query: "How do microservices communicate?"

1. SEARCH VECTOR DB
   ┌────────────────────────────────────────┐
   │ Query: "How do microservices          │
   │         communicate?"                  │
   └────────────────────────────────────────┘
                    ↓
   ┌────────────────────────────────────────┐
   │ Found: Chunk 2 (page_id: ABC123)      │
   │ Score: 0.89                            │
   │ Text: "...communicate via message      │
   │        queue..."                       │
   │ Metadata: {                            │
   │   page_id: "ABC123",                   │
   │   page_title: "Architecture Overview", │
   │   has_images: true,                    │
   │   image_count: 2                       │
   │ }                                      │
   └────────────────────────────────────────┘

2. RETRIEVE COMPLETE DOCUMENT
   Because has_images = true:
   ┌────────────────────────────────────────┐
   │ Fetch images for page_id ABC123:      │
   │ - storage/images/ABC123_0.png          │
   │ - storage/images/ABC123_1.png          │
   └────────────────────────────────────────┘

3. RETURN ANSWER
   Answer: "The microservices communicate via message queue..."
   Source: "Architecture Overview" (ABC123)
   Images: [diagram.png, screenshot.png]  ← User can view if needed
```

### Example 2: Image-based Query

```
User Query: "Show me the architecture diagram"

1. SEARCH VECTOR DB
   ┌────────────────────────────────────────┐
   │ Query: "architecture diagram"          │
   └────────────────────────────────────────┘
                    ↓
   ┌────────────────────────────────────────┐
   │ Found: Chunk 1 (page_id: ABC123)      │
   │ Score: 0.92                            │
   │ Text: "...[Image 1]: Diagram showing  │
   │        API Gateway and Auth..."        │
   │ Metadata: {                            │
   │   page_id: "ABC123",                   │
   │   image_paths: ["ABC123_0.png", ...]   │
   │ }                                      │
   └────────────────────────────────────────┘

2. DETECT VISUAL QUERY
   is_visual_query("Show me diagram") = True

3. FETCH ACTUAL IMAGES
   ┌────────────────────────────────────────┐
   │ Download: storage/images/ABC123_0.png  │
   │ (This is the actual diagram)           │
   └────────────────────────────────────────┘

4. ANALYZE WITH GPT-4o VISION
   ┌────────────────────────────────────────┐
   │ Send to GPT-4o:                        │
   │ - Image: ABC123_0.png                  │
   │ - Question: "Show me the architecture  │
   │             diagram"                   │
   │ - Context: (text from chunk)           │
   └────────────────────────────────────────┘
                    ↓
   "The diagram shows an API Gateway that connects to
    an Auth Service and User Service. The services
    communicate with a PostgreSQL database..."

5. RETURN ANSWER WITH IMAGE
   Answer: [Visual description from GPT-4o]
   Image to display: ABC123_0.png
   Source: "Architecture Overview" (ABC123)
```

### Example 3: Metadata-based Query

```
User Query: "Show me important documents from Engineering"

1. SEARCH VECTOR DB
   ┌────────────────────────────────────────┐
   │ Query: "important documents from       │
   │         Engineering"                   │
   └────────────────────────────────────────┘
                    ↓
   ┌────────────────────────────────────────┐
   │ Found: Chunk 1 (page_id: ABC123)      │
   │ Score: 0.88                            │
   │ Text: "Document: Architecture Overview │
   │        Notebook: Engineering           │
   │        Tags: important                 │
   │        ..."                            │
   │ Metadata: {                            │
   │   page_id: "ABC123",                   │
   │   notebook_name: "Engineering",        │
   │   tags: "important,architecture"       │
   │ }                                      │
   └────────────────────────────────────────┘

   ← Metadata was EMBEDDED in the text, so it's searchable!

2. RETURN COMPLETE DOCUMENT
   Title: "Architecture Overview"
   Notebook: Engineering
   Tags: important, architecture
   Content: [Full text]
   Images: [diagram.png, screenshot.png]
```

---

## The Key Insight

### Every chunk is a "pointer" to the complete document:

```python
# When we retrieve a chunk:
chunk = {
    "text": "...content...",
    "metadata": {
        "page_id": "ABC123",      # ← Universal document ID
        "page_title": "Architecture Overview",
        "has_images": true,
        "image_count": 2,
        "notebook_name": "Engineering",
        "tags": "important,architecture"
    }
}

# We can ALWAYS reconstruct the full document:
def get_complete_document(chunk):
    page_id = chunk.metadata["page_id"]

    # 1. Get all chunks from same document
    all_chunks = vector_store.get_by_metadata({"page_id": page_id})
    full_text = combine_chunks(all_chunks)

    # 2. Get all images from same document
    if chunk.metadata["has_images"]:
        images = []
        for i in range(chunk.metadata["image_count"]):
            image_path = f"{page_id}_{i}.png"
            image_data = image_storage.download(image_path)
            images.append(image_data)

    # 3. Return complete document
    return {
        "title": chunk.metadata["page_title"],
        "text": full_text,
        "images": images,
        "metadata": chunk.metadata
    }
```

---

## Why This Works

### 1. Single Point of Truth

- **page_id** is the unique identifier
- Every chunk from the same document has the same page_id
- Every image from the same document is named with page_id
- Everything is linked!

### 2. Unified Search

```python
# We DON'T do this (multiple searches):
text_results = search_text_index(query)
image_results = search_image_index(query)
metadata_results = search_metadata_index(query)
# Then try to merge... ❌ COMPLEX!

# We DO this (single search):
results = vector_store.search(query)  # ✅ SIMPLE!
# Each result has page_id → can get everything
```

### 3. Retrieval Guarantee

If ANY part of a document matches the query (text, metadata, or image description), you get:
- ✅ The full text context
- ✅ All images from that document
- ✅ All metadata
- ✅ Everything stays together

---

## Code Example: Complete Flow

```python
async def query_with_document_integrity(question: str):
    """Query that maintains document integrity."""

    # 1. Search unified index (text + metadata + image descriptions embedded)
    chunks = vector_store.search(question, k=5)

    # 2. Group chunks by document (page_id)
    documents = {}
    for chunk in chunks:
        page_id = chunk.metadata["page_id"]

        if page_id not in documents:
            documents[page_id] = {
                "page_id": page_id,
                "page_title": chunk.metadata["page_title"],
                "chunks": [],
                "images": [],
                "metadata": chunk.metadata
            }

        documents[page_id]["chunks"].append(chunk)

    # 3. For each document, fetch images if needed
    for page_id, doc_data in documents.items():
        if doc_data["metadata"].get("has_images"):
            # Fetch ALL images for this document
            for i in range(doc_data["metadata"]["image_count"]):
                image_path = f"{page_id}_{i}.png"
                image_data = await image_storage.download(image_path)
                doc_data["images"].append(image_data)

    # 4. Build context from complete documents
    context = ""
    for doc_data in documents.values():
        context += f"\n\n=== Document: {doc_data['page_title']} ===\n"

        # Add text from all chunks
        for chunk in doc_data["chunks"]:
            context += chunk.page_content + "\n"

        # Note about images
        if doc_data["images"]:
            context += f"\n(This document has {len(doc_data['images'])} images)\n"

    # 5. Generate answer
    if is_visual_query(question) and any(d["images"] for d in documents.values()):
        # Use GPT-4o Vision with actual images
        all_images = []
        for doc_data in documents.values():
            all_images.extend(doc_data["images"])

        answer = await vision_service.answer_question_about_images(
            question=question,
            images=all_images,
            context=context
        )
    else:
        # Regular text answer
        answer = await llm.generate(context=context, question=question)

    # 6. Return complete response with document integrity
    return {
        "answer": answer,
        "sources": [
            {
                "page_id": doc_data["page_id"],
                "page_title": doc_data["page_title"],
                "text_chunks": len(doc_data["chunks"]),
                "images": [f"{doc_data['page_id']}_{i}.png"
                          for i in range(len(doc_data["images"]))]
            }
            for doc_data in documents.values()
        ]
    }
```

---

## Summary

### The Architecture Maintains Document Integrity Because:

1. **Every chunk has page_id** - Links back to source document
2. **Images are named with page_id** - Easy to find all images for a document
3. **Metadata is embedded** - Searchable but also stored separately
4. **Single search** - One query retrieves all matching document parts
5. **Complete retrieval** - When we find a chunk, we get the whole document

### You Never Get:

- ❌ Text without its images
- ❌ Images without their text
- ❌ Partial documents
- ❌ Orphaned chunks

### You Always Get:

- ✅ Complete documents with all components
- ✅ Full context from the source page
- ✅ All related images
- ✅ Full metadata

**This is exactly what you wanted: treating each document as an integral entity that stays together!**
