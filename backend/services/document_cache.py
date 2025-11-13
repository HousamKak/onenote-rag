"""
Document Cache Service - High-level interface for cached OneNote documents.
Wraps database operations with business logic for RAG system integration.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from bs4 import BeautifulSoup

from models.document import Document, DocumentMetadata
from models.document_cache import CachedDocument, CachedImage, CacheStats
from services.document_cache_db import DocumentCacheDB

logger = logging.getLogger(__name__)


class DocumentCacheService:
    """
    Service for managing cached OneNote documents.
    Provides high-level interface between sync system and RAG system.
    """

    def __init__(self, db_path: str = "data/document_cache.db"):
        """
        Initialize document cache service.

        Args:
            db_path: Path to cache database
        """
        self.db = DocumentCacheDB(db_path)
        logger.info("DocumentCacheService initialized")

    # =========================================================================
    # READ OPERATIONS (for RAG system)
    # =========================================================================

    def get_document(self, page_id: str) -> Optional[Document]:
        """
        Get document from cache and convert to RAG Document format.

        Args:
            page_id: OneNote page ID

        Returns:
            Document if found, None otherwise
        """
        cached_doc = self.db.get_document(page_id)
        if not cached_doc:
            return None

        return self._cached_to_rag_document(cached_doc)

    def get_all_documents(self) -> List[Document]:
        """
        Get all documents from cache in RAG Document format.

        Returns:
            List of Document
        """
        cached_docs = self.db.get_all_documents(include_deleted=False)
        return [self._cached_to_rag_document(doc) for doc in cached_docs]

    def get_documents_needing_indexing(self) -> List[Document]:
        """
        Get documents that need to be indexed/re-indexed.

        Returns:
            List of Document
        """
        cached_docs = self.db.get_documents_needing_indexing()
        return [self._cached_to_rag_document(doc) for doc in cached_docs]

    def get_documents_modified_after(self, timestamp: datetime) -> List[Document]:
        """
        Get documents modified after a specific timestamp.

        Args:
            timestamp: Datetime threshold

        Returns:
            List of Document
        """
        cached_docs = self.db.get_documents_modified_after(timestamp)
        return [self._cached_to_rag_document(doc) for doc in cached_docs]

    # =========================================================================
    # WRITE OPERATIONS (from sync system)
    # =========================================================================

    def cache_document(self, document: Document) -> None:
        """
        Cache a document from OneNote sync.

        Args:
            document: Document to cache
        """
        # Convert RAG Document to CachedDocument
        cached_doc = self._rag_to_cached_document(document)

        # Upsert to database
        self.db.upsert_document(cached_doc)

        logger.debug(f"Cached document: {document.page_id}")

    def cache_documents_bulk(self, documents: List[Document]) -> int:
        """
        Cache multiple documents in bulk.

        Args:
            documents: List of documents to cache

        Returns:
            Number of documents cached
        """
        if not documents:
            return 0

        cached_docs = [self._rag_to_cached_document(doc) for doc in documents]
        count = self.db.bulk_upsert_documents(cached_docs)

        logger.info(f"Bulk cached {count} documents")
        return count

    def mark_document_indexed(
        self,
        page_id: str,
        chunk_count: int,
        image_count: int
    ) -> None:
        """
        Mark document as indexed in vector store.

        Args:
            page_id: OneNote page ID
            chunk_count: Number of chunks created
            image_count: Number of images in document
        """
        self.db.mark_document_indexed(page_id, chunk_count, image_count)

    def mark_document_deleted(self, page_id: str) -> None:
        """
        Mark document as deleted (soft delete).

        Args:
            page_id: OneNote page ID
        """
        self.db.mark_document_deleted(page_id)

    # =========================================================================
    # IMAGE OPERATIONS
    # =========================================================================

    def cache_image_metadata(
        self,
        page_id: str,
        image_index: int,
        file_path: str,
        alt_text: Optional[str] = None,
        vision_analysis: Optional[str] = None,
        graph_resource_id: Optional[str] = None
    ) -> None:
        """
        Cache image metadata.

        Args:
            page_id: OneNote page ID
            image_index: Image position in document (0, 1, 2, ...)
            file_path: Relative path to image file
            alt_text: Alt text from HTML
            vision_analysis: GPT-4o vision analysis
            graph_resource_id: Graph API resource URL
        """
        image = CachedImage(
            page_id=page_id,
            image_index=image_index,
            file_path=file_path,
            alt_text=alt_text,
            vision_analysis=vision_analysis,
            analyzed_at=datetime.now() if vision_analysis else None,
            graph_resource_id=graph_resource_id
        )

        self.db.upsert_image(image)

    def get_images_for_document(self, page_id: str) -> List[CachedImage]:
        """
        Get all images for a document.

        Args:
            page_id: OneNote page ID

        Returns:
            List of CachedImage
        """
        return self.db.get_images_for_page(page_id)

    # =========================================================================
    # SYNC COORDINATION
    # =========================================================================

    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get timestamp of last incremental sync.

        Returns:
            Datetime of last sync, None if never synced
        """
        sync_state = self.db.get_sync_state('global', 'global')
        if sync_state and sync_state.last_incremental_sync_at:
            return sync_state.last_incremental_sync_at
        return None

    def get_all_page_ids(self) -> set:
        """
        Get set of all page IDs currently in cache.

        Returns:
            Set of page_id strings
        """
        return self.db.get_all_page_ids(include_deleted=False)

    def get_stale_documents(self, hours: int = 24) -> List[str]:
        """
        Get page IDs of documents that haven't synced recently.

        Args:
            hours: Threshold in hours

        Returns:
            List of page_id strings
        """
        threshold = datetime.now() - timedelta(hours=hours)
        stale_docs = []

        all_docs = self.db.get_all_documents(include_deleted=False)
        for doc in all_docs:
            if doc.last_synced_at < threshold:
                stale_docs.append(doc.page_id)

        return stale_docs

    # =========================================================================
    # STATISTICS & HEALTH
    # =========================================================================

    def get_stats(self) -> CacheStats:
        """
        Get cache statistics and health.

        Returns:
            CacheStats
        """
        return self.db.get_cache_stats()

    def get_document_count(self) -> int:
        """
        Get total number of active documents in cache.

        Returns:
            Document count
        """
        stats = self.db.get_cache_stats()
        return stats.total_documents

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _cached_to_rag_document(self, cached_doc: CachedDocument) -> Document:
        """
        Convert CachedDocument to RAG Document format.

        Args:
            cached_doc: CachedDocument from database

        Returns:
            Document for RAG system
        """
        # Use plain text if available, otherwise extract from HTML
        content = cached_doc.plain_text
        if not content and cached_doc.html_content:
            content = self._extract_text_from_html(cached_doc.html_content)

        # Create metadata
        metadata = DocumentMetadata(
            page_id=cached_doc.page_id,
            page_title=cached_doc.page_title,
            notebook_name=cached_doc.notebook_name or "Unknown",
            section_name=cached_doc.section_name or "Unknown",
            created_date=cached_doc.created_date or datetime.now(),
            modified_date=cached_doc.modified_date,
            author=cached_doc.author or "Unknown",
            source_url=cached_doc.source_url or "",
            tags=cached_doc.tags or [],
            has_images=cached_doc.image_count > 0,
            image_count=cached_doc.image_count
        )

        # Create document
        return Document(
            page_id=cached_doc.page_id,
            content=content or "",
            html_content=cached_doc.html_content,
            metadata=metadata
        )

    def _rag_to_cached_document(self, document: Document) -> CachedDocument:
        """
        Convert RAG Document to CachedDocument format.

        Args:
            document: Document from RAG system

        Returns:
            CachedDocument for database
        """
        # Extract plain text from HTML if not already extracted
        plain_text = document.content
        if not plain_text and document.html_content:
            plain_text = self._extract_text_from_html(document.html_content)

        return CachedDocument(
            page_id=document.page_id,
            html_content=document.html_content or "",
            plain_text=plain_text,
            notebook_id=getattr(document.metadata, 'notebook_id', ''),
            notebook_name=document.metadata.notebook_name,
            section_id=getattr(document.metadata, 'section_id', ''),
            section_name=document.metadata.section_name,
            page_title=document.metadata.page_title,
            author=document.metadata.author,
            created_date=document.metadata.created_date,
            modified_date=document.metadata.modified_date,
            source_url=document.metadata.source_url,
            tags=document.metadata.tags,
            last_synced_at=datetime.now(),
            sync_version=1,
            is_deleted=False,
            image_count=document.metadata.image_count
        )

    @staticmethod
    def _extract_text_from_html(html_content: str) -> str:
        """
        Extract plain text from HTML content.

        Args:
            html_content: HTML string

        Returns:
            Plain text
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return ""
