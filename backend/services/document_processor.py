"""
Document processor for text extraction and chunking.
"""
import logging
import re
from typing import List
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument

from models.document import Document

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing and chunking documents."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize document processor.

        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def extract_text_from_html(self, html_content: str) -> str:
        """
        Extract plain text from OneNote HTML content.

        Args:
            html_content: HTML content from OneNote

        Returns:
            Cleaned plain text
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            logger.error(f"Error extracting text from HTML: {str(e)}")
            return ""

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remove very short lines (likely artifacts)
        lines = text.split('\n')
        lines = [line for line in lines if len(line.strip()) > 2]

        return '\n'.join(lines).strip()

    def chunk_document(self, document: Document) -> List[LangChainDocument]:
        """
        Process and chunk a document.

        Args:
            document: Document to process

        Returns:
            List of LangChain Document chunks
        """
        # Extract text from HTML
        text = self.extract_text_from_html(document.content)

        # Clean text
        text = self.clean_text(text)

        if not text:
            logger.warning(f"No text extracted from document {document.id}")
            return []

        # Create base metadata
        metadata = {
            "page_id": document.metadata.page_id,
            "page_title": document.metadata.page_title,
            "section_name": document.metadata.section_name,
            "notebook_name": document.metadata.notebook_name,
            "url": document.metadata.url or "",
            "author": document.metadata.author or "",
            "tags": ",".join(document.metadata.tags) if document.metadata.tags else "",
        }

        # Add dates if available
        if document.metadata.created_date:
            metadata["created_date"] = document.metadata.created_date.isoformat()
        if document.metadata.modified_date:
            metadata["modified_date"] = document.metadata.modified_date.isoformat()

        # Split into chunks
        chunks = self.text_splitter.create_documents(
            texts=[text],
            metadatas=[metadata]
        )

        # Add chunk index to metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(chunks)

        logger.debug(f"Created {len(chunks)} chunks from document {document.id}")
        return chunks

    def chunk_documents(self, documents: List[Document]) -> List[LangChainDocument]:
        """
        Process and chunk multiple documents.

        Args:
            documents: List of documents to process

        Returns:
            List of all document chunks
        """
        all_chunks = []

        for document in documents:
            chunks = self.chunk_document(document)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
        return all_chunks

    def update_chunk_size(self, chunk_size: int, chunk_overlap: int) -> None:
        """
        Update chunking parameters.

        Args:
            chunk_size: New chunk size
            chunk_overlap: New chunk overlap
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        logger.info(f"Updated chunk size to {chunk_size} with overlap {chunk_overlap}")
