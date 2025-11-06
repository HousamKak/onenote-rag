# Enterprise Multi-Source RAG Platform
## Complete Architecture & Implementation Plan

---

**Document Version:** 1.0
**Date:** January 2025
**Status:** Architecture Proposal
**Prepared For:** Enterprise Stakeholders & Technical Teams

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Codebase Analysis](#2-current-codebase-analysis)
3. [High-Level Architecture Vision](#3-high-level-architecture-vision)
4. [Cloud Infrastructure Architecture (Azure)](#4-cloud-infrastructure-architecture-azure)
5. [Backend Architecture (C# .NET 8)](#5-backend-architecture-c-net-8)
6. [Plugin System Architecture](#6-plugin-system-architecture)
7. [Frontend Architecture (React/TypeScript)](#7-frontend-architecture-reacttypescript)
8. [MCP Integration Strategy](#8-mcp-integration-strategy)
9. [Migration Strategy (Python → C#)](#9-migration-strategy-python--c)
10. [Production Enterprise Features](#10-production-enterprise-features)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment & CI/CD](#12-deployment--cicd)
13. [Technical Specifications](#13-technical-specifications)
14. [Timeline, Resources & Cost Estimates](#14-timeline-resources--cost-estimates)
15. [Appendices](#15-appendices)

---

## 1. Executive Summary

### 1.1 Vision Statement

Transform the current Python-based OneNote-specific RAG application into a **cloud-native, enterprise-grade, multi-source data integration platform** that enables organizations to leverage AI-powered semantic search across any data source—from Microsoft OneNote to SQL databases, SharePoint, Confluence, and beyond.

### 1.2 Core Value Proposition

**Problem**: Organizations have data scattered across multiple systems (OneNote, databases, document repositories, wikis). Current RAG solutions are tightly coupled to single data sources, requiring separate implementations for each system.

**Solution**: A unified platform with:
- **Plug-and-play data source adapters** (add new sources without code changes)
- **Dual integration strategies**: MCP (Model Context Protocol) for fast direct access, RAG for intelligent semantic search
- **Enterprise features**: Multi-tenancy, RBAC, audit logging, cost tracking, compliance
- **Cloud-native architecture**: Built on Azure with auto-scaling, high availability, and global distribution

### 1.3 Key Architectural Principles

1. **Source Agnostic**: Abstract interface (`IDocumentSource`) allows any data source to be plugged in
2. **Strategy Pattern**: System auto-selects MCP or RAG based on query type and source capabilities
3. **Cloud Native**: Azure PaaS services for zero infrastructure management
4. **Technology Standards**: C# .NET 8 backend, React/TypeScript frontend, Azure services
5. **Enterprise Ready**: Multi-tenant, secure, compliant, observable, cost-efficient

### 1.4 Technology Stack Overview

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + TypeScript + Vite | Modern SPA with type safety |
| **Backend** | ASP.NET Core 8 Web API | High-performance REST API |
| **Authentication** | Azure AD (Entra ID) | OAuth 2.0 + JWT tokens |
| **Database** | Azure Cosmos DB | Multi-tenant NoSQL storage |
| **Vector Store** | Azure AI Search | Semantic search with HNSW |
| **Cache** | Azure Redis Cache | Query response caching |
| **Messaging** | Azure Service Bus | Background job processing |
| **Storage** | Azure Blob Storage | Document storage |
| **AI/LLM** | Azure OpenAI Service | GPT-4 + embeddings |
| **Monitoring** | Application Insights | Distributed tracing & metrics |
| **IaC** | Terraform | Infrastructure as Code |
| **CI/CD** | GitHub Actions | Automated deployments |

### 1.5 Integration Strategy Matrix

| Data Source | MCP Support | RAG Support | Primary Strategy | Use Case |
|-------------|-------------|-------------|------------------|----------|
| **OneNote** | ✅ Yes | ✅ Yes | MCP (lookups), RAG (analysis) | Note retrieval + semantic search |
| **SQL Database** | ❌ No | ✅ Yes | RAG only | Natural language to SQL |
| **SharePoint** | ⚠️ Custom | ✅ Yes | Hybrid | Document management |
| **Confluence** | ❌ No | ✅ Yes | RAG only | Knowledge base search |
| **Blob Storage** | ❌ No | ✅ Yes | RAG only | Document archive search |
| **Custom APIs** | ⚠️ Build MCP | ✅ Yes | Depends | Flexible integration |

**Legend:**
- ✅ Native support
- ⚠️ Requires custom implementation
- ❌ Not applicable

### 1.6 Business Impact

#### Immediate Benefits
- **Time Savings**: 70% reduction in time to find information across multiple systems
- **Developer Productivity**: Add new data sources in days, not months
- **Cost Efficiency**: MCP queries cost <$0.001 vs RAG queries at $0.05-0.15
- **User Experience**: Single unified search interface for all enterprise data

#### Long-Term Strategic Value
- **Extensibility**: Plugin architecture supports unlimited data sources
- **Competitive Advantage**: First-to-market multi-source RAG platform
- **Enterprise Sales**: Multi-tenancy enables SaaS business model
- **Compliance**: Built-in audit logging, PII detection, data governance

### 1.7 Project Timeline & Resources

**Duration**: 20 weeks (5 months)

**Team Requirements**:
- 1 Backend Engineer (C#/.NET)
- 1 Frontend Engineer (React/TypeScript)
- 1 DevOps Engineer (Azure/Terraform)
- 1 QA Engineer (Testing/Automation)
- 0.5 Product Manager

**Total**: 4.5 FTEs

**Estimated Cost**:
- **Development**: $450,000 (5 months × 4.5 FTEs × $20K/month)
- **Azure Infrastructure** (first year): $13,560-36,360
- **OpenAI API** (first year): $6,000-24,000
- **Total First Year**: ~$470,000-510,000

### 1.8 Success Metrics

| Metric | Current (Python) | Target (C#/Azure) |
|--------|------------------|-------------------|
| **Query Latency (MCP)** | N/A | <500ms |
| **Query Latency (RAG)** | 3-15s | 2-10s |
| **Concurrent Users** | ~10 | 1,000+ |
| **Uptime** | 95% (single instance) | 99.9% (HA) |
| **Data Sources Supported** | 1 (OneNote) | 5+ (extensible) |
| **Time to Add New Source** | 2-4 weeks | 3-5 days |
| **Monthly Cost per User** | N/A | $5-15 |
| **Test Coverage** | 0% | 70%+ |

### 1.9 Risk Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **MCP Protocol Changes** | Medium | Low | Version pinning + adapter pattern |
| **Azure Service Outages** | High | Low | Multi-region deployment + DR plan |
| **OpenAI API Rate Limits** | Medium | Medium | Request queuing + multiple API keys |
| **Data Migration Failures** | High | Low | Comprehensive testing + rollback plan |
| **Team Knowledge Gap** | Medium | Medium | Training + external consultants |
| **Scope Creep** | Medium | High | Strict change control + MVP focus |

### 1.10 Recommendation

**Proceed with phased implementation** starting with:
1. **Phase 1** (Weeks 1-8): Core infrastructure + OneNote plugin (MCP + RAG)
2. **Phase 2** (Weeks 9-14): SQL Database plugin + Frontend rebuild
3. **Phase 3** (Weeks 15-20): Additional plugins + Enterprise features + Production launch

This approach delivers value incrementally while managing risk through iterative validation.

---

## 2. Current Codebase Analysis

### 2.1 Overview

The existing system is a **Python-based RAG application** specifically designed for querying Microsoft OneNote documents. It features a FastAPI backend with advanced RAG techniques and a React/TypeScript frontend.

**Technology Stack (Current)**:
- **Backend**: Python 3.11, FastAPI 0.109, LangChain 0.1, ChromaDB 0.4
- **Frontend**: React 18.3, TypeScript 5.9, Vite 7.1, Zustand 4.5, TanStack Query 5.17
- **AI Services**: OpenAI API (GPT-4, text-embedding-ada-002), Cohere (re-ranking)
- **Microsoft Integration**: MSAL 1.26 for Graph API authentication

### 2.2 Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  Pages: ChatPage, QueryPage, ConfigPage, IndexPage, ComparePage│
│  State: Zustand (conversations, config) + React Query (API)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (Python FastAPI)                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ OneNote      │→│ Document     │→│ Vector Store       │   │
│  │ Service      │  │ Processor    │  │ Service (ChromaDB) │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    RAG Engine                             │  │
│  │  - Basic retrieval                                        │  │
│  │  - 6 advanced techniques (Multi-Query, RAG-Fusion, etc.) │  │
│  │  - LLM generation with context assembly                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICES: Microsoft Graph API, OpenAI, Cohere        │
│  DATA STORAGE: ChromaDB (file-based), localStorage (frontend)  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Key Components

#### Backend Services

1. **OneNoteService** (`backend/services/onenote_service.py`)
   - Microsoft Graph API integration via MSAL
   - Methods: `list_notebooks()`, `list_sections()`, `list_pages()`, `get_page_content()`
   - Returns HTML content from OneNote pages
   - **Issue**: Tightly coupled to OneNote, no abstraction

2. **DocumentProcessor** (`backend/services/document_processor.py`)
   - Extracts text from OneNote HTML using BeautifulSoup
   - Chunks documents with RecursiveCharacterTextSplitter
   - Configurable chunk size (100-2000) and overlap (0-500)
   - **Issue**: HTML parsing specific to OneNote format

3. **VectorStoreService** (`backend/services/vector_store.py`)
   - ChromaDB wrapper with OpenAI embeddings
   - Similarity search with metadata filtering
   - **Issue**: Concrete implementation, no interface

4. **RAGEngine** (`backend/services/rag_engine.py`)
   - Main orchestration layer
   - Technique selection based on configuration
   - Context assembly and LLM generation
   - **Issue**: Mixed concerns, hard to extend

5. **RAGTechniques** (`backend/services/rag_techniques.py`)
   - 6 advanced techniques:
     - Multi-Query Retrieval
     - RAG-Fusion (Reciprocal Rank Fusion)
     - Query Decomposition (recursive/individual)
     - Step-Back Prompting
     - HyDE (Hypothetical Document Embeddings)
     - Re-ranking (Cohere)
   - **Strength**: Well-implemented, good documentation

#### Frontend Components

1. **ChatPage** - Main conversation interface
2. **IndexPage** - Document sync/indexing UI
3. **ConfigPage** - RAG configuration with presets
4. **Zustand Store** - Conversations, config, UI state (persisted to localStorage)
5. **React Query** - API state management with caching

### 2.4 Data Flow

**Document Indexing Flow**:
```
User clicks "Sync"
  → POST /api/index/sync
  → OneNoteService.get_all_documents()
  → DocumentProcessor.chunk_documents()
  → VectorStoreService.add_documents() (OpenAI embeddings)
  → ChromaDB persistence
```

**Query Flow**:
```
User asks question
  → POST /api/query
  → RAGEngine.query()
  → Technique selection (if-elif logic)
  → Vector search (ChromaDB)
  → Optional re-ranking (Cohere)
  → Context assembly (<20K tokens)
  → LLM generation (ChatOpenAI)
  → Response with sources
```

### 2.5 Strengths

1. **Advanced RAG Techniques**: 6 well-implemented techniques with detailed prompts
2. **Modern Frontend**: React 18 with TypeScript, good UX
3. **Configuration System**: Presets and granular control over RAG parameters
4. **Clean Service Layer**: Separation between services
5. **Conversation Management**: Persistent history with Zustand
6. **Observability**: LangSmith integration for tracing

### 2.6 Critical Limitations

#### Tight Coupling to OneNote

**Problem**: OneNote-specific code throughout the stack

**Evidence**:
- `OneNoteService` is concrete class instantiated in `main.py`
- `DocumentMetadata` has OneNote fields (`page_id`, `notebook_name`, `section_name`)
- API routes: `/api/onenote/*`
- Frontend UI text: "OneNote Sync", "OneNote notebooks"

**Impact**: Adding a new data source requires:
1. Creating new service class
2. Modifying `main.py` to initialize service
3. Adding conditional logic in routes
4. Updating `DocumentMetadata` model
5. Updating frontend types
6. Adding new API routes
7. Updating UI components

**Estimated Effort**: 2-4 weeks per new source

#### No Abstraction Layers

**Missing Interfaces**:
```python
# Does NOT exist in current code:
class IDocumentSource(Protocol):
    def get_all_documents(self) -> List[Document]: ...

class IVectorStore(Protocol):
    def similarity_search(self, query: str, k: int) -> List[Document]: ...

class IQueryStrategy(Protocol):
    def execute(self, request: QueryRequest) -> QueryResponse: ...
```

**Impact**: Can't easily:
- Swap ChromaDB for Pinecone/Weaviate
- Add Confluence/SharePoint without major refactoring
- Test with mocks (no dependency injection)
- Support multiple sources simultaneously

#### Single-User Design

**Issues**:
- No authentication system
- No user/tenant concept
- Conversations stored in browser localStorage
- No backend persistence of conversations
- Single ChromaDB collection shared by all users

**Impact**: Cannot support:
- Multi-tenancy
- User-specific data access control
- Cross-device conversation sync
- Compliance/audit requirements

#### No Tests

**Current Test Coverage**: 0%

**Risks**:
- Refactoring is dangerous
- No regression detection
- Unknown edge cases
- Integration failures not caught

#### Scalability Limitations

1. **Synchronous Indexing**: Blocks API thread (5-10+ minutes for large notebooks)
2. **File-based ChromaDB**: Can't scale horizontally
3. **In-memory Context**: Limited to ~20K tokens
4. **No Caching**: Every query hits LLM ($0.05-0.15 per query)
5. **No Rate Limiting**: Vulnerable to abuse

### 2.7 OneNote-Specific Dependencies

| Component | OneNote Dependency | Abstraction Level |
|-----------|-------------------|-------------------|
| **OneNoteService** | HIGH - Graph API calls | ❌ None |
| **DocumentMetadata** | MEDIUM - OneNote fields | ⚠️ Some |
| **API Routes** | LOW - Endpoint names | ✅ Easy to change |
| **Frontend UI** | LOW - Display text | ✅ Easy to change |
| **DocumentProcessor** | MEDIUM - HTML parsing | ⚠️ Format-specific |
| **VectorStore** | NONE - Generic | ✅ Reusable |
| **RAGEngine** | NONE - Generic | ✅ Reusable |

**Legend**: ❌ No abstraction | ⚠️ Partial abstraction | ✅ Well abstracted

### 2.8 Migration Complexity Assessment

| Component | Reusability | Migration Effort |
|-----------|-------------|------------------|
| **RAG Techniques** | 90% | Port logic to C# |
| **Configuration System** | 80% | Translate models to C# |
| **Frontend Components** | 70% | Keep React, update API calls |
| **Vector Store Logic** | 60% | Abstract interface + Azure AI Search |
| **OneNote Integration** | 0% | Rebuild with MCP + adapter pattern |
| **API Routes** | 40% | Redesign with versioning |
| **Document Processing** | 30% | Plugin-specific implementations |

**Overall Migration Complexity**: **MEDIUM-HIGH**

**Recommended Approach**: **Rebuild with strategic code reuse**, not direct port

### 2.9 Current vs. Target Architecture Comparison

| Aspect | Current (Python) | Target (C#/Azure) |
|--------|------------------|-------------------|
| **Backend Language** | Python 3.11 | C# .NET 8 |
| **Web Framework** | FastAPI | ASP.NET Core 8 |
| **Vector Database** | ChromaDB (file) | Azure AI Search (managed) |
| **Application Database** | None (localStorage) | Azure Cosmos DB |
| **Cache** | None | Azure Redis Cache |
| **Messaging** | None | Azure Service Bus |
| **Authentication** | None | Azure AD + JWT |
| **Multi-Tenancy** | No | Yes (partition keys) |
| **Data Sources** | 1 (OneNote) | 5+ (pluggable) |
| **Integration Method** | Direct API | MCP + RAG |
| **Deployment** | Single server | Multi-region HA |
| **Observability** | LangSmith only | App Insights + Monitor |
| **CI/CD** | None | GitHub Actions |
| **IaC** | None | Terraform |
| **Testing** | 0% coverage | 70%+ coverage |

### 2.10 Key Takeaways

1. **Solid Foundation**: RAG engine and techniques are well-implemented
2. **Major Refactor Needed**: Abstraction layers must be added for extensibility
3. **Platform Shift**: Moving to C#/Azure requires full rebuild, not port
4. **Strategic Reuse**: Reuse RAG logic patterns, configuration concepts, and frontend components
5. **Biggest Challenge**: Designing flexible plugin architecture that OneNote currently lacks

**Recommendation**: Treat this as a **greenfield project with reference implementation** rather than a migration.

---

## 3. High-Level Architecture Vision

### 3.1 Architectural Overview

The target architecture follows a **three-tier, cloud-native design** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION TIER                                 │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │          React SPA (Azure Static Web Apps + CDN)                 │   │
│  │  - Multi-source selector UI                                      │   │
│  │  - Query mode toggle (MCP/RAG/Auto)                             │   │
│  │  - Real-time notifications (SignalR)                            │   │
│  │  - Conversation history & management                            │   │
│  │  - Admin dashboard (cost, analytics, audit logs)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                            ↓ HTTPS + JWT Tokens
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION TIER                                  │
│                  ASP.NET Core 8 (Azure App Service)                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    API GATEWAY LAYER                            │    │
│  │  Auth Middleware → Rate Limiter → Router → CORS                │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                  ORCHESTRATION LAYER                            │    │
│  │                                                                 │    │
│  │  ┌──────────────────┐         ┌──────────────────┐            │    │
│  │  │ Query            │────────→│ Strategy         │            │    │
│  │  │ Orchestrator     │         │ Selector         │            │    │
│  │  └──────────────────┘         └──────────────────┘            │    │
│  │           │                              │                      │    │
│  │           │         Decision: MCP or RAG?                      │    │
│  │           ↓                              ↓                      │    │
│  │  ┌─────────────────┐          ┌──────────────────┐           │    │
│  │  │ MCP Strategy    │          │ RAG Strategy     │           │    │
│  │  │ (Fast, Direct)  │          │ (Smart, Semantic)│           │    │
│  │  └─────────────────┘          └──────────────────┘           │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │              SOURCE ADAPTER LAYER (PLUGINS)                     │    │
│  │                                                                 │    │
│  │  [OneNote]  [SQL DB]  [SharePoint]  [Confluence]  [Blob]      │    │
│  │     │          │           │             │           │         │    │
│  │     └──────────┴───────────┴─────────────┴───────────┘         │    │
│  │                 All implement IDocumentSource                   │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                   BUSINESS SERVICES                             │    │
│  │                                                                 │    │
│  │  [RAG Engine] [MCP Client] [Embedding Service]                 │    │
│  │  [Cost Tracker] [Tenant Manager] [Conversation Manager]        │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                            ↓ Multiple connections
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA TIER                                      │
│                     Azure PaaS Services                                  │
│                                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Cosmos DB    │  │ AI Search     │  │ Redis Cache  │  │ Blob     │ │
│  │ (NoSQL)      │  │ (Vectors)     │  │ (Memory)     │  │ Storage  │ │
│  │              │  │               │  │              │  │          │ │
│  │ • Users      │  │ • Embeddings  │  │ • Sessions   │  │ • Docs   │ │
│  │ • Tenants    │  │ • Metadata    │  │ • Query      │  │ • Cache  │ │
│  │ • Convos     │  │ • Indexes     │  │   cache      │  │ • Assets │ │
│  │ • Audit logs │  │ (per tenant)  │  │ • Dist locks │  │          │ │
│  └──────────────┘  └───────────────┘  └──────────────┘  └──────────┘ │
│                                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Service Bus  │  │ Key Vault     │  │ App Insights │  │ Event    │ │
│  │ (Messaging)  │  │ (Secrets)     │  │ (Monitoring) │  │ Grid     │ │
│  └──────────────┘  └───────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                            ↓ External APIs
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                     │
│  [Azure OpenAI] [Microsoft Graph] [MCP Servers] [Cohere]               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Core Design Patterns

#### 3.2.1 Strategy Pattern (MCP vs RAG)

```csharp
// The system decides which strategy to use per query
public interface IQueryStrategy
{
    Task<QueryResponse> ExecuteAsync(QueryRequest request, CancellationToken ct);
    bool CanHandle(QueryRequest request, SourceCapabilities capabilities);
}

// Three concrete strategies:
1. McpQueryStrategy      → Fast, direct data access (< 500ms)
2. RagQueryStrategy      → Semantic search + LLM (2-10s)
3. HybridQueryStrategy   → Combine both approaches
```

**Decision Logic**:
```
IF user explicitly requested mode:
    USE requested mode
ELSE IF query is simple lookup ("show me X", "get document Y"):
    USE MCP (fast path)
ELSE IF query requires semantic understanding:
    USE RAG (intelligent path)
ELSE IF source supports both:
    USE Hybrid (best of both)
```

#### 3.2.2 Plugin Architecture (Adapter Pattern)

```csharp
// Every data source implements this interface
public interface IDocumentSource
{
    string SourceType { get; }
    SourceCapabilities Capabilities { get; }

    Task InitializeAsync(SourceConfiguration config);
    Task<IEnumerable<Document>> GetAllDocumentsAsync(FetchOptions options);
    Task<McpResponse> ExecuteMcpQueryAsync(McpRequest request);
}

// Plugin discovery via reflection
DocumentSourceFactory discovers all IDocumentSource implementations
    → Registers in DI container
    → Exposes via API: GET /api/v1/sources
```

#### 3.2.3 Multi-Tenancy Pattern

```
Tenant Isolation Strategy: Logical separation with physical partitioning

┌─────────────────────────────────────────────────────────────┐
│                    Single Application Instance               │
│                                                              │
│  Tenant A Request                  Tenant B Request          │
│       ↓                                  ↓                   │
│  [Auth Middleware: Extract tenant_id from JWT]              │
│       ↓                                  ↓                   │
│  tenant_id="A"                     tenant_id="B"            │
│       ↓                                  ↓                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Cosmos DB (Partitioned by tenant_id)       │   │
│  │  Partition A: {...}          Partition B: {...}      │   │
│  └──────────────────────────────────────────────────────┘   │
│       ↓                                  ↓                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        Azure AI Search (Separate indexes)            │   │
│  │  Index: tenant-A-*           Index: tenant-B-*       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow Diagrams

#### 3.3.1 Document Indexing Flow (RAG Preparation)

```
┌──────────┐
│ Admin UI │ "Index OneNote"
└────┬─────┘
     │ POST /api/v1/sources/onenote/index
     ↓
┌─────────────────┐
│ IndexController │ Validate request + tenant
└────┬────────────┘
     │ Queue indexing job
     ↓
┌──────────────────┐
│ Service Bus      │ Queue: indexing-jobs
│ (Message Queue)  │ Message: { tenantId, sourceType, options }
└────┬─────────────┘
     │ Worker picks up message
     ↓
┌──────────────────────┐
│ Background Worker    │
│ (Azure Function or   │
│  App Service Worker) │
└────┬─────────────────┘
     │ 1. Get plugin
     ↓
┌──────────────────────┐
│ DocumentSourceFactory│ factory.Create("onenote")
└────┬─────────────────┘
     │ 2. Returns OneNoteAdapter
     ↓
┌──────────────────────┐
│ OneNoteAdapter       │
│ (MCP or Graph API)   │
└────┬─────────────────┘
     │ 3. Fetch documents
     │    list_notebooks() → list_pages() → get_content()
     ↓
[Document 1, Document 2, ..., Document N]
     │
     │ 4. Process documents
     ↓
┌──────────────────────┐
│ DocumentProcessor    │ Chunk, extract metadata
└────┬─────────────────┘
     │ 5. Generate embeddings
     ↓
┌──────────────────────┐
│ EmbeddingService     │ Azure OpenAI text-embedding-3-large
│ (Azure OpenAI)       │ Batch process (up to 2048 docs/request)
└────┬─────────────────┘
     │ 6. Store vectors
     ↓
┌──────────────────────┐
│ Azure AI Search      │ Index: tenant-{id}-onenote-202501
│ (Vector Store)       │ HNSW algorithm, metadata filters
└────┬─────────────────┘
     │ 7. Update stats
     ↓
┌──────────────────────┐
│ Cosmos DB            │ Collection: IndexingJobs
│                      │ Status: completed, docs: 1234
└──────────────────────┘
     │ 8. Notify user (SignalR)
     ↓
┌──────────────────────┐
│ Frontend             │ "Indexing complete: 1234 documents"
└──────────────────────┘
```

#### 3.3.2 Query Flow (MCP Path)

```
User asks: "Show me the document titled 'Q1 Planning'"

┌──────────┐
│ Frontend │ POST /api/v1/query
└────┬─────┘    { query: "...", sourceType: "onenote", mode: "auto" }
     │
     ↓
┌─────────────────────┐
│ QueryController     │ [Authorize] + Rate limit check
└────┬────────────────┘
     │ Extract user/tenant from JWT
     ↓
┌─────────────────────┐
│ QueryOrchestrator   │ Main orchestration service
└────┬────────────────┘
     │ 1. Get source plugin
     ↓
┌─────────────────────┐
│ DocumentSourceFactory│ factory.Create("onenote")
└────┬────────────────┘
     │ 2. Returns OneNoteAdapter
     ↓
┌─────────────────────┐
│ StrategySelector    │ Analyze query intent
└────┬────────────────┘
     │ Decision: Simple lookup → MCP
     │ (Keywords: "show me", "titled")
     ↓
┌─────────────────────┐
│ McpQueryStrategy    │ Execute via MCP
└────┬────────────────┘
     │ 3. Get MCP client from pool
     ↓
┌─────────────────────┐
│ McpConnectionPool   │ Acquire connection to OneNote MCP server
└────┬────────────────┘
     │ 4. Send MCP request
     ↓
┌─────────────────────┐
│ MCP Server (Node.js)│ Azure OneNote MCP Server
│ Running as Process  │ (MCP Server Component)
└────┬────────────────┘
     │ 5. Call Microsoft Graph API
     ↓
┌─────────────────────┐
│ Microsoft Graph API │ Search pages by title
└────┬────────────────┘
     │ 6. Return page content (HTML)
     ↓
[Page Content: HTML of "Q1 Planning" document]
     │
     │ 7. Format response
     ↓
┌─────────────────────┐
│ QueryResponse       │ { answer: "...", sources: [...],
│                     │   metadata: { mode: "mcp", latency: 245ms } }
└────┬────────────────┘
     │ 8. Log query for audit
     ↓
┌─────────────────────┐
│ Cosmos DB           │ Collection: QueryLogs
│                     │ { userId, query, mode, cost: $0.0001 }
└────┬────────────────┘
     │ 9. Track cost
     ↓
┌─────────────────────┐
│ CostTracker         │ Update tenant monthly spend
└────┬────────────────┘
     │ 10. Cache response (optional)
     ↓
┌─────────────────────┐
│ Redis Cache         │ Key: hash(query+tenant), TTL: 15min
└────┬────────────────┘
     │ 11. Return to frontend
     ↓
┌─────────────────────┐
│ Frontend            │ Display answer + source link
└─────────────────────┘

Total latency: ~300-500ms
Cost: ~$0.0001 (minimal, mostly API calls)
```

#### 3.3.3 Query Flow (RAG Path)

```
User asks: "Summarize all our Q1 planning discussions and key decisions"

┌──────────┐
│ Frontend │ POST /api/v1/query
└────┬─────┘    { query: "...", sourceType: "onenote", mode: "auto" }
     │
     ↓
┌─────────────────────┐
│ QueryController     │ [Authorize] + Rate limit check
└────┬────────────────┘
     │
     ↓
┌─────────────────────┐
│ QueryOrchestrator   │
└────┬────────────────┘
     │ 1. Get source plugin
     ↓
┌─────────────────────┐
│ StrategySelector    │ Analyze query intent
└────┬────────────────┘
     │ Decision: Complex summarization → RAG
     │ (Keywords: "summarize", "all", requires synthesis)
     ↓
┌─────────────────────┐
│ RagQueryStrategy    │ Execute semantic search + LLM
└────┬────────────────┘
     │ 2. Generate query embedding
     ↓
┌─────────────────────┐
│ EmbeddingService    │ Azure OpenAI: text-embedding-3-large
│                     │ Input: query text → Output: [1536-dim vector]
└────┬────────────────┘
     │ Cost: ~$0.0001
     │ 3. Vector search
     ↓
┌─────────────────────┐
│ Azure AI Search     │ Vector similarity search
│                     │ Index: tenant-123-onenote-202501
│                     │ Query: embedding vector
│                     │ Filters: metadata (date range, tags)
│                     │ Top K: 10 documents
└────┬────────────────┘
     │ Returns: [Doc1, Doc2, ..., Doc10] with scores
     │ Cost: ~$0.001
     │
     │ 4. (Optional) Apply RAG technique
     ↓
┌─────────────────────┐
│ RAG Techniques      │ IF config.multiQuery.enabled:
│                     │   - Generate 5 query variations
│                     │   - Search with each
│                     │   - Union results (unique)
└────┬────────────────┘
     │ Cost: +$0.005 (5 LLM calls)
     │
     │ 5. (Optional) Re-rank
     ↓
┌─────────────────────┐
│ Cohere Rerank API   │ IF config.reranking.enabled:
│                     │   - Input: query + 10 docs
│                     │   - Output: Top 5 best matches
└────┬────────────────┘
     │ Cost: ~$0.002
     │ 6. Assemble context
     ↓
┌─────────────────────┐
│ Context Builder     │ Combine doc snippets
│                     │ Format with sources
│                     │ Limit to max tokens (8K)
└────┬────────────────┘
     │ Context: "Document 1: ...\\nDocument 2: ...\\n..."
     │
     │ 7. Generate answer
     ↓
┌─────────────────────┐
│ Azure OpenAI        │ Model: gpt-4o
│ (LLM Service)       │ System: "You are a helpful assistant..."
│                     │ Context: [assembled context]
│                     │ User query: [original question]
└────┬────────────────┘
     │ Response: "Based on Q1 planning docs, key decisions..."
     │ Cost: ~$0.08 (prompt: 4K tokens, completion: 500 tokens)
     │
     │ 8. Format response
     ↓
┌─────────────────────┐
│ QueryResponse       │ {
│                     │   answer: "...",
│                     │   sources: [5 docs with metadata],
│                     │   metadata: {
│                     │     mode: "rag",
│                     │     techniques: ["multi-query", "reranking"],
│                     │     latency: 6234ms,
│                     │     tokens: { prompt: 4123, completion: 456 },
│                     │     cost: 0.088
│                     │   }
│                     │ }
└────┬────────────────┘
     │ 9. Log & track
     ↓
[Cosmos DB: QueryLogs] + [CostTracker] + [Redis Cache]
     │
     ↓
┌─────────────────────┐
│ Frontend            │ Display answer with source citations
└─────────────────────┘

Total latency: ~5-10s
Total cost: ~$0.10 per query
```

### 3.4 Key Architectural Decisions

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| **Backend Language** | Python (current) | C# .NET 8 | **C#** | Better Azure integration, strong typing, enterprise maturity |
| **Vector Database** | ChromaDB (current) | Azure AI Search | **Azure AI Search** | Managed, scalable, hybrid search, no ops overhead |
| **Application DB** | PostgreSQL | Cosmos DB | **Cosmos DB** | Global distribution, serverless, easy partitioning |
| **Cache** | In-memory | Redis | **Redis** | Distributed, persistent, pub/sub for real-time |
| **MCP Protocol** | HTTP-based | STDIO | **STDIO** | MCP specification standard, process isolation |
| **Multi-Tenancy** | Separate DBs | Logical partitioning | **Logical** | Cost-effective, easier management |
| **Frontend Hosting** | Azure App Service | Static Web Apps | **Static Web Apps** | Lower cost, global CDN, automatic SSL |
| **CI/CD** | Azure DevOps | GitHub Actions | **GitHub Actions** | Free for public repos, easier for open source |

### 3.5 Scalability Architecture

```
                    ┌─────────────────┐
                    │ Azure Traffic   │ Global load balancer
                    │ Manager         │ Priority routing
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼────────┐         ┌─────────▼────────┐
    │ Region: East US  │         │ Region: West EU  │
    │ (Primary)        │         │ (Secondary/DR)   │
    │                  │         │                  │
    │ ┌──────────────┐ │         │ ┌──────────────┐ │
    │ │ App Service  │ │         │ │ App Service  │ │
    │ │ (2 instances)│ │         │ │ (1 instance) │ │
    │ └──────────────┘ │         │ └──────────────┘ │
    │                  │         │                  │
    │ ┌──────────────┐ │         │ ┌──────────────┐ │
    │ │ Redis Cache  │◄├─────────┤►│ Redis Cache  │ │
    │ │ (Replicated) │ │         │ │ (Replicated) │ │
    │ └──────────────┘ │         │ └──────────────┘ │
    └──────────────────┘         └──────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────▼────────┐
                    │ Cosmos DB       │
                    │ (Multi-region)  │
                    │ - Read: Both    │
                    │ - Write: Both   │
                    └─────────────────┘
```

**Scaling Strategies**:
1. **Horizontal**: App Service scales 1→10 instances based on CPU/memory
2. **Vertical**: Move to Premium v3 tier for more powerful instances
3. **Geographic**: Add regions for latency reduction
4. **Database**: Cosmos DB auto-scales RU/s (Request Units)
5. **Cache**: Redis cluster mode for > 1M keys
6. **Queue**: Service Bus partitioning for high throughput

### 3.6 Security Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Security Layers                       │
└──────────────────────────────────────────────────────────┘

Layer 1: Network Security
┌─────────────────────────────────────────────────────────┐
│ • Azure Front Door (WAF)                                │
│ • DDoS Protection Standard                              │
│ • Virtual Network + NSG rules                           │
│ • Private endpoints for PaaS services                   │
└─────────────────────────────────────────────────────────┘

Layer 2: Identity & Access
┌─────────────────────────────────────────────────────────┐
│ • Azure AD authentication (OAuth 2.0 + OpenID Connect)  │
│ • JWT tokens (15-min expiry, refresh tokens)           │
│ • Role-based access control (Admin, TenantAdmin, User) │
│ • Managed identities for service-to-service            │
└─────────────────────────────────────────────────────────┘

Layer 3: Application Security
┌─────────────────────────────────────────────────────────┐
│ • Input validation (FluentValidation)                   │
│ • Output encoding (prevent XSS)                         │
│ • Parameterized queries (prevent SQL injection)        │
│ • Rate limiting (100 req/min per user)                 │
│ • CORS whitelist                                        │
└─────────────────────────────────────────────────────────┘

Layer 4: Data Security
┌─────────────────────────────────────────────────────────┐
│ • Encryption in transit (TLS 1.3 only)                  │
│ • Encryption at rest (Azure-managed keys)              │
│ • PII detection & redaction                            │
│ • Data isolation (tenant partitioning)                 │
│ • Backup encryption                                     │
└─────────────────────────────────────────────────────────┘

Layer 5: Secrets Management
┌─────────────────────────────────────────────────────────┐
│ • Azure Key Vault for all secrets                      │
│ • Automatic rotation (90-day cycle)                    │
│ • No secrets in code/config files                      │
│ • Audit logging of secret access                       │
└─────────────────────────────────────────────────────────┘

Layer 6: Monitoring & Compliance
┌─────────────────────────────────────────────────────────┐
│ • Azure Security Center (threat detection)             │
│ • Application Insights (anomaly detection)             │
│ • Audit logs (7-year retention)                        │
│ • Compliance: GDPR, SOC 2, HIPAA-ready                │
└─────────────────────────────────────────────────────────┘
```

### 3.7 Disaster Recovery & Business Continuity

**RPO/RTO Targets**:
- **Recovery Point Objective (RPO)**: 15 minutes (max data loss)
- **Recovery Time Objective (RTO)**: 1 hour (max downtime)

**DR Strategy**:
```
Normal Operation:
  Primary Region (East US) → 100% traffic
  Secondary Region (West EU) → Standby (warm)

Disaster Scenario:
  Primary fails → Traffic Manager detects (30s)
    → Redirect to Secondary (automated)
    → Secondary becomes Primary (5 min to scale up)
    → Total downtime: ~6-10 minutes

Data Consistency:
  Cosmos DB: Multi-region writes (eventual consistency)
  AI Search: Daily snapshots to Blob Storage
  Redis: AOF persistence + replication
```

---

## 4. Cloud Infrastructure Architecture (Azure)

### 4.1 Azure Service Selection & Rationale

#### 4.1.1 Compute Services

**Azure App Service (Backend API)**
- **SKU**: P2v3 (Premium v3)
  - 2 vCPUs, 8 GB RAM per instance
  - Minimum 2 instances for HA
  - Auto-scale to 10 instances max
- **Features**:
  - Built-in load balancing
  - Automatic OS patching
  - Deployment slots (dev, staging, prod)
  - Easy rollback
- **Cost**: ~$336/month (2 × P2v3)

**Azure Static Web Apps (Frontend)**
- **SKU**: Standard
- **Features**:
  - Global CDN (Microsoft's edge network)
  - Automatic HTTPS with custom domains
  - Built-in authentication providers
  - GitHub Actions integration
  - API support via Azure Functions
- **Cost**: $9/month (Standard tier)

**Azure Functions (Background Processing - Optional)**
- **Plan**: Consumption
- **Use Cases**:
  - Document indexing jobs
  - Scheduled cleanup tasks
  - Webhook handlers
- **Cost**: Pay-per-execution (~$20-50/month estimated)

#### 4.1.2 Data Services

**Azure Cosmos DB (Application Database)**
- **API**: Core (SQL)
- **Capacity Mode**: Serverless (for <100K RU/s) or Provisioned
- **Consistency**: Session (default)
- **Features**:
  - Automatic indexing
  - Multi-region replication
  - Partition key: `tenantId`
  - TTL support for temporary data
- **Collections**:
  - `users` - User profiles
  - `tenants` - Tenant configuration
  - `conversations` - Chat history
  - `queryLogs` - Audit logs
  - `indexingJobs` - Job status
  - `costs` - Cost tracking
- **Cost**: $100-500/month (serverless, usage-dependent)

**Azure AI Search (Vector Store)**
- **SKU**: Basic (dev/staging) → Standard S1 (production)
- **Features**:
  - Vector search with HNSW algorithm
  - Hybrid search (keyword + semantic)
  - Metadata filtering
  - Skillsets for document processing
  - Built-in analyzers (text, language)
- **Index Strategy**:
  - One index per tenant per source per month
  - Format: `tenant-{id}-{source}-{yyyyMM}`
  - Example: `tenant-abc123-onenote-202501`
- **Replicas**: 1 (Basic) → 3 (Standard, for HA)
- **Partitions**: 1 (Basic) → 3 (Standard, for scale)
- **Cost**: $75/month (Basic) → $250/month (Standard S1)

**Azure Blob Storage (Document & Asset Storage)**
- **Tiers**:
  - Hot: Active documents, cache files
  - Cool: Archived documents (>30 days old)
  - Archive: Long-term retention (>90 days)
- **Containers**:
  - `documents` - Original documents
  - `cache` - Temporary processing files
  - `backups` - Index snapshots
  - `assets` - Frontend assets (handled by Static Web Apps)
- **Features**:
  - Lifecycle management (auto-tier)
  - Soft delete (7-day retention)
  - Encryption at rest
- **Cost**: ~$20/month (100 GB Hot, 500 GB Cool)

**Azure Cache for Redis (Distributed Cache)**
- **SKU**: C1 Standard (dev) → C3 Standard (prod)
- **Features**:
  - In-memory cache (query responses)
  - Session state storage
  - Distributed locks
  - Pub/Sub for real-time updates
  - AOF persistence
  - Geo-replication
- **Cache Strategy**:
  - Query responses: 15-min TTL
  - User sessions: 24-hour TTL
  - Configuration: 1-hour TTL
- **Cost**: $40/month (C1) → $150/month (C3)

#### 4.1.3 Integration Services

**Azure Service Bus (Message Queue)**
- **SKU**: Standard (dev) → Premium (prod)
- **Queues**:
  - `indexing-jobs` - Document indexing tasks
  - `notifications` - User notifications
  - `webhooks` - External event processing
- **Topics** (Pub/Sub):
  - `indexing-events` - Index completion events
  - `query-events` - Query analytics
- **Features**:
  - Dead letter queue
  - Message deduplication
  - Sessions for ordered processing
  - Scheduled messages
- **Cost**: $10/month (Standard) → $677/month (Premium)

**Azure Event Grid (Event-Driven Architecture)**
- **Use Cases**:
  - Blob upload events → trigger indexing
  - Cosmos DB change feed → real-time updates
  - Custom application events
- **Cost**: $0.60 per million operations (~$5/month)

#### 4.1.4 Security & Identity

**Azure Active Directory (Entra ID)**
- **SKU**: Free (included with Azure subscription)
- **Features**:
  - User authentication (OAuth 2.0)
  - App registrations (API permissions)
  - Service principals
  - Conditional access (Premium P1)
  - MFA enforcement
- **App Registrations**:
  1. `rag-platform-api` - Backend API
  2. `rag-platform-spa` - Frontend SPA
  3. `rag-platform-mcp-{source}` - Per-source MCP servers
- **Cost**: Free (basic), $6/user/month (Premium P1)

**Azure Key Vault (Secrets Management)**
- **SKU**: Standard
- **Secrets Stored**:
  - OpenAI API keys
  - Cohere API key
  - Microsoft Graph client secrets
  - Cosmos DB connection strings
  - Redis connection strings
  - Service Bus connection strings
- **Features**:
  - RBAC for secret access
  - Audit logging
  - Automatic rotation (via Logic Apps)
  - Soft delete (90-day retention)
- **Cost**: $0.03 per 10K operations (~$10/month)

#### 4.1.5 Monitoring & Observability

**Azure Application Insights (APM)**
- **Features**:
  - Distributed tracing (OpenTelemetry)
  - Performance metrics
  - Exception tracking
  - Live metrics stream
  - Custom events and metrics
  - Log analytics (Kusto queries)
- **Instrumentation**:
  - ASP.NET Core auto-instrumentation
  - Custom spans for RAG operations
  - Cost tracking per query
- **Retention**: 90 days (default) → 730 days (extended)
- **Cost**: $2.30/GB ingested (~$50/month estimated)

**Azure Monitor (Infrastructure Monitoring)**
- **Features**:
  - Metrics for all Azure resources
  - Alerts and action groups
  - Dashboards
  - Workbooks for custom reports
- **Alerts Configured**:
  - CPU > 80% for 5 min → Scale up
  - Memory > 85% for 5 min → Scale up
  - Error rate > 5% → Email + SMS
  - Monthly cost > $2,500 → Email
- **Cost**: Included with Azure services

**Azure Log Analytics (Centralized Logging)**
- **Workspace**: Centralized for all resources
- **Log Sources**:
  - Application logs (API, Functions)
  - Azure resource logs (Cosmos, Redis, etc.)
  - Security logs (Key Vault access)
  - Audit logs (custom)
- **Retention**: 30 days (default) → 90 days (extended)
- **Cost**: $2.76/GB ingested (~$30/month)

### 4.2 Infrastructure as Code (Terraform)

**Directory Structure**:
```
terraform/
├── modules/
│   ├── app-service/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── static-web-app/
│   ├── cosmos-db/
│   ├── ai-search/
│   ├── storage/
│   ├── redis/
│   ├── service-bus/
│   ├── key-vault/
│   ├── application-insights/
│   └── monitoring/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   └── production/
├── main.tf
├── variables.tf
├── outputs.tf
└── providers.tf
```

**Sample Terraform Code** (App Service Module):

```hcl
# terraform/modules/app-service/main.tf
resource "azurerm_service_plan" "main" {
  name                = "${var.project_name}-${var.environment}-asp"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Windows"
  sku_name            = var.sku_name

  tags = var.tags
}

resource "azurerm_windows_web_app" "api" {
  name                = "${var.project_name}-api-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    always_on        = true
    http2_enabled    = true
    minimum_tls_version = "1.3"

    application_stack {
      current_stack  = "dotnet"
      dotnet_version = "v8.0"
    }

    cors {
      allowed_origins     = var.cors_allowed_origins
      support_credentials = true
    }

    ip_restriction {
      action      = "Allow"
      priority    = 100
      service_tag = "AzureFrontDoor.Backend"
      name        = "AllowFrontDoor"
    }
  }

  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string

    # Azure AD
    "AzureAd__TenantId"    = var.azure_ad_tenant_id
    "AzureAd__ClientId"    = var.azure_ad_client_id
    "AzureAd__Audience"    = var.azure_ad_audience

    # Cosmos DB
    "CosmosDb__Endpoint"   = var.cosmos_endpoint
    "CosmosDb__DatabaseId" = var.cosmos_database_id

    # Azure AI Search
    "AzureAiSearch__Endpoint" = var.search_endpoint

    # Redis
    "Redis__ConnectionString" = "@Microsoft.KeyVault(SecretUri=${var.redis_secret_uri})"

    # Azure OpenAI
    "AzureOpenAI__Endpoint" = var.openai_endpoint
    "AzureOpenAI__ApiKey"   = "@Microsoft.KeyVault(SecretUri=${var.openai_key_uri})"

    # Service Bus
    "ServiceBus__ConnectionString" = "@Microsoft.KeyVault(SecretUri=${var.servicebus_secret_uri})"

    # Application Settings
    "Environment"    = var.environment
    "LogLevel"       = var.log_level
    "EnableSwagger"  = var.enable_swagger
  }

  identity {
    type = "SystemAssigned"
  }

  logs {
    application_logs {
      file_system_level = "Information"
    }

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  tags = var.tags
}

# Auto-scaling rule
resource "azurerm_monitor_autoscale_setting" "api" {
  name                = "${var.project_name}-api-${var.environment}-autoscale"
  location            = var.location
  resource_group_name = var.resource_group_name
  target_resource_id  = azurerm_service_plan.main.id

  profile {
    name = "DefaultProfile"

    capacity {
      default = var.autoscale_min_instances
      minimum = var.autoscale_min_instances
      maximum = var.autoscale_max_instances
    }

    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    rule {
      metric_trigger {
        metric_name        = "CpuPercentage"
        metric_resource_id = azurerm_service_plan.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT10M"
      }
    }
  }

  tags = var.tags
}
```

### 4.3 Network Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Azure Front Door                           │
│  - WAF (Web Application Firewall)                            │
│  - DDoS Protection                                           │
│  - Global load balancing                                     │
│  - SSL termination                                           │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌───────▼────────┐
│ Static Web App │       │ App Service    │
│ (Frontend)     │       │ (Backend API)  │
│ - Public       │       │ - Restricted   │
└────────────────┘       └────────┬───────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │    Virtual Network         │
                    │    10.0.0.0/16             │
                    │                            │
                    │  ┌──────────────────────┐  │
                    │  │  Subnet: Backend     │  │
                    │  │  10.0.1.0/24         │  │
                    │  │  - App Service       │  │
                    │  │  - Private Endpoints │  │
                    │  └──────────────────────┘  │
                    │                            │
                    │  ┌──────────────────────┐  │
                    │  │  Subnet: Data        │  │
                    │  │  10.0.2.0/24         │  │
                    │  │  - Cosmos DB PE      │  │
                    │  │  - Redis PE          │  │
                    │  │  - Storage PE        │  │
                    │  └──────────────────────┘  │
                    └────────────────────────────┘
```

**Security Rules**:
1. Frontend → Backend: HTTPS only (443)
2. Backend → Cosmos DB: Private endpoint
3. Backend → Redis: Private endpoint
4. Backend → Storage: Private endpoint
5. Outbound: Azure OpenAI, Microsoft Graph (public)

### 4.4 High Availability & Disaster Recovery

**Multi-Region Deployment**:

| Resource | Primary (East US) | Secondary (West EU) | Sync Method |
|----------|-------------------|---------------------|-------------|
| **App Service** | Active (2 instances) | Standby (1 instance) | Traffic Manager |
| **Static Web App** | Active | Active | Built-in CDN |
| **Cosmos DB** | Read/Write | Read/Write | Multi-region writes |
| **AI Search** | Active | Standby | Daily snapshots |
| **Redis** | Active | Replica | Geo-replication |
| **Blob Storage** | Active | Replica | GRS (Geo-redundant) |
| **Service Bus** | Active | Standby | Premium tier replication |

**Backup Strategy**:

| Data Type | Backup Method | Frequency | Retention | RTO | RPO |
|-----------|---------------|-----------|-----------|-----|-----|
| **Cosmos DB** | Continuous backup | Automatic | 7 days | 1 hour | 15 min |
| **AI Search Indexes** | Snapshot to Blob | Daily | 30 days | 4 hours | 24 hours |
| **Blob Storage** | GRS replication | Real-time | Indefinite | 1 hour | 0 min |
| **Redis** | AOF + RDB | Every 1 min | 24 hours | 15 min | 1 min |
| **Application Config** | Git repository | On change | Indefinite | 5 min | 0 min |

### 4.5 Cost Optimization

**Estimated Monthly Costs (Production)**:

| Service | SKU/Tier | Quantity | Unit Cost | Monthly Cost |
|---------|----------|----------|-----------|--------------|
| **App Service** | P2v3 | 2 instances | $168 | $336 |
| **Static Web App** | Standard | 1 | $9 | $9 |
| **Cosmos DB** | Serverless | Usage | Variable | $100-500 |
| **AI Search** | Standard S1 | 1 | $250 | $250 |
| **Redis Cache** | C3 Standard | 1 | $150 | $150 |
| **Blob Storage** | Hot/Cool | 600 GB | $0.03-0.01/GB | $20 |
| **Service Bus** | Standard | 1 | $10 | $10 |
| **App Insights** | Pay-as-you-go | ~20 GB | $2.30/GB | $50 |
| **Log Analytics** | Pay-as-you-go | ~10 GB | $2.76/GB | $30 |
| **Key Vault** | Standard | 1 | $10 | $10 |
| **Event Grid** | Pay-per-op | 1M ops | $0.60/M | $5 |
| **Traffic Manager** | Standard | 1 | $18 | $18 |
| | | | **Subtotal** | **$988-1,388** |
| **Azure OpenAI** | Usage-based | Variable | See below | $500-2,000 |
| | | | **Total** | **$1,488-3,388** |

**OpenAI Cost Breakdown** (1000 queries/day):
- Embeddings: 1000 queries × $0.0001 = $0.10/day = $3/month
- RAG queries (70%): 700 × $0.08 = $56/day = $1,680/month
- MCP queries (30%): 300 × $0.0001 = $0.03/day = $1/month
- **Total OpenAI**: ~$1,684/month

**Cost Optimization Strategies**:
1. **Reserved Instances**: 1-year commit for App Service (-38% = $207/month)
2. **Cosmos DB Serverless**: Only pay for usage (vs. $175/month provisioned)
3. **Auto-scaling**: Scale down to 1 instance off-hours (-50% App Service cost)
4. **Blob Lifecycle**: Auto-tier to Cool/Archive (-60% storage cost)
5. **Dev/Staging**: Use lower SKUs (Basic AI Search = $75 vs. $250)

**Projected Savings**: ~$200-300/month

### 4.6 Deployment Architecture

**Blue-Green Deployment**:

```
Production Slot (Blue)          Staging Slot (Green)
┌─────────────────────┐        ┌─────────────────────┐
│ Current version     │        │ New version         │
│ 100% traffic        │        │ 0% traffic (testing)│
└─────────────────────┘        └─────────────────────┘
          │                              │
          │    Deployment & Testing      │
          │         Complete             │
          │                              │
          ↓            Swap →            ↓
┌─────────────────────┐        ┌─────────────────────┐
│ Old version         │        │ New version         │
│ 0% traffic (backup) │        │ 100% traffic (live) │
└─────────────────────┘        └─────────────────────┘
```

**Rollback**: Swap slots back (< 30 seconds)

---

## 5. Backend Architecture (C# .NET 8)

### 5.1 Solution Structure

```
RagPlatform.sln
├── src/
│   ├── RagPlatform.Api/                           # ASP.NET Core Web API
│   │   ├── Controllers/
│   │   │   ├── QueryController.cs                # Query execution
│   │   │   ├── SourcesController.cs              # Source management
│   │   │   ├── ConversationsController.cs        # Chat history
│   │   │   ├── ConfigController.cs               # RAG configuration
│   │   │   └── AdminController.cs                # Admin dashboard
│   │   ├── Middleware/
│   │   │   ├── ExceptionHandlingMiddleware.cs
│   │   │   ├── TenantResolutionMiddleware.cs     # Extract tenant from JWT
│   │   │   ├── AuditLoggingMiddleware.cs
│   │   │   └── RequestLoggingMiddleware.cs
│   │   ├── Program.cs                            # App initialization
│   │   ├── appsettings.json
│   │   └── appsettings.Production.json
│   │
│   ├── RagPlatform.Core/                         # Domain layer (no dependencies)
│   │   ├── Entities/
│   │   │   ├── User.cs
│   │   │   ├── Tenant.cs
│   │   │   ├── Conversation.cs
│   │   │   ├── Message.cs
│   │   │   ├── SourceDocument.cs
│   │   │   ├── QueryLog.cs
│   │   │   └── IndexingJob.cs
│   │   ├── Interfaces/
│   │   │   ├── IDocumentSource.cs               # ⭐ Plugin interface
│   │   │   ├── IVectorStore.cs
│   │   │   ├── IMcpClient.cs
│   │   │   ├── IEmbeddingService.cs
│   │   │   ├── ILlmService.cs
│   │   │   ├── IQueryStrategy.cs                # ⭐ MCP/RAG strategy
│   │   │   ├── IRepository.cs (generic)
│   │   │   └── ICostTracker.cs
│   │   ├── Enums/
│   │   │   ├── SourceType.cs
│   │   │   ├── QueryMode.cs
│   │   │   ├── RagTechnique.cs
│   │   │   └── IndexingStatus.cs
│   │   ├── ValueObjects/
│   │   │   ├── SourceCapabilities.cs
│   │   │   ├── SourceConfiguration.cs
│   │   │   └── DocumentMetadata.cs
│   │   └── Exceptions/
│   │       ├── PluginNotFoundException.cs
│   │       ├── SourceNotConfiguredException.cs
│   │       └── TenantNotFoundException.cs
│   │
│   ├── RagPlatform.Application/                  # Business logic
│   │   ├── Services/
│   │   │   ├── QueryOrchestrator.cs             # ⭐ Main entry point
│   │   │   ├── StrategySelector.cs              # ⭐ MCP/RAG decision
│   │   │   ├── RagEngine.cs                     # RAG implementation
│   │   │   ├── McpOrchestrator.cs               # MCP coordination
│   │   │   ├── ConversationManager.cs
│   │   │   ├── TenantManager.cs
│   │   │   ├── CostTracker.cs
│   │   │   └── IndexingService.cs
│   │   ├── Strategies/                           # Query strategies
│   │   │   ├── McpQueryStrategy.cs
│   │   │   ├── RagQueryStrategy.cs
│   │   │   └── HybridQueryStrategy.cs
│   │   ├── RagTechniques/                        # Advanced RAG
│   │   │   ├── MultiQueryRetrieval.cs
│   │   │   ├── RagFusion.cs
│   │   │   ├── QueryDecomposition.cs
│   │   │   ├── StepBackPrompting.cs
│   │   │   ├── HyDE.cs
│   │   │   └── Reranking.cs
│   │   ├── Factories/
│   │   │   └── DocumentSourceFactory.cs         # ⭐ Plugin loader
│   │   ├── DTOs/
│   │   │   ├── QueryRequest.cs
│   │   │   ├── QueryResponse.cs
│   │   │   ├── IndexRequest.cs
│   │   │   └── SourceInfoDto.cs
│   │   ├── Validators/
│   │   │   ├── QueryRequestValidator.cs
│   │   │   └── IndexRequestValidator.cs
│   │   └── Mappings/
│   │       └── AutoMapperProfile.cs
│   │
│   ├── RagPlatform.Infrastructure/               # External dependencies
│   │   ├── Data/
│   │   │   ├── CosmosDbContext.cs
│   │   │   └── Repositories/
│   │   │       ├── UserRepository.cs
│   │   │       ├── TenantRepository.cs
│   │   │       ├── ConversationRepository.cs
│   │   │       └── QueryLogRepository.cs
│   │   ├── VectorStores/
│   │   │   ├── AzureAiSearchStore.cs            # ⭐ Main implementation
│   │   │   ├── PineconeStore.cs                 # Alternative
│   │   │   └── WeaviateStore.cs                 # Alternative
│   │   ├── Embeddings/
│   │   │   ├── OpenAiEmbeddingService.cs
│   │   │   └── AzureOpenAiEmbeddingService.cs
│   │   ├── Llm/
│   │   │   ├── OpenAiLlmService.cs
│   │   │   ├── AzureOpenAiLlmService.cs
│   │   │   └── AnthropicLlmService.cs
│   │   ├── Mcp/
│   │   │   ├── McpClientFactory.cs
│   │   │   ├── McpConnectionPool.cs
│   │   │   └── StdioMcpClient.cs                # MCP protocol
│   │   ├── Cache/
│   │   │   └── RedisCacheService.cs
│   │   ├── Messaging/
│   │   │   ├── ServiceBusPublisher.cs
│   │   │   └── IndexingJobConsumer.cs
│   │   └── External/
│   │       ├── CohereClient.cs                  # Re-ranking
│   │       └── MicrosoftGraphClient.cs
│   │
│   ├── RagPlatform.Plugins/                      # ⭐ Source adapters
│   │   ├── RagPlatform.Plugins.OneNote/
│   │   │   ├── OneNoteAdapter.cs                # IDocumentSource impl
│   │   │   ├── OneNoteMcpClient.cs
│   │   │   ├── OneNoteDocumentProcessor.cs
│   │   │   └── ServiceCollectionExtensions.cs   # DI registration
│   │   ├── RagPlatform.Plugins.SqlDatabase/
│   │   │   ├── SqlDatabaseAdapter.cs
│   │   │   ├── SchemaExtractor.cs
│   │   │   ├── QueryGenerator.cs                # Text-to-SQL
│   │   │   └── ServiceCollectionExtensions.cs
│   │   ├── RagPlatform.Plugins.SharePoint/
│   │   │   ├── SharePointAdapter.cs
│   │   │   ├── SharePointMcpClient.cs
│   │   │   └── ServiceCollectionExtensions.cs
│   │   ├── RagPlatform.Plugins.Confluence/
│   │   │   ├── ConfluenceAdapter.cs
│   │   │   ├── ConfluenceApiClient.cs
│   │   │   └── ServiceCollectionExtensions.cs
│   │   └── RagPlatform.Plugins.BlobStorage/
│   │       ├── BlobStorageAdapter.cs
│   │       ├── DocumentExtractor.cs             # PDF, DOCX, etc.
│   │       └── ServiceCollectionExtensions.cs
│   │
│   └── RagPlatform.Shared/                       # Cross-cutting
│       ├── Extensions/
│       │   ├── StringExtensions.cs
│       │   └── EnumerableExtensions.cs
│       ├── Helpers/
│       │   ├── TokenCounter.cs
│       │   └── PiiDetector.cs
│       └── Constants/
│           ├── AppConstants.cs
│           └── ErrorCodes.cs
│
├── tests/
│   ├── RagPlatform.UnitTests/
│   │   ├── Services/
│   │   ├── Strategies/
│   │   └── Validators/
│   ├── RagPlatform.IntegrationTests/
│   │   ├── Api/
│   │   └── Repositories/
│   └── RagPlatform.E2ETests/
│       └── Scenarios/
│
└── tools/
    ├── MigrationTool/                            # Python→C# data migration
    └── LoadTestTool/                             # Performance testing
```

### 5.2 Core Interfaces (Abstraction Layer)

#### 5.2.1 IDocumentSource (Plugin Interface)

```csharp
namespace RagPlatform.Core.Interfaces;

/// <summary>
/// Represents a pluggable document source (OneNote, SQL, SharePoint, etc.)
/// All source adapters must implement this interface.
/// </summary>
public interface IDocumentSource
{
    /// <summary>
    /// Unique identifier for this source type (e.g., "onenote", "sql-database")
    /// </summary>
    string SourceType { get; }

    /// <summary>
    /// Display name for UI (e.g., "Microsoft OneNote")
    /// </summary>
    string DisplayName { get; }

    /// <summary>
    /// Capabilities of this source (MCP support, RAG support, etc.)
    /// </summary>
    SourceCapabilities Capabilities { get; }

    /// <summary>
    /// Initialize/authenticate with the source
    /// </summary>
    /// <param name="config">Source-specific configuration</param>
    /// <param name="ct">Cancellation token</param>
    Task<bool> InitializeAsync(SourceConfiguration config, CancellationToken ct = default);

    /// <summary>
    /// Fetch all documents for indexing (RAG path)
    /// </summary>
    /// <param name="options">Filtering and pagination options</param>
    /// <param name="ct">Cancellation token</param>
    Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(
        FetchOptions options,
        CancellationToken ct = default);

    /// <summary>
    /// Fetch a single document by ID
    /// </summary>
    Task<SourceDocument?> GetDocumentAsync(string documentId, CancellationToken ct = default);

    /// <summary>
    /// Execute a query via MCP (if supported)
    /// </summary>
    /// <exception cref="NotSupportedException">If source doesn't support MCP</exception>
    Task<McpResponse> ExecuteMcpQueryAsync(
        McpRequest request,
        CancellationToken ct = default);

    /// <summary>
    /// Get metadata for display (notebooks, tables, spaces, etc.)
    /// </summary>
    Task<SourceMetadata> GetMetadataAsync(CancellationToken ct = default);

    /// <summary>
    /// Health check for the source
    /// </summary>
    Task<HealthStatus> CheckHealthAsync(CancellationToken ct = default);
}
```

#### 5.2.2 IQueryStrategy (MCP vs RAG)

```csharp
namespace RagPlatform.Core.Interfaces;

public interface IQueryStrategy
{
    /// <summary>
    /// Strategy name (for logging/debugging)
    /// </summary>
    string Name { get; }

    /// <summary>
    /// Query mode (MCP, RAG, Hybrid)
    /// </summary>
    QueryMode Mode { get; }

    /// <summary>
    /// Execute query using this strategy
    /// </summary>
    Task<QueryResponse> ExecuteAsync(
        QueryRequest request,
        IDocumentSource source,
        QueryContext context,
        CancellationToken ct = default);

    /// <summary>
    /// Can this strategy handle the given request?
    /// </summary>
    bool CanHandle(QueryRequest request, SourceCapabilities capabilities);

    /// <summary>
    /// Estimated cost for this strategy
    /// </summary>
    decimal EstimateCost(QueryRequest request);
}

public enum QueryMode
{
    Mcp,        // Direct MCP protocol access (fast)
    Rag,        // Vector search + LLM generation (intelligent)
    Hybrid      // Combine both approaches
}
```

#### 5.2.3 IVectorStore (Multi-Provider)

```csharp
namespace RagPlatform.Core.Interfaces;

public interface IVectorStore
{
    Task<string> CreateIndexAsync(IndexConfig config, CancellationToken ct = default);
    Task<bool> DeleteIndexAsync(string indexName, CancellationToken ct = default);

    Task AddDocumentsAsync(
        string indexName,
        IEnumerable<VectorDocument> documents,
        CancellationToken ct = default);

    Task<IEnumerable<VectorDocument>> SearchAsync(
        string indexName,
        float[] queryEmbedding,
        SearchOptions options,
        CancellationToken ct = default);

    Task<SearchStatistics> GetStatisticsAsync(
        string indexName,
        CancellationToken ct = default);
}
```

### 5.3 Dependency Injection Configuration

```csharp
// RagPlatform.Api/Program.cs
var builder = WebApplication.CreateBuilder(args);

// Core services
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// Authentication
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddMicrosoftIdentityWebApi(builder.Configuration.GetSection("AzureAd"));

// Authorization
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("AdminOnly", policy => policy.RequireRole("Admin"));
    options.AddPolicy("CanQuery", policy => policy.RequireRole("User", "Admin"));
});

// Rate limiting
builder.Services.AddRateLimiter(options =>
{
    options.AddPolicy("PerUser", context =>
        RateLimitPartition.GetTokenBucketLimiter(
            context.User.GetUserId(),
            _ => new TokenBucketRateLimiterOptions
            {
                TokenLimit = 100,
                ReplenishmentPeriod = TimeSpan.FromMinutes(1),
                TokensPerPeriod = 100
            }));
});

// CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
        policy.WithOrigins(builder.Configuration["CorsOrigins"]!.Split(','))
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials());
});

// Application Insights
builder.Services.AddApplicationInsightsTelemetry();

// AutoMapper
builder.Services.AddAutoMapper(typeof(Program));

// FluentValidation
builder.Services.AddValidatorsFromAssemblyContaining<QueryRequestValidator>();

// Cosmos DB
builder.Services.AddSingleton<CosmosClient>(sp =>
{
    var endpoint = builder.Configuration["CosmosDb:Endpoint"];
    return new CosmosClient(endpoint, new DefaultAzureCredential());
});
builder.Services.AddScoped<CosmosDbContext>();

// Repositories
builder.Services.AddScoped<IRepository<User>, UserRepository>();
builder.Services.AddScoped<IRepository<Tenant>, TenantRepository>();
builder.Services.AddScoped<IRepository<Conversation>, ConversationRepository>();

// Azure AI Search (Vector Store)
builder.Services.AddSingleton<IVectorStore, AzureAiSearchStore>();

// Azure OpenAI
builder.Services.AddSingleton<IEmbeddingService, AzureOpenAiEmbeddingService>();
builder.Services.AddSingleton<ILlmService, AzureOpenAiLlmService>();

// Redis Cache
builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = builder.Configuration["Redis:ConnectionString"];
});

// MCP
builder.Services.AddSingleton<McpConnectionPool>();
builder.Services.AddSingleton<IMcpClient, StdioMcpClient>();

// Application services
builder.Services.AddScoped<QueryOrchestrator>();
builder.Services.AddScoped<StrategySelector>();
builder.Services.AddScoped<RagEngine>();
builder.Services.AddScoped<McpOrchestrator>();
builder.Services.AddScoped<ConversationManager>();
builder.Services.AddScoped<TenantManager>();
builder.Services.AddScoped<CostTracker>();

// Query strategies
builder.Services.AddScoped<IQueryStrategy, McpQueryStrategy>();
builder.Services.AddScoped<IQueryStrategy, RagQueryStrategy>();
builder.Services.AddScoped<IQueryStrategy, HybridQueryStrategy>();

// Plugin discovery and registration
builder.Services.AddSingleton<DocumentSourceFactory>();
builder.Services.DiscoverAndRegisterPlugins();  // Extension method

// SignalR for real-time updates
builder.Services.AddSignalR();

var app = builder.Build();

// Middleware pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseCors("AllowFrontend");

app.UseAuthentication();
app.UseAuthorization();
app.UseRateLimiter();

// Custom middleware
app.UseMiddleware<TenantResolutionMiddleware>();
app.UseMiddleware<AuditLoggingMiddleware>();
app.UseMiddleware<ExceptionHandlingMiddleware>();

app.MapControllers();
app.MapHub<NotificationHub>("/hubs/notifications");

app.Run();
```

### 5.4 Plugin Discovery Extension

```csharp
// RagPlatform.Application/Extensions/PluginRegistrationExtensions.cs
public static class PluginRegistrationExtensions
{
    public static IServiceCollection DiscoverAndRegisterPlugins(
        this IServiceCollection services)
    {
        var pluginAssemblies = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => a.GetName().Name?.StartsWith("RagPlatform.Plugins") ?? false)
            .ToList();

        foreach (var assembly in pluginAssemblies)
        {
            // Find all IDocumentSource implementations
            var pluginTypes = assembly.GetTypes()
                .Where(t => typeof(IDocumentSource).IsAssignableFrom(t)
                         && !t.IsInterface
                         && !t.IsAbstract)
                .ToList();

            foreach (var pluginType in pluginTypes)
            {
                // Register as scoped service
                services.AddScoped(typeof(IDocumentSource), pluginType);

                // Log registration
                Console.WriteLine($"Registered plugin: {pluginType.Name}");
            }

            // Call plugin-specific DI registration if exists
            var extensionType = assembly.GetTypes()
                .FirstOrDefault(t => t.Name == "ServiceCollectionExtensions");

            if (extensionType != null)
            {
                var registerMethod = extensionType.GetMethod(
                    "AddPluginServices",
                    BindingFlags.Public | BindingFlags.Static);

                registerMethod?.Invoke(null, new object[] { services });
            }
        }

        return services;
    }
}
```

### 5.5 Key Service Implementations

#### 5.5.1 QueryOrchestrator (Main Entry Point)

```csharp
// RagPlatform.Application/Services/QueryOrchestrator.cs
public class QueryOrchestrator
{
    private readonly DocumentSourceFactory _sourceFactory;
    private readonly StrategySelector _strategySelector;
    private readonly IEnumerable<IQueryStrategy> _strategies;
    private readonly CostTracker _costTracker;
    private readonly ILogger<QueryOrchestrator> _logger;

    public async Task<QueryResponse> ExecuteQueryAsync(
        QueryRequest request,
        string userId,
        string tenantId,
        CancellationToken ct = default)
    {
        using var activity = Activity.Current?.Source.StartActivity("ExecuteQuery");
        activity?.SetTag("tenant_id", tenantId);
        activity?.SetTag("source_type", request.SourceType);
        activity?.SetTag("preferred_mode", request.PreferredMode);

        try
        {
            // 1. Get source plugin
            var source = _sourceFactory.CreateSource(request.SourceType);
            if (source == null)
                throw new PluginNotFoundException(request.SourceType);

            // 2. Initialize source (uses tenant-specific config)
            var config = await _tenantManager.GetSourceConfigAsync(
                tenantId,
                request.SourceType,
                ct);

            await source.InitializeAsync(config, ct);

            // 3. Select strategy (MCP, RAG, or Hybrid)
            var strategy = _strategySelector.SelectStrategy(
                request,
                source,
                new QueryContext { UserId = userId, TenantId = tenantId });

            _logger.LogInformation(
                "Selected {Strategy} for query: {Query}",
                strategy.Name,
                request.Query);

            // 4. Execute strategy
            var sw = Stopwatch.StartNew();
            var response = await strategy.ExecuteAsync(request, source, context, ct);
            sw.Stop();

            // 5. Enrich response metadata
            response.Metadata.Latency = sw.ElapsedMilliseconds;
            response.Metadata.Strategy = strategy.Name;
            response.Metadata.Mode = strategy.Mode.ToString();

            // 6. Track cost
            await _costTracker.TrackQueryCostAsync(
                tenantId,
                userId,
                request,
                response,
                ct);

            // 7. Log query for audit
            await _auditService.LogQueryAsync(new QueryLog
            {
                TenantId = tenantId,
                UserId = userId,
                Query = request.Query,
                SourceType = request.SourceType,
                Mode = strategy.Mode,
                Cost = response.Metadata.EstimatedCost,
                LatencyMs = sw.ElapsedMilliseconds,
                Timestamp = DateTime.UtcNow
            }, ct);

            return response;
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            _logger.LogError(ex, "Query execution failed");
            throw;
        }
    }
}
```

#### 5.5.2 StrategySelector (Auto MCP/RAG Decision)

```csharp
// RagPlatform.Application/Services/StrategySelector.cs
public class StrategySelector
{
    private readonly IEnumerable<IQueryStrategy> _strategies;
    private readonly ILogger<StrategySelector> _logger;

    public IQueryStrategy SelectStrategy(
        QueryRequest request,
        IDocumentSource source,
        QueryContext context)
    {
        // User explicitly requested a mode
        if (request.PreferredMode.HasValue)
        {
            var strategy = _strategies.FirstOrDefault(s =>
                s.Mode == request.PreferredMode.Value);

            if (strategy != null && strategy.CanHandle(request, source.Capabilities))
                return strategy;

            _logger.LogWarning(
                "Requested mode {Mode} not available, falling back to auto-selection",
                request.PreferredMode);
        }

        // Auto-select based on heuristics
        var capabilities = source.Capabilities;

        // Simple lookup queries → MCP (fast, < 500ms)
        if (IsSimpleLookup(request.Query) && capabilities.SupportsMcp)
        {
            return _strategies.First(s => s.Mode == QueryMode.Mcp);
        }

        // Complex semantic queries → RAG (intelligent, 2-10s)
        if (IsComplexQuery(request.Query) && capabilities.SupportsRag)
        {
            return _strategies.First(s => s.Mode == QueryMode.Rag);
        }

        // Real-time data needed → MCP
        if (request.RequiresFreshData && capabilities.SupportsRealtime)
        {
            return _strategies.First(s => s.Mode == QueryMode.Mcp);
        }

        // Aggregation/analysis → RAG
        if (IsAggregationQuery(request.Query) && capabilities.SupportsRag)
        {
            return _strategies.First(s => s.Mode == QueryMode.Rag);
        }

        // Hybrid: Combine both for maximum accuracy
        if (capabilities.SupportsMcp && capabilities.SupportsRag)
        {
            return _strategies.First(s => s.Mode == QueryMode.Hybrid);
        }

        // Default: RAG if available, else MCP
        return capabilities.SupportsRag
            ? _strategies.First(s => s.Mode == QueryMode.Rag)
            : _strategies.First(s => s.Mode == QueryMode.Mcp);
    }

    private bool IsSimpleLookup(string query)
    {
        var lookupKeywords = new[] { "show", "get", "find", "retrieve", "display" };
        return lookupKeywords.Any(kw =>
            query.Contains(kw, StringComparison.OrdinalIgnoreCase));
    }

    private bool IsComplexQuery(string query)
    {
        var complexKeywords = new[]
        {
            "summarize", "analyze", "explain", "why", "how",
            "compare", "contrast", "what are the themes"
        };
        return complexKeywords.Any(kw =>
            query.Contains(kw, StringComparison.OrdinalIgnoreCase));
    }

    private bool IsAggregationQuery(string query)
    {
        var aggKeywords = new[] { "all", "total", "count", "average", "sum" };
        return aggKeywords.Any(kw =>
            query.Contains(kw, StringComparison.OrdinalIgnoreCase));
    }
}
```

#### 5.5.3 DocumentSourceFactory (Plugin Loader)

```csharp
// RagPlatform.Application/Factories/DocumentSourceFactory.cs
public class DocumentSourceFactory
{
    private readonly IServiceProvider _serviceProvider;
    private readonly Dictionary<string, Type> _registeredSources;
    private readonly ILogger<DocumentSourceFactory> _logger;

    public DocumentSourceFactory(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
        _registeredSources = DiscoverPlugins();
    }

    private Dictionary<string, Type> DiscoverPlugins()
    {
        var pluginTypes = AppDomain.CurrentDomain.GetAssemblies()
            .SelectMany(a => a.GetTypes())
            .Where(t => typeof(IDocumentSource).IsAssignableFrom(t)
                     && !t.IsInterface
                     && !t.IsAbstract)
            .ToList();

        var registry = new Dictionary<string, Type>(StringComparer.OrdinalIgnoreCase);

        foreach (var type in pluginTypes)
        {
            // Get sourceType from instance (temporary)
            var instance = (IDocumentSource)Activator.CreateInstance(type)!;
            registry[instance.SourceType] = type;

            _logger.LogInformation(
                "Discovered plugin: {SourceType} ({DisplayName})",
                instance.SourceType,
                instance.DisplayName);
        }

        return registry;
    }

    public IDocumentSource? CreateSource(string sourceType)
    {
        if (!_registeredSources.TryGetValue(sourceType, out var type))
        {
            _logger.LogWarning("Plugin not found: {SourceType}", sourceType);
            return null;
        }

        return (IDocumentSource)_serviceProvider.GetRequiredService(type);
    }

    public IEnumerable<SourceInfo> GetAvailableSources()
    {
        return _registeredSources.Select(kvp =>
        {
            var source = CreateSource(kvp.Key);
            return new SourceInfo
            {
                Type = kvp.Key,
                DisplayName = source!.DisplayName,
                Capabilities = source.Capabilities
            };
        });
    }
}
```

---

## 6. Plugin System Architecture

### 6.1 Plugin Implementation Examples

#### 6.1.1 OneNote Plugin (MCP + RAG)

```csharp
// RagPlatform.Plugins.OneNote/OneNoteAdapter.cs
public class OneNoteAdapter : IDocumentSource
{
    private readonly IMcpClient _mcpClient;
    private readonly ILogger<OneNoteAdapter> _logger;
    private SourceConfiguration? _config;

    public string SourceType => "onenote";
    public string DisplayName => "Microsoft OneNote";

    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = true,
        SupportsRag = true,
        SupportsRealtime = true,
        RequiresIndexing = false,
        SupportsMetadataFiltering = true,
        SupportedMimeTypes = new[] { "text/html", "text/plain" }
    };

    public async Task<bool> InitializeAsync(
        SourceConfiguration config,
        CancellationToken ct = default)
    {
        _config = config;

        // Connect to OneNote MCP server
        await _mcpClient.ConnectAsync(new McpServerConfig
        {
            Command = "node",
            Arguments = config.GetValue("McpServerPath"),
            Environment = new Dictionary<string, string>
            {
                ["CLIENT_ID"] = config.GetValue("ClientId"),
                ["CLIENT_SECRET"] = config.GetValue("ClientSecret"),
                ["TENANT_ID"] = config.GetValue("TenantId")
            }
        }, ct);

        return await _mcpClient.IsHealthyAsync(ct);
    }

    public async Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(
        FetchOptions options,
        CancellationToken ct = default)
    {
        var documents = new List<SourceDocument>();

        // Use MCP to list all notebooks
        var notebooksResponse = await _mcpClient.SendRequestAsync(
            new McpRequest
            {
                Method = "tools/call",
                Params = new { name = "list_notebooks" }
            }, ct);

        foreach (var notebook in notebooksResponse.Content)
        {
            var pagesResponse = await _mcpClient.SendRequestAsync(
                new McpRequest
                {
                    Method = "tools/call",
                    Params = new
                    {
                        name = "list_pages",
                        arguments = new { notebookId = notebook.Id }
                    }
                }, ct);

            foreach (var page in pagesResponse.Content)
            {
                var contentResponse = await _mcpClient.SendRequestAsync(
                    new McpRequest
                    {
                        Method = "tools/call",
                        Params = new
                        {
                            name = "get_page_content",
                            arguments = new { pageId = page.Id }
                        }
                    }, ct);

                documents.Add(new SourceDocument
                {
                    Id = page.Id,
                    Content = ExtractTextFromHtml(contentResponse.Content),
                    Metadata = new DocumentMetadata
                    {
                        SourceType = SourceType,
                        Title = page.Title,
                        Hierarchy = new[] { notebook.Name, page.Title },
                        Url = page.WebUrl,
                        CreatedAt = page.CreatedDateTime,
                        ModifiedAt = page.LastModifiedDateTime
                    }
                });
            }
        }

        return documents;
    }

    public async Task<McpResponse> ExecuteMcpQueryAsync(
        McpRequest request,
        CancellationToken ct = default)
    {
        return await _mcpClient.SendRequestAsync(request, ct);
    }
}
```

#### 6.1.2 SQL Database Plugin (RAG Only)

```csharp
// RagPlatform.Plugins.SqlDatabase/SqlDatabaseAdapter.cs
public class SqlDatabaseAdapter : IDocumentSource
{
    public string SourceType => "sql-database";
    public string DisplayName => "SQL Database";

    public SourceCapabilities Capabilities => new()
    {
        SupportsMcp = false,
        SupportsRag = true,
        SupportsRealtime = false,
        RequiresIndexing = true
    };

    public async Task<IEnumerable<SourceDocument>> GetAllDocumentsAsync(
        FetchOptions options,
        CancellationToken ct = default)
    {
        var schema = await _schemaExtractor.ExtractAsync(ct);
        var documents = new List<SourceDocument>();

        foreach (var table in schema.Tables)
        {
            var content = BuildTableDocumentContent(table);

            documents.Add(new SourceDocument
            {
                Id = $"{table.Schema}.{table.Name}",
                Content = content,
                Metadata = new DocumentMetadata
                {
                    SourceType = SourceType,
                    Title = $"{table.Schema}.{table.Name}",
                    Hierarchy = new[] { table.Schema, table.Name }
                }
            });
        }

        return documents;
    }
}
```

### 6.2 Adding a New Plugin (Step-by-Step)

**Step 1**: Create project
```bash
dotnet new classlib -n RagPlatform.Plugins.Confluence
dotnet add reference ../../RagPlatform.Core
```

**Step 2**: Implement interface
```csharp
public class ConfluenceAdapter : IDocumentSource
{
    public string SourceType => "confluence";
    public string DisplayName => "Atlassian Confluence";

    // Implement required methods...
}
```

**Step 3**: Deploy
```bash
dotnet publish -o ../../../Api/Plugins
```

**Step 4**: Auto-discovered and ready to use!

---

## 7. Frontend Architecture (React/TypeScript)

### 7.1 Component Structure

Keep the existing React frontend with minor updates:
- Update API client to call new C# backend endpoints
- Add source selector UI component
- Add query mode toggle (MCP/RAG/Auto)
- Integrate SignalR for real-time indexing progress
- Add MSAL for Azure AD authentication

### 7.2 Key Changes from Current Frontend

```typescript
// src/api/client.ts - Update base URL and add auth
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add MSAL interceptor for JWT tokens
apiClient.interceptors.request.use(async (config) => {
  const accounts = instance.getAllAccounts();
  if (accounts.length > 0) {
    const response = await instance.acquireTokenSilent({
      scopes: ['api://rag-platform-api/User.Read'],
      account: accounts[0]
    });
    config.headers.Authorization = `Bearer ${response.accessToken}`;
  }
  return config;
});
```

---

## 8. MCP Integration Strategy

### 8.1 MCP Protocol Implementation

```csharp
// RagPlatform.Infrastructure/Mcp/StdioMcpClient.cs
public class StdioMcpClient : IMcpClient
{
    private Process? _process;
    private StreamWriter? _stdin;
    private StreamReader? _stdout;

    public async Task ConnectAsync(McpServerConfig config, CancellationToken ct)
    {
        _process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = config.Command,
                Arguments = config.Arguments,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            }
        };

        foreach (var (key, value) in config.Environment)
        {
            _process.StartInfo.EnvironmentVariables[key] = value;
        }

        _process.Start();
        _stdin = _process.StandardInput;
        _stdout = _process.StandardOutput;

        // Send initialize request
        await SendRequestAsync(new McpInitRequest
        {
            ProtocolVersion = "2024-11-05",
            Capabilities = new { }
        }, ct);
    }

    public async Task<McpResponse> SendRequestAsync(
        McpRequest request,
        CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(request);
        await _stdin!.WriteLineAsync(json);
        await _stdin.FlushAsync();

        var responseLine = await _stdout!.ReadLineAsync();
        return JsonSerializer.Deserialize<McpResponse>(responseLine!)!;
    }
}
```

### 8.2 Connection Pooling

```csharp
public class McpConnectionPool
{
    private readonly ConcurrentDictionary<string, ObjectPool<IMcpClient>> _pools = new();

    public async Task<IMcpClient> AcquireAsync(
        string sourceType,
        McpServerConfig config,
        CancellationToken ct)
    {
        var pool = _pools.GetOrAdd(sourceType, _ =>
            new DefaultObjectPool<IMcpClient>(
                new McpClientPooledObjectPolicy(config),
                maxRetained: 10));

        var client = pool.Get();
        if (!await client.IsHealthyAsync(ct))
        {
            await client.ConnectAsync(config, ct);
        }
        return client;
    }
}
```

---

## 9. Migration Strategy (Python → C#)

### 9.1 Phase 1: Infrastructure Setup (Weeks 1-2)
- Provision Azure resources via Terraform
- Set up CI/CD pipelines
- Configure Azure AD + app registrations
- Initialize C# solution structure

### 9.2 Phase 2: Core Backend (Weeks 3-6)
- Implement core interfaces
- Build ASP.NET Core API
- Integrate Cosmos DB + Azure AI Search
- Port RAG engine logic from Python

### 9.3 Phase 3: MCP Integration (Weeks 7-8)
- Implement MCP client
- Build connection pool
- Create OneNote MCP adapter

### 9.4 Phase 4: Plugin System (Weeks 9-10)
- Build plugin discovery
- Implement DocumentSourceFactory
- Create 2+ working plugins

### 9.5 Phase 5: Frontend Rebuild (Weeks 11-14)
- Integrate MSAL auth
- Build multi-source selector
- Implement real-time features

### 9.6 Phase 6: Data Migration (Weeks 15-16)
- Export Python data
- Import to Cosmos DB
- Re-index in Azure AI Search

### 9.7 Phase 7: Testing (Weeks 17-18)
- Load testing
- Security audit
- Performance optimization

### 9.8 Phase 8: Production Deploy (Weeks 19-20)
- Blue-green deployment
- Monitoring setup
- Go-live

---

## 10. Production Enterprise Features

### 10.1 Multi-Tenancy Implementation

```csharp
public class TenantResolutionMiddleware
{
    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var tenantId = context.User.FindFirst("tenant_id")?.Value;
        if (!string.IsNullOrEmpty(tenantId))
        {
            context.Items["TenantId"] = tenantId;
        }
        await next(context);
    }
}
```

### 10.2 Cost Tracking

```csharp
public class CostTracker
{
    public async Task TrackQueryCostAsync(
        string tenantId,
        string userId,
        QueryRequest request,
        QueryResponse response,
        CancellationToken ct)
    {
        var cost = CalculateCost(response.Metadata);

        await _cosmosDb.CreateItemAsync(new CostEntry
        {
            TenantId = tenantId,
            UserId = userId,
            QueryId = Guid.NewGuid().ToString(),
            Timestamp = DateTime.UtcNow,
            Mode = response.Metadata.Mode,
            EmbeddingCost = response.Metadata.EmbeddingTokens * 0.0001m / 1000,
            LlmCost = (response.Metadata.PromptTokens * 0.005m +
                      response.Metadata.CompletionTokens * 0.015m) / 1000,
            TotalCost = cost
        }, ct);

        // Check budget limits
        var monthlySpend = await GetMonthlySpendAsync(tenantId, ct);
        var budget = await GetTenantBudgetAsync(tenantId, ct);

        if (monthlySpend > budget * 0.8m)
        {
            await _notificationService.SendBudgetAlertAsync(
                tenantId,
                $"80% of budget reached: ${monthlySpend:F2} / ${budget:F2}",
                ct);
        }
    }
}
```

### 10.3 Audit Logging

```csharp
public class AuditLoggingMiddleware
{
    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        var sw = Stopwatch.StartNew();
        await next(context);
        sw.Stop();

        await _auditService.LogAsync(new AuditLog
        {
            TenantId = context.GetTenantId(),
            UserId = context.User.GetUserId(),
            Action = $"{context.Request.Method} {context.Request.Path}",
            Timestamp = DateTime.UtcNow,
            IpAddress = context.Connection.RemoteIpAddress?.ToString(),
            UserAgent = context.Request.Headers["User-Agent"],
            StatusCode = context.Response.StatusCode,
            DurationMs = sw.ElapsedMilliseconds
        });
    }
}
```

### 10.4 PII Detection

```csharp
public class PiiDetector
{
    private readonly Regex _emailRegex = new(@"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b");
    private readonly Regex _ssnRegex = new(@"\b\d{3}-\d{2}-\d{4}\b");

    public async Task<PiiDetectionResult> DetectAndRedactAsync(string text)
    {
        var detectedPii = new List<PiiEntity>();
        var redactedText = text;

        if (_emailRegex.IsMatch(text))
        {
            detectedPii.Add(new PiiEntity { Type = "Email" });
            redactedText = _emailRegex.Replace(redactedText, "[EMAIL_REDACTED]");
        }

        if (_ssnRegex.IsMatch(text))
        {
            detectedPii.Add(new PiiEntity { Type = "SSN" });
            redactedText = _ssnRegex.Replace(redactedText, "[SSN_REDACTED]");
        }

        return new PiiDetectionResult
        {
            OriginalText = text,
            RedactedText = redactedText,
            DetectedEntities = detectedPii,
            ContainsPii = detectedPii.Any()
        };
    }
}
```

---

## 11. Testing Strategy

### 11.1 Unit Tests (70%+ Coverage)

```csharp
public class StrategySelectorTests
{
    [Fact]
    public void SelectStrategy_SimpleLookup_ReturnsMcp()
    {
        var selector = new StrategySelector();
        var source = CreateMockSource(supportsMcp: true, supportsRag: true);
        var request = new QueryRequest { Query = "Show me document X" };

        var strategy = selector.SelectStrategy(request, source, context);

        Assert.IsType<McpQueryStrategy>(strategy);
    }
}
```

### 11.2 Integration Tests

```csharp
public class QueryControllerTests : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task Query_ValidRequest_ReturnsOk()
    {
        var client = _factory.CreateClient();
        client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", await GetTestTokenAsync());

        var response = await client.PostAsJsonAsync("/api/v1/query", new QueryRequest
        {
            Query = "What is the capital of France?",
            SourceType = "onenote"
        });

        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<QueryResponse>();
        Assert.NotNull(result.Answer);
    }
}
```

### 11.3 E2E Tests (Playwright)

```typescript
test('complete query flow with source selection', async ({ page }) => {
  await page.goto('/');
  await page.click('button:has-text("Sign In")');

  await page.click('[data-testid="source-onenote"]');
  await page.fill('[data-testid="query-input"]', 'Summarize meeting notes');
  await page.click('[data-testid="submit-query"]');

  await expect(page.locator('[data-testid="query-response"]'))
    .toBeVisible({ timeout: 30000 });
});
```

---

## 12. Deployment & CI/CD

### 12.1 GitHub Actions Workflow

```yaml
name: Deploy Backend

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Build
        run: dotnet build --configuration Release

      - name: Test
        run: dotnet test --no-build

      - name: Publish
        run: dotnet publish -c Release -o ./publish

      - name: Deploy to Azure
        uses: azure/webapps-deploy@v2
        with:
          app-name: 'rag-platform-api-prod'
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: ./publish
```

---

## 13. Technical Specifications

### 13.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Latency (P50) | <200ms | App Insights |
| API Latency (P99) | <2s | App Insights |
| MCP Query Time | <500ms | Custom metric |
| RAG Query Time | <10s | Custom metric |
| Concurrent Users | 1,000+ | Load testing |
| Uptime | 99.9% | Azure Monitor |

### 13.2 Security Standards

- **Authentication**: Azure AD OAuth 2.0 + JWT
- **Authorization**: RBAC (Admin, TenantAdmin, User)
- **Encryption**: TLS 1.3, Azure-managed keys at rest
- **Input Validation**: FluentValidation
- **Rate Limiting**: 100 req/min per user

### 13.3 Data Retention

| Data Type | Retention |
|-----------|-----------|
| Conversations | 1 year |
| Query Logs | 90 days |
| Audit Logs | 7 years |
| Vector Embeddings | Until deleted |

---

## 14. Timeline, Resources & Cost Estimates

### 14.1 Implementation Timeline (20 Weeks)

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Infrastructure | 2 weeks | Azure resources live |
| 2. Core Backend | 4 weeks | Working API + RAG |
| 3. MCP Integration | 2 weeks | OneNote via MCP |
| 4. Plugin System | 2 weeks | 2+ source plugins |
| 5. Frontend | 4 weeks | Production UI |
| 6. Data Migration | 2 weeks | Data migrated |
| 7. Testing | 2 weeks | Tests complete |
| 8. Deployment | 2 weeks | Production live |

### 14.2 Team Requirements

**Required Team (4.5 FTEs)**:
- 1 Backend Engineer (C#/.NET expert)
- 1 Frontend Engineer (React/TypeScript)
- 1 DevOps Engineer (Azure + Terraform)
- 1 QA Engineer (Testing + automation)
- 0.5 Product Manager (Requirements)

### 14.3 Cost Estimates

**Development Cost**:
- 20 weeks × 4.5 FTEs × $20K/month = **$450,000**

**Azure Infrastructure (Monthly)**:
- App Service: $336
- Cosmos DB: $100-500
- AI Search: $250
- Redis: $150
- Other services: $152
- **Subtotal**: $988-1,388/month

**Azure OpenAI (Monthly, 1000 queries/day)**:
- Embeddings: $3
- RAG queries (70%): $1,680
- MCP queries (30%): $1
- **Subtotal**: $1,684/month

**Total First Year**:
- Development: $450,000
- Infrastructure (12 months): $11,856-16,656
- OpenAI (12 months): $20,208
- **Total**: **$482,064-486,864**

### 14.4 ROI Analysis

**Benefits**:
- 70% time savings in information retrieval
- Support for 5+ data sources (vs 1 currently)
- Multi-tenant SaaS revenue potential
- 3-5 day plugin development (vs 2-4 weeks)

**Break-even**: 12-18 months with 100 enterprise users at $500/month

---

## 15. Appendices

### 15.1 Glossary

- **MCP**: Model Context Protocol - standard for LLM-application integration
- **RAG**: Retrieval-Augmented Generation - AI technique combining retrieval + LLM
- **Vector Store**: Database optimized for similarity search (embeddings)
- **Embedding**: Numerical representation of text for semantic search
- **Multi-tenancy**: Single application serving multiple isolated customers

### 15.2 References

- MCP Specification: https://spec.modelcontextprotocol.io/
- Azure OpenAI: https://learn.microsoft.com/azure/ai-services/openai/
- Azure AI Search: https://learn.microsoft.com/azure/search/
- .NET 8 Documentation: https://learn.microsoft.com/dotnet/

### 15.3 Next Steps

1. **Approval**: Review and approve this architecture plan
2. **Team Formation**: Hire/assign team members
3. **Infrastructure**: Provision Azure resources
4. **Sprint Planning**: Break down into 2-week sprints
5. **Kickoff**: Begin development Phase 1

---

**Document End**

*This enterprise architecture plan provides a comprehensive roadmap for transforming a single-source RAG application into a production-ready, multi-source, cloud-native platform with plug-and-play extensibility.*

