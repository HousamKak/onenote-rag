"""
Main FastAPI application.
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from config import get_settings
from services import (
    OneNoteService,
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
import api.routes as routes
 
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting OneNote RAG application...")
 
    settings = get_settings()
 
    # Set environment variables for LangSmith
    os.environ['LANGCHAIN_TRACING_V2'] = settings.langchain_tracing_v2
    os.environ['LANGCHAIN_ENDPOINT'] = settings.langchain_endpoint
    os.environ['LANGCHAIN_API_KEY'] = settings.langchain_api_key
    os.environ['LANGCHAIN_PROJECT'] = settings.langchain_project
    os.environ['OPENAI_API_KEY'] = settings.openai_api_key
   
    # Disable ChromaDB telemetry to avoid SSL certificate issues
    os.environ['ANONYMIZED_TELEMETRY'] = 'False'
    os.environ['CHROMA_TELEMETRY_ENABLED'] = 'False'
   
    # Disable SSL verification for corporate proxy environments
    # This fixes "certificate verify failed: self-signed certificate in certificate chain" errors
    # when downloading tiktoken files from openaipublic.blob.core.windows.net
    import ssl
    import urllib3
    import warnings
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['SSL_CERT_FILE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['PYTHONHTTPSVERIFY'] = '0'
   
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
   
    # Monkey-patch requests to disable SSL verification globally for tiktoken downloads
    import requests
    original_request = requests.Session.request
    def patched_request(self, method, url, **kwargs):
        kwargs.setdefault('verify', False)
        return original_request(self, method, url, **kwargs)
    requests.Session.request = patched_request
   
    logger.info("SSL verification disabled for corporate proxy compatibility")
 
    logger.info(f"LangSmith tracing enabled: {settings.langchain_tracing_v2}")
    logger.info(f"LangSmith project: {settings.langchain_project}")
 
    # Initialize services
    logger.info("Initializing services...")
 
    # OneNote service
    try:
        routes.onenote_service = OneNoteService(
            client_id=settings.microsoft_client_id,
            client_secret=settings.microsoft_client_secret,
            tenant_id=settings.microsoft_tenant_id,
            manual_token=settings.microsoft_graph_token,
        )
        logger.info("OneNote service initialized")
    except Exception as e:
        logger.warning(f"OneNote service initialization failed: {str(e)}")
        logger.warning("OneNote features will not be available")
 
    # Document processor
    routes.document_processor = DocumentProcessor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    logger.info("Document processor initialized")
 
    # Vector store
    os.makedirs(settings.vector_db_path, exist_ok=True)
    routes.vector_store = VectorStoreService(
        persist_directory=settings.vector_db_path,
    )
    logger.info("Vector store initialized")
 
    # RAG engine
    routes.rag_engine = RAGEngine(vector_store=routes.vector_store)
    logger.info("RAG engine initialized")
 
    # Auto-sync OneNote documents on startup (INCREMENTAL ONLY)
    # This performs an incremental sync to catch any changes since last run
    if routes.onenote_service and settings.enable_startup_sync:
        logger.info("Starting automatic incremental sync on startup...")
        try:
            # Fetch all documents from OneNote
            documents = routes.onenote_service.get_all_documents()
            logger.info(f"Retrieved {len(documents)} documents from OneNote")
           
            if documents:
                documents_added = 0
                documents_updated = 0
                documents_skipped = 0
                total_chunks = 0
                
                # Perform incremental sync - only process changed/new documents
                for doc in documents:
                    page_id = doc.metadata.page_id
                    modified_date = doc.metadata.modified_date
                    
                    # Check if document exists and compare modification dates
                    existing_modified = routes.vector_store.get_page_modified_date(page_id)
                    
                    if existing_modified and modified_date:
                        # Convert to ISO format for comparison
                        existing_dt_str = existing_modified
                        new_dt_str = modified_date.isoformat()
                        
                        if existing_dt_str == new_dt_str:
                            # Document unchanged, skip it
                            logger.debug(f"Skipping unchanged page: {doc.metadata.page_title}")
                            documents_skipped += 1
                            continue
                        else:
                            # Document modified, update it
                            logger.info(f"Updating modified page: {doc.metadata.page_title}")
                            routes.vector_store.delete_by_page_id(page_id)
                            documents_updated += 1
                    else:
                        # New document
                        logger.info(f"Adding new page: {doc.metadata.page_title}")
                        documents_added += 1
                    
                    # Process and add the document
                    chunks = routes.document_processor.chunk_documents([doc])
                    routes.vector_store.add_documents(chunks)
                    total_chunks += len(chunks)
                
                logger.info(f"✅ Startup sync complete: {documents_added} added, {documents_updated} updated, {documents_skipped} skipped ({total_chunks} chunks)")
            else:
                logger.info("No documents found in OneNote")
               
        except Exception as e:
            logger.error(f"Auto-sync failed: {str(e)}")
            logger.warning("Application will continue without auto-sync")
    else:
        if not routes.onenote_service:
            logger.info("OneNote service not available, skipping auto-sync")
        else:
            logger.info("Startup sync disabled in settings")
 
    logger.info("Application startup complete!")
 
    yield
 
    # Shutdown
    logger.info("Shutting down application...")
 
 
# Create FastAPI app
app = FastAPI(
    title="OneNote RAG API",
    description="RAG system for querying OneNote documents with advanced techniques",
    version="1.0.0",
    lifespan=lifespan
)
 
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],  # Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Include routes
app.include_router(routes.router, prefix="/api")
 
 
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "OneNote RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }
 
 
if __name__ == "__main__":
    import uvicorn
 
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
 