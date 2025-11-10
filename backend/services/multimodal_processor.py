"""
Multimodal document processor for handling text, metadata, and images together.

This maintains DOCUMENT INTEGRITY - everything is linked by page_id.
"""
import logging
import re
import base64
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from langchain_core.documents import Document as LangChainDocument
import httpx

from models.document import Document
from .document_processor import DocumentProcessor
from .vision_service import GPT4VisionService

logger = logging.getLogger(__name__)


class MultimodalDocumentProcessor(DocumentProcessor):
    """
    Enhanced document processor with multimodal capabilities.

    Handles text, metadata, and images in a unified indexing approach where:
    - Text content is extracted
    - Metadata is enriched (prepended as context)
    - Images are analyzed with GPT-4o Vision
    - Everything is combined into unified chunks
    - page_id links all components together
    """

    def __init__(
        self,
        vision_service: GPT4VisionService,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_images_per_document: int = 10,
        access_token: Optional[str] = None
    ):
        """
        Initialize multimodal document processor.

        Args:
            vision_service: GPT-4o Vision service instance
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            max_images_per_document: Maximum images to process per document
            access_token: Optional access token for downloading OneNote images
        """
        super().__init__(chunk_size, chunk_overlap)
        self.vision_service = vision_service
        self.max_images_per_document = max_images_per_document
        self.access_token = access_token

        # HTTP client for downloading images
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            verify=False,
            headers={"Authorization": f"Bearer {access_token}"} if access_token else {}
        )

        logger.info("Initialized MultimodalDocumentProcessor with image support")

    def extract_image_urls_from_html(self, html_content: str) -> List[Dict[str, str]]:
        """
        Extract image URLs and metadata from OneNote HTML content.

        OneNote images are typically in the format:
        <img src="https://graph.microsoft.com/v1.0/users/.../onenote/resources/{id}/$value" />

        Args:
            html_content: HTML content from OneNote

        Returns:
            List of dictionaries with image info (url, alt_text, etc.)
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            images = []

            for img in soup.find_all('img'):
                src = img.get('src', '')
                alt = img.get('alt', '')
                data_fullres = img.get('data-fullres-src', '')  # OneNote may have full-res versions

                # Use full-res if available, otherwise use src
                image_url = data_fullres if data_fullres else src

                if image_url:
                    images.append({
                        "url": image_url,
                        "alt_text": alt,
                        "position": len(images)  # Track position in document
                    })

            logger.debug(f"Extracted {len(images)} image URLs from HTML")
            return images[:self.max_images_per_document]  # Limit number of images

        except Exception as e:
            logger.error(f"Error extracting image URLs: {str(e)}")
            return []

    async def download_image(self, image_url: str) -> Optional[bytes]:
        """
        Download image from URL.

        Args:
            image_url: URL of the image

        Returns:
            Image data as bytes, or None if download fails
        """
        try:
            # Handle data URLs (base64 encoded images)
            if image_url.startswith('data:image'):
                # Extract base64 data
                match = re.search(r'base64,(.+)', image_url)
                if match:
                    base64_data = match.group(1)
                    return base64.b64decode(base64_data)

            # Download from URL
            response = await self.http_client.get(image_url)
            response.raise_for_status()
            return response.content

        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {str(e)}")
            return None

    async def extract_and_analyze_images(
        self,
        html_content: str,
        document_context: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Extract images from HTML and analyze them with GPT-4o Vision.

        Args:
            html_content: HTML content from OneNote
            document_context: Optional context about the document

        Returns:
            List of image analysis results
        """
        # Extract image URLs
        image_infos = self.extract_image_urls_from_html(html_content)

        if not image_infos:
            logger.debug("No images found in document")
            return []

        logger.info(f"Processing {len(image_infos)} images")

        # Download and analyze each image
        analyzed_images = []
        for i, img_info in enumerate(image_infos):
            try:
                # Download image
                image_data = await self.download_image(img_info["url"])
                if not image_data:
                    logger.warning(f"Failed to download image {i+1}")
                    continue

                # Analyze with GPT-4o Vision
                context_str = f"{document_context} - Image {i+1}" if document_context else None
                image_context = await self.vision_service.create_image_context_for_indexing(
                    image_data=image_data,
                    image_index=i,
                    document_context=context_str
                )

                analyzed_images.append({
                    "position": i,
                    "url": img_info["url"],
                    "alt_text": img_info.get("alt_text", ""),
                    "context": image_context,
                    "data": image_data  # Keep for storage
                })

                logger.debug(f"Analyzed image {i+1}/{len(image_infos)}")

            except Exception as e:
                logger.error(f"Error processing image {i+1}: {str(e)}")
                continue

        logger.info(f"Successfully analyzed {len(analyzed_images)} images")
        return analyzed_images

    async def chunk_document_multimodal(
        self,
        document: Document,
        enrich_with_metadata: bool = True,
        include_images: bool = True
    ) -> Tuple[List[LangChainDocument], List[Dict]]:
        """
        Process and chunk a document with multimodal support (text + metadata + images).

        This creates a unified embedding approach where:
        - Metadata is prepended as context (if enabled)
        - Text content is extracted
        - Images are analyzed and their descriptions are appended
        - Everything is chunked together for semantic search
        - page_id in metadata links everything

        Args:
            document: Document to process
            enrich_with_metadata: If True, prepend metadata context
            include_images: If True, analyze and include images

        Returns:
            Tuple of (chunks, image_data_list)
            - chunks: LangChain Document chunks ready for embedding
            - image_data_list: List of image data dicts for storage
        """
        # Extract text
        text = self.extract_text_from_html(document.content)
        text = self.clean_text(text)

        if not text:
            logger.warning(f"No text extracted from document {document.id}")
            return ([], [])

        # Build content parts
        content_parts = []

        # 1. Add metadata context
        if enrich_with_metadata:
            metadata_context = self.build_metadata_context(document)
            if metadata_context:
                content_parts.append(metadata_context)

        # 2. Add text content
        content_parts.append(text)

        # 3. Extract and analyze images
        image_data_list = []
        if include_images:
            try:
                doc_context = f"{document.metadata.page_title} from {document.metadata.notebook_name}"
                analyzed_images = await self.extract_and_analyze_images(
                    document.content,
                    document_context=doc_context
                )

                if analyzed_images:
                    content_parts.append("\n\n=== Images in Document ===\n")
                    for img in analyzed_images:
                        content_parts.append(img["context"])
                        content_parts.append("\n")

                        # Store image data for later storage
                        image_data_list.append({
                            "page_id": document.metadata.page_id,
                            "position": img["position"],
                            "url": img["url"],
                            "data": img["data"],
                            "alt_text": img.get("alt_text", "")
                        })

                    logger.info(f"Added {len(analyzed_images)} image contexts to document {document.id}")

            except Exception as e:
                logger.error(f"Error processing images for document {document.id}: {str(e)}")

        # Combine all content
        enriched_text = "".join(content_parts)

        # Create metadata - KEY: page_id links everything!
        metadata = {
            "page_id": document.metadata.page_id,  # ← The magic key!
            "page_title": document.metadata.page_title,
            "section_name": document.metadata.section_name,
            "notebook_name": document.metadata.notebook_name,
            "url": document.metadata.url or "",
            "author": document.metadata.author or "",
            "tags": ",".join(document.metadata.tags) if document.metadata.tags else "",
            "metadata_enriched": enrich_with_metadata,
            "has_images": len(image_data_list) > 0,
            "image_count": len(image_data_list),
        }

        # Add dates
        if document.metadata.created_date:
            metadata["created_date"] = document.metadata.created_date.isoformat()
        if document.metadata.modified_date:
            metadata["modified_date"] = document.metadata.modified_date.isoformat()

        # Chunk the enriched content
        chunks = self.text_splitter.create_documents(
            texts=[enriched_text],
            metadatas=[metadata]
        )

        # Add chunk indices
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)

        logger.info(
            f"Created {len(chunks)} multimodal chunks from document {document.id} "
            f"(text + {len(image_data_list)} images)"
        )

        return (chunks, image_data_list)

    async def chunk_documents_multimodal(
        self,
        documents: List[Document],
        enrich_with_metadata: bool = True,
        include_images: bool = True
    ) -> Tuple[List[LangChainDocument], List[Dict]]:
        """
        Process and chunk multiple documents with multimodal support.

        Args:
            documents: List of documents to process
            enrich_with_metadata: If True, prepend metadata context
            include_images: If True, analyze and include images

        Returns:
            Tuple of (all_chunks, all_image_data)
        """
        all_chunks = []
        all_image_data = []

        for document in documents:
            chunks, image_data = await self.chunk_document_multimodal(
                document,
                enrich_with_metadata=enrich_with_metadata,
                include_images=include_images
            )
            all_chunks.extend(chunks)
            all_image_data.extend(image_data)

        logger.info(
            f"Created {len(all_chunks)} chunks from {len(documents)} documents "
            f"with {len(all_image_data)} images"
        )

        return (all_chunks, all_image_data)

    async def close(self):
        """Close HTTP client and cleanup resources."""
        await self.http_client.aclose()
        logger.debug("Closed MultimodalDocumentProcessor HTTP client")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
