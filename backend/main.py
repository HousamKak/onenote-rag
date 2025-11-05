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
