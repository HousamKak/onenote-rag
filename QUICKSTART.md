# 🚀 Quick Start - OneNote RAG System

## Prerequisites Check
- [ ] Python 3.9+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] OpenAI API key
- [ ] LangSmith API key

## Setup (5 minutes)

### Backend

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
copy .env.example .env  # Windows
cp .env.example .env    # Mac/Linux

# 6. Edit .env and add your API keys
# Required:
#   OPENAI_API_KEY=sk-...
#   LANGCHAIN_API_KEY=lsv2_pt_...
#   LANGCHAIN_PROJECT=onenote-rag

# 7. Run backend
python main.py
```

Backend runs at: **http://localhost:8000**
API Docs: **http://localhost:8000/docs**

### Frontend

```bash
# 1. Navigate to frontend (new terminal)
cd frontend

# 2. Install dependencies
npm install

# 3. Run development server
npm run dev
```

Frontend runs at: **http://localhost:5173**

## First Use (2 minutes)

1. **Open Browser**: `http://localhost:5173`

2. **Add Demo Documents**:
   - Go to "Index" tab
   - Scroll to "Add Demo Documents"
   - Paste these examples:

```
Document 1:
LangChain is a framework for developing applications powered by language models. It provides modular components for document loading, text splitting, embeddings, vector stores, and chains that combine these components into powerful workflows.

Document 2:
Retrieval-Augmented Generation (RAG) is a technique that enhances LLM responses by retrieving relevant documents from a knowledge base. The process involves: 1) Embedding and storing documents in a vector database, 2) Retrieving relevant documents based on query similarity, 3) Providing retrieved documents as context to the LLM for answer generation.

Document 3:
ChromaDB is an open-source embedding database designed for LLM applications. It stores document embeddings and enables fast similarity search. ChromaDB supports metadata filtering, persistence, and can be used as a vector store for retrieval-augmented generation systems.
```

   - Click "Add to Index"
   - Wait for success message

3. **Ask Your First Question**:
   - Go to "Query" tab
   - Type: "What is RAG?"
   - Click "Ask"
   - View the answer with sources!

4. **Try Different Configurations**:
   - Go to "Config" tab
   - Try different presets (Fast, Balanced, Quality)
   - Save and query again

5. **Compare Results**:
   - Go to "Compare" tab
   - Select Fast, Balanced, and Quality
   - Ask: "Explain vector databases for LLMs"
   - See results side-by-side!

## Verify Installation

### Backend Health Check
```bash
curl http://localhost:8000/api/health
# Should return: {"status":"healthy"}
```

### Frontend Working
- Open http://localhost:5173
- Should see "OneNote RAG" header
- All tabs should be clickable

### LangSmith Tracking
- Open https://smith.langchain.com
- Go to your project "onenote-rag"
- Should see traces after running queries

## Troubleshooting

### Backend Issues

**"Module not found" error**
```bash
pip install --upgrade -r requirements.txt
```

**"ChromaDB error"**
```bash
rm -rf ./data/chroma_db
python main.py
```

**"OpenAI API key not found"**
- Check `.env` file exists in `backend/` folder
- Verify `OPENAI_API_KEY=sk-...` is set correctly

### Frontend Issues

**"npm install" fails**
```bash
rm -rf node_modules package-lock.json
npm install
```

**"Cannot connect to API"**
- Verify backend is running on port 8000
- Check console for CORS errors
- Try: `curl http://localhost:8000/api/health`

**Blank page / errors**
- Open browser console (F12)
- Check for errors
- Try `npm run dev` again

## Next Steps

1. **Connect to OneNote** (optional):
   - Get Microsoft Azure app credentials
   - Add to backend `.env`
   - Use "Full Sync" button

2. **Explore Advanced Features**:
   - Enable multi-query in Config
   - Try query decomposition
   - Compare different techniques

3. **Monitor with LangSmith**:
   - View query traces
   - Analyze performance
   - Track costs

4. **Customize**:
   - Add your own documents
   - Adjust configuration parameters
   - Try different questions

## Common Demo Scenarios

### Quick Lookup (Fast mode)
```
Q: "What is LangChain?"
Expected: 1-2 second response with accurate definition
```

### Detailed Analysis (Quality mode)
```
Q: "Explain the complete RAG pipeline"
Expected: 6-8 second response with comprehensive explanation
```

### Comparison
```
Q: "What are vector databases?"
Configs: Fast vs Quality
Expected: Side-by-side comparison showing quality difference
```

## Getting Help

- **API Documentation**: http://localhost:8000/docs
- **README**: See main README.md
- **Demo Guide**: See DEMO_GUIDE.md
- **Backend Logs**: Check terminal running `python main.py`
- **Frontend Logs**: Check browser console (F12)

---

**You're all set! 🎉**

Start with the "Index" tab to add documents, then head to "Query" to start asking questions!
