"""
OneNote Discovery Service - Discover and normalize notebooks from multiple sources.

Implements the algorithm from the Shared Notebook Solution:
1. Discover notebooks from 3 sources (owned, recent, shared)
2. Normalize via getNotebookFromWebUrl to get siteId and proper OneNote object
3. Return unified list of accessible notebooks

Key Innovation:
Uses getNotebookFromWebUrl to convert ANY notebook (owned or shared) into a proper
OneNote object with siteId, enabling site-scoped API access for all notebooks.
"""
import logging
import re
from typing import List, Dict, Any, Optional
import requests

from models.notebook import NotebookCandidate, NormalizedNotebook

logger = logging.getLogger(__name__)


class OneNoteDiscoveryService:
    """
    Discover and normalize OneNote notebooks from multiple sources.

    Supports:
    - Owned notebooks (/me/onenote/notebooks)
    - Recent notebooks (/me/onenote/notebooks/getRecentNotebooks)
    - Shared notebooks (/me/drive/sharedWithMe)
    """

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        """
        Initialize discovery service with user's access token.

        Args:
            access_token: User's Microsoft Graph access token (delegated permissions)
        """
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })
        logger.info("OneNote Discovery Service initialized")

    async def discover_all_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover notebooks from all available sources.

        Returns:
            List of NotebookCandidate objects (before normalization)
        """
        candidates = []

        # Source 1: Owned notebooks
        logger.info("Discovering owned notebooks...")
        owned = await self._discover_owned_notebooks()
        candidates.extend(owned)
        logger.info(f"Found {len(owned)} owned notebooks")

        # Source 2: Recent notebooks
        logger.info("Discovering recent notebooks...")
        recent = await self._discover_recent_notebooks()
        candidates.extend(recent)
        logger.info(f"Found {len(recent)} recent notebooks")

        # Source 3: Shared notebooks
        logger.info("Discovering shared notebooks...")
        shared = await self._discover_shared_notebooks()
        candidates.extend(shared)
        logger.info(f"Found {len(shared)} shared notebooks")

        # Deduplicate by webUrl
        seen_urls = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate.web_url not in seen_urls:
                seen_urls.add(candidate.web_url)
                unique_candidates.append(candidate)

        logger.info(f"Total unique notebooks discovered: {len(unique_candidates)}")
        return unique_candidates

    async def _discover_owned_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover user's own notebooks via /me/onenote/notebooks.

        Returns:
            List of NotebookCandidate objects
        """
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            candidates = []
            for notebook in data.get("value", []):
                web_url = notebook.get("links", {}).get("oneNoteWebUrl", {}).get("href")
                if web_url:
                    candidates.append(NotebookCandidate(
                        display_name=notebook.get("displayName", "Unnamed Notebook"),
                        web_url=web_url,
                        source="owned",
                        last_modified_datetime=notebook.get("lastModifiedDateTime")
                    ))

            return candidates

        except Exception as e:
            logger.error(f"Error discovering owned notebooks: {e}")
            return []

    async def _discover_recent_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover recently used notebooks via /me/onenote/notebooks/getRecentNotebooks.

        Returns:
            List of NotebookCandidate objects
        """
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks/getRecentNotebooks(includePersonalNotebooks=true)"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            candidates = []
            for notebook in data.get("value", []):
                web_url = notebook.get("links", {}).get("oneNoteWebUrl", {}).get("href")
                if web_url:
                    candidates.append(NotebookCandidate(
                        display_name=notebook.get("displayName", "Unnamed Notebook"),
                        web_url=web_url,
                        source="recent",
                        last_modified_datetime=notebook.get("lastAccessedTime")
                    ))

            return candidates

        except Exception as e:
            logger.error(f"Error discovering recent notebooks: {e}")
            return []

    async def _discover_shared_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover shared notebooks via /me/drive/sharedWithMe.

        Filters for OneNote notebooks (package.type = "oneNote").

        Returns:
            List of NotebookCandidate objects
        """
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/sharedWithMe"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            candidates = []
            for item in data.get("value", []):
                # Filter for OneNote packages
                remote_item = item.get("remoteItem", {})
                package = remote_item.get("package", {})

                if package.get("type") == "oneNote":
                    web_url = remote_item.get("webUrl")
                    if web_url:
                        candidates.append(NotebookCandidate(
                            display_name=item.get("name", "Unnamed Notebook"),
                            web_url=web_url,
                            source="shared",
                            last_modified_datetime=remote_item.get("lastModifiedDateTime")
                        ))

            return candidates

        except Exception as e:
            logger.error(f"Error discovering shared notebooks: {e}")
            return []

    async def normalize_notebook(self, web_url: str) -> Optional[NormalizedNotebook]:
        """
        Normalize a notebook via getNotebookFromWebUrl.

        This is the KEY step that converts any notebook (owned or shared) into
        a proper OneNote object with siteId for site-scoped API access.

        Args:
            web_url: OneNote web URL from any source

        Returns:
            NormalizedNotebook with id, siteId, and API endpoints, or None if failed
        """
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks/getNotebookFromWebUrl"
            payload = {"webUrl": web_url}

            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract siteId from self URL using regex
            # Format: .../sites/{siteId}/onenote/notebooks/{notebookId}
            self_url = data.get("self", "")
            site_id = self._extract_site_id(self_url)

            if not site_id:
                logger.warning(f"Could not extract site_id from: {self_url}")
                return None

            # Determine created_by from response
            created_by = data.get("createdBy", {}).get("user", {}).get("displayName")

            normalized = NormalizedNotebook(
                id=data.get("id"),
                display_name=data.get("displayName", "Unnamed"),
                site_id=site_id,
                sections_url=data.get("sectionsUrl", ""),
                section_groups_url=data.get("sectionGroupsUrl"),
                web_url=data.get("links", {}).get("oneNoteWebUrl", {}).get("href", web_url),
                user_role=data.get("userRole", "Unknown"),
                is_shared=data.get("isShared", False),
                created_by=created_by,
                last_modified_datetime=data.get("lastModifiedDateTime")
            )

            logger.info(
                f"Normalized notebook: {normalized.display_name} "
                f"(id={normalized.id}, site_id={site_id}, shared={normalized.is_shared})"
            )

            return normalized

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Notebook not found or not accessible: {web_url}")
            elif e.response.status_code == 403:
                logger.warning(f"Access denied to notebook: {web_url}")
            else:
                logger.error(f"HTTP error normalizing notebook: {e}")
            return None
        except Exception as e:
            logger.error(f"Error normalizing notebook {web_url}: {e}")
            return None

    @staticmethod
    def _extract_site_id(self_url: str) -> Optional[str]:
        """
        Extract siteId from OneNote self URL.

        Format: https://graph.microsoft.com/v1.0/sites/{siteId}/onenote/notebooks/{notebookId}
        where siteId is like: "contoso.sharepoint.com,guid1,guid2"

        Args:
            self_url: Self URL from notebook object

        Returns:
            Extracted site ID or None if not found
        """
        match = re.search(r'/sites/([^/]+)/onenote', self_url)
        if match:
            return match.group(1)
        return None

    async def discover_and_normalize_all(self) -> List[NormalizedNotebook]:
        """
        Discover all notebooks and normalize them in one call.

        This is the main entry point for the discovery flow.

        Returns:
            List of NormalizedNotebook objects ready for storage/sync
        """
        # Step 1: Discover candidates from all sources
        candidates = await self.discover_all_notebooks()

        # Step 2: Normalize each candidate
        normalized = []
        for candidate in candidates:
            logger.info(f"Normalizing: {candidate.display_name} (source: {candidate.source})")
            result = await self.normalize_notebook(candidate.web_url)
            if result:
                normalized.append(result)
            else:
                logger.warning(f"Failed to normalize: {candidate.display_name}")

        logger.info(f"Successfully normalized {len(normalized)}/{len(candidates)} notebooks")
        return normalized
