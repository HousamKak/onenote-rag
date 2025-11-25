"""Data models for the application."""
from .document import Document, DocumentMetadata
from .query import QueryRequest, QueryResponse, Source, ResponseMetadata, CompareRequest, CompareResponse
from .rag_config import (
    RAGConfig,
    MultiQueryConfig,
    RAGFusionConfig,
    DecompositionConfig,
    StepBackConfig,
    HyDEConfig,
    RerankingConfig
)
from .settings import (
    Setting,
    SettingCreate,
    SettingUpdate,
    SettingResponse,
)
from .notebook import (
    Notebook,
    NotebookCandidate,
    NormalizedNotebook,
    NotebookSelectionRequest,
    NotebookStatus,
)

__all__ = [
    "Document",
    "DocumentMetadata",
    "QueryRequest",
    "QueryResponse",
    "Source",
    "ResponseMetadata",
    "CompareRequest",
    "CompareResponse",
    "RAGConfig",
    "MultiQueryConfig",
    "RAGFusionConfig",
    "DecompositionConfig",
    "StepBackConfig",
    "HyDEConfig",
    "RerankingConfig",
    "Setting",
    "SettingCreate",
    "SettingUpdate",
    "SettingResponse",
    "Notebook",
    "NotebookCandidate",
    "NormalizedNotebook",
    "NotebookSelectionRequest",
    "NotebookStatus",
]
