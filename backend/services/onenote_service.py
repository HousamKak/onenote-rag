"""
OneNote service for interacting with Microsoft Graph API.
"""
import logging
import time
from typing import List, Dict, Any, Optional
import requests
from msal import ConfidentialClientApplication
 
from models.document import Document, DocumentMetadata
 
logger = logging.getLogger(__name__)
 
 
class OneNoteService:
    """Service for interacting with OneNote via Microsoft Graph API."""
 
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    
    # Rate limiting configuration
    MIN_REQUEST_INTERVAL = 0.5  # Minimum 500ms between requests
    RATE_LIMIT_RETRY_DELAY = 60  # Wait 60s on 429 error
    MAX_RATE_LIMIT_RETRIES = 3  # Max retries for 429 errors
 
    def __init__(self, client_id: str = "", client_secret: str = "", tenant_id: str = "", manual_token: str = ""):
        """
        Initialize OneNote service.
 
        Args:
            client_id: Microsoft application client ID (optional if using manual_token)
            client_secret: Microsoft application client secret (optional if using manual_token)
            tenant_id: Microsoft tenant ID (optional if using manual_token)
            manual_token: Manual Bearer token from Graph Explorer (bypasses OAuth)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token: Optional[str] = None
        
        # Rate limiting state
        self.last_request_time = 0
       
        # Create a session for connection pooling and reuse
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
 
        # Use manual token if provided, otherwise authenticate via OAuth
        if manual_token:
            self.access_token = manual_token
            self.session.headers.update({"Authorization": f"Bearer {manual_token}"})
            logger.info("Using manual Bearer token from Graph Explorer")
        elif client_id and client_secret and tenant_id:
            self._authenticate()
        else:
            logger.warning("No authentication method provided. Service will not work.")
 
    def _authenticate(self) -> None:
        """Authenticate with Microsoft Graph API using client credentials."""
        try:
            app = ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret,
            )
 
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
 
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                logger.info("Successfully authenticated with Microsoft Graph API")
            else:
                logger.error(f"Authentication failed: {result.get('error_description')}")
 
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
    
    def _wait_for_rate_limit(self) -> None:
        """Enforce minimum delay between API requests to avoid rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request_with_retry(self, url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with rate limiting and retry logic for 429 errors.
        
        Args:
            url: API endpoint URL
            max_retries: Maximum number of retries for server errors
            
        Returns:
            Response JSON data or None on failure
        """
        retry_delay = 2
        rate_limit_retries = 0
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._wait_for_rate_limit()
                
                response = self.session.get(url, timeout=30)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    rate_limit_retries += 1
                    
                    if rate_limit_retries > self.MAX_RATE_LIMIT_RETRIES:
                        logger.error(f"Max rate limit retries ({self.MAX_RATE_LIMIT_RETRIES}) exceeded")
                        return None
                    
                    # Check for Retry-After header
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            wait_time = self.RATE_LIMIT_RETRY_DELAY
                    else:
                        wait_time = self.RATE_LIMIT_RETRY_DELAY
                    
                    logger.warning(
                        f"Rate limit hit (429). Waiting {wait_time}s before retry "
                        f"({rate_limit_retries}/{self.MAX_RATE_LIMIT_RETRIES})"
                    )
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    if hasattr(e, 'response') and e.response is not None and e.response.status_code >= 500:
                        logger.warning(
                            f"Server error (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                            f"Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                
                logger.error(f"Request failed: {str(e)}")
                return None
        
        return None
 
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
 
    def list_notebooks(self) -> List[Dict[str, Any]]:
        """
        List all notebooks for the authenticated user.
 
        Returns:
            List of notebook dictionaries
        """
        if not self.access_token:
            logger.warning("Not authenticated. Returning empty list.")
            return []
 
        url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks"
        data = self._make_request_with_retry(url)
        
        if data:
            notebooks = data.get("value", [])
            logger.info(f"Found {len(notebooks)} notebooks")
            return notebooks
        
        return []
 
    def list_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        List all sections in a notebook with rate limiting and retry logic.
 
        Args:
            notebook_id: Notebook ID
 
        Returns:
            List of section dictionaries
        """
        if not self.access_token:
            return []
 
        url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks/{notebook_id}/sections"
        data = self._make_request_with_retry(url)
        
        if data:
            sections = data.get("value", [])
            logger.info(f"Found {len(sections)} sections in notebook {notebook_id}")
            return sections
        
        return []
 
    def list_pages(self, section_id: str) -> List[Dict[str, Any]]:
        """
        List all pages in a section with rate limiting, retry logic and pagination support.
        Handles large sections (e.g., 125 pages) by implementing rate limiting between requests.
 
        Args:
            section_id: Section ID
 
        Returns:
            List of page dictionaries (fetches all pages via pagination with rate limiting)
        """
        if not self.access_token:
            return []
 
        all_pages = []
        url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/sections/{section_id}/pages"
        page_batch = 1
        
        # Fetch all pages using pagination with rate limiting
        while url:
            logger.debug(f"Fetching page batch {page_batch} for section {section_id}")
            
            data = self._make_request_with_retry(url)
            
            if not data:
                # If request failed, return what we have so far
                logger.warning(f"Failed to fetch page batch {page_batch}, returning {len(all_pages)} pages collected so far")
                break
            
            pages = data.get("value", [])
            all_pages.extend(pages)
            logger.debug(f"Batch {page_batch}: Retrieved {len(pages)} pages (total: {len(all_pages)})")
            
            # Check for next page
            url = data.get("@odata.nextLink")
            if url:
                page_batch += 1
                # Additional small delay between pagination requests for large datasets
                if len(all_pages) > 50:
                    logger.debug(f"Large dataset detected ({len(all_pages)} pages), adding extra delay")
                    time.sleep(0.2)  # Extra 200ms for large datasets
        
        logger.info(f"Found {len(all_pages)} total pages in section {section_id} across {page_batch} batches")
        return all_pages
 
    def get_page_content(self, page_id: str) -> Optional[str]:
        """
        Get the HTML content of a OneNote page with rate limiting and retry logic.
        This is called for each page, so rate limiting is critical for large sections.
 
        Args:
            page_id: Page ID
 
        Returns:
            HTML content as string, or None if error
        """
        if not self.access_token:
            return None
        
        # Apply rate limiting before making request
        self._wait_for_rate_limit()
        
        max_retries = 3
        retry_delay = 2
        rate_limit_retries = 0
       
        for attempt in range(max_retries):
            try:
                url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/pages/{page_id}/content"
                response = self.session.get(url, timeout=30)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    rate_limit_retries += 1
                    
                    if rate_limit_retries > self.MAX_RATE_LIMIT_RETRIES:
                        logger.error(f"Max rate limit retries exceeded for page {page_id}")
                        return None
                    
                    retry_after = response.headers.get('Retry-After', str(self.RATE_LIMIT_RETRY_DELAY))
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        wait_time = self.RATE_LIMIT_RETRY_DELAY
                    
                    logger.warning(f"Rate limit hit fetching page content. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                content = response.text
                logger.debug(f"Retrieved content for page {page_id} ({len(content)} chars)")
                return content
 
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    if hasattr(e, 'response') and e.response is not None and e.response.status_code >= 500:
                        logger.warning(f"Server error fetching content (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
               
                logger.error(f"Error fetching page content: {str(e)}")
                return None
       
        return None
 
    def get_all_documents(self, notebook_ids: Optional[List[str]] = None) -> List[Document]:
        """
        Get all documents from specified notebooks (or all notebooks).
 
        Args:
            notebook_ids: Optional list of notebook IDs to process
 
        Returns:
            List of Document objects
        """
        documents = []
 
        # Get notebooks
        notebooks = self.list_notebooks()
        if notebook_ids:
            notebooks = [nb for nb in notebooks if nb["id"] in notebook_ids]
 
        for notebook in notebooks:
            notebook_name = notebook["displayName"]
            notebook_id = notebook["id"]
 
            # Get sections
            sections = self.list_sections(notebook_id)
 
            for section in sections:
                section_name = section["displayName"]
                section_id = section["id"]
 
                # Get pages
                pages = self.list_pages(section_id)
 
                for page in pages:
                    page_id = page["id"]
                    page_title = page["title"]
                    page_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href", "")
 
                    # Get page content
                    content = self.get_page_content(page_id)
                    if not content:
                        continue
 
                    # Create document
                    metadata = DocumentMetadata(
                        page_id=page_id,
                        page_title=page_title,
                        section_name=section_name,
                        notebook_name=notebook_name,
                        created_date=page.get("createdDateTime"),
                        modified_date=page.get("lastModifiedDateTime"),
                        url=page_url,
                    )
 
                    doc = Document(
                        id=page_id,
                        content=content,
                        metadata=metadata,
                    )
 
                    documents.append(doc)
 
        logger.info(f"Retrieved {len(documents)} documents")
        return documents
 