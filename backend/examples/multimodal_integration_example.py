"""
Example script demonstrating multimodal RAG integration.

This script shows how to:
1. Initialize multimodal services
2. Index documents with images
3. Query with multimodal support
4. Retrieve images from responses

Prerequisites:
- OpenAI API key set in environment
- OneNote documents with images
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.onenote_service import OneNoteService
from services.document_processor import DocumentProcessor
from services.vector_store import VectorStoreService
from services.vision_service import GPT4VisionService
from services.image_storage import ImageStorageService
from services.multimodal_processor import MultimodalDocumentProcessor
from services.multimodal_query import MultimodalQueryHandler
from services.rag_engine import RAGEngine


async def main():
    """Main example function."""

    print("=" * 80)
    print("MULTIMODAL RAG INTEGRATION EXAMPLE")
    print("=" * 80)

    # Step 1: Initialize services
    print("\n[1/5] Initializing services...")

    # Get API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return

    # Initialize vision service
    vision_service = GPT4VisionService(
        api_key=openai_key,
        default_model="gpt-4o-mini",  # Cost-efficient for indexing
        max_tokens=1000,
        temperature=0.0
    )
    print("  ✓ Vision service initialized")

    # Initialize image storage
    image_storage = ImageStorageService(
        storage_type="local",
        base_path="backend/storage/images"
    )
    print("  ✓ Image storage initialized")

    # Initialize multimodal processor
    multimodal_processor = MultimodalDocumentProcessor(
        vision_service=vision_service,
        chunk_size=1000,
        chunk_overlap=200,
        max_images_per_document=10,
        access_token=os.getenv("MICROSOFT_GRAPH_TOKEN")  # If available
    )
    print("  ✓ Multimodal document processor initialized")

    # Initialize multimodal query handler
    multimodal_handler = MultimodalQueryHandler(
        vision_service=vision_service,
        image_storage=image_storage
    )
    print("  ✓ Multimodal query handler initialized")

    # Initialize vector store
    vector_store = VectorStoreService(
        persist_directory="./data/chroma_multimodal",
        embedding_provider="openai"
    )
    print("  ✓ Vector store initialized")

    # Initialize RAG engine with multimodal support
    rag_engine = RAGEngine(
        vector_store=vector_store,
        multimodal_handler=multimodal_handler
    )
    print("  ✓ RAG engine initialized with multimodal support")

    # Step 2: Index a sample document with images (if you have OneNote setup)
    print("\n[2/5] Document indexing example...")
    print("  NOTE: Skipping actual OneNote indexing in this example")
    print("  To index real documents:")
    print("    1. Initialize OneNoteService")
    print("    2. Fetch documents with get_all_documents()")
    print("    3. Process with multimodal_processor.chunk_document_multimodal()")
    print("    4. Store images with image_storage.upload()")
    print("    5. Add chunks to vector_store.add_documents()")

    # Example pseudo-code for indexing:
    print("\n  Example code for multimodal indexing:")
    print("  ```python")
    print("  # Get OneNote documents")
    print("  onenote = OneNoteService(...)")
    print("  documents = onenote.get_all_documents()")
    print("")
    print("  # Process each document")
    print("  for doc in documents:")
    print("      # Chunk with multimodal support (text + images)")
    print("      chunks, image_data_list = await multimodal_processor.chunk_document_multimodal(")
    print("          document=doc,")
    print("          enrich_with_metadata=True,")
    print("          include_images=True")
    print("      )")
    print("")
    print("      # Store images using page_id naming")
    print("      for img_data in image_data_list:")
    print("          image_path = image_storage.generate_image_path(")
    print("              page_id=img_data['page_id'],")
    print("              image_index=img_data['position']")
    print("          )")
    print("          await image_storage.upload(image_path, img_data['data'])")
    print("")
    print("      # Add chunks to vector store")
    print("      vector_store.add_documents(chunks)")
    print("  ```")

    # Step 3: Demonstrate visual query detection
    print("\n[3/5] Visual query detection...")

    test_queries = [
        ("What is the project timeline?", False),  # Not visual
        ("Show me the architecture diagram", True),  # Visual
        ("What images are in the documentation?", True),  # Visual
        ("Explain the API endpoints", False),  # Not visual
    ]

    for query, expected_visual in test_queries:
        is_visual = multimodal_handler.is_visual_query(query)
        status = "✓" if is_visual == expected_visual else "✗"
        print(f"  {status} '{query}' → {'VISUAL' if is_visual else 'TEXT'}")

    # Step 4: Query example (text-only since we don't have actual data indexed)
    print("\n[4/5] Query example...")
    print("  NOTE: Using synchronous query (text-only)")
    print("  For multimodal queries, use: await rag_engine.query_async()")

    try:
        response = rag_engine.query(
            question="What is multimodal RAG?",
            config=None  # Use default
        )
        print(f"  ✓ Query completed in {response.metadata.latency_ms}ms")
        print(f"  ✓ Retrieved {len(response.sources)} sources")
        print(f"  ✓ Used techniques: {', '.join(response.metadata.techniques_used)}")

        if response.images:
            print(f"  ✓ Response includes {len(response.images)} images")
        else:
            print("  ℹ No images in response (expected for text query)")

    except Exception as e:
        print(f"  ℹ Query failed (expected if no documents indexed): {str(e)}")

    # Step 5: Demonstrate document integrity via page_id
    print("\n[5/5] Document integrity demonstration...")
    print("  Document integrity is maintained through page_id:")
    print("")
    print("  1. When indexing:")
    print("     - All chunks from a document get the same page_id in metadata")
    print("     - Images are named: {page_id}_{index}.png")
    print("     - Both stored in separate systems but linked by page_id")
    print("")
    print("  2. When querying:")
    print("     - Vector search retrieves text chunks")
    print("     - page_id in chunk metadata links to original document")
    print("     - Use page_id to fetch all images: image_storage.generate_image_path(page_id, i)")
    print("     - Can reconstruct complete document: all chunks + all images")
    print("")
    print("  3. Example:")
    print("     - Document ABC123 has 3 chunks and 2 images")
    print("     - Chunks stored with metadata: {page_id: 'ABC123', chunk_index: 0/1/2}")
    print("     - Images stored as: ABC12345/ABC123_0.png, ABC12345/ABC123_1.png")
    print("     - Query retrieves chunk 1 → page_id='ABC123'")
    print("     - Fetch ALL chunks with page_id='ABC123'")
    print("     - Fetch ALL images: ABC123_*.png")
    print("     - Result: Complete document reconstructed!")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. Multimodal RAG combines text + metadata + images in unified chunks")
    print("2. page_id is the magic key linking all components")
    print("3. Visual queries are auto-detected and enhanced with images")
    print("4. Document integrity maintained - can always reconstruct full documents")
    print("5. Cost-efficient: GPT-4o-mini for indexing, GPT-4o for important queries")
    print("\nNext Steps:")
    print("- Set up OneNote connection")
    print("- Index documents with images")
    print("- Try visual queries like 'Show me the diagrams'")
    print("- Access images via API: GET /api/images/{page_id}/{image_index}")
    print("- Use multimodal query endpoint: POST /api/query/multimodal")


if __name__ == "__main__":
    asyncio.run(main())
