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
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
from services.auth_service import AuthService
from services.token_store import TokenStore
from services.vision_service import GPT4VisionService
from services.image_storage import ImageStorageService
from services.multimodal_query import MultimodalQueryHandler
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.settings_service import SettingsService
from services.document_cache import DocumentCacheService
from services.document_cache_db import DocumentCacheDB
from middleware.auth import initialize_auth
import api.routes as routes
import api.sync_routes as sync_routes
 
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
 
    # Authentication services (user-delegated OAuth)
    try:
        client_id = dynamic_settings.get("microsoft_client_id", settings.microsoft_client_id)
        client_secret = dynamic_settings.get("microsoft_client_secret", settings.microsoft_client_secret)
        tenant_id = dynamic_settings.get("microsoft_tenant_id", settings.microsoft_tenant_id)

        routes.auth_service = AuthService(
            client_id=client_id,
            tenant_id=tenant_id,
            client_secret=client_secret,
        )
        logger.info("Auth service initialized for user-delegated OAuth")

        routes.token_store = TokenStore()
        logger.info("Token store initialized (in-memory)")

        # Initialize auth middleware
        initialize_auth(routes.auth_service, routes.token_store)
        logger.info("Authentication middleware initialized")

        # Note: OneNote service is now created per-user, not globally
        routes.onenote_service = None  # Keep for backward compatibility

    except Exception as e:
        logger.warning(f"Authentication service initialization failed: {str(e)}")
        logger.warning("User authentication will not be available")
 
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

        if openai_key:
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

            # Initialize multimodal query handler (for queries)
            multimodal_handler = MultimodalQueryHandler(
                vision_service=vision_service,
                image_storage=image_storage
            )
            logger.info("Multimodal query handler initialized")

            # Expose multimodal services to routes
            # Note: MultimodalDocumentProcessor is created per-request with user's token
            routes.vision_service = vision_service
            routes.image_storage = image_storage
            routes.multimodal_processor = None  # Created per-request now
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

    # =========================================================================
    # Initialize Document Cache & Sync System
    # =========================================================================
    logger.info("Initializing document cache and sync system...")

    # Initialize document cache database
    cache_db_path = "./data/document_cache.db"
    os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)

    cache_db = DocumentCacheDB(db_path=cache_db_path)
    logger.info(f"Document cache database initialized at: {cache_db_path}")

    # Initialize document cache service
    routes.document_cache = DocumentCacheService(db_path=cache_db_path)
    logger.info("Document cache service initialized")

    # Store cache_db for global access
    routes.cache_db = cache_db

    # Set sync services for API routes
    sync_routes.set_document_cache(routes.document_cache)

    logger.info("✅ Document cache and sync system initialized")
    logger.info("Note: Sync is user-triggered. Use /api/sync/* endpoints after login.")

    logger.info("✅ Application startup complete! Server is ready to accept requests.")

    # Sync status tracking (for backward compatibility with frontend)
    routes.sync_status = {
        "in_progress": False,
        "status": "ready",
        "message": "Sync system ready. Use /api/sync/* endpoints to trigger sync."
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

# Include sync routes
app.include_router(sync_routes.router)
 
 
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
 