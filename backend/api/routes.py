"""
API routes for the OneNote RAG application.
"""
import logging
import secrets
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
from models.user import UserContext
from services import (
    OneNoteService,
    DocumentProcessor,
    VectorStoreService,
    RAGEngine,
)
from services.settings_service import SettingsService
from services.auth_service import AuthService
from services.token_store import TokenStore
from middleware.auth import get_current_user, generate_state
from config import get_settings, get_dynamic_settings
 
logger = logging.getLogger(__name__)
 
router = APIRouter()
 
# Global services (will be initialized in main.py)
onenote_service: Optional[OneNoteService] = None  # Will be removed - per-user now
document_processor: Optional[DocumentProcessor] = None
vector_store: Optional[VectorStoreService] = None
rag_engine: Optional[RAGEngine] = None
settings_service: Optional[SettingsService] = None

# Authentication services
auth_service: Optional[AuthService] = None
token_store: Optional[TokenStore] = None

# Multimodal services (optional - initialized if OpenAI key available)
multimodal_processor: Optional[Any] = None  # MultimodalDocumentProcessor
vision_service: Optional[Any] = None  # GPT4VisionService
image_storage: Optional[Any] = None  # ImageStorageService

# Document cache services (new sync system)
document_cache: Optional[Any] = None  # DocumentCacheService
cache_db: Optional[Any] = None  # DocumentCacheDB

# Startup sync status
sync_status: Dict[str, Any] = {
    "in_progress": False,
    "status": "not_started",
    "message": "Sync has not started yet",
    "documents_processed": 0
}
 
REQUIRED_OIDC_SCOPES = ["openid","profile","offline_access"]

def build_oauth_scopes(raw_scopes: List[str]) -> List[str]: 
    """Ensure OpenID Connect scopes are included for ID tokens."""
    scopes = [scope for scope in (raw_scopes or []) if scope]
    added_scopes: List[str]=[]
    for required_scope in REQUIRED_OIDC_SCOPES:
        if required_scope not in scopes:
            scopes.append(required_scope)
            added_scopes.append(required_scope)
    if added_scopes:
        logger.info(f"Added required OpenID scopes automatically: {added_scopes}")
    return scopes


 
def get_rag_engine() -> RAGEngine:
    """Dependency to get RAG engine."""
    if rag_engine is None:
        raise HTTPException(status_code=500, detail="RAG engine not initialized")
    return rag_engine
 
 
def get_onenote_service(user: UserContext = Depends(get_current_user)) -> OneNoteService:
    """
    Dependency to create user-specific OneNote service.

    Each user gets their own OneNote service instance with their access token.
    """
    return OneNoteService(access_token=user.access_token)
 
 
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


def get_multimodal_processor():
    """
    Dependency to get multimodal procesor (optional).
    
    Creates a MultimodalDocumentProcessor if vision_service is available
    (i.e., OpenAI key is configured). Includes image_storage to read
    cached images instead of re-downloading from OneNote.
    """
    if vision_service:
        from services.multimodal_document_processor import MultimodalDocumentProcessor
        return MultimodalDocumentProcessor(
            vision_service=vision_service,
            image_storage=image_storage # pass image_storage for reacding cached images
        )
    return None # Returns None if multimodal services not available


def get_settings_service() -> SettingsService:
    """Dependency to get settings service."""
    if settings_service is None:
        raise HTTPException(status_code=500, detail="Settings service not initialized")
    return settings_service


def create_sync_orchestrator_for_user(user: UserContext):
    """
    Create a SyncOrchestrator instance for a specific user.

    Args:
        user: Current user context with access token

    Returns:
        SyncOrchestrator configured for the user
    """
    from services.sync_orchestrator import SyncOrchestrator

    if not document_cache or not cache_db:
        raise HTTPException(status_code=500, detail="Document cache not initialized")

    if not image_storage:
        raise HTTPException(status_code=500, detail="Image storage not initialized")

    # Create OneNoteService with user's token
    user_onenote_service = OneNoteService(access_token=user.access_token)

    # Create SyncOrchestrator
    orchestrator = SyncOrchestrator(
        onenote_service=user_onenote_service,
        document_cache=document_cache,
        image_storage=image_storage,
        cache_db=cache_db
    )

    return orchestrator


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/sync-status")
async def get_sync_status():
    """Get the status of the background startup sync."""
    return sync_status


# ================================
# Authentication Routes
# ================================


@router.get("/auth/debug")
async def auth_debug():
    """Debug endpoint to check auth configuration."""
    settings = get_dynamic_settings()
    client_secret = settings.get("microsoft_client_secret", "")
    return {
        "auth_service_initialized": auth_service is not None,
        "microsoft_client_id": settings.get("microsoft_client_id", ""),
        "microsoft_client_secret_set": bool(client_secret), # Don't expose the actual secret
        "microsoft_client_secret_length": len(client_secret) if client_secret else 0,
        "microsoft_tenant_id": settings.get("microsoft_tenant_id", ""),
        "oauth_redirect_uri": settings.get("oauth_redirect_uri", ""),
        "oauth_scopes": settings.get("oauth_scopes", ""),
    }



class AuthCallbackRequest(BaseModel):
    """Request model for OAuth callback."""
    code: str
    state: str


@router.get("/auth/login")
async def login():
    """
    Generate Microsoft OAuth login URL.

    Returns authorization URL and state for CSRF protection.
    """
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")

    settings = get_dynamic_settings()
    redirect_uri = settings.get("oauth_redirect_uri", "http://localhost:5173/auth/callback")
    scopes = settings.get("oauth_scopes", "User.Read Files.Read Notes.Read").split()
    scopes = build_oauth_scopes(scopes)
    
    logger.info(f"Login endpoint called. Redirect URI: {redirect_uri}, Scopes: {scopes}")

    state = generate_state()
    auth_url = auth_service.get_authorization_url(
        redirect_uri=redirect_uri,
        state=state,
        scopes=scopes
    )

    logger.info(f"Generated auth URL: {auth_url}")
    return {
        "auth_url": auth_url,
        "state": state,
        "redirect_uri": redirect_uri,
    }


@router.post("/auth/callback")
async def auth_callback(request: AuthCallbackRequest):
    """
    Handle OAuth callback and exchange code for tokens.

    Returns access token (session token) for frontend to use in API calls.
    """
    if not auth_service or not token_store:
        raise HTTPException(status_code=500, detail="Auth service not initialized")

    try:
        settings = get_dynamic_settings()
        redirect_uri = settings.get("oauth_redirect_uri", "http://localhost:5173/auth/callback")
        scopes = settings.get("oauth_scopes", "User.Read Files.Read Notes.Read").split()
        scopes = build_oauth_scopes(scopes)

        # Exchange authorization code for tokens
        token_response = await auth_service.acquire_token_by_code(
            code=request.code,
            redirect_uri=redirect_uri,
            scopes=scopes
        )

        # Validate and extract user info from ID token
        id_token = token_response.get("id_token")
        if not id_token:
            # Fallback to access token if no ID token
            logger.error("ID token missing from token response. Ensure OpenID scopes are configured.")
            raise HTTPException(
                status_code=400, 
                detail=(
                    "Authentication failed: Microsoft did not return an ID token. "
                    "Verify that 'openid pofile offline_access' scopes are configured in settings."
                    ),
            )

        claims = auth_service.validate_token(id_token)
        user_info = auth_service.extract_user_info(claims)
        user_id = user_info["user_id"]

        if not user_id:
            raise HTTPException(status_code=400, detail="Could not extract user ID from token")

        # Store tokens for this user
        token_store.set_tokens(
            user_id=user_id,
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token", ""),
            expires_in=token_response.get("expires_in", 3600),
            token_type=token_response.get("token_type", "Bearer"),
            scope=token_response.get("scope"),
            id_token=id_token
        )

        logger.info(f"User {user_id} authenticated successfully")

        # Return the ID token to frontend (it will use this for auth)
        return {
            "access_token": id_token,  # Frontend will send this as Bearer token
            "token_type": "Bearer",
            "user": {
                "id": user_id,
                "email": user_info.get("email"),
                "name": user_info.get("name")
            }
        }

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/refresh")
async def refresh_token(user: UserContext = Depends(get_current_user)):
    """
    Refresh user's access token.

    This is automatically called by the get_current_user middleware when needed,
    but can also be called explicitly by the frontend.
    """
    if not token_store:
        raise HTTPException(status_code=500, detail="Token store not initialized")

    # Token is already refreshed by middleware if needed
    token_data = token_store.get_tokens(user.user_id)

    if not token_data:
        raise HTTPException(status_code=401, detail="Session expired")

    # Return the ID token (frontend auth token)
    return {
        "access_token": token_data.id_token or token_data.access_token,
        "token_type": "Bearer"
    }


@router.post("/auth/logout")
async def logout(user: UserContext = Depends(get_current_user)):
    """
    Logout user and clear their tokens.
    """
    if not token_store:
        raise HTTPException(status_code=500, detail="Token store not initialized")

    token_store.delete_tokens(user.user_id)
    logger.info(f"User {user.user_id} logged out")

    return {"message": "Logged out successfully"}


@router.get("/auth/user")
async def get_user_info(user: UserContext = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "id": user.user_id,
        "email": user.email,
        "name": user.name
    }


# ================================
# Settings routes
# ================================
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



 
@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingUpdate,
    service: SettingsService = Depends(get_settings_service)
) -> Dict[str, Any]:
    """Update a setting value."""
    global onenote_service
   
    try:
        service.set_setting(key=key, value=update.value)
       
        # Reinitialize OneNote service if authentication-related settings changed
        onenote_auth_keys = [
            "use_azure_ad_auth",
            "microsoft_client_id",
            "microsoft_client_secret",
            "microsoft_tenant_id",
            "microsoft_graph_token"
        ]
       
        if key in onenote_auth_keys:
            try:
                # Get all current settings
                all_settings = service.get_settings_dict()
               
                # Parse the use_azure_ad_auth setting
                use_azure_ad_str = all_settings.get("use_azure_ad_auth", "true")
                use_azure_ad = use_azure_ad_str.lower() in ('true', '1', 'yes')
               
                # Reinitialize the OneNote service with updated settings
                onenote_service = OneNoteService(
                    client_id=all_settings.get("microsoft_client_id", ""),
                    client_secret=all_settings.get("microsoft_client_secret", ""),
                    tenant_id=all_settings.get("microsoft_tenant_id", ""),
                    manual_token=all_settings.get("microsoft_graph_token", ""),
                    use_azure_ad=use_azure_ad,
                )
               
                auth_method = "Azure AD" if use_azure_ad else "Manual Token"
                logger.info(f"OneNote service reinitialized with {auth_method} authentication")
               
            except Exception as reinit_error:
                logger.warning(f"Failed to reinitialize OneNote service: {str(reinit_error)}")
       
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
    user: UserContext = Depends(get_current_user),
    processor: DocumentProcessor = Depends(get_document_processor),
    store: VectorStoreService = Depends(get_vector_store),
    multimodal_proc: Optional[Any] = Depends(get_multimodal_processor)
):
    """
    Sync OneNote documents using the new cache-based system.

    NEW ARCHITECTURE:
    Step 1: Sync from OneNote → Local Cache (SyncOrchestrator)
    Step 2: Index from Cache → Vector Store (DocumentProcessor)

    Benefits:
    - Respects rate limits during sync
    - RAG queries read from cache (no Graph API calls)
    - Faster, more reliable
    - Full audit trail

    Supports three modes:
    - Incremental sync (default): Only updates changed documents
    - Full sync (full_sync=True): Syncs all documents
    - Force reindex (force_reindex=True): Re-indexes all from cache

    Multimodal processing is supported if image services are available.
    """
    try:
        logger.info(f"Starting sync with new cache-based system (full_sync={request.full_sync}, force_reindex={request.force_reindex})")

        # Step 1: Sync OneNote → Local Cache (respects rate limits)
        logger.info("Step 1: Syncing from OneNote to local cache...")
        orchestrator = create_sync_orchestrator_for_user(user)

        if request.full_sync:
            sync_result = await orchestrator.sync_full(
                notebook_ids=request.notebook_ids,
                triggered_by="api",
                user_id=user.user_id
            )
        else:
            sync_result = await orchestrator.sync_incremental(
                triggered_by="api",
                user_id=user.user_id
            )

        logger.info(f"Sync to cache complete: {sync_result.pages_added} added, {sync_result.pages_updated} updated, {sync_result.pages_deleted} deleted")

        # Step 2: Index from Cache → Vector Store
        logger.info("Step 2: Indexing documents from cache to vector store...")

        if not document_cache:
            raise HTTPException(status_code=500, detail="Document cache not initialized")

        # Get documents that need indexing
        if request.force_reindex:
            # Force reindex: get all documents from cache
            documents_to_index = document_cache.get_all_documents()
            logger.info(f"Force reindex: Processing all {len(documents_to_index)} documents from cache")

            # Clear vector store for force reindex
            if request.full_sync:
                logger.info("Clearing vector store for full reindex")
                store.clear_collection()
        else:
            # Normal flow: only index documents that need it
            documents_to_index = document_cache.get_documents_needing_indexing()
            logger.info(f"Found {len(documents_to_index)} documents needing indexing")

        if not documents_to_index:
            return SyncResponse(
                status="success",
                documents_processed=sync_result.pages_fetched,
                documents_added=sync_result.pages_added,
                documents_updated=sync_result.pages_updated,
                documents_skipped=sync_result.pages_skipped,
                chunks_created=0,
                message=f"Sync complete: {sync_result.pages_added} added, {sync_result.pages_updated} updated, {sync_result.pages_deleted} deleted. No documents need indexing."
            )

        # Process and index documents
        total_chunks = 0
        indexed_count = 0
        multimodal_count = 0

        for doc in documents_to_index:
            try:
                #============================================
                # MULTIMODAL PROCESSING & CHUNKING
                #============================================
                #check if multimodal processor is available and document has images
                if multimodal_proc and doc.metadata and doc.metadata.image_count > 0 :
                    logger.info(f"🖼️ Processing {doc.metadata.image_count} images for '{doc.metadata.page_title}'")
                    
                    try:
                        # Use multimodal processor to analyze images and chunk document
                        # This returns (chunks_with_image_context, image_data_list)
                        chunks, image_data = await multimodal_proc.chunk_document_multimodal(
                            doc,
                            enrich_with_metadata=True,
                            include_images=True
                        )
                        multimodal_count += 1
                        logger.info(f"✅ Created {len(chunks)} multimodal chunks with {len(image_data)} images for '{doc.metadata.page_title}'")
                    except Exception as img_error:
                        logger.warning(f"⚠️  Failed to process images for '{doc.metadata.page_title}': {img_error}")
                        logger.debug(f"Image processing error details:", exc_info=True)
                        # Fallback to text-only chunking
                        chunks = processor.chunk_documents([doc])
                else:
                    # Standard text-only chunking (no images or multimodal not available)
                    chunks = processor.chunk_documents([doc])
                
                # ============================================
                # EMBEDDING & VECTOR STORE
                # ============================================
                # Add to vector store (embeddings include both text AND image context)
                if chunks:
                    store.add_documents(chunks)
                    total_chunks += len(chunks)
                    indexed_count += 1

                    # Mark as indexed in cache
                    document_cache.mark_document_indexed(
                        page_id=doc.page_id,
                        chunk_count=len(chunks),
                        image_count=doc.metadata.image_count if doc.metadata else 0
                    )

                    logger.debug(f"✅ Indexed '{doc.metadata.page_title}': {len(chunks)} chunks")

            except Exception as e:
                logger.error(f"❌ Error indexing document {doc.page_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue with other documents

        logger.info(f"✅ Indexing complete: {indexed_count}/{len(documents_to_index)} documents, {total_chunks} chunks")
        if multimodal_count > 0:
            logger.info(f" 🎨 Multimodal processing for {multimodal_count} documents enriched with image context")


        # Build response message
        message_parts = []
        if sync_result.pages_added > 0:
            message_parts.append(f"{sync_result.pages_added} added")
        if sync_result.pages_updated > 0:
            message_parts.append(f"{sync_result.pages_updated} updated")
        if sync_result.pages_deleted > 0:
            message_parts.append(f"{sync_result.pages_deleted} deleted")
        if sync_result.pages_skipped > 0:
            message_parts.append(f"{sync_result.pages_skipped} skipped")

        message = f"Sync complete: {', '.join(message_parts)} ({total_chunks} chunks indexed"
        if multimodal_count > 0:
            message += f", {multimodal_count} with image context"
        message += ")"

        return SyncResponse(
            status="success",
            documents_processed=sync_result.pages_fetched,
            documents_added=sync_result.pages_added,
            documents_updated=sync_result.pages_updated,
            documents_skipped=sync_result.pages_skipped,
            chunks_created=total_chunks,
            message=message
        )

    except Exception as e:
        logger.error(f"Error during sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
 
 
class IndexStats(BaseModel):
    total_documents: int
    collection_name: str
    persist_directory: str
 
 
@router.get("/index/stats", response_model=IndexStats)
async def get_index_stats(
    user: UserContext = Depends(get_current_user),
    store: VectorStoreService = Depends(get_vector_store)
):
    """Get vector database statistics."""
    try:
        stats = store.get_stats()
        return IndexStats(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/index/stats/detailed")
async def get_detailed_stats(
     user: UserContext = Depends(get_current_user),
     store: VectorStoreService = Depends(get_vector_store)
     
):
    """Get detailed statistics from both database and vector store"""
    try:
        #Get vector store stats
        vector_stats = store.get_stats()
        
        # Get database stats
        if document_cache:
            import sqlite3
            conn = sqlite3.connect(document_cache.db_path if hasattr(document_cache, 'db_path') else 'data/document_cache.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT
                    COUNT(*) as total_docs,
                    COUNT(CASE WHEN indexed_at IS NOT NULL THEN 1 END) as indexed_docs,
                    COUNT(CASE WHEN indexed_at IS NULL THEN 1 END) as unindexed_docs,
                    SUM(chunk_count) as total_chunks_db,
                    SUM(image_count) as total_images,
                    COUNT(CASE WHEN image_count > 0 THEN 1 END) as doc_with_images
                    FROM onenote_document
                    WHERE is_deleted = 0
                ''')
            db_stats = cursor.fetchone()
            conn.close()
            
            return{
                "vector_store":{
                    "chunks_in_chromadb":vector_stats["total_documents"],
                    "collection_name":vector_stats["collection_name"],
                },
                "database":{
                    "total_documents":db_stats[0] or 0,
                    "indexed_documents":db_stats[1] or 0,
                    "unindexed_documents":db_stats[2] or 0,
                    "total_chunks_expected":db_stats[3] or 0,
                    "total_images":db_stats[4] or 0,
                    "documents_with_images":db_stats[5] or 0,
                },
                "sync_status":{
                    "in_sync":(db_stats[3] or 0) == vector_stats["total_documents"],
                    "missing_chunks": max(0, (db_stats[3] or 0) - vector_stats["total_documents"])
                }
            }
        else:
            return {"error":"Document cache not initialized"}
    except Exception as e:
        logger.error(f"Error getting detailed stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/index/clear")
async def clear_index(
    user: UserContext = Depends(get_current_user),
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
    user: UserContext = Depends(get_current_user),
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
    # No auth required - images are public cached content
):
    """
    Retrieve an image by page_id and image index.

    Returns the image file directly for display.
    Public endpoint - no authentication required
    """
    try:
        # URL decode the page_id (! becomes %21 etc.)
        from urllib.parse import unquote
        page_id = unquote(page_id)
        
        logger.debug(f"Image request: page_id={page_id}, image_index={image_index}")
        # Use the globally initiallized image_storage service if available
        # This ensures we use the same path as during indexing
        if image_storage is None:
            raise HTTPException(
                status_code=500,
                detail="Image storage service not available. Multimodal features may be disabled."
            )

        # Generate image path
        image_path = image_storage.generate_image_path(page_id, image_index)

        # Check if image exists
        if not await image_storage.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
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
    user: UserContext = Depends(get_current_user),
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
    user: UserContext = Depends(get_current_user),
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
    user: UserContext = Depends(get_current_user),
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
 