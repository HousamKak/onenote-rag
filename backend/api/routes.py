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
from services import (
    OneNoteService,
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
from config import get_settings
 
logger = logging.getLogger(__name__)
 
router = APIRouter()
 
# Global services (will be initialized in main.py)
onenote_service: Optional[OneNoteService] = None
document_processor: Optional[DocumentProcessor] = None
vector_store: Optional[VectorStoreService] = None
rag_engine: Optional[RAGEngine] = None
 
 
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
 
 
# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
 
 
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
    Sync OneNote documents to vector database.
   
    Supports three modes:
    - Incremental sync (default): Only updates modified/new documents
    - Full sync: Clears DB and reindexes everything
    - Force reindex: Reindexes all documents without checking modification dates
    """
    try:
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
                    # Convert to comparable format
                    existing_dt = existing_modified if isinstance(existing_modified, str) else str(existing_modified)
                    new_dt = str(modified_date)
                   
                    if existing_dt == new_dt:
                        logger.debug(f"Skipping unchanged page: {doc.metadata.page_title}")
                        documents_skipped += 1
                        continue
               
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
 
            # Process and chunk the document
            chunks = processor.chunk_documents([doc])
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
 
 
# Query routes
@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    engine: RAGEngine = Depends(get_rag_engine)
):
    """Query the RAG system."""
    try:
        response = engine.query(request.question, request.config)
        return response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
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
 