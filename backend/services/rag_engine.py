"""
Main RAG engine that orchestrates query processing with multimodal support.
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
from models.query import QueryResponse, Source, ResponseMetadata, ImageReference
from .rag_techniques import RAGTechniques
from .vector_store import VectorStoreService
from .multimodal_query import MultimodalQueryHandler
 
logger = logging.getLogger(__name__)
 
 
class RAGEngine:
    """Main RAG engine for processing queries with multimodal support."""
 
    def __init__(
        self,
        vector_store: VectorStoreService,
        multimodal_handler: Optional[MultimodalQueryHandler] = None
    ):
        """
        Initialize RAG engine.
 
        Args:
            vector_store: Vector store service instance
            multimodal_handler: Optional multimodal query handler for visual queries
        """
        self.vector_store = vector_store
        self.default_config = RAGConfig()
        self.multimodal_handler = multimodal_handler
 
        if multimodal_handler:
            logger.info("RAG engine initialized with multimodal support")
        else:
            logger.info("RAG engine initialized (text-only mode)")
 
    async def query_async(
        self,
        question: str,
        config: Optional[RAGConfig] = None
    ) -> QueryResponse:
        """
        Process a query using RAG with full multimodal support (async version).
 
        This method supports visual queries and can retrieve images along with text answers.
 
        Args:
            question: User question
            config: RAG configuration (uses default if not provided)
 
        Returns:
            QueryResponse with answer, sources, and optionally images
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
 
        # Apply "source of truth" filtering: documents retrieved 3+ times are kept entirely
        retrieved_docs = self._apply_source_of_truth_filter(retrieved_docs, threshold=3)
 
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
 
        # Check if multimodal enhancement is available and needed
        images = []
        filter_result = None
        if self.multimodal_handler:
            try:
                # Get potential images from documents
                images = await self.multimodal_handler.get_images_from_documents(
                    documents=retrieved_docs,
                    max_images=10  # Get more than needed for filtering
                )
               
                # Apply intelligent context filtering if enabled
                if config.context_filter.enabled:
                    from services.context_filter import ContextFilterService
                   
                    techniques_used.append("context_filtering")
                    logger.info(f"Applying context filter (strictness: {config.context_filter.strictness})")
                   
                    # Create filter
                    context_filter = ContextFilterService(
                        model_name=config.context_filter.model_name,
                        temperature=0.0,
                        strictness=config.context_filter.strictness
                    )
                   
                    # Filter context (both chunks and images)
                    retrieved_docs, images, filter_result = await context_filter.filter_context(
                        query=question,
                        documents=retrieved_docs,
                        images=images,
                        max_relevant_chunks=config.context_filter.max_relevant_chunks,
                        max_relevant_images=config.context_filter.max_relevant_images
                    )
                   
                    logger.info(
                        f"Context filter: {len(retrieved_docs)} chunks, {len(images)} images kept as relevant"
                    )
               
                # Enhance answer with images if it's a visual query
                if images:
                    answer, images = await self.multimodal_handler.enhance_query_response(
                        query=question,
                        documents=retrieved_docs,
                        base_answer=self._generate_answer(question, retrieved_docs, llm, config),
                        max_images=len(images),  # Use all filtered images
                        pre_filtered_images=images  # Pass filtered images directly
                    )
                    if images:
                        techniques_used.append("multimodal_visual_query")
                        logger.info(f"Enhanced answer with {len(images)} images")
                else:
                    # No images, generate text-only answer
                    answer = self._generate_answer(question, retrieved_docs, llm, config)
            except Exception as e:
                logger.error(f"Error enhancing with multimodal: {str(e)}", exc_info=True)
                # Continue with text-only answer
                answer = self._generate_answer(question, retrieved_docs, llm, config)
        else:
            # Generate answer without multimodal
            answer = self._generate_answer(question, retrieved_docs, llm, config)
 
        # Build response
        response = self._build_response(
            answer=answer,
            documents=retrieved_docs,
            techniques_used=techniques_used,
            config=config,
            start_time=start_time,
            images=images,
            filter_result=filter_result
        )
 
        logger.info(f"Query processed in {response.metadata.latency_ms}ms")
        return response
 
    def query(
        self,
        question: str,
        config: Optional[RAGConfig] = None
    ) -> QueryResponse:
        """
        Process a query using RAG (synchronous version - text-only).
 
        NOTE: For multimodal support (images), use query_async() instead.
        This method is kept for backwards compatibility with the current API.
 
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
 
        # Build response (text-only in sync version)
        response = self._build_response(
            answer=answer,
            documents=retrieved_docs,
            techniques_used=techniques_used,
            config=config,
            start_time=start_time
        )
 
        logger.info(f"Query processed in {response.metadata.latency_ms}ms")
        return response
 
    def _apply_source_of_truth_filter(
        self,
        documents: List[Document],
        threshold: int = 3
    ) -> List[Document]:
        """
        Apply "source of truth" filtering: if a document (page) is retrieved 3+ times,
        keep all chunks from that document and discard chunks from less-frequently retrieved documents.
       
        This helps focus on highly relevant documents that consistently appear in results.
       
        Args:
            documents: List of retrieved documents
            threshold: Minimum number of times a page must appear to be considered "source of truth"
           
        Returns:
            Filtered list of documents, prioritizing high-frequency sources
        """
        if not documents or len(documents) <= threshold:
            return documents
       
        # Count how many times each page appears
        from collections import Counter
        page_counts = Counter()
       
        for doc in documents:
            page_id = doc.metadata.get("page_id", "unknown")
            page_counts[page_id] += 1
       
        # Identify "source of truth" pages (retrieved threshold+ times)
        source_of_truth_pages = {
            page_id for page_id, count in page_counts.items()
            if count >= threshold
        }
       
        if not source_of_truth_pages:
            # No pages meet threshold, return original list
            return documents
       
        # Filter: keep only chunks from source-of-truth pages
        filtered_docs = [
            doc for doc in documents
            if doc.metadata.get("page_id", "unknown") in source_of_truth_pages
        ]
       
        # Log the filtering decision
        if len(filtered_docs) < len(documents):
            discarded = len(documents) - len(filtered_docs)
            page_titles = {doc.metadata.get("page_title", "Unknown") for doc in filtered_docs}
            logger.info(
                f"Source-of-truth filter: Kept {len(filtered_docs)} chunks from {len(source_of_truth_pages)} "
                f"high-frequency page(s) [{', '.join(list(page_titles)[:3])}{'...' if len(page_titles) > 3 else ''}], "
                f"discarded {discarded} chunks from lower-frequency pages"
            )
       
        return filtered_docs
 
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
        template = """You are an expert OneNote knowledge assistant. Provide answers that are **concise, direct, and to the point** unless the query explicitly asks for elaboration or detailed explanation.
 
**CONTEXT (Retrieved OneNote Documents):**
{context}
 
**USER QUESTION:**
{question}
 
**RESPONSE REQUIREMENTS:**
 
**1. CONTENT GUIDELINES:**
- **Answer directly and concisely** - get straight to the point
- Start with the core answer in 1-2 sentences, then add supporting details only if needed
- Use the information from the context above
- Synthesize information across sources when relevant
- Cite sources when appropriate (e.g., "According to [Source 2], ...")
- If the context is incomplete, provide what's available briefly
- Only say you can't answer if the context is completely unrelated
- **Exception:** If the query asks for "detailed", "comprehensive", "explain in detail", or similar elaboration keywords, provide thorough answers
 
**2. STRUCTURE & FORMATTING:**
- Use **markdown formatting** strategically:
  * **Bold** for key terms
  * Bullet lists (- item) for multiple distinct points
  * Numbered lists (1. item) for sequential steps
  * Code blocks (```language```) for code/commands
  * Headers (##, ###) only for longer, multi-section answers
  * Blockquotes (>) for important callouts
- Keep formatting clean and minimal for short answers
- For complex topics, organize with clear structure
 
**3. TONE & STYLE:**
- **Concise and direct** - respect the user's time
- Professional yet conversational
- Lead with the answer, not preamble
- No unnecessary hedging or filler phrases
 
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
        start_time: float,
        images: Optional[List[Dict]] = None,
        filter_result: Optional[any] = None
    ) -> QueryResponse:
        """
        Build query response object.
 
        Args:
            answer: Generated answer
            documents: Retrieved documents
            techniques_used: List of techniques applied
            config: RAG configuration
            start_time: Query start time
            images: Optional list of images for multimodal responses
 
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
        filter_summary = None
        if filter_result:
            filter_summary = {
                "chunks_kept": len(filter_result.relevant_chunks),
                "chunks_filtered": len(filter_result.filtered_chunks),
                "images_kept": len(filter_result.relevant_images),
                "images_filtered": len(filter_result.filtered_images),
                "overall_assessment": filter_result.overall_assessment
            }
       
        metadata = ResponseMetadata(
            techniques_used=techniques_used,
            latency_ms=latency_ms,
            tokens_used=None,  # Would need to track this
            cost_usd=None,  # Would need to calculate this
            model_name=config.model_name,
            retrieval_k=len(documents),
            filter_summary=filter_summary
        )
 
        # Format images for response if provided
        image_references = None
        if images and self.multimodal_handler:
            formatted_images = self.multimodal_handler.format_images_for_response(images)
            image_references = [
                ImageReference(
                    page_id=img["page_id"],
                    page_title=img["page_title"],
                    image_index=img["image_index"],
                    image_path=img["image_path"],
                    public_url=img["public_url"]
                )
                for img in formatted_images
            ]
 
        return QueryResponse(
            answer=answer,
            sources=sources,
            metadata=metadata,
            images=image_references
        )
 