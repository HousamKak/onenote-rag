"""
API routes for the OneNote RAG application.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
 
from models import (
    QueryRequest,
    QueryResponse,
    CompareRequest,
    CompareResponse,
    RAGConfig,
)
from models.rag_config import PRESET_CONFIGS, AVAILABLE_MODELS
from models.settings import SettingCreate, SettingUpdate, SettingResponse
from services import (
    OneNoteService,
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
from services.settings_service import SettingsService
from config import get_settings
 
logger = logging.getLogger(__name__)
 
router = APIRouter()
 
# Global services (will be initialized in main.py)
onenote_service: Optional[OneNoteService] = None
document_processor: Optional[DocumentProcessor] = None
vector_store: Optional[VectorStoreService] = None
rag_engine: Optional[RAGEngine] = None
settings_service: Optional[SettingsService] = None

# Multimodal services (optional - initialized if OpenAI key available)
multimodal_processor: Optional[Any] = None  # MultimodalDocumentProcessor
vision_service: Optional[Any] = None  # GPT4VisionService
image_storage: Optional[Any] = None  # ImageStorageService

# Startup sync status
sync_status: Dict[str, Any] = {
    "in_progress": False,
    "status": "not_started",
    "message": "Sync has not started yet",
    "documents_processed": 0
}
 
 
def get_rag_engine() -> RAGEngine:
    """Dependency to get RAG engine."""
    if rag_engine is None:
        raise HTTPException(status_code=500, detail="RAG engine not initialized")
    return rag_engine
 
 
def get_onenote_service() -> OneNoteService:
    """Dependency to get OneNote service."""
    if onenote_service is None:
        raise HTTPException(status_code=500, detail="OneNote service not initialized")
    return onenote_service
 
 
def get_vector_store() -> VectorStoreService:
    """Dependency to get vector store."""
    if vector_store is None:
        raise HTTPException(status_code=500, detail="Vector store not initialized")
    return vector_store
 
 
def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor."""
    if document_processor is None:
        raise HTTPException(status_code=500, detail="Document processor not initialized")
    return document_processor


def get_settings_service() -> SettingsService:
    """Dependency to get settings service."""
    if settings_service is None:
        raise HTTPException(status_code=500, detail="Settings service not initialized")
    return settings_service


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/sync-status")
async def get_sync_status():
    """Get the status of the background startup sync."""
    return sync_status


# Settings routes
@router.get("/settings", response_model=List[SettingResponse])
async def get_all_settings(
    service: SettingsService = Depends(get_settings_service)
) -> List[SettingResponse]:
    """Get all settings (sensitive values are masked)."""
    try:
        settings = service.get_all_settings(mask_sensitive=True)
        return [SettingResponse(**s) for s in settings]
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    service: SettingsService = Depends(get_settings_service)
) -> SettingResponse:
    """Get a specific setting (sensitive values are masked)."""
    try:
        value = service.get_setting(key, decrypt=False)
        setting_info = service.db.get_setting(key)
        
        if not setting_info:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        from services.settings_service import SENSITIVE_KEYS
        is_sensitive = key in SENSITIVE_KEYS
        has_value = bool(value)
        masked_value = "********" if (is_sensitive and has_value) else (value or "")
        
        return SettingResponse(
            key=key,
            value=masked_value,
            is_sensitive=is_sensitive,
            description=setting_info.get("description"),
            has_value=has_value
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting setting {key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    service: SettingsService = Depends(get_settings_service)
) -> Dict[str, Any]:
    """Update a setting value."""
    try:
        service.set_setting(key=key, value=update.value)
        return {
            "status": "success",
            "message": f"Setting '{key}' updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating setting {key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def create_setting(
    setting: SettingCreate,
    service: SettingsService = Depends(get_settings_service)
) -> Dict[str, Any]:
    """Create a new setting."""
    try:
        service.set_setting(
            key=setting.key,
            value=setting.value,
            description=setting.description
        )
        return {
            "status": "success",
            "message": f"Setting '{setting.key}' created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating setting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/settings/{key}")
async def delete_setting(
    key: str,
    service: SettingsService = Depends(get_settings_service)
) -> Dict[str, Any]:
    """Delete a setting."""
    try:
        deleted = service.delete_setting(key)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        
        return {
            "status": "success",
            "message": f"Setting '{key}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/test-connection")
async def test_api_connection(
    service: SettingsService = Depends(get_settings_service)
) -> Dict[str, Any]:
    """Test if API keys are valid by making a simple API call."""
    try:
        import httpx
        from langchain_openai import ChatOpenAI
        
        openai_key = service.get_setting("openai_api_key")
        if not openai_key:
            return {
                "status": "error",
                "service": "openai",
                "message": "OpenAI API key not configured"
            }
        
        # Test OpenAI connection
        http_client = httpx.Client(verify=False)
        llm = ChatOpenAI(
            api_key=openai_key,
            model_name="gpt-3.5-turbo",
            http_client=http_client
        )
        
        # Try a simple completion
        response = llm.invoke("Say 'OK' if you can read this.")
        
        return {
            "status": "success",
            "service": "openai",
            "message": "Connection successful"
        }
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        return {
            "status": "error",
            "service": "openai",
            "message": str(e)
        } 
# Configuration routes
@router.get("/config/presets")
async def get_presets() -> Dict[str, RAGConfig]:
    """Get all preset configurations."""
    return PRESET_CONFIGS
 
 
@router.get("/config/presets/{preset_name}")
async def get_preset(preset_name: str) -> RAGConfig:
    """Get a specific preset configuration."""
    if preset_name not in PRESET_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    return PRESET_CONFIGS[preset_name]
 
 
@router.get("/config/default")
async def get_default_config() -> RAGConfig:
    """Get the default configuration."""
    return RAGConfig()
 
 
@router.get("/config/models")
async def get_available_models() -> List[str]:
    """Get list of available LLM models."""
    return AVAILABLE_MODELS
 
 
@router.post("/config/validate")
async def validate_config(config: RAGConfig) -> Dict[str, Any]:
    """Validate a configuration."""
    return {
        "valid": True,
        "config": config,
        "warnings": []
    }
 
 
# OneNote routes
class NotebookListResponse(BaseModel):
    notebooks: List[Dict[str, Any]]
 
 
@router.get("/onenote/notebooks", response_model=NotebookListResponse)
async def list_notebooks(
    service: OneNoteService = Depends(get_onenote_service)
):
    """List all OneNote notebooks."""
    try:
        notebooks = service.list_notebooks()
        return {"notebooks": notebooks}
    except Exception as e:
        logger.error(f"Error listing notebooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
class SectionListResponse(BaseModel):
    sections: List[Dict[str, Any]]
 
 
@router.get("/onenote/sections/{notebook_id}", response_model=SectionListResponse)
async def list_sections(
    notebook_id: str,
    service: OneNoteService = Depends(get_onenote_service)
):
    """List all sections in a notebook."""
    try:
        sections = service.list_sections(notebook_id)
        return {"sections": sections}
    except Exception as e:
        logger.error(f"Error listing sections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
class PageListResponse(BaseModel):
    pages: List[Dict[str, Any]]
 
 
@router.get("/onenote/pages/{section_id}", response_model=PageListResponse)
async def list_pages(
    section_id: str,
    service: OneNoteService = Depends(get_onenote_service)
):
    """List all pages in a section."""
    try:
        pages = service.list_pages(section_id)
        return {"pages": pages}
    except Exception as e:
        logger.error(f"Error listing pages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
# Indexing routes
class SyncRequest(BaseModel):
    notebook_ids: Optional[List[str]] = None
    full_sync: bool = False  # Changed default to False for incremental sync
    force_reindex: bool = False  # Force reindexing even if not modified
    multimodal: bool = True  # Enable multimodal processing (images) if available
 
 
class SyncResponse(BaseModel):
    status: str
    documents_processed: int
    documents_added: int
    documents_updated: int
    documents_skipped: int
    chunks_created: int
    message: str
 
 
@router.post("/index/sync", response_model=SyncResponse)
async def sync_documents(
    request: SyncRequest,
    onenote: OneNoteService = Depends(get_onenote_service),
    processor: DocumentProcessor = Depends(get_document_processor),
    store: VectorStoreService = Depends(get_vector_store)
):
    """
    Sync OneNote documents to vector database with optional multimodal support.

    Supports four modes:
    - Incremental sync (default): Only updates modified/new documents
    - Full sync: Clears DB and reindexes everything
    - Force reindex: Reindexes all documents without checking modification dates
    - Multimodal (default if available): Processes images along with text

    Multimodal processing:
    - If multimodal=True and services available: Uses MultimodalDocumentProcessor
    - If multimodal=False or services unavailable: Uses standard DocumentProcessor (text-only)
    - Images are analyzed with GPT-4o Vision and stored separately
    - All components linked by page_id for document integrity
    """
    try:
        # Check if multimodal processing is requested and available
        use_multimodal = request.multimodal and multimodal_processor is not None

        if request.multimodal and multimodal_processor is None:
            logger.warning("Multimodal processing requested but not available - falling back to text-only")

        if use_multimodal:
            logger.info("Using MULTIMODAL processing (text + images)")
        else:
            logger.info("Using TEXT-ONLY processing")
        # Get documents from OneNote
        logger.info(f"Fetching documents from OneNote (notebooks: {request.notebook_ids})")
        documents = onenote.get_all_documents(request.notebook_ids)
 
        if not documents:
            return SyncResponse(
                status="success",
                documents_processed=0,
                documents_added=0,
                documents_updated=0,
                documents_skipped=0,
                chunks_created=0,
                message="No documents found to sync"
            )
 
        # Clear existing data if full sync
        if request.full_sync:
            logger.info("Performing full sync - clearing existing data")
            store.clear_collection()
 
        # Process documents based on sync mode
        documents_added = 0
        documents_updated = 0
        documents_skipped = 0
        total_chunks = 0
 
        for doc in documents:
            page_id = doc.metadata.page_id
            modified_date = doc.metadata.modified_date
           
            # Check if document needs updating (incremental sync)
            if not request.full_sync and not request.force_reindex:
                existing_modified = store.get_page_modified_date(page_id)
               
                if existing_modified and modified_date:
                    # CRITICAL FIX: Convert both to ISO format for proper comparison
                    # The stored date is already in ISO format from .isoformat()
                    existing_dt_str = existing_modified  # Already a string in ISO format
                    
                    # Convert the datetime object to ISO format for comparison
                    new_dt_str = modified_date.isoformat()
                    
                    # Compare the ISO formatted strings
                    if existing_dt_str == new_dt_str:
                        logger.debug(f"Skipping unchanged page: {doc.metadata.page_title} (modified: {existing_dt_str})")
                        documents_skipped += 1
                        continue
                    else:
                        logger.info(f"Page modified: {doc.metadata.page_title}")
                        logger.debug(f"  Existing: {existing_dt_str}")
                        logger.debug(f"  New:      {new_dt_str}")
               
                # Document is new or modified - delete old version and add new
                if existing_modified:
                    logger.info(f"Updating modified page: {doc.metadata.page_title}")
                    store.delete_by_page_id(page_id)
                    documents_updated += 1
                else:
                    logger.info(f"Adding new page: {doc.metadata.page_title}")
                    documents_added += 1
            else:
                # Full sync or force reindex - just count as added
                documents_added += 1
 
            # Process and chunk the document (multimodal or text-only)
            if use_multimodal:
                # Multimodal processing: text + metadata + images
                chunks, image_data_list = await multimodal_processor.chunk_document_multimodal(
                    document=doc,
                    enrich_with_metadata=True,
                    include_images=True
                )

                # Store images in image storage
                if image_data_list and image_storage:
                    for img_data in image_data_list:
                        try:
                            image_path = image_storage.generate_image_path(
                                page_id=img_data["page_id"],
                                image_index=img_data["position"]
                            )
                            await image_storage.upload(
                                image_path=image_path,
                                image_data=img_data["data"],
                                content_type="image/png",
                                metadata={
                                    "page_id": img_data["page_id"],
                                    "position": img_data["position"],
                                    "url": img_data.get("url", "")
                                }
                            )
                            logger.debug(f"Stored image {img_data['position']} for page {page_id}")
                        except Exception as e:
                            logger.error(f"Error storing image: {str(e)}")

                    logger.info(f"Stored {len(image_data_list)} images for document {page_id}")
            else:
                # Text-only processing (original behavior)
                chunks = processor.chunk_documents([doc])

            # Add chunks to vector store
            store.add_documents(chunks)
            total_chunks += len(chunks)
 
        message_parts = []
        if documents_added > 0:
            message_parts.append(f"{documents_added} added")
        if documents_updated > 0:
            message_parts.append(f"{documents_updated} updated")
        if documents_skipped > 0:
            message_parts.append(f"{documents_skipped} skipped")
       
        message = f"Successfully synced: {', '.join(message_parts)} ({total_chunks} chunks)"
 
        return SyncResponse(
            status="success",
            documents_processed=len(documents),
            documents_added=documents_added,
            documents_updated=documents_updated,
            documents_skipped=documents_skipped,
            chunks_created=total_chunks,
            message=message
        )
 
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
class IndexStats(BaseModel):
    total_documents: int
    collection_name: str
    persist_directory: str
 
 
@router.get("/index/stats", response_model=IndexStats)
async def get_index_stats(
    store: VectorStoreService = Depends(get_vector_store)
):
    """Get vector database statistics."""
    try:
        stats = store.get_stats()
        return IndexStats(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.delete("/index/clear")
async def clear_index(
    store: VectorStoreService = Depends(get_vector_store)
):
    """Clear all documents from vector database."""
    try:
        store.clear_collection()
        return {"status": "success", "message": "Vector database cleared"}
    except Exception as e:
        logger.error(f"Error clearing index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
class IndexedPage(BaseModel):
    page_id: str
    page_title: str
    section_name: str
    notebook_name: str
    modified_date: Optional[str]
    created_date: Optional[str]
    chunk_count: int
    url: Optional[str]
 
 
@router.get("/index/pages")
async def get_indexed_pages(
    store: VectorStoreService = Depends(get_vector_store)
):
    """Get list of all indexed pages with their metadata."""
    try:
        pages_data = store.get_indexed_pages()
        return {"pages": pages_data}
    except Exception as e:
        logger.error(f"Error getting indexed pages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Multimodal / Image routes
@router.get("/images/{page_id}/{image_index}")
async def get_image(
    page_id: str,
    image_index: int
):
    """
    Retrieve an image by page_id and image index.

    Returns the image file directly for display.
    """
    try:
        from services.image_storage import ImageStorageService

        # Initialize image storage
        image_storage = ImageStorageService(
            storage_type="local",
            base_path="backend/storage/images"
        )

        # Generate image path
        image_path = image_storage.generate_image_path(page_id, image_index)

        # Check if image exists
        if not await image_storage.exists(image_path):
            raise HTTPException(status_code=404, detail="Image not found")

        # Download image
        image_data = await image_storage.download(image_path)

        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")

        from fastapi.responses import Response
        return Response(content=image_data, media_type="image/png")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
# Query routes
@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    engine: RAGEngine = Depends(get_rag_engine)
):
    """Query the RAG system (text-only, synchronous)."""
    try:
        response = engine.query(request.question, request.config)
        return response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/multimodal", response_model=QueryResponse)
async def query_documents_multimodal(
    request: QueryRequest,
    engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Query the RAG system with multimodal support (text + images).

    Automatically detects visual queries and includes relevant images in the response.
    Uses the async query method for full multimodal support.
    """
    try:
        response = await engine.query_async(request.question, request.config)
        return response
    except Exception as e:
        logger.error(f"Error processing multimodal query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.post("/query/compare", response_model=CompareResponse)
async def compare_configs(
    request: CompareRequest,
    engine: RAGEngine = Depends(get_rag_engine)
):
    """Compare results from multiple configurations."""
    try:
        results = []
 
        for config_name in request.config_names:
            if config_name not in PRESET_CONFIGS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Preset '{config_name}' not found"
                )
 
            config = PRESET_CONFIGS[config_name]
            response = engine.query(request.question, config)
 
            results.append({
                "config_name": config_name,
                "answer": response.answer,
                "sources": [s.dict() for s in response.sources],
                "metadata": response.metadata.dict()
            })
 
        return CompareResponse(results=results)
 
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
# Demo/Testing route for when OneNote is not available
class DemoDocumentRequest(BaseModel):
    texts: List[str]
    notebook_name: str = "Demo Notebook"
 
 
@router.post("/demo/add-documents")
async def add_demo_documents(
    request: DemoDocumentRequest,
    processor: DocumentProcessor = Depends(get_document_processor),
    store: VectorStoreService = Depends(get_vector_store)
):
    """Add demo documents directly (for testing without OneNote)."""
    try:
        from langchain_core.documents import Document as LangChainDocument
 
        # Create documents with metadata
        all_chunks = []
        for i, text in enumerate(request.texts):
            doc = LangChainDocument(
                page_content=text,
                metadata={
                    "page_id": f"demo-{i}",
                    "page_title": f"Demo Page {i+1}",
                    "section_name": "Demo Section",
                    "notebook_name": request.notebook_name,
                    "url": "",
                }
            )
 
            # Chunk the document if it's large
            if len(text) > processor.chunk_size:
                chunks = processor.text_splitter.create_documents(
                    texts=[text],
                    metadatas=[doc.metadata]
                )
                # Add chunk metadata
                for j, chunk in enumerate(chunks):
                    chunk.metadata["chunk_index"] = j
                    chunk.metadata["total_chunks"] = len(chunks)
                all_chunks.extend(chunks)
            else:
                # Add as-is if smaller than chunk size
                doc.metadata["chunk_index"] = 0
                doc.metadata["total_chunks"] = 1
                all_chunks.append(doc)
 
        # Add to vector store
        store.add_documents(all_chunks)
 
        logger.info(f"Added {len(request.texts)} demo documents as {len(all_chunks)} chunks to vector store")
 
        return {
            "status": "success",
            "documents_added": len(request.texts),
            "chunks_created": len(all_chunks),
            "message": f"Added {len(request.texts)} demo documents ({len(all_chunks)} chunks)"
        }
 
    except Exception as e:
        logger.error(f"Error adding demo documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 