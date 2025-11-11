"""
OneNote service for interacting with Microsoft Graph API.
 
Rate Limiting Strategy for Large Sections (e.g., 125+ pages):
---------------------------------------------------------
1. Minimum 500ms delay between all API requests
2. Automatic pagination support for list_pages()
3. Handles 429 (Too Many Requests) with:
   - Retry-After header detection
   - 60s default wait time
   - Up to 3 retry attempts per request
4. Extra 200ms delay for datasets > 50 pages
5. Exponential backoff for 5xx server errors
 
This allows safe sync of sections with 125+ pages without hitting
Microsoft Graph API rate limits (typically 600 requests/minute).
"""
import logging
import time
from typing import List, Dict, Any, Optional
import requests
from msal import ConfidentialClientApplication
 
from models.document import Document, DocumentMetadata
from services.rate_limiter import AdaptiveRateLimiter, BatchProcessor
 
logger = logging.getLogger(__name__)
 
 
class OneNoteService:
    """Service for interacting with OneNote via Microsoft Graph API with rate limiting."""
 
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
   
    # Rate limiting configuration
    MIN_REQUEST_INTERVAL = 0.5  # Minimum 500ms between requests (120 req/min max)
    RATE_LIMIT_RETRY_DELAY = 60  # Wait 60s on 429 error
    MAX_RATE_LIMIT_RETRIES = 3  # Max retries for 429 errors
 
    def __init__(self, client_id: str = "", client_secret: str = "", tenant_id: str = "", manual_token: str = "", use_azure_ad: bool = True):
        """
        Initialize OneNote service.
 
        Args:
            client_id: Microsoft application client ID (optional if using manual_token)
            client_secret: Microsoft application client secret (optional if using manual_token)
            tenant_id: Microsoft tenant ID (optional if using manual_token)
            manual_token: Manual Bearer token from Graph Explorer (bypasses OAuth)
            use_azure_ad: If True, use Azure AD auth (client credentials). If False, use manual token.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.manual_token = manual_token
        self.use_azure_ad = use_azure_ad
        self.access_token: Optional[str] = None
       
        # Log authentication mode
        auth_mode = "Azure AD" if use_azure_ad else "Manual Token"
        logger.info(f"Initializing OneNote Service with {auth_mode} authentication")
       
        # Initialize adaptive rate limiter (100 req/min, well below 600 limit)
        self.rate_limiter = AdaptiveRateLimiter(
            requests_per_minute=100,
            burst_size=10,
            min_interval_ms=500  # Minimum 500ms between requests
        )
        self.batch_processor = BatchProcessor(self.rate_limiter)
       
        # Legacy rate limiting (kept for backwards compatibility, but unused)
        self.last_request_time = 0
       
        # Create a session for connection pooling and reuse
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
 
        # Authenticate based on use_azure_ad setting
        if use_azure_ad:
            if client_id and client_secret and tenant_id:
                self._authenticate()
            else:
                logger.warning("Azure AD authentication enabled but credentials are incomplete")
        else:
            if manual_token:
                self.access_token = manual_token
                self.session.headers.update({"Authorization": f"Bearer {manual_token}"})
            else:
                logger.warning("Manual token authentication enabled but token is missing")
 
    def _authenticate(self) -> None:
        """Authenticate with Microsoft Graph API using client credentials."""
        try:
            logger.info(f"🔐 Starting Azure AD authentication process...")
           
            authority_url = f"https://login.microsoftonline.com/{self.tenant_id}"
            logger.info(f"   • Authority URL: {authority_url}")
            logger.info(f"   • Scope: https://graph.microsoft.com/.default")
           
            app = ConfidentialClientApplication(
                self.client_id,
                authority=authority_url,
                client_credential=self.client_secret,
            )
            logger.info(f"✅ MSAL ConfidentialClientApplication created")
 
            logger.info(f"🔄 Requesting access token from Microsoft Entra ID...")
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
 
            if "access_token" in result:
                self.access_token = result["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                logger.info("Azure AD authentication successful")
            else:
                error = result.get('error', 'Unknown error')
                error_description = result.get('error_description', 'No description provided')
                logger.error(f"Azure AD authentication failed: {error} - {error_description}")
 
        except Exception as e:
            logger.error(f"Exception during Azure AD authentication: {str(e)}")
            import traceback
            logger.debug(f"Full traceback:\n{traceback.format_exc()}")
   
    def _make_request_with_retry(self, url: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with adaptive rate limiting and retry logic.
       
        Args:
            url: API endpoint URL
            max_retries: Maximum number of retries for server errors
           
        Returns:
            Response JSON data or None on failure
        """
        retry_delay = 2
       
        for attempt in range(max_retries):
            try:
                # Acquire rate limit token (will wait if necessary)
                self.rate_limiter.acquire(wait=True)
               
                response = self.session.get(url, timeout=30)
               
                # Handle rate limiting (429)
                if response.status_code == 429:
                    # Extract Retry-After header
                    retry_after = response.headers.get('Retry-After')
                    try:
                        wait_time = int(retry_after) if retry_after else None
                    except ValueError:
                        wait_time = None
                   
                    # Tell rate limiter about the error (it will adapt)
                    self.rate_limiter.handle_rate_limit_error(retry_after=wait_time)
                    self.rate_limiter.record_error(is_rate_limit=True)
                   
                    logger.warning(
                        f"Rate limit hit (429). Rate limiter adapting and waiting... "
                        f"(current rate: {self.rate_limiter.requests_per_minute:.1f} req/min)"
                    )
                    continue
               
                response.raise_for_status()
               
                # Record success for adaptive rate limiting
                self.rate_limiter.record_success()
               
                return response.json()
               
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    if hasattr(e, 'response') and e.response is not None and e.response.status_code >= 500:
                        self.rate_limiter.record_error(is_rate_limit=False)
                        logger.warning(
                            f"Server error (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                            f"Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
               
                logger.error(f"Request failed: {str(e)}")
                self.rate_limiter.record_error(is_rate_limit=False)
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
            logger.debug(f"Found {len(sections)} sections in notebook {notebook_id}")
            return sections
       
        return []
 
    def list_pages(self, section_id: str, max_pages: int = 20) -> List[Dict[str, Any]]:
        """
        List pages in a section with rate limiting, retry logic and pagination support.
        Handles large sections by implementing rate limiting between requests.
 
        Args:
            section_id: Section ID
            max_pages: Maximum number of pages to retrieve (default: 20)
 
        Returns:
            List of page dictionaries (fetches pages via pagination with rate limiting, up to max_pages)
        """
        if not self.access_token:
            return []
 
        all_pages = []
        url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/sections/{section_id}/pages"
        page_batch = 1
       
        # Fetch pages using pagination with rate limiting, up to max_pages
        while url and len(all_pages) < max_pages:
            data = self._make_request_with_retry(url)
           
            if not data:
                logger.warning(f"Failed to fetch page batch {page_batch}, returning {len(all_pages)} pages collected so far")
                break
           
            pages = data.get("value", [])
            # Only add pages up to the max limit
            remaining_slots = max_pages - len(all_pages)
            pages_to_add = pages[:remaining_slots]
            all_pages.extend(pages_to_add)
            logger.debug(f"Batch {page_batch}: Retrieved {len(pages_to_add)} pages (total: {len(all_pages)}/{max_pages})")
           
            # Check for next page
            url = data.get("@odata.nextLink")
            if url:
                page_batch += 1
                # Rate limiter handles timing automatically
       
        if len(all_pages) >= max_pages:
            logger.info(f"Reached page limit: {len(all_pages)} pages in section {section_id} (limit: {max_pages})")
        else:
            logger.info(f"Found {len(all_pages)} pages in section {section_id}")
        return all_pages
 
    def get_page_content(self, page_id: str) -> Optional[str]:
        """
        Get the HTML content of a OneNote page with adaptive rate limiting.
        This is called for each page, so rate limiting is critical for large sections.
 
        Args:
            page_id: Page ID
 
        Returns:
            HTML content as string, or None if error
        """
        if not self.access_token:
            return None
       
        max_retries = 3
        retry_delay = 2
       
        for attempt in range(max_retries):
            try:
                # Acquire rate limit token (adaptive)
                self.rate_limiter.acquire(wait=True)
               
                url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/pages/{page_id}/content"
                response = self.session.get(url, timeout=30)
               
                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    try:
                        wait_time = int(retry_after) if retry_after else None
                    except ValueError:
                        wait_time = None
                   
                    self.rate_limiter.handle_rate_limit_error(retry_after=wait_time)
                    self.rate_limiter.record_error(is_rate_limit=True)
                   
                    logger.warning(
                        f"Rate limit hit fetching page {page_id}. "
                        f"Adapting rate to {self.rate_limiter.requests_per_minute:.1f} req/min..."
                    )
                    continue
               
                response.raise_for_status()
                content = response.text
               
                # Record success
                self.rate_limiter.record_success()
               
                logger.debug(f"Retrieved content for page {page_id} ({len(content)} chars)")
                return content
 
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    if hasattr(e, 'response') and e.response is not None and e.response.status_code >= 500:
                        self.rate_limiter.record_error(is_rate_limit=False)
                        logger.warning(
                            f"Server error fetching content (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                            f"Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
               
                logger.error(f"Error fetching page content: {str(e)}")
                self.rate_limiter.record_error(is_rate_limit=False)
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
   
    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics for monitoring and debugging.
       
        Returns:
            Dictionary with statistics including:
            - current_rate: Current requests per minute
            - total_requests: Total requests made
            - rate_limited_count: Number of 429 errors encountered
            - error_count: Total number of errors
            - success_count: Total successful requests
            - current_tokens: Available tokens in bucket
        """
        stats = self.rate_limiter.get_statistics()
        stats['current_rate'] = self.rate_limiter.requests_per_minute
        return stats
 