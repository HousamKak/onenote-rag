# OneNote RAG System - Demo Guide

This guide will help you demonstrate the system to your tech lead in under 10 minutes.

## 🎯 Quick Start (5 minutes)

### 1. Setup Environment

```bash
# Terminal 1 - Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Add your OPENAI_API_KEY and LANGCHAIN_API_KEY
```

```bash
# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

### 2. Demo Flow

## 📋 Demonstration Script

### Part 1: System Overview (2 minutes)

**Show**: README.md architecture diagram

**Say**:
> "This is a production-ready RAG system that allows us to query OneNote documents using AI. The key innovation is that we can toggle between 6 different advanced RAG techniques to optimize for speed vs. accuracy based on the use case."

**Highlight**:
- FastAPI backend with LangChain
- React + TypeScript frontend
- ChromaDB vector database
- LangSmith for complete observability

### Part 2: Indexing Demo (2 minutes)

1. Open `http://localhost:5173/index`

**Show**: Index page

**Say**:
> "First, we need to index our documents. Since we might not have OneNote set up yet, I'll use the demo mode to add sample documents."

**Demo**:
```
Document 1: "LangChain is a framework for developing applications powered by language models. It provides tools for document loading, text splitting, embeddings, and vector stores."

Document 2: "RAG (Retrieval-Augmented Generation) combines information retrieval with text generation. It retrieves relevant documents and uses them as context for the LLM to generate accurate answers."

Document 3: "ChromaDB is an open-source embedding database. It's designed to make it easy to build LLM apps by making knowledge, facts, and skills pluggable for LLMs."
```

**Action**:
- Paste the documents
- Click "Add to Index"
- Show the document count increase

### Part 3: Basic Query (2 minutes)

1. Navigate to `http://localhost:5173/query`

**Say**:
> "Now let's ask a question with the default configuration - basic RAG."

**Demo Query**: "What is RAG and how does it work?"

**Show**:
- Answer generation (1-2 seconds)
- Source citations with snippets
- Performance metrics (latency, model used)
- "basic_rag" technique badge

**Highlight**:
> "Notice the answer is accurate, pulled from our indexed documents, and we can see exactly which sources were used. This took about 1.5 seconds."

### Part 4: Advanced Techniques (3 minutes)

1. Navigate to `http://localhost:5173/config`

**Say**:
> "This is where it gets interesting. Let's enable some advanced techniques."

**Demo**:
1. Click "Balanced" preset
   - Show Multi-Query enabled (3 queries)
   - Show Re-ranking enabled
2. Click "Save Configuration"

**Say**:
> "The balanced preset generates multiple query variations and re-ranks results for better accuracy."

3. Go back to Query page
4. Ask the same question: "What is RAG and how does it work?"

**Show**:
- Longer latency (3-4 seconds)
- Multiple technique badges: ["multi_query", "reranking"]
- Potentially different/better answer

**Highlight**:
> "Same question, but now we're using multi-query retrieval and re-ranking. Notice the latency increased, but we likely got more comprehensive results."

### Part 5: Configuration Comparison (2 minutes)

1. Navigate to `http://localhost:5173/compare`

**Say**:
> "Finally, let's compare different configurations side-by-side."

**Demo**:
1. Select: Fast, Balanced, Quality
2. Enter query: "Explain vector databases for LLMs"
3. Click "Compare"

**Show**:
- Three answers side-by-side
- Latency comparison
- Technique badges for each
- Quality differences

**Highlight**:
> "This comparison view lets us empirically test which configuration works best for different types of questions. Fast gives quick answers, Quality uses all techniques for maximum accuracy."

## 💡 Key Points to Emphasize

### 1. Production-Ready Features
- ✅ Clean architecture with separation of concerns
- ✅ Type-safe TypeScript frontend
- ✅ Comprehensive error handling
- ✅ LangSmith integration for monitoring
- ✅ Configurable and extensible

### 2. Advanced RAG Techniques
- Multi-Query: Generates 5 different versions of the query
- RAG-Fusion: Reciprocal Rank Fusion for better ranking
- Query Decomposition: Breaks complex questions into sub-questions
- Step-Back Prompting: Asks broader questions for context
- HyDE: Generates hypothetical documents for retrieval
- Re-ranking: Uses Cohere to reorder results

### 3. Flexibility
- Preset configurations for different use cases
- Fine-grained control over each technique
- Side-by-side comparison for empirical testing
- Demo mode works without OneNote

### 4. Observability
- LangSmith traces every query
- Performance metrics visible in UI
- Token usage and cost tracking
- Source attribution for every answer

## 🎤 Talking Points by Audience

### For Technical Leads
- "Modern tech stack: FastAPI, React 18, TypeScript, LangChain"
- "6 advanced RAG techniques based on latest research papers"
- "Modular design allows easy addition of new techniques"
- "Complete observability with LangSmith"

### For Product Managers
- "Users can optimize for speed vs. accuracy based on their needs"
- "Clear source attribution builds trust"
- "Comparison mode helps users find the right balance"
- "Works with existing OneNote investment"

### For Data Scientists
- "Implements cutting-edge RAG techniques: RAG-Fusion, HyDE, etc."
- "A/B testing built-in with comparison mode"
- "Configurable parameters for experimentation"
- "Full trace data in LangSmith for analysis"

## 🚀 Advanced Demo (If Time Permits)

### Show LangSmith Dashboard
1. Open LangSmith dashboard
2. Show the "onenote-rag" project
3. Click on a recent trace
4. Show:
   - Complete execution flow
   - Individual technique execution times
   - Token usage breakdown
   - Costs per query

### Show Configuration Presets
```python
# backend/models/rag_config.py
PRESET_CONFIGS = {
    "fast": {...},        # Basic RAG, 1-2s
    "balanced": {...},    # Multi-query + reranking, 3-4s
    "quality": {...},     # All techniques, 6-8s
    "research": {...}     # Decomposition focus, 10-15s
}
```

### Show Code Quality
- Open `backend/services/rag_techniques.py`
- Show clean implementation of techniques
- Point out docstrings and type hints
- Show separation of concerns

## 📊 Sample Questions for Demo

**Quick Lookup** (Use Fast):
- "What is LangChain?"
- "What does ChromaDB do?"

**Comparison** (Use Balanced):
- "What's the difference between RAG and fine-tuning?"
- "Compare vector databases and traditional databases"

**Complex Analysis** (Use Quality/Research):
- "Explain the complete RAG pipeline from document ingestion to answer generation"
- "What are the tradeoffs between different RAG optimization techniques?"

## 🎯 Closing

**Summary Statement**:
> "In summary, we've built a production-ready RAG system that:
> 1. Indexes OneNote documents efficiently
> 2. Provides configurable query answering with 6 advanced techniques
> 3. Allows empirical comparison of different approaches
> 4. Includes complete observability and monitoring
>
> This gives us a flexible foundation for document Q&A that can be optimized for different use cases - from quick lookups to deep research."

**Next Steps**:
- Connect to actual OneNote instance
- Add authentication/authorization
- Deploy to staging environment
- Gather user feedback on configurations

## 📝 Questions You Might Get

**Q: Why not just use ChatGPT?**
A: ChatGPT doesn't have access to our private OneNote data and can hallucinate. RAG grounds answers in our actual documents with source citations.

**Q: What's the cost per query?**
A: Fast: ~$0.01, Balanced: ~$0.03, Quality: ~$0.06. Varies with document length.

**Q: Can we add more techniques?**
A: Yes! The architecture is modular. New techniques go in `rag_techniques.py` and can be toggled from the UI.

**Q: How do we choose which configuration?**
A: Use the comparison mode to test with real queries, then pick based on latency/accuracy tradeoff.

**Q: What about data privacy?**
A: All data stays in our infrastructure. OpenAI only sees the query and retrieved chunks, not full documents.

---

**Good luck with your demo! 🚀**
