"""
Main RAG engine that orchestrates query processing.
"""
import logging
import time
import httpx
from typing import List, Dict, Any, Optional
 
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
 
from models.rag_config import RAGConfig
from models.query import QueryResponse, Source, ResponseMetadata
from .rag_techniques import RAGTechniques
from .vector_store import VectorStoreService
 
logger = logging.getLogger(__name__)
 
 
class RAGEngine:
    """Main RAG engine for processing queries."""
 
    def __init__(self, vector_store: VectorStoreService):
        """
        Initialize RAG engine.
 
        Args:
            vector_store: Vector store service instance
        """
        self.vector_store = vector_store
        self.default_config = RAGConfig()
 
    def query(
        self,
        question: str,
        config: Optional[RAGConfig] = None
    ) -> QueryResponse:
        """
        Process a query using RAG.
 
        Args:
            question: User question
            config: RAG configuration (uses default if not provided)
 
        Returns:
            QueryResponse with answer and metadata
        """
        start_time = time.time()
 
        # Use default config if not provided
        if config is None:
            config = self.default_config
 
        logger.info(f"Processing query: {question[:100]}...")
 
        # Initialize LLM with SSL verification disabled for corporate proxies
        http_client = httpx.Client(verify=False)
        llm = ChatOpenAI(
            model_name=config.model_name,
            temperature=config.temperature,
            http_client=http_client
        )
 
        # Get retriever
        retriever = self.vector_store.get_retriever(k=config.retrieval_k)
 
        # Track which techniques are used
        techniques_used = ["basic_rag"]
 
        # Initialize RAG techniques
        rag_techniques = RAGTechniques(llm)
 
        # Apply advanced techniques to get documents
        retrieved_docs = []
 
        # Check which techniques are enabled and apply them
        if config.multi_query.enabled:
            techniques_used.append("multi_query")
            retrieved_docs = rag_techniques.multi_query_retrieval(
                question, retriever, config.multi_query
            )
 
        elif config.rag_fusion.enabled:
            techniques_used.append("rag_fusion")
            retrieved_docs = rag_techniques.rag_fusion(
                question, retriever, config.rag_fusion
            )
 
        elif config.decomposition.enabled and config.decomposition.mode == "recursive":
            techniques_used.append("decomposition_recursive")
            answer, retrieved_docs = rag_techniques.decomposition_recursive(
                question, retriever, config.decomposition
            )
            # For decomposition, we already have the answer
            return self._build_response(
                answer=answer,
                documents=retrieved_docs,
                techniques_used=techniques_used,
                config=config,
                start_time=start_time
            )
 
        elif config.hyde.enabled:
            techniques_used.append("hyde")
            retrieved_docs = rag_techniques.hyde(question, retriever)
 
        elif config.step_back.enabled:
            techniques_used.append("step_back")
            normal_docs, step_back_docs = rag_techniques.step_back_prompting(
                question, retriever, config.step_back
            )
            retrieved_docs = normal_docs + step_back_docs
 
        else:
            # Basic retrieval
            retrieved_docs = retriever.get_relevant_documents(question)
 
        # Apply re-ranking if enabled
        if config.reranking.enabled and retrieved_docs:
            techniques_used.append("reranking")
            retrieved_docs = self._apply_reranking(
                question, retrieved_docs, config
            )
 
        # Limit documents to retrieval_k
        retrieved_docs = retrieved_docs[:config.retrieval_k]
 
        # Limit context size to prevent token overflow
        retrieved_docs = self._limit_context_size(retrieved_docs, max_tokens=20000)
 
        # Log retrieved documents for verification
        logger.info(f"Retrieved {len(retrieved_docs)} documents for answer generation")
        for i, doc in enumerate(retrieved_docs[:3], 1):  # Log first 3
            logger.info(f"  Doc {i}: {doc.metadata.get('page_title', 'N/A')} "
                       f"[chunk {doc.metadata.get('chunk_index', 'N/A')}/{doc.metadata.get('total_chunks', 'N/A')}] "
                       f"- {len(doc.page_content)} chars")
 
        # Generate answer
        answer = self._generate_answer(question, retrieved_docs, llm, config)
 
        # Build response
        response = self._build_response(
            answer=answer,
            documents=retrieved_docs,
            techniques_used=techniques_used,
            config=config,
            start_time=start_time
        )
 
        logger.info(f"Query processed in {response.metadata.latency_ms}ms")
        return response
 
    def _limit_context_size(
        self,
        documents: List[Document],
        max_tokens: int = 20000
    ) -> List[Document]:
        """
        Limit documents to prevent token overflow.
        Uses approximate token count (1 token ≈ 4 characters).
 
        Also filters out abnormally large documents that shouldn't have been retrieved.
 
        Args:
            documents: List of documents
            max_tokens: Maximum tokens to allow
 
        Returns:
            Filtered list of documents
        """
        if not documents:
            return documents
 
        # First, filter out suspiciously large documents (likely un-chunked)
        # Normal chunks should be under 2000 chars (chunk_size=1000 + overlap=200 + margin)
        MAX_CHUNK_SIZE = 3000
        filtered_docs = []
 
        for doc in documents:
            doc_chars = len(doc.page_content)
            if doc_chars > MAX_CHUNK_SIZE:
                logger.warning(
                    f"Skipping abnormally large document: {doc_chars} chars, "
                    f"chunk_index={doc.metadata.get('chunk_index', 'N/A')}, "
                    f"title={doc.metadata.get('page_title', 'N/A')}"
                )
                continue
            filtered_docs.append(doc)
 
        documents = filtered_docs
 
        # Now apply token limit
        total_chars = 0
        max_chars = max_tokens * 4
        limited_docs = []
 
        for doc in documents:
            doc_chars = len(doc.page_content)
            if total_chars + doc_chars <= max_chars:
                limited_docs.append(doc)
                total_chars += doc_chars
            else:
                # Stop adding documents - don't truncate
                logger.debug(f"Reached token limit, stopping at {len(limited_docs)} documents")
                break
 
        if len(limited_docs) < len(documents):
            logger.info(
                f"Limited context from {len(documents)} to {len(limited_docs)} documents "
                f"to stay within {max_tokens} token limit"
            )
 
        return limited_docs
 
    def _generate_answer(
        self,
        question: str,
        documents: List[Document],
        llm: ChatOpenAI,
        config: RAGConfig
    ) -> str:
        """
        Generate answer from question and retrieved documents.
 
        Args:
            question: User question
            documents: Retrieved documents
            llm: Language model
            config: RAG configuration
 
        Returns:
            Generated answer
        """
        if not documents:
            return "I couldn't find any relevant information to answer your question."
 
        # Format context with source attribution
        context_parts = []
        for i, doc in enumerate(documents, 1):
            page_title = doc.metadata.get("page_title", "Unknown")
            notebook = doc.metadata.get("notebook_name", "Unknown")
            section = doc.metadata.get("section_name", "Unknown")
           
            context_parts.append(
                f"[Source {i}: {page_title} - {notebook}/{section}]\n{doc.page_content}"
            )
       
        context = "\n\n---\n\n".join(context_parts)
 
        # Log context being sent (first 500 chars)
        logger.debug(f"Context being sent to LLM ({len(context)} chars): {context[:500]}...")
 
        # Create prompt with detailed instructions
        template = """You are an expert OneNote knowledge assistant delivering precise, well-structured answers grounded in provided document context.
 
**CONTEXT (Retrieved OneNote Documents):**
{context}
 
**USER QUESTION:**
{question}
 
**RESPONSE REQUIREMENTS:**
 
**1. CONTENT GUIDELINES:**
- Answer directly and comprehensively using the information from the context above
- If the context contains relevant information, provide it even if incomplete
- Synthesize information across multiple sources when relevant
- Cite sources explicitly (e.g., "According to [Source 2], ..." or "As mentioned in [Source 1] and [Source 3], ...")
- If the context is partial, provide what's available and note what's missing (e.g., "Based on the available documents, [answer]. Additional details about [specific topic] were not found in the documents.")
- Only say you can't answer if the context is completely unrelated to the question
- Distinguish between facts from documents vs. logical inferences you make
 
**2. STRUCTURE & FORMATTING:**
- Use **markdown formatting** for readability:
  * **Bold** for key terms and emphasis
  * Bullet lists (- item) for multiple points
  * Numbered lists (1. item) for sequential steps
  * Code blocks (```language```) for any code/commands
  * Headers (##, ###) for longer answers with sections
  * Blockquotes (>) for direct quotes or important callouts
- Organize complex answers with clear sections
- Lead with a direct answer, then provide supporting details
 
**3. TONE & STYLE:**
- Professional yet conversational
- Concise but thorough (prefer clarity over brevity)
- Confident on sourced facts, cautious on inferences
- Helpful and actionable
 
**YOUR ANSWER:**"""
 
        prompt = ChatPromptTemplate.from_template(template)
 
        # Generate answer
        chain = prompt | llm | StrOutputParser()
 
        try:
            answer = chain.invoke({
                "context": context,
                "question": question
            })
            return answer
 
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return f"Error generating answer: {str(e)}"
 
    def _apply_reranking(
        self,
        question: str,
        documents: List[Document],
        config: RAGConfig
    ) -> List[Document]:
        """
        Apply re-ranking to documents.
 
        Args:
            question: User question
            documents: Documents to re-rank
            config: RAG configuration
 
        Returns:
            Re-ranked documents
        """
        # Simple re-ranking: return top N documents based on initial retrieval scores
        return documents[:config.reranking.top_n]
 
    def _build_response(
        self,
        answer: str,
        documents: List[Document],
        techniques_used: List[str],
        config: RAGConfig,
        start_time: float
    ) -> QueryResponse:
        """
        Build query response object.
 
        Args:
            answer: Generated answer
            documents: Retrieved documents
            techniques_used: List of techniques applied
            config: RAG configuration
            start_time: Query start time
 
        Returns:
            QueryResponse object
        """
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
 
        # Build sources
        sources = []
        for doc in documents:
            source = Source(
                document_id=doc.metadata.get("page_id", "unknown"),
                page_title=doc.metadata.get("page_title", "Unknown"),
                notebook_name=doc.metadata.get("notebook_name", "Unknown"),
                section_name=doc.metadata.get("section_name", "Unknown"),
                content_snippet=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                relevance_score=0.0,  # Would need to calculate this properly
                url=doc.metadata.get("url", "")
            )
            sources.append(source)
 
        # Build metadata
        metadata = ResponseMetadata(
            techniques_used=techniques_used,
            latency_ms=latency_ms,
            tokens_used=None,  # Would need to track this
            cost_usd=None,  # Would need to calculate this
            model_name=config.model_name,
            retrieval_k=len(documents)
        )
 
        return QueryResponse(
            answer=answer,
            sources=sources,
            metadata=metadata
        )
 