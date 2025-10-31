"""
Vector store service using ChromaDB.
"""
import logging
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing vector database operations."""

    def __init__(self, persist_directory: str, collection_name: str = "onenote_documents"):
        """
        Initialize vector store service.

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore: Optional[Chroma] = None

        self._initialize_vectorstore()

    def _initialize_vectorstore(self) -> None:
        """Initialize or load the vector store."""
        try:
            self.vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            logger.info(f"Initialized vector store at {self.persist_directory}")

        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of LangChain documents to add
        """
        if not documents:
            logger.warning("No documents to add")
            return

        try:
            self.vectorstore.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")

            # Log sample for verification
            if documents:
                sample = documents[0]
                logger.info(f"Sample document - Length: {len(sample.page_content)} chars, "
                           f"Metadata: {sample.metadata.get('page_title', 'N/A')} "
                           f"[chunk {sample.metadata.get('chunk_index', 'N/A')}/{sample.metadata.get('total_chunks', 'N/A')}]")

        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of relevant documents
        """
        try:
            results = self.vectorstore.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            logger.debug(f"Found {len(results)} results for query: {query[:50]}...")
            if results:
                logger.debug(f"First result metadata: {results[0].metadata}")
                logger.debug(f"First result content length: {len(results[0].page_content)} chars")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of (document, score) tuples
        """
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            logger.debug(f"Found {len(results)} results with scores")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search with scores: {str(e)}")
            return []

    def get_retriever(self, k: int = 4, filter: Optional[Dict[str, Any]] = None):
        """
        Get a retriever instance.

        Args:
            k: Number of documents to retrieve
            filter: Optional metadata filter

        Returns:
            Retriever instance
        """
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter

        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)

    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        try:
            # Delete the collection and recreate it
            self.vectorstore._client.delete_collection(self.collection_name)
            self._initialize_vectorstore()
            logger.info("Cleared vector store collection")

        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        try:
            collection = self.vectorstore._collection
            count = collection.count()

            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {
                "total_documents": 0,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "error": str(e)
            }

    def delete_by_metadata(self, filter: Dict[str, Any]) -> None:
        """
        Delete documents matching metadata filter.

        Args:
            filter: Metadata filter
        """
        try:
            # This is a workaround since Chroma doesn't have direct delete by filter
            # We'd need to implement this based on specific requirements
            logger.warning("Delete by metadata not fully implemented")

        except Exception as e:
            logger.error(f"Error deleting by metadata: {str(e)}")
            raise
