# Multimodal Indexing Architecture Discussion
## Text, Metadata, and Images - How to Index and Retrieve

**Date:** January 2025
**Status:** Architecture Design Discussion

---

## Current State Analysis

### What You Currently Do

```python
# Current flow (document_processor.py)
def chunk_document(document: Document):
    # 1. Extract text from HTML
    text = extract_text_from_html(document.content)

    # 2. Create metadata dict
    metadata = {
        "page_id": document.metadata.page_id,
        "page_title": document.metadata.page_title,
        "section_name": document.metadata.section_name,
        "notebook_name": document.metadata.notebook_name,
        "url": document.metadata.url,
        "author": document.metadata.author,
        "tags": ",".join(document.metadata.tags),
        "created_date": document.metadata.created_date.isoformat(),
        "modified_date": document.metadata.modified_date.isoformat()
    }

    # 3. Chunk text
    chunks = text_splitter.create_documents(
        texts=[text],
        metadatas=[metadata]  # Same metadata for all chunks
    )

    # 4. Add to vector store
    vector_store.add_documents(chunks)
    # Only the TEXT is embedded! Metadata is stored but NOT embedded
```

### The Key Insight

**Currently:**
- ✅ Text content is **embedded** (converted to vectors for semantic search)
- ❌ Metadata is **stored** but NOT embedded (only filterable, not searchable semantically)
- ❌ Images are not indexed at all

**This means:**
- ✅ Query "Tell me about the architecture" → finds text chunks with "architecture"
- ❌ Query "Show me documents from the Product notebook" → **cannot** find via semantic search
- ❌ Query "Find pages authored by John" → **cannot** find via semantic search (need filters)

---

## The Three Indexing Strategies

### Strategy 1: Text-Only Indexing (Your Current Approach)

```
Document: "Product Roadmap Q1 2024"
Metadata: {notebook: "Product", section: "Planning", author: "John"}

Indexing:
┌─────────────────────┐
│  Text Chunks        │
├─────────────────────┤
│ "Q1 2024 focuses   │ → Embedded to vector [0.23, -0.45, ...]
│  on new features"  │
├─────────────────────┤
│ "Architecture will │ → Embedded to vector [0.18, 0.32, ...]
│  be redesigned"    │
└─────────────────────┘

Metadata: STORED but NOT embedded (attached to each chunk)
```

**Pros:**
- ✅ Simple
- ✅ Cost-effective (fewer embeddings)
- ✅ Fast indexing

**Cons:**
- ❌ Cannot search by metadata semantically
- ❌ Misses context from metadata
- ❌ User must know exact filters

---

### Strategy 2: Metadata-Enriched Indexing (Recommended)

```
Document: "Product Roadmap Q1 2024"
Metadata: {notebook: "Product", section: "Planning", author: "John", tags: ["important", "q1"]}

Indexing:
┌─────────────────────────────────────────────┐
│  Enriched Text Chunks                       │
├─────────────────────────────────────────────┤
│ CONTEXT: Document "Product Roadmap Q1 2024"│
│ from Product notebook, Planning section.   │
│ Tagged: important, q1. Author: John        │
│                                             │
│ CONTENT: Q1 2024 focuses on new features   │ → Embedded together!
└─────────────────────────────────────────────┘

Metadata: ALSO stored separately for filtering
```

**Implementation:**

```python
def chunk_document_with_metadata_enrichment(document: Document):
    """Enrich text with metadata for better semantic search."""

    text = extract_text_from_html(document.content)
    metadata = document.metadata

    # Create metadata context
    metadata_context = f"""
    Document: "{metadata.page_title}"
    Notebook: {metadata.notebook_name}
    Section: {metadata.section_name}
    Author: {metadata.author or 'Unknown'}
    Tags: {', '.join(metadata.tags) if metadata.tags else 'None'}
    Created: {metadata.created_date.strftime('%B %Y') if metadata.created_date else 'Unknown'}
    """

    # Prepend metadata to text BEFORE chunking
    enriched_text = f"{metadata_context}\n\n{text}"

    # Chunk the enriched text
    chunks = text_splitter.create_documents(
        texts=[enriched_text],
        metadatas=[metadata.dict()]
    )

    return chunks
```

**Pros:**
- ✅ Metadata is now searchable semantically
- ✅ Query "documents from Product team" → finds Product notebook docs
- ✅ Query "John's notes from Q1" → finds via embedded context
- ✅ Better retrieval accuracy (+10-15%)

**Cons:**
- ⚠️ Slightly larger chunks (metadata adds ~100-200 chars)
- ⚠️ Tiny cost increase (same number of chunks, slightly longer)

**This is my recommended approach for text + metadata!**

---

### Strategy 3: Separate Metadata Index (Advanced)

```
Two separate indices:

Index 1: Content Index (text chunks)
┌─────────────────────┐
│ "Q1 2024 focuses   │ → Vector [0.23, -0.45, ...]
│  on new features"  │
└─────────────────────┘

Index 2: Metadata Index (document-level)
┌─────────────────────────────────────┐
│ "Product Roadmap Q1 2024            │ → Vector [0.15, 0.28, ...]
│  Product notebook, Planning section │
│  by John, tags: important, q1"     │
└─────────────────────────────────────┘
```

**Query Strategy:**
1. Search BOTH indices
2. Merge results with RRF (Reciprocal Rank Fusion)

**Pros:**
- ✅ Highest flexibility
- ✅ Can search content vs metadata separately
- ✅ Better for document-level queries

**Cons:**
- ❌ Complex (maintain two indices)
- ❌ Higher cost (more embeddings)
- ❌ Slower queries (search both indices)

**Use this only if you have very metadata-heavy queries!**

---

## Image Indexing Strategies

### Current Situation: No Image Indexing

Right now, images in OneNote pages are **completely invisible** to your RAG system!

### Image Indexing Options

#### Option A: Image Text Extraction Only (Basic)

```
Document with image:
┌────────────────────────────────────┐
│ Text: "See the error below:"       │
│                                    │
│ [IMAGE: Screenshot showing         │
│  "Error 404: User not found"]     │
│                                    │
│ Text: "This needs to be fixed"    │
└────────────────────────────────────┘

Indexing:
1. Extract text from page → "See the error below: This needs to be fixed"
2. OCR image → "Error 404: User not found"
3. Combine all text → "See the error below: Error 404: User not found. This needs to be fixed"
4. Embed combined text

Result: Image text is searchable, but image itself is not!
```

**Implementation:**

```python
async def process_document_with_images(document: Document, images: List[bytes]):
    """Process document with image text extraction."""

    # Extract page text
    page_text = extract_text_from_html(document.content)

    # Extract text from all images
    image_texts = []
    for i, image_data in enumerate(images):
        # Use GPT-4o Vision for OCR
        result = await vision_service.analyze_image(
            image_data,
            task="ocr"
        )
        if result["text"]:
            image_texts.append(f"[Image {i+1} text]: {result['text']}")

    # Combine everything
    full_text = page_text
    if image_texts:
        full_text += "\n\n=== Text from Images ===\n" + "\n\n".join(image_texts)

    # Chunk and embed
    chunks = text_splitter.create_documents([full_text], [metadata])

    return chunks
```

**Pros:**
- ✅ Simple - reuses existing text indexing
- ✅ Makes image text searchable
- ✅ Query "error 404" → finds documents with that error in images

**Cons:**
- ❌ Cannot search by visual content
- ❌ Cannot answer "what does the diagram look like?"
- ❌ Loses spatial/visual information

---

#### Option B: Separate Image Index with Visual Embeddings (Advanced)

```
Two indices:

Index 1: Text Index (as before)
┌─────────────────────┐
│ Text chunks         │ → Text embeddings
└─────────────────────┘

Index 2: Image Index (separate)
┌─────────────────────────────────────────┐
│ Image ID: img_123                       │
│ Description: "Architecture diagram"     │ → CLIP embedding
│ OCR Text: "API Gateway → Backend"       │
│ Document: "System Design"               │
└─────────────────────────────────────────┘
```

**Implementation:**

```python
# Two separate vector collections

class MultimodalVectorStore:
    def __init__(self):
        # Text embeddings (OpenAI)
        self.text_collection = Chroma(
            collection_name="text_chunks",
            embedding_function=OpenAIEmbeddings()
        )

        # Image embeddings (CLIP)
        self.image_collection = Chroma(
            collection_name="images",
            embedding_function=CLIPEmbeddings()  # Custom CLIP wrapper
        )

    async def add_document_with_images(
        self,
        document: Document,
        images: List[Dict]  # {image_data, description, ocr_text}
    ):
        # 1. Index text chunks (existing flow)
        text_chunks = process_text(document)
        self.text_collection.add_documents(text_chunks)

        # 2. Index images separately
        for img in images:
            # Generate CLIP embedding for image
            image_embedding = await clip_service.embed_image(img["image_data"])

            # Store with metadata
            self.image_collection.add(
                embeddings=[image_embedding],
                metadatas=[{
                    "image_id": img["id"],
                    "document_id": document.id,
                    "description": img["description"],
                    "ocr_text": img["ocr_text"],
                    "url": img["storage_url"]
                }],
                ids=[img["id"]]
            )
```

**Query Strategy:**

```python
async def query_multimodal(question: str, include_images: bool = True):
    # 1. Search text index (always)
    text_results = text_collection.search(question, k=10)

    # 2. If visual query, also search images
    if include_images and is_visual_query(question):
        # Search images with CLIP text encoder
        image_results = image_collection.search(question, k=5)

        # Merge results
        combined = merge_text_and_image_results(text_results, image_results)
    else:
        combined = text_results

    return combined
```

**Pros:**
- ✅ Can search by visual similarity
- ✅ Query "architecture diagram" → finds diagrams even without text
- ✅ Can use images as query input
- ✅ Better for visual content

**Cons:**
- ❌ Complex (two indices, two embedding models)
- ❌ Higher cost (CLIP embeddings)
- ❌ Need to merge results from both indices

---

#### Option C: Unified Multimodal Index with GPT-4o Vision (Recommended!)

```
Single index with multimodal chunks:

┌──────────────────────────────────────────────────┐
│ Chunk Type: Text + Image Context                 │
│                                                   │
│ CONTENT:                                         │
│ "See the error below: This needs to be fixed"   │
│                                                   │
│ IMAGE CONTEXT:                                   │
│ [Image 1]: Screenshot of error dialog           │
│ Description: "Web interface showing Error 404:  │
│  User not found message with red border"        │
│ Text in image: "Error 404: User not found"      │
│                                                   │
│ → Embedded together as ONE chunk                 │
└──────────────────────────────────────────────────┘

All embedded with text embeddings (OpenAI)
```

**Implementation:**

```python
async def process_document_with_gpt4o_vision(
    document: Document,
    images: List[bytes]
):
    """Unified indexing with GPT-4o Vision analysis."""

    page_text = extract_text_from_html(document.content)

    # Analyze all images with GPT-4o Vision
    image_contexts = []
    for i, image_data in enumerate(images):
        analysis = await vision_service.analyze_image(
            image_data,
            task="comprehensive"
        )

        # Build rich context
        context = f"""
        [Image {i+1}]: {analysis['description']}
        Text in image: {analysis['text_content']}
        Key elements: {', '.join(analysis['key_elements'])}
        """
        image_contexts.append(context)

        # Store image separately for retrieval
        await storage.upload(f"images/{document.id}_{i}.png", image_data)

    # Combine text + image contexts
    full_content = page_text
    if image_contexts:
        full_content += "\n\n=== Images ===\n" + "\n".join(image_contexts)

    # Chunk and embed (single embedding model - OpenAI)
    chunks = text_splitter.create_documents(
        texts=[full_content],
        metadatas=[{
            **document.metadata.dict(),
            "has_images": len(images) > 0,
            "image_count": len(images)
        }]
    )

    return chunks
```

**Query Flow:**

```python
async def query_with_images(question: str):
    # 1. Regular retrieval (text + image context embedded together)
    documents = vector_store.search(question, k=5)

    # 2. If visual question, fetch actual images
    if is_visual_query(question):
        images_to_show = []
        for doc in documents:
            if doc.metadata.get("has_images"):
                # Fetch images from storage
                imgs = await fetch_images_for_document(doc.metadata["page_id"])
                images_to_show.extend(imgs)

    # 3. Generate answer with image context
    answer = await llm.generate(
        context=documents,
        question=question,
        images=images_to_show  # Available for reference
    )

    return {
        "answer": answer,
        "sources": documents,
        "images": images_to_show
    }
```

**Pros:**
- ✅ **Single index** (simpler architecture)
- ✅ **Single embedding model** (OpenAI - cost-effective)
- ✅ **Image context is searchable** via text embeddings
- ✅ **GPT-4o Vision provides rich descriptions** (better than OCR alone)
- ✅ **Images linked to text** (maintains document structure)
- ✅ Can still show actual images when relevant

**Cons:**
- ⚠️ Cannot search by pure visual similarity (no CLIP)
- ⚠️ Need to fetch images separately for display

**This is my recommended approach!** Simple, effective, uses GPT-4o Vision.

---

## Comparison Table

| Strategy | Complexity | Cost | Semantic Search | Visual Search | Maintenance |
|----------|-----------|------|----------------|---------------|-------------|
| **Text-Only** (current) | Low | $ | Text only | ❌ No | Easy |
| **Text + Metadata Enrichment** | Low | $ | Text + Metadata | ❌ No | Easy |
| **Separate Metadata Index** | Medium | $$ | Text + Metadata | ❌ No | Medium |
| **Image Text Extraction** | Low | $ | Text + Image Text | ❌ No | Easy |
| **Separate Image Index (CLIP)** | High | $$$ | Text | ✅ Yes | Hard |
| **Unified with GPT-4o Vision** | Medium | $$ | Text + Image Context | ⚠️ Partial | Medium |

---

## My Recommendations

### Phase 1: Immediate (This Week)
**Implement Metadata Enrichment**

```python
def chunk_document_v2(document: Document):
    # Add metadata context to chunks
    metadata_header = f"""
    Document: {document.metadata.page_title}
    From: {document.metadata.notebook_name} / {document.metadata.section_name}
    Tags: {', '.join(document.metadata.tags)}
    """

    enriched_text = metadata_header + "\n\n" + document.content
    chunks = text_splitter.create_documents([enriched_text], [metadata.dict()])

    return chunks
```

**Impact:**
- ✅ +10-15% retrieval accuracy
- ✅ Metadata becomes semantically searchable
- ✅ Zero architecture changes
- ✅ Minimal cost increase

---

### Phase 2: Next Sprint (2-3 weeks)
**Implement GPT-4o Vision for Images**

```python
async def process_multimodal_document(document: Document, images: List[bytes]):
    # 1. Process text
    page_text = extract_text_from_html(document.content)

    # 2. Analyze images with GPT-4o Vision
    image_analyses = []
    for img in images:
        analysis = await gpt4o_vision.analyze_image(img, task="comprehensive")
        image_analyses.append({
            "description": analysis["description"],
            "text": analysis["text_content"],
            "elements": analysis["key_elements"]
        })

    # 3. Combine into enriched document
    full_content = build_multimodal_content(page_text, image_analyses, document.metadata)

    # 4. Chunk and index (single vector store)
    chunks = text_splitter.create_documents([full_content], [metadata])

    return chunks
```

**Impact:**
- ✅ Images become searchable
- ✅ Can answer visual questions
- ✅ Single index (simple)
- ✅ Uses existing OpenAI embeddings

---

### Phase 3: Future (If Needed)
**Add CLIP for Pure Visual Similarity**

Only implement if you need:
- Image-to-image search ("find similar diagrams")
- Visual clustering
- Image recommendations

**Most users won't need this!**

---

## Do Current RAG Techniques Handle This?

### Current Techniques (from UPCOMING_FEATURES.md)

**Already implemented:**
- ✅ Multi-Query Retrieval
- ✅ RAG-Fusion
- ✅ Query Decomposition
- ✅ Step-Back Prompting
- ✅ HyDE
- ⚠️ Re-ranking (needs upgrade)

**These work fine with multimodal indexing!**

### What Changes Needed?

#### 1. Document Processing Pipeline
**Current:**
```python
Document → Extract Text → Chunk → Embed → Store
```

**New (Multimodal):**
```python
Document → Extract Text → Analyze Images (GPT-4o) →
Enrich with Metadata → Combine → Chunk → Embed → Store
```

#### 2. Retrieval Strategy
**Current:**
```python
Query → Embed Query → Search Vectors → Return Chunks
```

**New (Multimodal):**
```python
Query → Detect if Visual Query →
  If visual: Search + Fetch Images
  If not: Regular search
→ Return Chunks + Images
```

#### 3. Answer Generation
**Current:**
```python
Context Chunks → LLM → Answer
```

**New (Multimodal):**
```python
Context Chunks + Image Contexts → LLM → Answer
(LLM sees image descriptions, not actual images)

Optional: For visual questions, can use GPT-4o Vision directly
```

---

## Implementation Flow

### Complete Multimodal Flow

```python
# 1. INDEXING PHASE

async def index_onenote_page(page_data: Dict):
    """Index a OneNote page with text, metadata, and images."""

    # Extract components
    page_text = extract_text_from_html(page_data["content"])
    images = extract_images_from_page(page_data)
    metadata = extract_metadata(page_data)

    # Enrich with metadata
    metadata_context = f"""
    Document: {metadata.title}
    Notebook: {metadata.notebook_name}
    Section: {metadata.section_name}
    Tags: {', '.join(metadata.tags)}
    Author: {metadata.author}
    """

    # Analyze images with GPT-4o Vision
    image_contexts = []
    for i, img_data in enumerate(images):
        analysis = await vision_service.analyze_image(img_data, task="comprehensive")

        # Store image in object storage
        img_url = await storage.upload(f"images/{metadata.page_id}_{i}.png", img_data)

        # Build context
        image_context = f"""
        [Image {i+1}]
        Description: {analysis['description']}
        Text found: {analysis['text_content']}
        Key elements: {', '.join(analysis['key_elements'])}
        Storage URL: {img_url}
        """
        image_contexts.append(image_context)

    # Combine all content
    full_content = f"""
{metadata_context}

=== Page Content ===
{page_text}
"""

    if image_contexts:
        full_content += f"""

=== Images ===
{chr(10).join(image_contexts)}
"""

    # Create document
    document = Document(
        page_content=full_content,
        metadata={
            **metadata.dict(),
            "has_images": len(images) > 0,
            "image_count": len(images),
            "content_length": len(page_text),
            "image_urls": [f"images/{metadata.page_id}_{i}.png" for i in range(len(images))]
        }
    )

    # Chunk and embed
    chunks = text_splitter.create_documents(
        texts=[document.page_content],
        metadatas=[document.metadata]
    )

    # Add to vector store (single embedding call per chunk)
    vector_store.add_documents(chunks)

    return {"status": "success", "chunks": len(chunks), "images": len(images)}


# 2. QUERY PHASE

async def query_multimodal(question: str, config: RAGConfig):
    """Query with multimodal understanding."""

    # Detect query type
    is_visual = is_visual_query(question)  # Check for "image", "diagram", "screenshot", etc.

    # 1. Retrieve relevant chunks (includes image contexts)
    documents = await rag_engine.retrieve_documents(question, config)

    # 2. If visual query, fetch actual images
    images_to_include = []
    if is_visual and config.include_images:
        for doc in documents[:3]:  # Top 3 docs
            if doc.metadata.get("has_images"):
                # Fetch images from storage
                image_urls = doc.metadata.get("image_urls", [])
                for url in image_urls[:2]:  # Max 2 images per doc
                    image_data = await storage.download(url)
                    images_to_include.append({
                        "url": url,
                        "document": doc.metadata["page_title"]
                    })

    # 3. Build context for LLM
    context = build_context_from_documents(documents)

    # 4. Generate answer
    # Option A: Text-only (fast, cheap)
    if not is_visual:
        answer = await llm.generate(context=context, question=question)

    # Option B: With images (better for visual questions)
    else:
        # Use GPT-4o Vision to analyze images in context
        answer = await generate_answer_with_images(
            context=context,
            question=question,
            images=images_to_include
        )

    return {
        "answer": answer,
        "sources": documents,
        "images": images_to_include if is_visual else []
    }


# 3. HELPER FUNCTIONS

def is_visual_query(question: str) -> bool:
    """Detect if query is about visual content."""
    visual_keywords = [
        "image", "picture", "screenshot", "diagram", "chart", "graph",
        "look like", "show me", "visual", "illustration", "photo"
    ]
    return any(keyword in question.lower() for keyword in visual_keywords)

async def generate_answer_with_images(
    context: str,
    question: str,
    images: List[Dict]
) -> str:
    """Generate answer using GPT-4o Vision for visual questions."""

    # Fetch actual image data
    image_data_list = []
    for img in images:
        data = await storage.download(img["url"])
        image_data_list.append(data)

    # Use GPT-4o Vision to answer question about images
    vision_answer = await vision_service.answer_question_about_images(
        question=question,
        images=image_data_list,
        context=context
    )

    return vision_answer
```

---

## Answer to Your Questions

### Q1: Do you currently embed and index document metadata?

**Answer:** ❌ **No, you don't.**

Currently, metadata is **stored** alongside chunks but **NOT embedded**. This means:
- Metadata is only filterable (exact match)
- Metadata is NOT semantically searchable
- Query "documents from Product team" won't find Product notebook docs via semantic search

**Solution:** Use metadata enrichment (prepend metadata to text before embedding)

---

### Q2: How would you embed and index images?

**Answer:** **Three options:**

1. **Basic:** Extract text from images (OCR), append to document text, embed as text
2. **Advanced:** Separate image index with CLIP embeddings (complex, expensive)
3. **Recommended:** Use GPT-4o Vision to generate rich descriptions, embed descriptions as text (simple, effective)

**Recommendation:** Start with Option 3 (GPT-4o Vision).

---

### Q3: How to handle documents with images + text + metadata?

**Answer:** **Unified multimodal chunks** (recommended):

```
Single chunk contains:
┌─────────────────────────────────────────┐
│ Metadata context (notebook, section)   │
│ Text content                            │
│ Image descriptions (from GPT-4o Vision) │
│ Image OCR text                          │
└─────────────────────────────────────────┘
  ↓
Single embedding (OpenAI)
  ↓
Single vector store
```

This is **simple**, **effective**, and **maintains document coherence**.

---

### Q4: Can current RAG techniques handle this?

**Answer:** ✅ **Yes, with minor modifications!**

Current techniques work fine:
- Multi-Query: Works on enriched text
- RAG-Fusion: Works on enriched text
- Re-ranking: Can re-rank multimodal chunks
- HyDE: Generates hypothetical docs with metadata

**Only change needed:** Document processing pipeline (add GPT-4o Vision analysis)

**Query flow stays mostly the same!**

---

## Summary & Action Plan

### Recommended Architecture

```
1. Indexing:
   Text + Metadata + Image Analysis → Single Enriched Document → Chunk → Embed (OpenAI) → Single Vector Store

2. Storage:
   - Vectors: Qdrant/Weaviate (with hybrid search)
   - Images: MinIO/S3 (actual image files)
   - Metadata: PostgreSQL (for filtering, analytics)

3. Query:
   Query → Retrieve enriched chunks → If visual query: Fetch images → Generate answer

4. Answer Generation:
   - Text questions: Use LLM with text context
   - Visual questions: Use GPT-4o Vision with images + context
```

### Implementation Priority

**Week 1:** Metadata enrichment (2 days)
**Week 2-3:** GPT-4o Vision integration (1 week)
**Week 4:** Testing and optimization (3 days)

### Cost Impact

**Indexing 1,000 documents with 5,000 images:**
- Current: $10 (text only)
- With metadata enrichment: $10.50 (+5%)
- With GPT-4o-mini for images: $18 (+80%, but 100x more capable!)

**Worth it!**

---

Want me to create detailed implementation code for any of these strategies?
