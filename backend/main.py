"""
Main FastAPI application.
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from config import get_settings, set_settings_service, get_dynamic_settings
from services import (
    OneNoteService,
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
from services.vision_service import GPT4VisionService
from services.image_storage import ImageStorageService
from services.multimodal_query import MultimodalQueryHandler
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.settings_service import SettingsService
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
 
    # Initialize settings service with database and encryption
    logger.info("Initializing settings service...")
    db_service = DatabaseService(db_path="./data/settings.db")
    encryption_service = EncryptionService(key_file="./data/.encryption_key")
    routes.settings_service = SettingsService(db_service, encryption_service)
    set_settings_service(routes.settings_service)
    logger.info("Settings service initialized")
    
    # Get dynamic settings (from database or .env)
    dynamic_settings = get_dynamic_settings()
    
    # Update environment variables with database settings if available
    if dynamic_settings.get("openai_api_key"):
        os.environ['OPENAI_API_KEY'] = dynamic_settings["openai_api_key"]
    if dynamic_settings.get("langchain_api_key"):
        os.environ['LANGCHAIN_API_KEY'] = dynamic_settings["langchain_api_key"]
    
    logger.info("Configuration loaded from database (with .env fallback)")
 
    # Initialize services
    logger.info("Initializing services...")
 
    # OneNote service
    try:
        use_azure_ad_str = dynamic_settings.get("use_azure_ad_auth", str(settings.use_azure_ad_auth))
        use_azure_ad = use_azure_ad_str.lower() in ('true', '1', 'yes')
        
        routes.onenote_service = OneNoteService(
            client_id=dynamic_settings.get("microsoft_client_id", settings.microsoft_client_id),
            client_secret=dynamic_settings.get("microsoft_client_secret", settings.microsoft_client_secret),
            tenant_id=dynamic_settings.get("microsoft_tenant_id", settings.microsoft_tenant_id),
            manual_token=dynamic_settings.get("microsoft_graph_token", settings.microsoft_graph_token),
            use_azure_ad=use_azure_ad,
        )
        auth_method = "Azure AD" if use_azure_ad else "Manual Token"
        logger.info(f"OneNote service initialized with {auth_method} authentication")
    except Exception as e:
        logger.warning(f"OneNote service initialization failed: {str(e)}")
        logger.warning("OneNote features will not be available")
 
    # Document processor
    chunk_size = int(dynamic_settings.get("chunk_size", settings.chunk_size))
    chunk_overlap = int(dynamic_settings.get("chunk_overlap", settings.chunk_overlap))
    routes.document_processor = DocumentProcessor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    logger.info("Document processor initialized")
 
    # Multimodal services (optional - only if OpenAI API key is available)
    multimodal_handler = None
    try:
        openai_key = dynamic_settings.get("openai_api_key", settings.openai_api_key)
        access_token = dynamic_settings.get("microsoft_graph_token", settings.microsoft_graph_token)

        if openai_key:
            from services.multimodal_processor import MultimodalDocumentProcessor

            # Initialize vision service
            vision_service = GPT4VisionService(
                api_key=openai_key,
                default_model="gpt-4o-mini",  # Use mini for cost efficiency during indexing
                max_tokens=1000,
                temperature=0.0
            )
            logger.info("Vision service initialized")

            # Initialize image storage
            base_dir = os.path.dirname(os.path.dirname(__file__))  # Project root
            storage_path = os.path.join(base_dir, "storage", "images")
            os.makedirs(storage_path, exist_ok=True)
            
            image_storage = ImageStorageService(
                storage_type="local",
                base_path=storage_path
            )
            logger.info(f"Image storage initialized at: {storage_path}")

            # Initialize multimodal document processor (for indexing)
            multimodal_processor = MultimodalDocumentProcessor(
                vision_service=vision_service,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                max_images_per_document=10,
                access_token=access_token
            )
            logger.info("Multimodal document processor initialized")

            # Initialize multimodal query handler (for queries)
            multimodal_handler = MultimodalQueryHandler(
                vision_service=vision_service,
                image_storage=image_storage
            )
            logger.info("Multimodal query handler initialized")

            # Expose multimodal services to routes
            routes.vision_service = vision_service
            routes.image_storage = image_storage
            routes.multimodal_processor = multimodal_processor
            logger.info("Multimodal services exposed to API routes")
        else:
            logger.info("Multimodal features disabled (no OpenAI API key)")
    except Exception as e:
        logger.warning(f"Failed to initialize multimodal services: {str(e)}")
        logger.warning("Continuing with text-only mode")

    # Vector store
    os.makedirs(settings.vector_db_path, exist_ok=True)
    routes.vector_store = VectorStoreService(
        persist_directory=settings.vector_db_path,
        embedding_provider=dynamic_settings.get("embedding_provider", settings.embedding_provider),
    )
    logger.info("Vector store initialized")

    # RAG engine with optional multimodal support
    routes.rag_engine = RAGEngine(
        vector_store=routes.vector_store,
        multimodal_handler=multimodal_handler
    )
    logger.info("RAG engine initialized")
 
    logger.info("✅ Application startup complete! Server is ready to accept requests.")
 
    # Schedule auto-sync to run in background (non-blocking)
    # This performs an incremental sync to catch any changes since last run
    enable_sync = dynamic_settings.get("enable_startup_sync", str(settings.enable_startup_sync)).lower() == "true"
    if routes.onenote_service and enable_sync:
        logger.info("Scheduling automatic incremental sync in background...")
        
        # Import asyncio to schedule background task
        import asyncio
        
        # Create background task function
        async def background_sync():
            """Background task to sync OneNote documents without blocking startup."""
            try:
                # Set sync status
                routes.sync_status = {
                    "in_progress": True,
                    "status": "running",
                    "message": "Background sync in progress...",
                    "documents_processed": 0
                }
                
                logger.info("Starting background incremental sync...")
                
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
                        
                        # Process and add the document (with multimodal support if available)
                        use_multimodal = multimodal_processor is not None

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
                                        img_path = image_storage.generate_image_path(
                                            page_id=img_data["page_id"],
                                            image_index=img_data["position"]
                                        )
                                        await image_storage.upload(
                                            image_path=img_path,
                                            image_data=img_data["data"],
                                            content_type="image/png",
                                            metadata={
                                                "page_id": img_data["page_id"],
                                                "position": img_data["position"]
                                            }
                                        )
                                    except Exception as e:
                                        logger.error(f"Error storing image during startup sync: {str(e)}")

                                logger.debug(f"Stored {len(image_data_list)} images for {page_id}")
                        else:
                            # Text-only processing
                            chunks = routes.document_processor.chunk_documents([doc])

                        routes.vector_store.add_documents(chunks)
                        total_chunks += len(chunks)
                        
                        # Update progress
                        routes.sync_status["documents_processed"] = documents_added + documents_updated
                    
                    logger.info(f"✅ Background sync complete: {documents_added} added, {documents_updated} updated, {documents_skipped} skipped ({total_chunks} chunks)")
                    routes.sync_status = {
                        "in_progress": False,
                        "status": "complete",
                        "message": f"Sync complete: {documents_added} added, {documents_updated} updated, {documents_skipped} skipped",
                        "documents_added": documents_added,
                        "documents_updated": documents_updated,
                        "documents_skipped": documents_skipped,
                        "total_chunks": total_chunks
                    }
                else:
                    logger.info("No documents found in OneNote")
                    routes.sync_status = {
                        "in_progress": False,
                        "status": "complete",
                        "message": "No documents found in OneNote",
                        "documents_processed": 0
                    }
                       
            except Exception as e:
                logger.error(f"Background sync failed: {str(e)}")
                routes.sync_status = {
                    "in_progress": False,
                    "status": "error",
                    "message": f"Sync failed: {str(e)}",
                    "documents_processed": 0
                }
        
        # Schedule the background task
        asyncio.create_task(background_sync())
        logger.info("Background sync task scheduled")
    else:
        if not routes.onenote_service:
            logger.info("OneNote service not available, skipping auto-sync")
            routes.sync_status = {
                "in_progress": False,
                "status": "skipped",
                "message": "OneNote service not available"
            }
        else:
            logger.info("Startup sync disabled in settings")
            routes.sync_status = {
                "in_progress": False,
                "status": "disabled",
                "message": "Startup sync is disabled"
            }
 
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
 