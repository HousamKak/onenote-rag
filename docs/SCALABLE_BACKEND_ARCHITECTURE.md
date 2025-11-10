# Scalable Backend Architecture
## OneNote RAG Platform - Python/FastAPI Implementation

**Version:** 2.0
**Date:** January 2025
**Status:** Architecture Specification for Production Scale

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Principles](#architectural-principles)
3. [High-Level Architecture](#high-level-architecture)
4. [Layer-by-Layer Design](#layer-by-layer-design)
5. [Service Architecture](#service-architecture)
6. [Data Architecture](#data-architecture)
7. [API Architecture](#api-architecture)
8. [Authentication & Authorization](#authentication--authorization)
9. [Scalability Patterns](#scalability-patterns)
10. [Integration Architecture](#integration-architecture)
11. [Observability & Monitoring](#observability--monitoring)
12. [Deployment Architecture](#deployment-architecture)

---

## Executive Summary

This document defines a scalable, production-ready backend architecture for the OneNote RAG platform, building upon the existing Python/FastAPI foundation while addressing upcoming features and scalability requirements.

### Key Design Goals

- **Horizontal Scalability:** Support 1,000+ concurrent users
- **Modular Design:** Clean separation of concerns for maintainability
- **Multi-Source Support:** Abstract data source integration
- **Advanced RAG:** Implement cutting-edge retrieval techniques
- **Enterprise Features:** SSO, RBAC, audit logging, multi-tenancy
- **Performance:** <3s query response time (90th percentile)
- **Extensibility:** Plugin architecture for new features

### Technology Stack (Enhanced)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.110+ | High-performance async REST API |
| **Task Queue** | Celery + Redis | Background job processing |
| **Vector Database** | Qdrant / Weaviate | Scalable vector search with hybrid retrieval |
| **Primary Database** | PostgreSQL 16 | Metadata, settings, conversations, audit logs |
| **Cache Layer** | Redis 7+ | Query caching, session storage |
| **Object Storage** | MinIO / S3 | Image storage, document cache |
| **Message Broker** | RabbitMQ / Redis | Event-driven architecture |
| **LLM Gateway** | LiteLLM | Multi-provider LLM routing |
| **Search Engine** | Elasticsearch (optional) | Full-text search for metadata |
| **Authentication** | Azure AD / Auth0 | Enterprise SSO |

---

## Architectural Principles

### 1. Separation of Concerns

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
│              Controllers, Request/Response              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Service Layer (Business Logic)        │
│      RAG Engine, Query Service, Document Service       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               Repository Layer (Data Access)            │
│        VectorStoreRepo, PostgresRepo, CacheRepo        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer (External)          │
│     Databases, Vector Stores, External APIs, Storage   │
└─────────────────────────────────────────────────────────┘
```

### 2. Dependency Injection

All services use dependency injection for testability and loose coupling:

```python
# Example
class QueryService:
    def __init__(
        self,
        rag_engine: RAGEngine,
        vector_store: VectorStoreRepository,
        conversation_repo: ConversationRepository,
        cache: CacheService,
        llm_gateway: LLMGateway,
        logger: Logger
    ):
        self.rag_engine = rag_engine
        self.vector_store = vector_store
        # ...
```

### 3. Event-Driven Architecture

Asynchronous processing for long-running tasks:

```python
# Events
DocumentIndexedEvent
QueryExecutedEvent
UserActionEvent
ImageProcessedEvent
DiagramGeneratedEvent

# Handlers
@event_handler("DocumentIndexedEvent")
async def update_analytics(event):
    # Update statistics, trigger notifications
```

### 4. Plugin Architecture

Extensible system for data sources, RAG techniques, and features:

```python
# Base interface
class DataSourcePlugin(ABC):
    @abstractmethod
    async def fetch_documents(self) -> List[Document]:
        pass

    @abstractmethod
    async def get_metadata(self, doc_id: str) -> Dict:
        pass

# Implementations
class OneNotePlugin(DataSourcePlugin): ...
class SharePointPlugin(DataSourcePlugin): ...
class DatabricksPlugin(DataSourcePlugin): ...
```

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         LOAD BALANCER                            │
│                    (Nginx / AWS ALB / Azure Gateway)             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   API GATEWAY LAYER (Optional)                   │
│          Rate Limiting, Auth, Routing, API Versioning            │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION CLUSTER                   │
│              (Multiple instances with autoscaling)               │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  API Pod 1 │  │  API Pod 2 │  │  API Pod N │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└──────────────────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
┌──────────────────────────────────────────────────────────────────┐
│                    SHARED SERVICES LAYER                         │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Redis     │  │  PostgreSQL  │  │ Vector Store │           │
│  │   Cache     │  │   Database   │  │  (Qdrant)    │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  RabbitMQ   │  │    MinIO     │  │ Elasticsearch│           │
│  │  Message    │  │   Object     │  │  (Optional)  │           │
│  │   Broker    │  │   Storage    │  │              │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
└──────────────────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
┌──────────────────────────────────────────────────────────────────┐
│                    WORKER SERVICES                               │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Celery    │  │   Image    │  │  Diagram   │                │
│  │  Workers   │  │ Processing │  │ Generation │                │
│  │ (Indexing) │  │  Workers   │  │  Workers   │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└──────────────────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
┌──────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │  Azure AD  │  │   OpenAI   │  │ Microsoft  │  │Databricks │ │
│  │    SSO     │  │    API     │  │   Graph    │  │   API     │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer-by-Layer Design

### 1. API Layer

**Location:** `backend/api/`

#### Structure

```
backend/api/
├── __init__.py
├── main.py                    # FastAPI app initialization
├── dependencies.py            # Dependency injection setup
├── middleware.py              # Custom middleware
├── routes/
│   ├── __init__.py
│   ├── query.py              # Query endpoints
│   ├── documents.py          # Document management
│   ├── conversations.py      # Conversation history
│   ├── images.py             # Image operations
│   ├── diagrams.py           # Diagram generation
│   ├── auth.py               # Authentication
│   ├── admin.py              # Admin operations
│   └── webhooks.py           # Webhook endpoints
├── schemas/
│   ├── __init__.py
│   ├── query.py              # Query request/response schemas
│   ├── document.py           # Document schemas
│   ├── conversation.py       # Conversation schemas
│   ├── user.py               # User schemas
│   └── common.py             # Shared schemas
└── exceptions.py             # Custom exception handlers
```

#### Key Features

**1. API Versioning**

```python
# main.py
app = FastAPI(title="OneNote RAG API", version="2.0")

# Version 1 routes
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(query.router, tags=["Query"])
v1_router.include_router(documents.router, tags=["Documents"])

# Version 2 routes (with breaking changes)
v2_router = APIRouter(prefix="/api/v2")
v2_router.include_router(query_v2.router, tags=["Query"])

app.include_router(v1_router)
app.include_router(v2_router)
```

**2. Request Validation**

```python
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    conversation_id: Optional[str] = None
    config: Optional[RAGConfig] = None
    filters: Optional[DocumentFilters] = None
    selected_files: Optional[List[str]] = None  # NEW: Context selection

    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()
```

**3. Middleware Stack**

```python
# middleware.py

# 1. Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 2. Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response

# 3. Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    user_id = request.state.user.id if hasattr(request.state, 'user') else 'anonymous'
    if not await rate_limiter.check(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return await call_next(request)

# 4. Error handling middleware
@app.middleware("http")
async def error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request.state.request_id}
        )
```

### 2. Service Layer

**Location:** `backend/services/`

#### Enhanced Structure

```
backend/services/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── query_service.py           # Query orchestration
│   ├── conversation_service.py    # Conversation management (NEW)
│   ├── document_service.py        # Document operations
│   ├── user_service.py            # User management (NEW)
│   └── analytics_service.py       # Usage analytics (NEW)
├── rag/
│   ├── __init__.py
│   ├── rag_engine.py              # Enhanced RAG engine
│   ├── rag_techniques.py          # Advanced techniques
│   ├── hybrid_search.py           # Dense + Sparse retrieval (NEW)
│   ├── reranking.py               # Cross-encoder reranking (NEW)
│   └── query_optimizer.py         # Query optimization (NEW)
├── datasources/
│   ├── __init__.py
│   ├── base.py                    # Base data source interface
│   ├── onenote.py                 # OneNote integration
│   ├── sharepoint.py              # SharePoint integration (NEW)
│   ├── databricks.py              # Databricks integration (NEW)
│   └── file_system.py             # Local file system (NEW)
├── multimodal/
│   ├── __init__.py
│   ├── image_service.py           # Image processing (NEW)
│   ├── ocr_service.py             # OCR extraction (NEW)
│   ├── diagram_service.py         # Diagram generation (NEW)
│   └── chart_service.py           # Chart generation (NEW)
├── auth/
│   ├── __init__.py
│   ├── azure_ad.py                # Azure AD SSO (NEW)
│   ├── jwt_handler.py             # JWT token handling (NEW)
│   └── rbac.py                    # Role-based access control (NEW)
├── infrastructure/
│   ├── __init__.py
│   ├── cache_service.py           # Redis caching (ENHANCED)
│   ├── queue_service.py           # Task queue (NEW)
│   ├── storage_service.py         # Object storage (NEW)
│   └── notification_service.py    # Notifications (NEW)
└── llm/
    ├── __init__.py
    ├── llm_gateway.py             # Multi-provider gateway (NEW)
    ├── prompt_manager.py          # Prompt templates (ENHANCED)
    └── token_counter.py           # Token tracking (NEW)
```

#### Key Service Implementations

**A. Conversation Service (NEW)**

```python
# backend/services/core/conversation_service.py

from typing import List, Optional
from uuid import uuid4
from datetime import datetime

class ConversationService:
    """Manages multi-turn conversations with memory and context."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        cache: CacheService,
        llm_gateway: LLMGateway
    ):
        self.conversation_repo = conversation_repo
        self.cache = cache
        self.llm_gateway = llm_gateway

    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            id=str(uuid4()),
            user_id=user_id,
            title=title or "New Conversation",
            created_at=datetime.utcnow(),
            messages=[]
        )
        await self.conversation_repo.save(conversation)
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """Add a message to conversation."""
        message = Message(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )

        conversation = await self.conversation_repo.get(conversation_id)
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()

        await self.conversation_repo.update(conversation)

        # Invalidate cache
        await self.cache.delete(f"conversation:{conversation_id}")

        return message

    async def get_conversation_context(
        self,
        conversation_id: str,
        max_messages: int = 10,
        max_tokens: int = 4000
    ) -> List[dict]:
        """Get conversation history for LLM context."""

        # Try cache first
        cache_key = f"conversation_context:{conversation_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        conversation = await self.conversation_repo.get(conversation_id)

        # Get recent messages
        recent_messages = conversation.messages[-max_messages:]

        # Format for LLM
        context = []
        total_tokens = 0

        for msg in reversed(recent_messages):
            msg_tokens = self.llm_gateway.count_tokens(msg.content)
            if total_tokens + msg_tokens > max_tokens:
                break

            context.insert(0, {
                "role": msg.role,
                "content": msg.content
            })
            total_tokens += msg_tokens

        # Cache for 5 minutes
        await self.cache.set(cache_key, context, ttl=300)

        return context

    async def generate_title(
        self,
        conversation_id: str
    ) -> str:
        """Auto-generate conversation title from first exchange."""
        conversation = await self.conversation_repo.get(conversation_id)

        if len(conversation.messages) < 2:
            return "New Conversation"

        first_user_message = next(
            (m for m in conversation.messages if m.role == "user"),
            None
        )

        if not first_user_message:
            return "New Conversation"

        # Use LLM to generate concise title
        prompt = f"Generate a concise 3-5 word title for this question: {first_user_message.content}"
        title = await self.llm_gateway.generate(
            prompt=prompt,
            max_tokens=15,
            temperature=0.3
        )

        conversation.title = title.strip('"').strip()
        await self.conversation_repo.update(conversation)

        return conversation.title
```

**B. Image Service (NEW)**

```python
# backend/services/multimodal/image_service.py

from PIL import Image
import io
from typing import Optional, Dict, Any

class ImageService:
    """Handles image extraction, processing, and analysis."""

    def __init__(
        self,
        storage: StorageService,
        ocr: OCRService,
        vision_model: VisionModel,
        cache: CacheService
    ):
        self.storage = storage
        self.ocr = ocr
        self.vision_model = vision_model
        self.cache = cache

    async def process_image(
        self,
        image_data: bytes,
        page_id: str,
        image_id: str
    ) -> Dict[str, Any]:
        """Process image: store, OCR, generate caption."""

        # Store original image
        storage_path = f"images/{page_id}/{image_id}.png"
        await self.storage.upload(storage_path, image_data)

        # Generate thumbnail
        thumbnail = self._create_thumbnail(image_data)
        thumbnail_path = f"thumbnails/{page_id}/{image_id}_thumb.png"
        await self.storage.upload(thumbnail_path, thumbnail)

        # Extract text via OCR
        ocr_text = await self.ocr.extract_text(image_data)

        # Generate image caption
        caption = await self.vision_model.generate_caption(image_data)

        # Generate image embedding for visual search
        image_embedding = await self.vision_model.generate_embedding(image_data)

        return {
            "image_id": image_id,
            "page_id": page_id,
            "storage_path": storage_path,
            "thumbnail_path": thumbnail_path,
            "ocr_text": ocr_text,
            "caption": caption,
            "embedding": image_embedding,
            "dimensions": self._get_dimensions(image_data)
        }

    def _create_thumbnail(
        self,
        image_data: bytes,
        size: tuple = (300, 300)
    ) -> bytes:
        """Create thumbnail."""
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail(size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _get_dimensions(self, image_data: bytes) -> Dict[str, int]:
        """Get image dimensions."""
        img = Image.open(io.BytesIO(image_data))
        return {"width": img.width, "height": img.height}

    async def search_by_image(
        self,
        query_image: bytes,
        top_k: int = 10
    ) -> List[Dict]:
        """Search for similar images."""
        query_embedding = await self.vision_model.generate_embedding(query_image)

        # Search in vector store
        results = await self.vector_store.search_images(
            embedding=query_embedding,
            top_k=top_k
        )

        return results
```

**C. Diagram Service (NEW)**

```python
# backend/services/multimodal/diagram_service.py

from typing import List, Dict, Any
import mermaid
import plotly.graph_objects as go

class DiagramService:
    """Generates diagrams and charts from data."""

    def __init__(
        self,
        storage: StorageService,
        llm_gateway: LLMGateway
    ):
        self.storage = storage
        self.llm_gateway = llm_gateway

    async def generate_diagram_from_data(
        self,
        data: Dict[str, Any],
        diagram_type: str,
        title: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate diagram from structured data."""

        if diagram_type == "flowchart":
            return await self._generate_flowchart(data, title)
        elif diagram_type == "sequence":
            return await self._generate_sequence_diagram(data, title)
        elif diagram_type == "mindmap":
            return await self._generate_mindmap(data, title)
        elif diagram_type == "chart":
            return await self._generate_chart(data, title)
        else:
            raise ValueError(f"Unknown diagram type: {diagram_type}")

    async def generate_diagram_from_text(
        self,
        text: str,
        user_prompt: str
    ) -> Dict[str, str]:
        """Use LLM to convert text description to diagram."""

        # Use LLM to extract structured data and determine diagram type
        extraction_prompt = f"""
        Analyze this text and determine what type of diagram would best represent it:
        {text}

        User request: {user_prompt}

        Return JSON with:
        - diagram_type: "flowchart", "sequence", "mindmap", or "chart"
        - data: structured data for the diagram
        - title: suggested title
        """

        result = await self.llm_gateway.generate(
            prompt=extraction_prompt,
            response_format="json"
        )

        return await self.generate_diagram_from_data(
            data=result["data"],
            diagram_type=result["diagram_type"],
            title=result["title"]
        )

    async def _generate_flowchart(
        self,
        data: Dict[str, Any],
        title: Optional[str]
    ) -> Dict[str, str]:
        """Generate Mermaid flowchart."""

        mermaid_code = "graph TD\n"
        for node_id, node_data in data.items():
            label = node_data.get("label", node_id)
            mermaid_code += f"    {node_id}[{label}]\n"

            for edge in node_data.get("edges", []):
                mermaid_code += f"    {node_id} --> {edge}\n"

        # Render to PNG
        png_data = await self._render_mermaid(mermaid_code)

        # Store diagram
        diagram_id = str(uuid4())
        storage_path = f"diagrams/{diagram_id}.png"
        await self.storage.upload(storage_path, png_data)

        return {
            "diagram_id": diagram_id,
            "storage_path": storage_path,
            "mermaid_code": mermaid_code,
            "type": "flowchart"
        }

    async def _generate_chart(
        self,
        data: Dict[str, Any],
        title: Optional[str]
    ) -> Dict[str, str]:
        """Generate Plotly chart."""

        chart_type = data.get("type", "bar")

        if chart_type == "bar":
            fig = go.Figure(data=[
                go.Bar(
                    x=data["x"],
                    y=data["y"],
                    name=title or "Chart"
                )
            ])
        elif chart_type == "line":
            fig = go.Figure(data=[
                go.Scatter(
                    x=data["x"],
                    y=data["y"],
                    mode='lines+markers',
                    name=title or "Chart"
                )
            ])
        elif chart_type == "pie":
            fig = go.Figure(data=[
                go.Pie(
                    labels=data["labels"],
                    values=data["values"]
                )
            ])

        fig.update_layout(title=title or "Chart")

        # Export to PNG
        png_data = fig.to_image(format="png")

        # Store chart
        chart_id = str(uuid4())
        storage_path = f"charts/{chart_id}.png"
        await self.storage.upload(storage_path, png_data)

        return {
            "chart_id": chart_id,
            "storage_path": storage_path,
            "type": chart_type
        }
```

**D. LLM Gateway (NEW)**

```python
# backend/services/llm/llm_gateway.py

from typing import Optional, List, Dict, Any
import litellm
from litellm import completion, embedding

class LLMGateway:
    """Multi-provider LLM gateway with fallback, caching, and rate limiting."""

    def __init__(
        self,
        cache: CacheService,
        config: LLMConfig
    ):
        self.cache = cache
        self.config = config
        self.providers = config.providers  # ["openai", "anthropic", "azure"]
        self.current_provider_index = 0

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: str = "text",
        use_cache: bool = True
    ) -> str:
        """Generate completion with automatic fallback."""

        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(prompt, model, temperature)
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        model = model or self.config.default_model

        # Try providers in order with fallback
        for attempt in range(len(self.providers)):
            provider = self.providers[self.current_provider_index]

            try:
                response = await completion(
                    model=f"{provider}/{model}",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": response_format}
                )

                result = response.choices[0].message.content

                # Cache result
                if use_cache:
                    await self.cache.set(cache_key, result, ttl=3600)

                return result

            except Exception as e:
                logger.error(f"LLM provider {provider} failed: {str(e)}")

                # Try next provider
                self.current_provider_index = (self.current_provider_index + 1) % len(self.providers)

                if attempt == len(self.providers) - 1:
                    raise Exception("All LLM providers failed")

    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings with batching."""

        model = model or self.config.default_embedding_model

        # Batch requests
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = await embedding(
                model=model,
                input=batch
            )

            embeddings = [item["embedding"] for item in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text."""
        model = model or self.config.default_model
        return litellm.token_counter(model=model, text=text)
```

### 3. Repository Layer

**Location:** `backend/repositories/`

```
backend/repositories/
├── __init__.py
├── base.py                    # Base repository interface
├── vector_store_repository.py # Vector database operations
├── postgres_repository.py     # PostgreSQL operations
├── conversation_repository.py # Conversation CRUD
├── user_repository.py         # User CRUD
├── document_repository.py     # Document metadata CRUD
├── image_repository.py        # Image metadata CRUD
└── audit_repository.py        # Audit log CRUD
```

**Key Implementation:**

```python
# backend/repositories/base.py

from typing import Generic, TypeVar, Optional, List
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """Base repository interface."""

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_many(self, ids: List[str]) -> List[T]:
        """Get multiple entities."""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity."""
        pass

    @abstractmethod
    async def list(
        self,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[dict] = None
    ) -> List[T]:
        """List entities with pagination."""
        pass
```

---

## Data Architecture

### Database Schema (PostgreSQL)

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    azure_ad_oid VARCHAR(255) UNIQUE,  -- Azure AD Object ID
    role VARCHAR(50) DEFAULT 'user',    -- user, admin, viewer
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6)
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);

-- Documents metadata table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,  -- onenote, sharepoint, databricks, etc.
    source_id VARCHAR(500) NOT NULL,    -- External ID from source system
    title VARCHAR(1000),
    content_type VARCHAR(100),
    url TEXT,
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    indexed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    tags TEXT[],
    UNIQUE(source_type, source_id)
);

CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_indexed_at ON documents(indexed_at DESC);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);

-- Images table
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    storage_path VARCHAR(500) NOT NULL,
    thumbnail_path VARCHAR(500),
    ocr_text TEXT,
    caption TEXT,
    dimensions JSONB,  -- {width, height}
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_images_document_id ON images(document_id);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,  -- query, document_access, admin_action, etc.
    resource_type VARCHAR(100),
    resource_id VARCHAR(500),
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    details JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Query analytics table
CREATE TABLE query_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    query TEXT NOT NULL,
    rag_technique VARCHAR(100),
    latency_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    documents_retrieved INTEGER,
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_query_analytics_user_id ON query_analytics(user_id);
CREATE INDEX idx_query_analytics_timestamp ON query_analytics(timestamp DESC);

-- Settings table (encrypted sensitive values)
CREATE TABLE settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    is_sensitive BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Vector Store Schema (Qdrant)

```python
# Vector collections

# 1. Text chunks collection
{
    "collection_name": "document_chunks",
    "vectors": {
        "size": 1536,  # OpenAI embedding dimension
        "distance": "Cosine"
    },
    "payload_schema": {
        "document_id": "keyword",
        "chunk_index": "integer",
        "source_type": "keyword",
        "title": "text",
        "content": "text",
        "url": "keyword",
        "tags": "keyword[]",
        "created_at": "datetime",
        "modified_at": "datetime",
        "metadata": "object"
    }
}

# 2. Images collection (for visual search)
{
    "collection_name": "images",
    "vectors": {
        "size": 512,  # CLIP embedding dimension
        "distance": "Cosine"
    },
    "payload_schema": {
        "image_id": "keyword",
        "document_id": "keyword",
        "storage_path": "keyword",
        "ocr_text": "text",
        "caption": "text",
        "dimensions": "object"
    }
}

# 3. Hybrid search: Sparse vectors for BM25
{
    "collection_name": "document_chunks_sparse",
    "sparse_vectors": {
        "text": {
            "modifier": "idf"  # TF-IDF weighting
        }
    }
}
```

---

## API Architecture

### Complete API Specification

#### 1. Query & Conversation APIs

```yaml
# Query with conversation context
POST /api/v2/query
Request:
  question: string
  conversation_id?: string
  config?: RAGConfig
  filters?: DocumentFilters
  selected_files?: string[]  # NEW: Context selection
  include_images?: boolean

Response:
  answer: string
  sources: Source[]
  images: Image[]  # NEW
  suggested_diagrams: DiagramSuggestion[]  # NEW
  metadata: ResponseMetadata
  conversation_id: string

# List conversations
GET /api/v2/conversations
Query Params:
  limit: integer (default 50)
  offset: integer (default 0)

Response:
  conversations: Conversation[]
  total: integer

# Get conversation
GET /api/v2/conversations/{id}
Response:
  conversation: Conversation with full message history

# Delete conversation
DELETE /api/v2/conversations/{id}
Response:
  success: boolean
```

#### 2. Document & Image APIs

```yaml
# Search documents with filters
POST /api/v2/documents/search
Request:
  query?: string
  filters: {
    source_types?: string[]
    tags?: string[]
    date_range?: {from: date, to: date}
    selected_files?: string[]  # NEW
  }
  limit: integer

Response:
  documents: Document[]
  total: integer

# Get document with images
GET /api/v2/documents/{id}
Response:
  document: Document
  images: Image[]
  related_documents: Document[]

# Upload image
POST /api/v2/images/upload
Request: multipart/form-data
  file: binary
  document_id: string

Response:
  image: Image with OCR text and caption

# Search by image
POST /api/v2/images/search
Request: multipart/form-data
  file: binary
  top_k: integer

Response:
  results: SimilarImage[]
```

#### 3. Diagram & Chart APIs

```yaml
# Generate diagram from data
POST /api/v2/diagrams/generate
Request:
  data: object
  type: "flowchart" | "sequence" | "mindmap" | "chart"
  title?: string

Response:
  diagram_id: string
  storage_path: string
  thumbnail_path: string
  code?: string  # Mermaid code if applicable

# Generate diagram from text
POST /api/v2/diagrams/from-text
Request:
  text: string
  prompt: string

Response:
  diagram_id: string
  storage_path: string
  type: string
```

#### 4. Authentication APIs

```yaml
# SSO login
POST /api/v2/auth/login
Request:
  provider: "azure_ad" | "google" | "okta"
  code: string  # OAuth authorization code

Response:
  access_token: string (JWT)
  refresh_token: string
  user: User
  expires_in: integer

# Refresh token
POST /api/v2/auth/refresh
Request:
  refresh_token: string

Response:
  access_token: string
  expires_in: integer

# Logout
POST /api/v2/auth/logout
Response:
  success: boolean
```

#### 5. Admin APIs

```yaml
# Get system analytics
GET /api/v2/admin/analytics
Query Params:
  from: date
  to: date

Response:
  total_users: integer
  total_queries: integer
  avg_latency_ms: float
  total_cost_usd: float
  queries_by_day: ChartData[]
  top_users: UserStats[]

# Get audit logs
GET /api/v2/admin/audit-logs
Query Params:
  user_id?: string
  action?: string
  from: date
  to: date
  limit: integer

Response:
  logs: AuditLog[]
  total: integer
```

---

## Authentication & Authorization

### Azure AD SSO Integration

```python
# backend/services/auth/azure_ad.py

from msal import ConfidentialClientApplication
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class AzureADService:
    """Azure AD OAuth2 authentication."""

    def __init__(self, config: AzureADConfig):
        self.config = config
        self.msal_app = ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}"
        )

    async def authenticate(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        result = self.msal_app.acquire_token_by_authorization_code(
            code=authorization_code,
            scopes=["User.Read", "Notes.Read"],
            redirect_uri=self.config.redirect_uri
        )

        if "error" in result:
            raise HTTPException(status_code=401, detail=result["error_description"])

        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "id_token": result["id_token"],
            "expires_in": result["expires_in"]
        }

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_handler: JWTHandler = Depends()
) -> User:
    """Verify JWT and return current user."""
    token = credentials.credentials

    try:
        payload = jwt_handler.decode(token)
        user_id = payload["sub"]

        # Get user from database
        user = await user_repository.get(user_id)

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return user

    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Usage in routes
@router.post("/query")
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    # User is authenticated
    ...
```

### Role-Based Access Control (RBAC)

```python
# backend/services/auth/rbac.py

from enum import Enum
from functools import wraps

class Permission(Enum):
    QUERY = "query"
    VIEW_DOCUMENTS = "view_documents"
    EDIT_DOCUMENTS = "edit_documents"
    DELETE_DOCUMENTS = "delete_documents"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_USERS = "manage_users"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    "viewer": [Permission.QUERY, Permission.VIEW_DOCUMENTS],
    "user": [Permission.QUERY, Permission.VIEW_DOCUMENTS, Permission.EDIT_DOCUMENTS],
    "admin": [perm for perm in Permission]
}

def require_permission(permission: Permission):
    """Decorator to check user permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])

            if permission not in user_permissions and Permission.ADMIN not in user_permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator

# Usage
@router.delete("/documents/{id}")
@require_permission(Permission.DELETE_DOCUMENTS)
async def delete_document(
    id: str,
    current_user: User = Depends(get_current_user)
):
    ...
```

---

## Scalability Patterns

### 1. Horizontal Scaling

```yaml
# Docker Compose / Kubernetes deployment

services:
  # API servers (scale horizontally)
  api:
    image: onenote-rag-api:latest
    replicas: 5  # Scale based on load
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
      - QDRANT_URL=http://qdrant:6333
    resources:
      limits:
        cpu: "2"
        memory: 4G

  # Worker services (scale independently)
  celery-worker:
    image: onenote-rag-worker:latest
    replicas: 3
    command: celery -A tasks worker --concurrency=4

  # Shared services (managed separately)
  postgres:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
```

### 2. Caching Strategy

```python
# backend/services/infrastructure/cache_service.py

from typing import Optional, Any
import json
import hashlib

class CacheService:
    """Multi-level caching strategy."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_query_result(
        self,
        question: str,
        config: RAGConfig
    ) -> Optional[QueryResponse]:
        """Cache query results."""
        cache_key = self._get_query_cache_key(question, config)

        cached = await self.redis.get(cache_key)
        if cached:
            return QueryResponse.parse_raw(cached)

        return None

    async def set_query_result(
        self,
        question: str,
        config: RAGConfig,
        result: QueryResponse,
        ttl: int = 3600
    ):
        """Store query result in cache."""
        cache_key = self._get_query_cache_key(question, config)
        await self.redis.setex(
            cache_key,
            ttl,
            result.json()
        )

    def _get_query_cache_key(self, question: str, config: RAGConfig) -> str:
        """Generate cache key from question and config."""
        config_hash = hashlib.md5(
            json.dumps(config.dict(), sort_keys=True).encode()
        ).hexdigest()

        question_hash = hashlib.md5(question.lower().encode()).hexdigest()

        return f"query:{question_hash}:{config_hash}"

    async def get_document_embedding(self, document_id: str) -> Optional[List[float]]:
        """Cache document embeddings."""
        key = f"embedding:{document_id}"
        cached = await self.redis.get(key)

        if cached:
            return json.loads(cached)

        return None

    async def set_document_embedding(
        self,
        document_id: str,
        embedding: List[float],
        ttl: int = 86400  # 24 hours
    ):
        """Store document embedding."""
        key = f"embedding:{document_id}"
        await self.redis.setex(
            key,
            ttl,
            json.dumps(embedding)
        )
```

### 3. Background Job Processing

```python
# backend/tasks.py

from celery import Celery
from celery.schedules import crontab

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task(bind=True, max_retries=3)
def index_document(self, document_id: str, source_type: str):
    """Index a single document asynchronously."""
    try:
        # Fetch document from source
        document = fetch_document_from_source(document_id, source_type)

        # Process images if any
        if document.has_images:
            for image in document.images:
                process_image.delay(image.id, document_id)

        # Chunk document
        chunks = chunk_document(document)

        # Generate embeddings
        embeddings = generate_embeddings([chunk.content for chunk in chunks])

        # Store in vector database
        vector_store.add_documents(chunks, embeddings)

        # Update metadata in PostgreSQL
        update_document_metadata(document_id)

        return {"status": "success", "document_id": document_id}

    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@celery_app.task
def process_image(image_id: str, document_id: str):
    """Process image: OCR, caption, store."""
    image_service = ImageService()
    result = image_service.process_image(image_id, document_id)
    return result

@celery_app.task
def batch_index_documents(document_ids: List[str], source_type: str):
    """Index multiple documents in parallel."""
    for doc_id in document_ids:
        index_document.delay(doc_id, source_type)

# Scheduled tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Incremental sync every hour
    sender.add_periodic_task(
        crontab(minute=0, hour='*'),
        incremental_sync.s(),
        name='hourly_incremental_sync'
    )

    # Analytics aggregation daily
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        aggregate_analytics.s(),
        name='daily_analytics'
    )

@celery_app.task
def incremental_sync():
    """Sync modified documents from all sources."""
    sources = ['onenote', 'sharepoint', 'databricks']

    for source in sources:
        modified_docs = get_modified_documents(source)
        batch_index_documents.delay(modified_docs, source)
```

---

## Integration Architecture

### Data Source Plugin System

```python
# backend/services/datasources/base.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class DataSourcePlugin(ABC):
    """Base interface for all data source plugins."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Unique identifier for this data source."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """Declare plugin capabilities."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with data source."""
        pass

    @abstractmethod
    async def fetch_documents(
        self,
        filters: Optional[Dict] = None,
        modified_since: Optional[datetime] = None
    ) -> List[Document]:
        """Fetch documents from source."""
        pass

    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a single document."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Document]:
        """Search within data source (if supported)."""
        pass

# Example: Databricks plugin
class DatabricksPlugin(DataSourcePlugin):
    """Databricks data source integration."""

    @property
    def source_type(self) -> str:
        return "databricks"

    @property
    def capabilities(self) -> Dict[str, bool]:
        return {
            "supports_search": True,
            "supports_incremental_sync": True,
            "supports_realtime": False,
            "supports_images": False
        }

    def __init__(self, config: DatabricksConfig):
        self.config = config
        self.client = None

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        from databricks import sql

        self.client = sql.connect(
            server_hostname=credentials["server_hostname"],
            http_path=credentials["http_path"],
            access_token=credentials["access_token"]
        )

        return self.client is not None

    async def fetch_documents(
        self,
        filters: Optional[Dict] = None,
        modified_since: Optional[datetime] = None
    ) -> List[Document]:
        """Fetch tables/notebooks from Databricks."""

        documents = []

        # Fetch tables
        with self.client.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            for table in tables:
                # Get table schema
                cursor.execute(f"DESCRIBE TABLE {table.tableName}")
                schema = cursor.fetchall()

                # Create document
                doc = Document(
                    id=f"databricks:table:{table.tableName}",
                    source_type="databricks",
                    source_id=table.tableName,
                    title=f"Table: {table.tableName}",
                    content=self._format_table_schema(schema),
                    metadata={
                        "database": table.database,
                        "table_type": "table",
                        "schema": schema
                    }
                )
                documents.append(doc)

        # Fetch notebooks (if enabled)
        if self.config.include_notebooks:
            notebooks = await self._fetch_notebooks()
            documents.extend(notebooks)

        return documents

    def _format_table_schema(self, schema) -> str:
        """Format table schema as text for embeddings."""
        lines = [f"Column: {col.col_name}, Type: {col.data_type}, Comment: {col.comment or 'N/A'}"
                 for col in schema]
        return "\n".join(lines)
```

### Plugin Registry

```python
# backend/services/datasources/registry.py

from typing import Dict, Type
from .base import DataSourcePlugin
from .onenote import OneNotePlugin
from .sharepoint import SharePointPlugin
from .databricks import DatabricksPlugin

class DataSourceRegistry:
    """Central registry for data source plugins."""

    def __init__(self):
        self._plugins: Dict[str, Type[DataSourcePlugin]] = {}
        self._instances: Dict[str, DataSourcePlugin] = {}

    def register(self, plugin_class: Type[DataSourcePlugin]):
        """Register a new plugin."""
        plugin = plugin_class()
        self._plugins[plugin.source_type] = plugin_class

    async def initialize_plugin(
        self,
        source_type: str,
        config: Dict[str, Any]
    ) -> DataSourcePlugin:
        """Initialize and authenticate a plugin."""
        if source_type not in self._plugins:
            raise ValueError(f"Unknown data source: {source_type}")

        plugin_class = self._plugins[source_type]
        plugin = plugin_class(config)

        # Authenticate
        if not await plugin.authenticate(config.get("credentials", {})):
            raise Exception(f"Failed to authenticate {source_type}")

        self._instances[source_type] = plugin
        return plugin

    def get_plugin(self, source_type: str) -> Optional[DataSourcePlugin]:
        """Get initialized plugin instance."""
        return self._instances.get(source_type)

    def list_plugins(self) -> List[str]:
        """List all registered plugin types."""
        return list(self._plugins.keys())

# Global registry
registry = DataSourceRegistry()

# Register plugins
registry.register(OneNotePlugin)
registry.register(SharePointPlugin)
registry.register(DatabricksPlugin)
```

---

## Observability & Monitoring

### Logging Strategy

```python
# backend/core/logging.py

import structlog
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure structured logging."""

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
logger = structlog.get_logger()

logger.info(
    "query_executed",
    user_id=user.id,
    question=question,
    latency_ms=latency,
    technique="rag_fusion",
    documents_retrieved=len(sources)
)
```

### Metrics & Tracing

```python
# backend/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Prometheus metrics
query_counter = Counter(
    'rag_queries_total',
    'Total number of queries',
    ['user_id', 'rag_technique', 'status']
)

query_latency = Histogram(
    'rag_query_duration_seconds',
    'Query latency in seconds',
    ['rag_technique']
)

document_count = Gauge(
    'rag_documents_indexed',
    'Number of indexed documents',
    ['source_type']
)

# OpenTelemetry tracing
tracer = trace.get_tracer(__name__)

# Usage in services
async def query_with_metrics(request: QueryRequest):
    with tracer.start_as_current_span("rag_query") as span:
        span.set_attribute("user.id", request.user_id)
        span.set_attribute("rag.technique", request.config.technique)

        start_time = time.time()

        try:
            result = await rag_engine.query(request)

            query_counter.labels(
                user_id=request.user_id,
                rag_technique=request.config.technique,
                status="success"
            ).inc()

            return result

        except Exception as e:
            query_counter.labels(
                user_id=request.user_id,
                rag_technique=request.config.technique,
                status="error"
            ).inc()

            span.record_exception(e)
            raise

        finally:
            latency = time.time() - start_time
            query_latency.labels(
                rag_technique=request.config.technique
            ).observe(latency)
```

---

## Deployment Architecture

### Docker Compose (Development/Staging)

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ragdb
      - REDIS_URL=redis://redis:6379/0
      - QDRANT_URL=http://qdrant:6333
      - MINIO_URL=http://minio:9000
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ragdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=ragdb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant-data:/qdrant/storage

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    command: npm run dev

volumes:
  postgres-data:
  redis-data:
  qdrant-data:
  minio-data:
```

### Kubernetes (Production)

See separate Kubernetes manifests in `/k8s` directory.

---

## Summary

This scalable backend architecture provides:

1. **Modular Design**: Clean separation of concerns with layers
2. **Horizontal Scalability**: API and workers scale independently
3. **Advanced Features**: Conversations, images, diagrams, SSO, RBAC
4. **Multi-Source Support**: Plugin architecture for any data source
5. **Performance**: Caching, async processing, background jobs
6. **Observability**: Structured logging, metrics, tracing
7. **Production-Ready**: PostgreSQL, Redis, Qdrant, Docker, Kubernetes

The architecture is ready for 1,000+ concurrent users and unlimited data sources.
