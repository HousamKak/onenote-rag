"""
OneNote service for interacting with Microsoft Graph API.
"""
import logging
from typing import List, Dict, Any, Optional
import requests
from msal import ConfidentialClientApplication

from models.document import Document, DocumentMetadata

logger = logging.getLogger(__name__)


class OneNoteService:
    """Service for interacting with OneNote via Microsoft Graph API."""

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        """
        Initialize OneNote service.

        Args:
            client_id: Microsoft application client ID
            client_secret: Microsoft application client secret
            tenant_id: Microsoft tenant ID
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token: Optional[str] = None

        # For now, we'll use a simple token-based approach
        # In production, you'd implement proper OAuth flow
        if client_id and client_secret and tenant_id:
            self._authenticate()

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
                logger.info("Successfully authenticated with Microsoft Graph API")
            else:
                logger.error(f"Authentication failed: {result.get('error_description')}")

        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")

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

        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks"
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            notebooks = response.json().get("value", [])
            logger.info(f"Found {len(notebooks)} notebooks")
            return notebooks

        except requests.RequestException as e:
            logger.error(f"Error fetching notebooks: {str(e)}")
            return []

    def list_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        List all sections in a notebook.

        Args:
            notebook_id: Notebook ID

        Returns:
            List of section dictionaries
        """
        if not self.access_token:
            return []

        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks/{notebook_id}/sections"
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            sections = response.json().get("value", [])
            logger.info(f"Found {len(sections)} sections in notebook {notebook_id}")
            return sections

        except requests.RequestException as e:
            logger.error(f"Error fetching sections: {str(e)}")
            return []

    def list_pages(self, section_id: str) -> List[Dict[str, Any]]:
        """
        List all pages in a section.

        Args:
            section_id: Section ID

        Returns:
            List of page dictionaries
        """
        if not self.access_token:
            return []

        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/sections/{section_id}/pages"
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            pages = response.json().get("value", [])
            logger.info(f"Found {len(pages)} pages in section {section_id}")
            return pages

        except requests.RequestException as e:
            logger.error(f"Error fetching pages: {str(e)}")
            return []

    def get_page_content(self, page_id: str) -> Optional[str]:
        """
        Get the HTML content of a OneNote page.

        Args:
            page_id: Page ID

        Returns:
            HTML content as string, or None if error
        """
        if not self.access_token:
            return None

        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/pages/{page_id}/content"
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            content = response.text
            logger.debug(f"Retrieved content for page {page_id}")
            return content

        except requests.RequestException as e:
            logger.error(f"Error fetching page content: {str(e)}")
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
