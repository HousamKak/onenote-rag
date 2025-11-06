"""
Configuration management for the application.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
 
 
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
 
    # OpenAI
    openai_api_key: str
 
    # LangSmith
    langchain_tracing_v2: str = "true"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: str
    langchain_project: str = "onenote-rag"
 
    # Microsoft Graph
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = ""
    microsoft_graph_token: str = ""  # Manual Bearer token from Graph Explorer
 
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
 
 
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
 