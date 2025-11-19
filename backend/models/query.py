"""Query and response models."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .rag_config import RAGConfig


class QueryRequest(BaseModel):
    """Request model for querying the RAG system."""

    question: str = Field(..., min_length=1, description="User question")
    config: Optional[RAGConfig] = Field(None, description="RAG configuration (uses default if not provided)")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the key points from the project meeting?",
                "config": None,
                "session_id": "session-123"
            }
        }


class Source(BaseModel):
    """Source document reference."""

    document_id: str = Field(..., description="Document ID")
    page_title: str = Field(..., description="OneNote page title")
    notebook_name: str = Field(..., description="Notebook name")
    section_name: str = Field(..., description="Section name")
    content_snippet: str = Field(..., description="Relevant content snippet")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    url: Optional[str] = Field(None, description="OneNote page URL")


class ResponseMetadata(BaseModel):
    """Metadata about the query response."""

    techniques_used: List[str] = Field(..., description="List of RAG techniques applied")
    latency_ms: int = Field(..., ge=0, description="Response latency in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    cost_usd: Optional[float] = Field(None, description="Estimated cost in USD")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    model_name: str = Field(..., description="LLM model used")
    retrieval_k: int = Field(..., description="Number of documents retrieved")
    filter_summary: Optional[Dict[str, Any]] = Field(None, description="Context filter summary if filtering was applied")


class ImageReference(BaseModel):
    """Reference to an image associated with the query response."""

    page_id: str = Field(..., description="OneNote page ID containing the image")
    page_title: str = Field(..., description="Page title")
    image_index: int = Field(..., ge=0, description="Index of image in the page")
    image_path: str = Field(..., description="Storage path of the image")
    public_url: str = Field(..., description="Public URL or API endpoint to retrieve the image")


class QueryResponse(BaseModel):
    """Response model for RAG queries with optional multimodal content."""

    answer: str = Field(..., description="Generated answer")
    sources: List[Source] = Field(..., description="Source documents used")
    metadata: ResponseMetadata = Field(..., description="Response metadata")
    images: Optional[List[ImageReference]] = Field(default=None, description="Images related to the answer (for visual queries)")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The key points from the project meeting were...",
                "sources": [
                    {
                        "document_id": "doc-123",
                        "page_title": "Project Meeting Notes",
                        "notebook_name": "Work",
                        "section_name": "Meetings",
                        "content_snippet": "Key decisions made...",
                        "relevance_score": 0.95,
                        "url": "https://..."
                    }
                ],
                "metadata": {
                    "techniques_used": ["multi_query", "reranking"],
                    "latency_ms": 2500,
                    "tokens_used": 1500,
                    "cost_usd": 0.03,
                    "model_name": "gpt-3.5-turbo",
                    "retrieval_k": 5
                }
            }
        }


class CompareRequest(BaseModel):
    """Request model for comparing multiple configurations."""

    question: str = Field(..., min_length=1, description="User question")
    config_names: List[str] = Field(..., min_items=2, max_items=4, description="Preset config names to compare")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the main project goals?",
                "config_names": ["fast", "balanced", "quality"]
            }
        }


class CompareResponse(BaseModel):
    """Response model for configuration comparison."""

    results: List[Dict[str, Any]] = Field(..., description="Results for each configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "config_name": "fast",
                        "answer": "The answer...",
                        "sources": [],
                        "metadata": {}
                    }
                ]
            }
        }
