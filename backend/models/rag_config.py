"""RAG configuration models."""
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

# Available OpenAI models
AVAILABLE_MODELS = [
    "gpt-4o",           # Latest GPT-4 Omni
    "gpt-4o-mini",      # Cost-effective GPT-4 Omni
    "gpt-4-turbo",      # GPT-4 Turbo
    "gpt-4",            # Standard GPT-4
    "gpt-3.5-turbo",    # GPT-3.5 Turbo
]


class MultiQueryConfig(BaseModel):
    """Configuration for Multi-Query retrieval technique."""
    enabled: bool = Field(default=False, description="Enable multi-query retrieval")
    num_queries: int = Field(default=5, ge=2, le=10, description="Number of query variations to generate")


class RAGFusionConfig(BaseModel):
    """Configuration for RAG-Fusion technique."""
    enabled: bool = Field(default=False, description="Enable RAG-Fusion")
    num_queries: int = Field(default=4, ge=2, le=10, description="Number of related queries to generate")
    rrf_k: int = Field(default=60, ge=1, le=100, description="RRF constant for scoring")


class DecompositionConfig(BaseModel):
    """Configuration for Query Decomposition technique."""
    enabled: bool = Field(default=False, description="Enable query decomposition")
    mode: Literal["recursive", "individual"] = Field(default="recursive", description="Decomposition mode")
    max_sub_questions: int = Field(default=3, ge=2, le=5, description="Maximum number of sub-questions")


class StepBackConfig(BaseModel):
    """Configuration for Step-Back prompting technique."""
    enabled: bool = Field(default=False, description="Enable step-back prompting")
    include_original: bool = Field(default=True, description="Include original query in retrieval")


class HyDEConfig(BaseModel):
    """Configuration for HyDE (Hypothetical Document Embeddings) technique."""
    enabled: bool = Field(default=False, description="Enable HyDE")


class RerankingConfig(BaseModel):
    """Configuration for Re-ranking technique."""
    enabled: bool = Field(default=False, description="Enable re-ranking")
    top_k: int = Field(default=10, ge=5, le=20, description="Number of documents to retrieve before re-ranking")
    top_n: int = Field(default=3, ge=1, le=10, description="Number of documents to keep after re-ranking")


class ContextFilterConfig(BaseModel):
    """Configuration for intelligent context filtering."""
    enabled: bool = Field(default=True, description="Enable context filtering based")
    model_name: str = Field(default="gpt-4o-mini", description="LLM model for context filtering")
    strictness: Literal["lenient", "balanced", "strict"] = Field(
        default="balanced",
        description="lenient (inclusive), balanced, strict (selective)"
    )
    max_relevant_chunks: int = Field(default=10, ge=5, le=20, description="Max text chunks to keep")
    max_relevant_images: int = Field(default=5, ge=0, le=10, description="Max images to keep")
    
    
class RAGConfig(BaseModel):
    """Complete RAG configuration with all techniques."""

    # Basic settings
    chunk_size: int = Field(default=1000, ge=100, le=2000, description="Text chunk size")
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")
    retrieval_k: int = Field(default=4, ge=1, le=20, description="Number of documents to retrieve")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="LLM temperature")
    model_name: str = Field(default="gpt-4o-mini", description="LLM model name")

    # Advanced techniques
    multi_query: MultiQueryConfig = Field(default_factory=MultiQueryConfig)
    rag_fusion: RAGFusionConfig = Field(default_factory=RAGFusionConfig)
    decomposition: DecompositionConfig = Field(default_factory=DecompositionConfig)
    step_back: StepBackConfig = Field(default_factory=StepBackConfig)
    hyde: HyDEConfig = Field(default_factory=HyDEConfig)
    reranking: RerankingConfig = Field(default_factory=RerankingConfig)
    context_filter: ContextFilterConfig = Field(default_factory=ContextFilterConfig)
    
    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "retrieval_k": 4,
                "temperature": 0.0,
                "model_name": "gpt-4o-mini",
                "multi_query": {"enabled": True, "num_queries": 5},
                "rag_fusion": {"enabled": False},
                "decomposition": {"enabled": False},
                "step_back": {"enabled": False},
                "hyde": {"enabled": False},
                "reranking": {"enabled": False}
            }
        }
    }


# Preset configurations
PRESET_CONFIGS = {
    "fast": RAGConfig(
        chunk_size=1000,
        retrieval_k=3,
        temperature=0.0,
        model_name="gpt-4o-mini"
    ),
    "balanced": RAGConfig(
        chunk_size=800,
        retrieval_k=5,
        temperature=0.0,
        model_name="gpt-4o-mini",
        multi_query=MultiQueryConfig(enabled=True, num_queries=3),
        reranking=RerankingConfig(enabled=True, top_k=10, top_n=5)
    ),
    "quality": RAGConfig(
        chunk_size=500,
        retrieval_k=8,
        temperature=0.0,
        model_name="gpt-4o",
        multi_query=MultiQueryConfig(enabled=True, num_queries=5),
        rag_fusion=RAGFusionConfig(enabled=True, num_queries=4),
        step_back=StepBackConfig(enabled=True),
        reranking=RerankingConfig(enabled=True, top_k=15, top_n=5)
    ),
    "research": RAGConfig(
        chunk_size=600,
        retrieval_k=6,
        temperature=0.0,
        model_name="gpt-4o",
        decomposition=DecompositionConfig(enabled=True, mode="recursive", max_sub_questions=3),
        step_back=StepBackConfig(enabled=True),
        reranking=RerankingConfig(enabled=True, top_k=12, top_n=4)
    )
}
