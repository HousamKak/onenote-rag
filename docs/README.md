# OneNote RAG System - Architecture Documentation

This directory contains comprehensive D2 diagrams documenting the architecture, processes, and technology stack of the OneNote RAG system. Every diagram now ships in two variants:
- **Full** – deep dive with callouts for each subsystem.
- **Lite** – quick summary with the same dashed boxes that highlight the production-ready alternative next to each non-prod component.

## 📊 Available Diagrams

### 1. **architecture-overview.d2** / **architecture-overview-summary.d2**
High-level system architecture showing:
- Frontend (React + TypeScript)
- Backend (FastAPI)
- Data layer (SQLite + ChromaDB)
- External services (OpenAI, Microsoft Graph, LangSmith)
- Production alternatives for databases and deployment
- Lite view focuses on “User → Frontend → API → Data/AI → Observability” with Azure-first alternatives beside each block.

### 2. **rag-process-flow.d2** / **rag-process-flow-summary.d2**
Detailed RAG query processing pipeline:
- Query reception and embedding
- Vector similarity search
- RAG technique application (Basic, HyDE, CoT, Self-Ask, ReAct)
- LLM generation
- Response assembly
- Performance metrics
- Lite view condenses the six major stages, plus dashed alternatives for Azure AI Search, Azure OpenAI, and observability.

### 3. **tech-stack.d2** / **tech-stack-summary.d2**
Complete technology stack overview:
- Frontend technologies (React, TypeScript, Vite, Tailwind)
- Backend frameworks (FastAPI, LangChain, OpenAI SDK)
- Current databases (SQLite, ChromaDB)
- Production alternatives (PostgreSQL, Pinecone, Weaviate, Qdrant)
- Deployment options (Docker, Kubernetes, Cloud Services)
- Monitoring and observability tools
- Lite view compares “Current PoC stack vs Production-ready stack” line by line.

### 4. **document-indexing-flow.d2** / **document-indexing-flow-summary.d2**
OneNote document indexing process:
- Authentication (OAuth 2.0 / Manual token)
- Fetching OneNote structure (notebooks → sections → pages)
- Content extraction and parsing
- Document chunking strategy
- Embedding generation
- Vector storage in ChromaDB
- Incremental sync logic
- Error handling and performance notes
- Lite view captures “Source → Extract → Chunk → Embed → Store → Ready” with Databricks/Azure AI alternatives.

### 5. **frontend-architecture.d2** / **frontend-architecture-summary.d2**
React frontend architecture:
- Component structure and routing
- State management (Zustand + Context)
- Theme system (Claude vs Neo-brutalism)
- API client layer
- Styling system (Tailwind CSS)
- Build process (Vite)
- Responsive design
- Lite view highlights the SPA pipeline plus Next.js/Redux/APIM alternatives.

### 6. **backend-architecture.d2** / **backend-architecture-summary.d2**
FastAPI backend architecture:
- API routes and endpoints
- Service layer (RAG Engine, Vector Store, Document Processor)
- Data models (Pydantic)
- Configuration management
- Database services (SQLite + ChromaDB)
- Security (Encryption, Authentication)
- External API integrations
- Lite view summarizes “Gateway → Services → Storage/AI/Monitoring” with Azure Functions, Azure SQL, Azure AI Search, Databricks, and App Insights options.

## 🎨 Viewing the Diagrams

### Option 1: Interactive HTML Viewer (⭐ Recommended - No Installation Required!)

**The easiest way to view all diagrams with pan and zoom:**

Open `diagram-viewer.html` in your web browser and use the on-screen zoom/pan controls to explore each SVG (full or lite). If you prefer a file-server, run `python -m http.server 8080` inside `docs/` and visit `http://localhost:8080/diagram-viewer.html`.

### Option 2: Online D2 Playground
1. Visit [D2 Playground](https://play.d2lang.com/)
2. Copy the content of any `.d2` file
3. Paste into the editor
4. View the rendered diagram instantly

**Or use the "Open in D2" button in the HTML viewer!**

### Option 3: Install D2 CLI (For Offline Rendering)

#### macOS (Homebrew)
```bash
brew install d2
```

#### Linux/macOS (Script)
```bash
curl -fsSL https://d2lang.com/install.sh | sh -s --
```

#### Windows (Scoop)
```powershell
scoop install d2
```

#### Render Diagrams
```bash
# Render to SVG
d2 architecture-overview.d2 architecture-overview.svg

# Render to PNG
d2 architecture-overview.d2 architecture-overview.png

# Render with specific theme
d2 --theme=200 rag-process-flow.d2 output.svg

# Watch mode (auto-refresh)
d2 --watch tech-stack.d2 tech-stack.svg
```

### Option 4: VS Code Extension
1. Install the [D2 extension](https://marketplace.visualstudio.com/items?itemName=terrastruct.d2) for VS Code
2. Open any `.d2` file
3. Click the preview button or use `Ctrl+K V` (Windows/Linux) or `Cmd+K V` (Mac)

## 📁 File Structure

```
docs/
├── README.md                      # This file
├── diagram-viewer.html            # Simple SVG viewer (pan + zoom)
├── architecture-overview.d2       # High-level system architecture (full)
├── architecture-overview-summary.d2  # High-level lite view
├── rag-process-flow.d2            # RAG query processing pipeline (full)
├── rag-process-flow-summary.d2    # RAG pipeline lite view
├── tech-stack.d2                  # Technology stack (full)
├── tech-stack-summary.d2          # Tech stack current vs prod
├── document-indexing-flow.d2      # OneNote indexing process (full)
├── document-indexing-flow-summary.d2 # Indexing lite view
├── frontend-architecture.d2       # React frontend structure (full)
├── frontend-architecture-summary.d2  # Frontend lite view
├── backend-architecture.d2        # FastAPI backend structure (full)
└── backend-architecture-summary.d2   # Backend lite view
```

## 🔍 Key Concepts Explained

### Current Tech Stack
**Frontend:**
- React 18.3 + TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Zustand for state management
- Dual theme system (Claude/Neo-brutalism)

**Backend:**
- FastAPI for REST API
- LangChain for RAG orchestration
- OpenAI for embeddings & LLM
- ChromaDB for vector storage
- SQLite for settings storage
- Fernet encryption for API keys

### Production Alternatives

#### Vector Databases
| Current | Production Options | Best For |
|---------|-------------------|----------|
| **ChromaDB (local)** | **Pinecone** | Fully managed, auto-scaling |
| | **Weaviate** | Self-hosted, GraphQL, multi-modal |
| | **Qdrant** | Fast Rust-based, Docker-friendly |
| | **PostgreSQL + pgvector** | Existing PG infrastructure |

#### Relational Databases
| Current | Production Options | Best For |
|---------|-------------------|----------|
| **SQLite (local)** | **PostgreSQL** | ✓ Recommended, ACID, extensions |
| | **MySQL/MariaDB** | Wide support, mature |
| | **Azure SQL Database** | Managed Azure service |

#### Deployment Options
- **Docker + Docker Compose**: Containerized deployment
- **Kubernetes / AKS**: Scalable orchestration
- **Azure Container Apps**: Serverless containers
- **AWS ECS / Fargate**: AWS container services
- **Vercel/Netlify + Railway**: Jamstack deployment

### RAG Techniques Implemented

1. **Basic RAG**: Simple retrieve → generate
2. **HyDE**: Hypothetical document embeddings
3. **Chain of Thought (CoT)**: Step-by-step reasoning
4. **Self-Ask**: Break into sub-questions
5. **ReAct**: Reasoning + Acting paradigm

## 🔐 Security Notes

### Files NOT in Git
- `.env` - Environment variables with API keys
- `backend/data/.encryption_key` - Fernet encryption key
- `backend/data/settings.db` - Encrypted settings database
- `backend/data/chroma_db/` - Vector database files

### Encryption
All sensitive API keys are encrypted using Fernet symmetric encryption before being stored in the SQLite database.

## 📊 Performance Metrics

**Typical RAG Query:**
- Embedding: 100-200ms
- Vector Search: 50-100ms
- LLM Generation: 1-5s
- **Total: 1.5-6s**

**Document Indexing (1000 pages):**
- Auth: 1-2s
- Fetch: 5-10s
- Chunking: ~1s
- Embeddings: 2-5s per 100 chunks
- Storage: 1-2s per 100 chunks
- **Total: ~2-5 minutes**

## 🚀 Next Steps for Production

1. **Database Migration**
   - Migrate SQLite → PostgreSQL
   - Consider Pinecone/Qdrant for vectors

2. **Add Caching**
   - Redis for embeddings cache
   - Session management

3. **Monitoring**
   - ELK Stack or Azure Log Analytics
   - Prometheus + Grafana
   - Error tracking (Sentry)

4. **Authentication**
   - Add user authentication (Auth0, Azure AD B2C)
   - Multi-tenancy support

5. **Deployment**
   - Containerize with Docker
   - Set up CI/CD pipeline
   - Deploy to cloud (Azure/AWS)

## 📝 Diagram Maintenance

When updating the system:
1. Update the relevant `.d2` files
2. Re-render diagrams if needed
3. Keep this README in sync
4. Document any new components or flows

## 🔗 Resources

- [D2 Language Documentation](https://d2lang.com/)
- [D2 Playground](https://play.d2lang.com/)
- [D2 GitHub Repository](https://github.com/terrastruct/d2)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
