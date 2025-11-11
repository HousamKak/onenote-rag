"""
Configuration management for the application.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
 
 
class Settings(BaseSettings):
    """Application settings loaded from environment variables or database."""
 
    # OpenAI
    openai_api_key: str = ""
 
    # LangSmith
    langchain_tracing_v2: str = "true"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: str = ""
    langchain_project: str = "onenote-rag"
 
    # Microsoft Graph
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = ""
    microsoft_graph_token: str = ""  # Manual Bearer token from Graph Explorer
    use_azure_ad_auth: bool = True  # True = Azure AD (client credentials), False = Manual token
 
    # Application
    chunk_size: int = 1000
    chunk_overlap: int = 200
    vector_db_path: str = "./data/chroma_db"
    enable_startup_sync: bool = True  # Enable automatic incremental sync on startup
    
    # Embeddings
    embedding_provider: str = "openai"  # Options: "openai"
   
    # ChromaDB Settings
    anonymized_telemetry: str = "False"
    chroma_telemetry_enabled: str = "False"
 
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings service reference (will be set in main.py)
_settings_service: Optional[object] = None


def set_settings_service(service):
    """Set the global settings service instance."""
    global _settings_service
    _settings_service = service


def get_dynamic_settings() -> dict:
    """
    Get settings dynamically from database if available, otherwise from .env.
    
    Returns:
        Dictionary of all settings
    """
    if _settings_service is not None:
        try:
            return _settings_service.get_settings_dict()
        except Exception:
            pass
    
    # Fallback to environment-based settings
    settings = Settings()
    return {
        "openai_api_key": settings.openai_api_key,
        "langchain_tracing_v2": settings.langchain_tracing_v2,
        "langchain_endpoint": settings.langchain_endpoint,
        "langchain_api_key": settings.langchain_api_key,
        "langchain_project": settings.langchain_project,
        "microsoft_client_id": settings.microsoft_client_id,
        "microsoft_client_secret": settings.microsoft_client_secret,
        "microsoft_tenant_id": settings.microsoft_tenant_id,
        "microsoft_graph_token": settings.microsoft_graph_token,
        "use_azure_ad_auth": str(settings.use_azure_ad_auth),
        "chunk_size": str(settings.chunk_size),
        "chunk_overlap": str(settings.chunk_overlap),
        "enable_startup_sync": str(settings.enable_startup_sync),
        "embedding_provider": settings.embedding_provider,
    }
 
 
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (for backward compatibility)."""
    return Settings()
 