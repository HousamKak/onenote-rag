"""
Context Filter Service - Intelligent relevance evaluation for retrieved content.
 
This service uses GPT-4 to evaluate which retrieved text chunks and images
are actually relevant to the user's question before generating the final answer.
 
Benefits:
- Reduces token usage by filtering out irrelevant content
- Improves answer quality by focusing on relevant information
- Provides transparency about what was filtered and why
- Intelligently filters images based on visual content relevance
"""
 
import logging
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import httpx
 
logger = logging.getLogger(__name__)
 
 
class RelevantChunk(BaseModel):
    """A text chunk marked as relevant."""
    chunk_index: int = Field(description="Index of the chunk in the original list")
    page_title: str = Field(description="Title of the page this chunk is from")
    relevance_score: float = Field(description="Relevance score from 0.0 to 1.0", ge=0.0, le=1.0)
    reason: str = Field(description="Why this chunk is relevant to the query")
 
 
class RelevantImage(BaseModel):
    """An image marked as relevant."""
    page_id: str = Field(description="Page ID of the document")
    image_index: int = Field(description="Index of the image in the document")
    page_title: str = Field(description="Title of the page")
    relevance_score: float = Field(description="Relevance score from 0.0 to 1.0", ge=0.0, le=1.0)
    reason: str = Field(description="Why this image is likely relevant based on context")
 
 
class FilteredChunk(BaseModel):
    """A text chunk marked as NOT relevant."""
    chunk_index: int = Field(description="Index of the chunk in the original list")
    page_title: str = Field(description="Title of the page")
    reason: str = Field(description="Why this chunk is NOT relevant")
 
 
class FilteredImage(BaseModel):
    """An image marked as NOT relevant."""
    page_id: str = Field(description="Page ID")
    image_index: int = Field(description="Image index")
    page_title: str = Field(description="Page title")
    reason: str = Field(description="Why this image is NOT relevant")
 
 
class ContextFilterResult(BaseModel):
    """Result of context filtering."""
    relevant_chunks: List[RelevantChunk] = Field(description="Text chunks that are relevant")
    relevant_images: List[RelevantImage] = Field(description="Images that are likely relevant")
    filtered_out_chunks: List[FilteredChunk] = Field(description="Chunks filtered out as not relevant")
    filtered_out_images: List[FilteredImage] = Field(description="Images filtered out as not relevant")
    overall_assessment: str = Field(description="Overall assessment of the retrieved content quality")
 
 
class ContextFilterService:
    """
    Service to filter retrieved context for relevance using GPT-4.
   
    This acts as an intelligent "gatekeeper" before answer generation.
    """
   
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.0,
        strictness: str = "balanced"
    ):
        """
        Initialize context filter.
       
        Args:
            model_name: LLM model to use for filtering (gpt-4o-mini is cost-effective)
            temperature: Temperature for filtering (0.0 for deterministic)
            strictness: How strict to be - "lenient", "balanced", "strict"
        """
        self.model_name = model_name
        self.temperature = temperature
        self.strictness = strictness
       
        # Initialize LLM with async HTTP client (SSL verification disabled for corporate proxies)
        http_client = httpx.AsyncClient(verify=False)
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            http_client=http_client
        )
       
        logger.info(f"Context filter initialized with {model_name} (strictness: {strictness})")
   
    async def filter_context(
        self,
        query: str,
        documents: List[Document],
        images: List[Dict[str, Any]],
        max_relevant_chunks: int = 10,
        max_relevant_images: int = 5
    ) -> Tuple[List[Document], List[Dict[str, Any]], ContextFilterResult]:
        """
        Filter retrieved documents and images for relevance.
       
        Args:
            query: User's question
            documents: Retrieved text chunks
            images: Retrieved images with metadata
            max_relevant_chunks: Maximum chunks to keep
            max_relevant_images: Maximum images to keep
           
        Returns:
            Tuple of (filtered_documents, filtered_images, filter_result)
        """
        try:
            logger.info(f"Filtering {len(documents)} chunks and {len(images)} images for query: {query[:100]}...")
           
            # Build filtering prompt
            prompt = self._build_filter_prompt(
                query=query,
                documents=documents,
                images=images,
                max_relevant_chunks=max_relevant_chunks,
                max_relevant_images=max_relevant_images
            )
           
            # Use structured output to get filtering decisions
            structured_llm = self.llm.with_structured_output(ContextFilterResult)
            filter_result = await structured_llm.ainvoke(prompt)
           
            # Apply filtering
            filtered_docs = self._apply_chunk_filter(documents, filter_result.relevant_chunks)
            filtered_images = self._apply_image_filter(images, filter_result.relevant_images)
           
            logger.info(
                f"Context filter: {len(filtered_docs)}/{len(documents)} chunks kept, "
                f"{len(filtered_images)}/{len(images)} images kept"
            )
           
            return (filtered_docs, filtered_images, filter_result)
           
        except Exception as e:
            logger.error(f"Error in context filtering: {e}", exc_info=True)
            # On error, return original content (fail-safe)
            logger.warning("Returning unfiltered content due to error")
            return (documents, images, None)
   
    def _build_filter_prompt(
        self,
        query: str,
        documents: List[Document],
        images: List[Dict[str, Any]],
        max_relevant_chunks: int,
        max_relevant_images: int
    ) -> str:
        """Build prompt for context filtering."""
       
        strictness_guidance = {
            "lenient": "Be inclusive - keep content that might be tangentially related.",
            "balanced": "Balance precision and recall - keep clearly relevant content and potentially useful context.",
            "strict": "Be selective - only keep content that directly answers or strongly supports the question."
        }
       
        prompt = f"""You are an expert information relevance evaluator. Your task is to evaluate which retrieved text chunks and images are RELEVANT to answering the user's question.
 
**USER QUESTION:**
{query}
 
**EVALUATION CRITERIA:**
{strictness_guidance.get(self.strictness, strictness_guidance["balanced"])}
 
Consider:
1. Direct relevance: Does the content directly answer or address the question?
2. Supporting evidence: Does it provide context, examples, or data that supports an answer?
3. Background info: Is it necessary background to understand the answer?
4. Tangential info: Is it only loosely related or off-topic?
 
**TEXT CHUNKS TO EVALUATE:**
"""
       
        # Add text chunks
        for i, doc in enumerate(documents[:20]):  # Limit to avoid token overflow
            page_title = doc.metadata.get("page_title", "Unknown")
            chunk_preview = doc.page_content[:300]
            prompt += f"\n[Chunk {i}] From: {page_title}\n{chunk_preview}...\n"
       
        if len(documents) > 20:
            prompt += f"\n... and {len(documents) - 20} more chunks\n"
       
        # Add images
        if images:
            prompt += f"\n\n**IMAGES TO EVALUATE:**\n"
            prompt += "Note: You cannot see the actual images, but evaluate based on:\n"
            prompt += "- The page title and context\n"
            prompt += "- Whether visual information (charts, diagrams, screenshots) would help answer this question\n"
            prompt += "- The type of question (if it asks to 'show', 'visualize', 'display', images are likely relevant)\n\n"
           
            for img in images:
                page_id = img.get("page_id", "unknown")
                image_index = img.get("image_index", 0)
                page_title = img.get("page_title", "Unknown")
                prompt += f"[Image {page_id}/{image_index}] From: {page_title}\n"
       
        prompt += f"""
 
**YOUR TASK:**
1. Select up to {max_relevant_chunks} most relevant text chunks
2. Select up to {max_relevant_images} most relevant images (if visual info would help)
3. For each selected item, provide:
   - Relevance score (0.0-1.0)
   - Reason why it's relevant
4. For filtered-out items, briefly explain why they're NOT relevant
 
**OUTPUT:**
Return a structured evaluation with:
- relevant_chunks: List of relevant chunks with scores and reasons
- relevant_images: List of relevant images with scores and reasons  
- filtered_out_chunks: List of filtered chunks with reasons
- filtered_out_images: List of filtered images with reasons
- overall_assessment: Brief assessment of content quality
 
Be decisive and clear in your reasoning.
"""
       
        return prompt
   
    def _apply_chunk_filter(
        self,
        documents: List[Document],
        relevant_chunks: List[RelevantChunk]
    ) -> List[Document]:
        """Apply chunk filter to documents."""
        if not relevant_chunks:
            logger.warning("No relevant chunks identified - returning empty list")
            return []
       
        # Sort by relevance score
        sorted_chunks = sorted(relevant_chunks, key=lambda x: x.relevance_score, reverse=True)
       
        # Keep only the relevant chunks
        filtered_docs = []
        for chunk in sorted_chunks:
            if 0 <= chunk.chunk_index < len(documents):
                filtered_docs.append(documents[chunk.chunk_index])
       
        return filtered_docs
   
    def _apply_image_filter(
        self,
        images: List[Dict[str, Any]],
        relevant_images: List[RelevantImage]
    ) -> List[Dict[str, Any]]:
        """Apply image filter."""
        if not relevant_images:
            logger.info("No relevant images identified")
            return []
       
        # Create lookup set for relevant images
        relevant_set = {
            (img.page_id, img.image_index)
            for img in relevant_images
        }
       
        # Filter images
        filtered = [
            img for img in images
            if (img.get("page_id"), img.get("image_index")) in relevant_set
        ]
       
        # Sort by relevance score
        relevance_map = {
            (img.page_id, img.image_index): img.relevance_score
            for img in relevant_images
        }
        filtered.sort(
            key=lambda x: relevance_map.get((x.get("page_id"), x.get("image_index")), 0),
            reverse=True
        )
       
        return filtered
 