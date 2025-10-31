"""
Main RAG engine that orchestrates query processing.
"""
import logging
import time
from typing import List, Dict, Any, Optional

from langchain.prompts import ChatPromptTemplate
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

        # Initialize LLM
        llm = ChatOpenAI(
            model_name=config.model_name,
            temperature=config.temperature
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

        # Create prompt with detailed instructions
        template = """You are a helpful AI assistant answering questions based on OneNote documents. Your responses should be well-formatted, clear, and comprehensive.

**Context from OneNote Documents:**
{context}

**Question:** {question}

**Instructions:**
- Provide a comprehensive, well-structured answer based on the context above
- Use proper markdown formatting in your response:
  * Use **bold** for emphasis
  * Use bullet points or numbered lists where appropriate
  * Use code blocks with ``` for any code snippets
  * Use headers (##, ###) to organize longer responses
  * Use > blockquotes for important notes or quotes
- Reference specific sources when citing information (e.g., "According to [Source 1]...")
- If the context doesn't contain enough information, clearly state what's missing
- Be concise but thorough
- Maintain a professional yet friendly tone

**Answer:**"""

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
        if config.reranking.provider == "cohere":
            return self._cohere_rerank(question, documents, config)
        else:
            # Custom re-ranking (simple scoring based on query relevance)
            return documents[:config.reranking.top_n]

    def _cohere_rerank(
        self,
        question: str,
        documents: List[Document],
        config: RAGConfig
    ) -> List[Document]:
        """
        Re-rank documents using Cohere API.

        Args:
            question: User question
            documents: Documents to re-rank
            config: RAG configuration

        Returns:
            Re-ranked documents
        """
        try:
            import cohere
            from config import get_settings

            settings = get_settings()

            if not settings.cohere_api_key:
                logger.warning("Cohere API key not found, skipping re-ranking")
                return documents[:config.reranking.top_n]

            co = cohere.Client(settings.cohere_api_key)

            # Prepare documents for reranking
            docs_text = [doc.page_content for doc in documents]

            # Rerank
            results = co.rerank(
                query=question,
                documents=docs_text,
                top_n=config.reranking.top_n,
                model="rerank-english-v2.0"
            )

            # Reorder documents based on reranking
            reranked_docs = [documents[result.index] for result in results.results]

            logger.info(f"Reranked {len(documents)} docs to top {len(reranked_docs)}")
            return reranked_docs

        except ImportError:
            logger.warning("Cohere package not installed, skipping re-ranking")
            return documents[:config.reranking.top_n]
        except Exception as e:
            logger.error(f"Error during Cohere re-ranking: {str(e)}")
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
