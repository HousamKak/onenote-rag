# OneNote RAG Backend

A sophisticated RAG (Retrieval-Augmented Generation) system for querying OneNote documents with toggleable advanced techniques.

## Features

- **OneNote Integration**: Extract and index documents from Microsoft OneNote
- **Vector Database**: ChromaDB for efficient similarity search
- **Basic RAG**: Standard retrieval-augmented generation pipeline
- **Advanced Techniques** (Toggleable):
  - Multi-Query Retrieval
  - RAG-Fusion with Reciprocal Rank Fusion
  - Query Decomposition (Recursive/Individual)
  - Step-Back Prompting
  - HyDE (Hypothetical Document Embeddings)
  - Re-ranking with Cohere
- **LangSmith Integration**: Track and monitor all RAG operations
- **Preset Configurations**: Fast, Balanced, Quality, and Research modes

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `LANGCHAIN_API_KEY`: Your LangSmith API key
- `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID`: For OneNote access (optional)
- `COHERE_API_KEY`: For re-ranking feature (optional)

### 3. Run the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Quick Start (Demo Mode)

If you don't have OneNote set up, you can use demo mode:

```python
import requests

# Add demo documents
response = requests.post("http://localhost:8000/api/demo/add-documents", json={
    "texts": [
        "LangChain is a framework for developing applications powered by language models.",
        "RAG (Retrieval-Augmented Generation) combines retrieval with generation.",
        "Vector databases store embeddings for efficient similarity search."
    ],
    "notebook_name": "AI Knowledge Base"
})

# Query the documents
response = requests.post("http://localhost:8000/api/query", json={
    "question": "What is RAG?",
    "config": {
        "chunk_size": 1000,
        "retrieval_k": 3,
        "temperature": 0.0,
        "model_name": "gpt-3.5-turbo",
        "multi_query": {"enabled": True, "num_queries": 3}
    }
})

print(response.json())
```

## API Endpoints

### Configuration
- `GET /api/config/presets` - Get all preset configurations
- `GET /api/config/presets/{name}` - Get specific preset
- `GET /api/config/default` - Get default configuration

### OneNote
- `GET /api/onenote/notebooks` - List notebooks
- `GET /api/onenote/sections/{notebook_id}` - List sections
- `GET /api/onenote/pages/{section_id}` - List pages

### Indexing
- `POST /api/index/sync` - Sync OneNote documents
- `GET /api/index/stats` - Get database statistics
- `DELETE /api/index/clear` - Clear vector database

### Query
- `POST /api/query` - Query documents
- `POST /api/query/compare` - Compare multiple configurations

### Demo
- `POST /api/demo/add-documents` - Add demo documents (testing)

## Configuration Examples

### Fast (Basic RAG)
```json
{
  "chunk_size": 1000,
  "retrieval_k": 3,
  "temperature": 0.0,
  "model_name": "gpt-3.5-turbo"
}
```

### Balanced (Multi-Query + Re-ranking)
```json
{
  "chunk_size": 800,
  "retrieval_k": 5,
  "model_name": "gpt-3.5-turbo",
  "multi_query": {"enabled": true, "num_queries": 3},
  "reranking": {"enabled": true, "top_k": 10, "top_n": 5}
}
```

### Quality (Multiple Techniques)
```json
{
  "chunk_size": 500,
  "retrieval_k": 8,
  "model_name": "gpt-4-turbo-preview",
  "multi_query": {"enabled": true, "num_queries": 5},
  "rag_fusion": {"enabled": true, "num_queries": 4},
  "step_back": {"enabled": true},
  "reranking": {"enabled": true, "top_k": 15, "top_n": 5}
}
```

## Project Structure

```
backend/
├── api/
│   ├── __init__.py
│   └── routes.py           # API endpoints
├── models/
│   ├── __init__.py
│   ├── document.py         # Document models
│   ├── query.py            # Query/response models
│   └── rag_config.py       # Configuration models
├── services/
│   ├── __init__.py
│   ├── onenote_service.py  # OneNote API integration
│   ├── document_processor.py  # Text processing
│   ├── vector_store.py     # ChromaDB operations
│   ├── rag_engine.py       # Main RAG logic
│   └── rag_techniques.py   # Advanced techniques
├── config.py               # Configuration management
├── main.py                 # FastAPI application
├── requirements.txt
└── README.md
```

## LangSmith Monitoring

All queries are automatically traced in LangSmith. Visit your LangSmith dashboard to see:
- Query traces
- Latency metrics
- Token usage
- Technique comparisons

## Troubleshooting

### Vector Database Issues
If you encounter ChromaDB errors, try clearing the database:
```bash
rm -rf ./data/chroma_db
```

### OneNote Authentication
If OneNote integration fails, the API will still work in demo mode. Check your Microsoft credentials in `.env`.

### Memory Issues
For large document collections, consider:
- Reducing `chunk_size`
- Limiting `retrieval_k`
- Processing documents in batches

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black .
```

Type checking:
```bash
mypy .
```

## License

MIT License
