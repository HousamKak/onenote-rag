"""
Multimodal query handler for detecting and processing visual queries.

Maintains document integrity by using page_id to reunite documents with their images.
"""
import logging
from typing import List, Dict, Optional, Tuple
from langchain_core.documents import Document

from .vision_service import GPT4VisionService
from .image_storage import ImageStorageService

logger = logging.getLogger(__name__)


class MultimodalQueryHandler:
    """
    Handler for multimodal queries that may involve images.

    Detects visual queries and retrieves relevant images from storage
    using page_id to maintain document integrity.
    """

    # Keywords that indicate a visual query
    VISUAL_KEYWORDS = [
        "image", "picture", "photo", "screenshot",
        "diagram", "chart", "graph", "illustration",
        "visual", "show me", "look like", "see",
        "drawing", "sketch", "figure", "plot",
        "visualization", "graphic", "infographic"
    ]

    def __init__(
        self,
        vision_service: GPT4VisionService,
        image_storage: ImageStorageService
    ):
        """
        Initialize multimodal query handler.

        Args:
            vision_service: GPT-4o Vision service
            image_storage: Image storage service
        """
        self.vision_service = vision_service
        self.image_storage = image_storage

    def is_visual_query(self, query: str) -> bool:
        """
        Detect if a query is asking about visual content.

        Args:
            query: User query

        Returns:
            True if query appears to be about visual content
        """
        query_lower = query.lower()

        # Check for visual keywords
        for keyword in self.VISUAL_KEYWORDS:
            if keyword in query_lower:
                logger.debug(f"Visual query detected (keyword: '{keyword}')")
                return True

        # Check for question patterns about visual content
        visual_patterns = [
            "what does", "how does", "what do",
            "what is shown", "what are shown",
            "which image", "which diagram"
        ]

        for pattern in visual_patterns:
            if pattern in query_lower and any(kw in query_lower for kw in ["image", "diagram", "chart", "show"]):
                logger.debug(f"Visual query detected (pattern: '{pattern}')")
                return True

        return False

    async def get_images_from_documents(
        self,
        documents: List[Document],
        max_images: int = 5,
        max_images_per_doc: int = 2
    ) -> List[Dict[str, any]]:
        """
        Extract and download images from retrieved documents using page_id.

        This is where DOCUMENT INTEGRITY is maintained - we use page_id
        to find all images belonging to retrieved documents.

        Args:
            documents: Retrieved documents from vector store
            max_images: Maximum total images to retrieve
            max_images_per_doc: Maximum images per document

        Returns:
            List of image data dictionaries
        """
        images = []

        for doc in documents:
            if len(images) >= max_images:
                break

            # Check if document has images
            if not doc.metadata.get("has_images", False):
                continue

            page_id = doc.metadata.get("page_id")  # ← The magic key!
            image_count = doc.metadata.get("image_count", 0)

            if not page_id:
                continue

            # Get images for this document (up to max_images_per_doc)
            doc_images_count = min(image_count, max_images_per_doc)

            for i in range(doc_images_count):
                if len(images) >= max_images:
                    break

                try:
                    # Generate image path using page_id
                    image_path = self.image_storage.generate_image_path(
                        page_id=page_id,
                        image_index=i
                    )

                    # Check if image exists
                    if not await self.image_storage.exists(image_path):
                        logger.warning(f"Image not found: {image_path}")
                        continue

                    # Download image
                    image_data = await self.image_storage.download(image_path)

                    if image_data:
                        images.append({
                            "page_id": page_id,
                            "page_title": doc.metadata.get("page_title"),
                            "image_index": i,
                            "image_path": image_path,
                            "image_data": image_data,
                            "public_url": f"/api/images/{page_id}/{i}"
                        })

                except Exception as e:
                    logger.error(f"Error retrieving image {i} for document {page_id}: {str(e)}")
                    continue

        logger.info(f"Retrieved {len(images)} images from {len(documents)} documents")
        return images

    async def answer_visual_query(
        self,
        query: str,
        documents: List[Document],
        images: List[Dict[str, any]],
        context: str
    ) -> str:
        """
        Answer a visual query using retrieved images and GPT-4o Vision.

        Args:
            query: User's query
            documents: Retrieved text documents
            images: Retrieved images
            context: Text context from documents

        Returns:
            Answer to the visual query
        """
        try:
            # Extract image data
            image_data_list = [img["image_data"] for img in images]

            # Use vision service to answer question about images
            answer = await self.vision_service.answer_question_about_images(
                question=query,
                images=image_data_list,
                context=context,
                model="gpt-4o"  # Use best model for question answering
            )

            return answer

        except Exception as e:
            logger.error(f"Error answering visual query: {str(e)}")
            return f"I encountered an error analyzing the images: {str(e)}"

    async def enhance_query_response(
        self,
        query: str,
        documents: List[Document],
        base_answer: str,
        max_images: int = 5
    ) -> Tuple[str, List[Dict[str, any]]]:
        """
        Enhance query response with images if it's a visual query.

        Args:
            query: User query
            documents: Retrieved documents
            base_answer: Base text answer from RAG
            max_images: Maximum images to include

        Returns:
            Tuple of (enhanced_answer, images_list)
        """
        # Check if visual query
        if not self.is_visual_query(query):
            logger.debug("Not a visual query, returning base answer")
            return (base_answer, [])

        # Get images from documents using page_id
        images = await self.get_images_from_documents(
            documents=documents,
            max_images=max_images
        )

        if not images:
            logger.info("No images found for visual query")
            return (base_answer, [])

        # Build text context from documents
        context = "\n\n".join([
            f"From: {doc.metadata.get('page_title', 'Unknown')}\n{doc.page_content[:500]}..."
            for doc in documents[:3]
        ])

        # Get visual answer
        visual_answer = await self.answer_visual_query(
            query=query,
            documents=documents,
            images=images,
            context=context
        )

        # Combine base answer with visual answer
        enhanced_answer = f"{visual_answer}\n\n---\n\nAdditional Context:\n{base_answer}"

        logger.info(f"Enhanced answer with {len(images)} images")

        return (enhanced_answer, images)

    def format_images_for_response(
        self,
        images: List[Dict[str, any]]
    ) -> List[Dict[str, str]]:
        """
        Format images for API response (without binary data).

        Args:
            images: List of image dictionaries with binary data

        Returns:
            List of image metadata for response
        """
        formatted = []

        for img in images:
            formatted.append({
                "page_id": img["page_id"],
                "page_title": img.get("page_title", "Unknown"),
                "image_index": img["image_index"],
                "image_path": img["image_path"],
                "public_url": img["public_url"]
            })

        return formatted

    async def group_documents_by_page_id(
        self,
        documents: List[Document]
    ) -> Dict[str, Dict]:
        """
        Group retrieved chunks by page_id to reconstruct complete documents.

        This demonstrates document integrity - we can always reunite
        all chunks and images belonging to the same document.

        Args:
            documents: List of retrieved document chunks

        Returns:
            Dictionary mapping page_id to document data
        """
        grouped = {}

        for doc in documents:
            page_id = doc.metadata.get("page_id")
            if not page_id:
                continue

            if page_id not in grouped:
                grouped[page_id] = {
                    "page_id": page_id,
                    "page_title": doc.metadata.get("page_title"),
                    "notebook_name": doc.metadata.get("notebook_name"),
                    "section_name": doc.metadata.get("section_name"),
                    "has_images": doc.metadata.get("has_images", False),
                    "image_count": doc.metadata.get("image_count", 0),
                    "chunks": [],
                    "images": []
                }

            grouped[page_id]["chunks"].append(doc)

        # For each document, fetch its images if it has any
        for page_id, doc_data in grouped.items():
            if doc_data["has_images"]:
                for i in range(doc_data["image_count"]):
                    image_path = self.image_storage.generate_image_path(page_id, i)

                    if await self.image_storage.exists(image_path):
                        image_data = await self.image_storage.download(image_path)
                        if image_data:
                            doc_data["images"].append({
                                "index": i,
                                "path": image_path,
                                "data": image_data
                            })

        logger.info(f"Grouped {len(documents)} chunks into {len(grouped)} complete documents")

        return grouped
