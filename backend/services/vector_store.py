"""
Vector store service using ChromaDB.
"""
import logging
import ssl
import httpx
from typing import List, Optional, Dict, Any, Literal
import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
 
logger = logging.getLogger(__name__)
 
 
class VectorStoreService:
    """Service for managing vector database operations."""
 
    def __init__(
        self, 
        persist_directory: str, 
        collection_name: str = "onenote_documents",
        embedding_provider: Literal["openai", "bge"] = "bge",
        embedding_device: str = "cpu"
    ):
        """
        Initialize vector store service.
 
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_provider: "openai" for OpenAI API or "bge" for local BGE embeddings
            embedding_device: "cpu" or "cuda" (for GPU acceleration with BGE)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
       
        # Initialize embeddings based on provider
        if embedding_provider == "bge":
            logger.info("Initializing BGE-Large-EN-v1.5 embeddings (this may take a moment on first run)...")
            logger.info(f"Using device: {embedding_device}")
            self.embeddings = HuggingFaceBgeEmbeddings(
                model_name="BAAI/bge-large-en-v1.5",
                model_kwargs={'device': embedding_device},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ BGE embeddings initialized successfully (1024 dimensions, better than OpenAI)")
        else:
            logger.info("Initializing OpenAI embeddings...")
            http_client = httpx.Client(verify=False)
            self.embeddings = OpenAIEmbeddings(http_client=http_client)
            logger.info("✅ OpenAI embeddings initialized")
            
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
 
    def delete_by_page_id(self, page_id: str) -> None:
        """
        Delete all chunks for a specific page.
 
        Args:
            page_id: OneNote page ID to delete
        """
        try:
            collection = self.vectorstore._collection
            # Query for documents with this page_id
            results = collection.get(where={"page_id": page_id})
           
            if results and results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for page {page_id}")
            else:
                logger.debug(f"No chunks found for page {page_id}")
 
        except Exception as e:
            logger.error(f"Error deleting page {page_id}: {str(e)}")
            raise
 
    def get_page_modified_date(self, page_id: str) -> Optional[str]:
        """
        Get the modified date of a page from the vector store.
 
        Args:
            page_id: OneNote page ID
 
        Returns:
            Modified date string or None if not found
        """
        try:
            collection = self.vectorstore._collection
            results = collection.get(
                where={"page_id": page_id},
                limit=1,
                include=["metadatas"]
            )
           
            if results and results['metadatas'] and len(results['metadatas']) > 0:
                return results['metadatas'][0].get('modified_date')
            return None
 
        except Exception as e:
            logger.error(f"Error getting modified date for page {page_id}: {str(e)}")
            return None
 
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
 
    def get_indexed_pages(self) -> List[Dict[str, Any]]:
        """
        Get list of all indexed pages with their metadata.
       
        Returns:
            List of page dictionaries with metadata and chunk counts
        """
        try:
            collection = self.vectorstore._collection
           
            # Get all documents with metadata
            results = collection.get(
                include=["metadatas"]
            )
           
            if not results or not results['metadatas']:
                return []
           
            # Group by page_id and aggregate metadata
            pages_dict = {}
            for metadata in results['metadatas']:
                page_id = metadata.get('page_id')
                if not page_id:
                    continue
               
                if page_id not in pages_dict:
                    pages_dict[page_id] = {
                        'page_id': page_id,
                        'page_title': metadata.get('page_title', 'Untitled'),
                        'section_name': metadata.get('section_name', 'Unknown'),
                        'notebook_name': metadata.get('notebook_name', 'Unknown'),
                        'modified_date': metadata.get('modified_date'),
                        'created_date': metadata.get('created_date'),
                        'url': metadata.get('url', ''),
                        'chunk_count': 0
                    }
               
                pages_dict[page_id]['chunk_count'] += 1
           
            # Convert to list and sort by modified date (newest first)
            pages_list = list(pages_dict.values())
            pages_list.sort(
                key=lambda x: x.get('modified_date', ''),
                reverse=True
            )
           
            logger.info(f"Found {len(pages_list)} indexed pages with {len(results['metadatas'])} total chunks")
            return pages_list
           
        except Exception as e:
            logger.error(f"Error getting indexed pages: {str(e)}")
            return []
 
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
 