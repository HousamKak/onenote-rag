"""
OneNote Discovery Service - Discover and normalize notebooks from multiple official sources.
 
Discovery Strategy:
1. Owned notebooks: /me/onenote/notebooks
2. Shared notebooks: /me/drive/sharedWithMe (filtered by package.type = "oneNote")
3. Recent notebooks: /me/drive/recent (filtered by package.type = "oneNote")
4. Normalize via getNotebookFromWebUrl to get siteId and proper OneNote object
 
Key Innovation:
Uses getNotebookFromWebUrl to convert ANY notebook (owned, shared, or recent) into a proper
OneNote object with siteId, enabling site-scoped API access for all notebooks.
 
Requirements:
- Owned notebooks: Requires Notes.Read or Notes.Read.All
- Shared notebooks: Requires Files.Read.All for package metadata
- Recent notebooks: Requires Files.Read or Files.Read.All
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
import requests
 
from models.notebook import NotebookCandidate, NormalizedNotebook
 
logger = logging.getLogger(__name__)
 
 
class OneNoteDiscoveryService:
    """
    Discover and normalize OneNote notebooks from official Microsoft Graph endpoints.
 
    Supports:
    - Owned notebooks: /me/onenote/notebooks
    - Shared notebooks: /me/drive/sharedWithMe (requires Files.Read.All for package field)
    - Recent notebooks: /me/insights/used (requires Sites.Read.All for insights data)
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
        logger.info("🔐 [DISCOVERY] ========================================")
        logger.info("🔐 [DISCOVERY] Starting notebook discovery from all sources")
        logger.info("🔐 [DISCOVERY] ========================================")
       
        candidates = []
 
        # Source 1: Owned notebooks
        logger.info("🔐 [DISCOVERY] SOURCE 1: Discovering owned notebooks...")
        owned = await self._discover_owned_notebooks()
        candidates.extend(owned)
        logger.info(f"🔐 [DISCOVERY] SOURCE 1 RESULT: Found {len(owned)} owned notebooks")
 
        # Source 2: Shared notebooks (via sharedWithMe)
        logger.info("🔐 [DISCOVERY] SOURCE 2: Discovering shared notebooks...")
        shared = await self._discover_shared_notebooks()
        candidates.extend(shared)
        logger.info(f"🔐 [DISCOVERY] SOURCE 2 RESULT: Found {len(shared)} shared notebooks")
 
        # Source 3: Recently accessed/viewed notebooks (via insights/used)
        logger.info("🔐 [DISCOVERY] SOURCE 3: Discovering recently accessed notebooks...")
        recent = await self._discover_recent_notebooks()
        candidates.extend(recent)
        logger.info(f"🔐 [DISCOVERY] SOURCE 3 RESULT: Found {len(recent)} recently accessed notebooks")
 
        # Deduplicate by webUrl
        logger.info(f"🔐 [DISCOVERY] Deduplicating notebooks (total candidates: {len(candidates)})...")
        seen_urls = set()
        unique_candidates = []
        duplicates_removed = 0
       
        for candidate in candidates:
            if candidate.web_url not in seen_urls:
                seen_urls.add(candidate.web_url)
                unique_candidates.append(candidate)
            else:
                duplicates_removed += 1
                logger.debug(f"🔐 [DISCOVERY] Duplicate removed: {candidate.display_name}")
 
        if duplicates_removed > 0:
            logger.info(f"🔐 [DISCOVERY] Removed {duplicates_removed} duplicate(s)")
       
        logger.info("🔐 [DISCOVERY] ========================================")
        logger.info(f"🔐 [DISCOVERY] FINAL RESULT: {len(unique_candidates)} unique notebooks discovered")
        logger.info(f"🔐 [DISCOVERY]   - Owned: {len(owned)}")
        logger.info(f"🔐 [DISCOVERY]   - Shared: {len(shared)}")
        logger.info(f"🔐 [DISCOVERY]   - Recent: {len(recent)}")
        logger.info(f"🔐 [DISCOVERY]   - Duplicates removed: {duplicates_removed}")
        logger.info("🔐 [DISCOVERY] ========================================")
       
        return unique_candidates
 
    async def _discover_owned_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover user's own notebooks via /me/onenote/notebooks.
 
        Returns:
            List of NotebookCandidate objects
        """
        logger.info("🔐 [DISCOVERY] === Starting Owned Notebook Discovery ===")
        logger.info(f"🔐 [DISCOVERY] API Endpoint: {self.GRAPH_API_ENDPOINT}/me/onenote/notebooks")
       
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks"
           
            logger.info(f"🔐 [DISCOVERY] Making GET request to: {url}")
            response = self.session.get(url, timeout=30)
            logger.info(f"🔐 [DISCOVERY] Response status: {response.status_code}")
           
            if response.status_code == 401:
                logger.error(f"❌ [DISCOVERY] 401 Unauthorized - Token may be invalid or expired")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
            elif response.status_code == 403:
                logger.error(f"❌ [DISCOVERY] 403 Forbidden - May need Notes.Read.All scope")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
           
            response.raise_for_status()
            data = response.json()
           
            notebooks_count = len(data.get("value", []))
            logger.info(f"🔐 [DISCOVERY] Found {notebooks_count} owned notebooks")
 
            candidates = []
            for notebook in data.get("value", []):
                display_name = notebook.get("displayName", "Unnamed Notebook")
                web_url = notebook.get("links", {}).get("oneNoteWebUrl", {}).get("href")
                if web_url:
                    logger.info(f"✓ [DISCOVERY] Found owned notebook: {display_name} -> {web_url}")
                    candidates.append(NotebookCandidate(
                        display_name=display_name,
                        web_url=web_url,
                        source="owned",
                        last_modified_datetime=notebook.get("lastModifiedDateTime")
                    ))
                else:
                    logger.warning(f"⚠️  [DISCOVERY] Owned notebook {display_name} has no webUrl")
 
            logger.info(f"🔐 [DISCOVERY] Owned notebooks discovery complete: {len(candidates)} candidates")
            return candidates
 
        except Exception as e:
            logger.error(f"❌ [DISCOVERY] Error discovering owned notebooks: {e}")
            return []
 
    async def _discover_shared_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover shared notebooks via /me/drive/sharedWithMe.
 
        Filters for OneNote notebooks (package.type = "oneNote").
       
        Note: The 'package' field requires Files.Read.All permission.
        If permission is missing, this will return an empty list until
        the permission is added in Azure AD and user re-authenticates.
 
        Returns:
            List of NotebookCandidate objects
        """
        logger.info("🔐 [DISCOVERY] === Starting Shared Notebook Discovery ===")
        logger.info(f"🔐 [DISCOVERY] API Endpoint: {self.GRAPH_API_ENDPOINT}/me/drive/sharedWithMe")
       
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/sharedWithMe"
           
            # Log token preview (for debugging)
            auth_header = self.session.headers.get('Authorization', 'No auth header')
            if auth_header != 'No auth header' and auth_header.startswith('Bearer '):
                token_preview = auth_header[:27] + '...' + auth_header[-20:]
                logger.info(f"🔐 [DISCOVERY] Using token: {token_preview}")
            else:
                logger.warning(f"🔐 [DISCOVERY] Auth header issue: {auth_header[:50]}")
           
            logger.info(f"🔐 [DISCOVERY] Making GET request to: {url}")
            response = self.session.get(url, timeout=30)
            logger.info(f"🔐 [DISCOVERY] Response status: {response.status_code}")
           
            if response.status_code == 401:
                logger.error(f"❌ [DISCOVERY] 401 Unauthorized - Token may be invalid or expired")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
            elif response.status_code == 403:
                logger.error(f"❌ [DISCOVERY] 403 Forbidden - May need Files.Read.All scope")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
           
            response.raise_for_status()
            data = response.json()
            logger.info(f"🔐 [DISCOVERY] Successfully retrieved sharedWithMe data")
 
            total_items = len(data.get("value", []))
            logger.info(f"Found {total_items} total items in sharedWithMe")
 
            candidates = []
            onenote_count = 0
            missing_package_count = 0
            other_types = {}
           
            for item in data.get("value", []):
                item_name = item.get("name", "Unnamed")
               
                # Check for package field - may be missing without Files.Read.All permission
                remote_item = item.get("remoteItem", {})
                package = remote_item.get("package")
               
                if package is None:
                    # Package field is missing - insufficient permissions
                    missing_package_count += 1
                    logger.debug(f"Item '{item_name}' has no package field (needs Files.Read.All permission)")
                    continue
               
                package_type = package.get("type") if isinstance(package, dict) else None
 
                # Track what types we're seeing
                if package_type:
                    other_types[package_type] = other_types.get(package_type, 0) + 1
                else:
                    other_types["unknown"] = other_types.get("unknown", 0) + 1
 
                logger.debug(f"Item: {item_name}, Package type: {package_type}")
 
                if package_type == "oneNote":
                    onenote_count += 1
                    web_url = remote_item.get("webUrl")
                    if web_url:
                        logger.info(f"✓ Found OneNote shared notebook: {item_name} -> {web_url}")
                        candidates.append(NotebookCandidate(
                            display_name=item_name,
                            web_url=web_url,
                            source="shared",
                            last_modified_datetime=remote_item.get("lastModifiedDateTime")
                        ))
                    else:
                        logger.warning(f"OneNote item {item_name} has no webUrl")
 
            # Log summary
            logger.info(f"🔐 [DISCOVERY] === Shared Notebook Discovery Summary ===")
            logger.info(f"🔐 [DISCOVERY] Total items in sharedWithMe: {total_items}")
            logger.info(f"🔐 [DISCOVERY] Items missing 'package' field: {missing_package_count}")
            logger.info(f"🔐 [DISCOVERY] Package type distribution: {other_types}")
            logger.info(f"🔐 [DISCOVERY] OneNote notebooks found: {onenote_count}")
            logger.info(f"🔐 [DISCOVERY] Candidates returned: {len(candidates)}")
           
            if missing_package_count > 0:
                logger.warning(
                    f"⚠️  [DISCOVERY] {missing_package_count} items missing 'package' field. "
                    f"Add Files.Read.All permission in Azure AD to discover shared notebooks."
                )
           
            if onenote_count == 0 and missing_package_count > 0:
                logger.warning(
                    "⚠️  [DISCOVERY] No shared notebooks discovered. This may be because:\n"
                    "  1. Files.Read.All permission is not granted in Azure AD\n"
                    "  2. User needs to re-authenticate after permission is added\n"
                    "  3. No OneNote notebooks are actually shared with this user"
                )
            elif onenote_count == 0 and missing_package_count == 0:
                logger.info("ℹ️  [DISCOVERY] No OneNote notebooks are shared with this user")
           
            return candidates
 
        except Exception as e:
            logger.error(f"❌ [DISCOVERY] Error discovering shared notebooks: {e}")
            logger.error(f"❌ [DISCOVERY] Exception type: {type(e).__name__}")
            logger.error(f"❌ [DISCOVERY] Exception details: {str(e)}")
            import traceback
            logger.error(f"❌ [DISCOVERY] Traceback:\n{traceback.format_exc()}")
            return []
 
    async def _discover_recent_notebooks(self) -> List[NotebookCandidate]:
        """
        Discover recently accessed notebooks via /me/drive/recent.
 
        This endpoint returns driveItems that have been recently accessed by the user,
        including OneNote notebooks. It shows files the user has recently opened,
        modified, or viewed.
 
        Filters for OneNote notebooks by checking package.type = "oneNote".
       
        Note: Requires Files.Read or Files.Read.All permission.
 
        Returns:
            List of NotebookCandidate objects
        """
        logger.info("🔐 [DISCOVERY] === Starting Recent Notebook Discovery ===")
        logger.info(f"🔐 [DISCOVERY] API Endpoint: {self.GRAPH_API_ENDPOINT}/me/drive/recent")
       
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/drive/recent"
           
            logger.info(f"🔐 [DISCOVERY] Making GET request to: {url}")
            response = self.session.get(url, timeout=30)
            logger.info(f"🔐 [DISCOVERY] Response status: {response.status_code}")
           
            if response.status_code == 401:
                logger.error(f"❌ [DISCOVERY] 401 Unauthorized - Token may be invalid or expired")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
                return []
            elif response.status_code == 403:
                logger.error(f"❌ [DISCOVERY] 403 Forbidden - May need Files.Read.All scope")
                logger.error(f"❌ [DISCOVERY] Response: {response.text[:500]}")
                return []
           
            response.raise_for_status()
            data = response.json()
            logger.info(f"🔐 [DISCOVERY] Successfully retrieved drive/recent data")
 
            total_items = len(data.get("value", []))
            logger.info(f"Found {total_items} total items in recently accessed")
 
            candidates = []
            onenote_count = 0
            item_types = {}
           
            for item in data.get("value", []):
                item_name = item.get("name", "Unnamed")
                web_url = item.get("webUrl")
                last_modified = item.get("lastModifiedDateTime")
               
                # Check for package type (OneNote indicator)
                package = item.get("package", {})
                package_type = package.get("type") if package else None
               
                # Track item types we're seeing
                if package_type:
                    item_types[f"package:{package_type}"] = item_types.get(f"package:{package_type}", 0) + 1
                elif item.get("folder"):
                    item_types["folder"] = item_types.get("folder", 0) + 1
                elif item.get("file"):
                    mime_type = item.get("file", {}).get("mimeType", "unknown")
                    item_types[f"file:{mime_type}"] = item_types.get(f"file:{mime_type}", 0) + 1
                else:
                    item_types["unknown"] = item_types.get("unknown", 0) + 1
               
                logger.debug(f"Item: {item_name}, Package type: {package_type}, URL: {web_url}")
 
                # Check if this is a OneNote notebook
                if package_type == "oneNote" and web_url:
                    onenote_count += 1
                   
                    logger.info(f"✓ Found recently accessed OneNote notebook: {item_name} -> {web_url}")
                    logger.info(f"  Last modified: {last_modified}")
                   
                    candidates.append(NotebookCandidate(
                        display_name=item_name,
                        web_url=web_url,
                        source="recent",
                        last_modified_datetime=last_modified
                    ))
 
            # Log summary
            logger.info(f"🔐 [DISCOVERY] === Recent Notebook Discovery Summary ===")
            logger.info(f"🔐 [DISCOVERY] Total items in drive/recent: {total_items}")
            logger.info(f"🔐 [DISCOVERY] Item type distribution: {item_types}")
            logger.info(f"🔐 [DISCOVERY] OneNote notebooks found: {onenote_count}")
            logger.info(f"🔐 [DISCOVERY] Candidates returned: {len(candidates)}")
           
            if onenote_count == 0 and total_items > 0:
                logger.info("ℹ️  [DISCOVERY] No OneNote notebooks in recently accessed items")
            elif onenote_count == 0 and total_items == 0:
                logger.warning(
                    "⚠️  [DISCOVERY] No recent items found. This may be because:\n"
                    "  1. Files.Read.All permission is not granted\n"
                    "  2. User needs to re-authenticate after permission is added\n"
                    "  3. No recent files have been accessed"
                )
           
            return candidates
 
        except Exception as e:
            logger.error(f"❌ [DISCOVERY] Error discovering recent notebooks: {e}")
            logger.error(f"❌ [DISCOVERY] Exception type: {type(e).__name__}")
            logger.error(f"❌ [DISCOVERY] Exception details: {str(e)}")
            import traceback
            logger.error(f"❌ [DISCOVERY] Traceback:\n{traceback.format_exc()}")
            return []
 
    async def normalize_notebook(self, web_url: str, source: str = "unknown") -> Optional[NormalizedNotebook]:
        """
        Normalize a notebook via getNotebookFromWebUrl.
 
        This is the KEY step that converts any notebook (owned or shared) into
        a proper OneNote object with siteId for site-scoped API access.
 
        Args:
            web_url: OneNote web URL from any source
            source: The source of discovery (owned, recent, shared)
 
        Returns:
            NormalizedNotebook with id, siteId, and API endpoints, or None if failed
        """
        try:
            url = f"{self.GRAPH_API_ENDPOINT}/me/onenote/notebooks/getNotebookFromWebUrl"
            payload = {"webUrl": web_url}
 
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
           
            # Parse JSON response
            try:
                data = response.json()
            except Exception as json_error:
                logger.error(f"Failed to parse JSON response: {json_error}")
                logger.error(f"Raw response: {response.text[:500]}")
                return None
 
            # Validate response is a dictionary
            if not isinstance(data, dict):
                logger.error(f"Expected dict response, got {type(data)}: {data}")
                return None
 
            # Log the response for debugging
            logger.debug(f"getNotebookFromWebUrl response: {data}")
 
            # Extract siteId from self URL using regex
            # Format: .../sites/{siteId}/onenote/notebooks/{notebookId}
            self_url = data.get("self", "")
            site_id = self._extract_site_id(self_url)
 
            if not site_id:
                logger.warning(f"Could not extract site_id from: {self_url}")
                return None
 
            # Determine created_by from response
            # Note: API returns "createdBy" as a string, not a dict
            created_by = data.get("createdBy")
            if not created_by or not isinstance(created_by, str):
                # Fall back to dict structure if it exists
                created_by_obj = data.get("createdBy")
                if created_by_obj and isinstance(created_by_obj, dict):
                    user_obj = created_by_obj.get("user")
                    if user_obj and isinstance(user_obj, dict):
                        created_by = user_obj.get("displayName")
 
            # Determine lastModifiedBy from response
            last_modified_by = data.get("lastModifiedBy")
            if not last_modified_by or not isinstance(last_modified_by, str):
                # Fall back to dict structure if it exists
                last_modified_by_obj = data.get("lastModifiedBy")
                if last_modified_by_obj and isinstance(last_modified_by_obj, dict):
                    user_obj = last_modified_by_obj.get("user")
                    if user_obj and isinstance(user_obj, dict):
                        last_modified_by = user_obj.get("displayName")
 
            # Extract web_url safely
            notebook_web_url = web_url  # Default to input web_url
            links = data.get("links")
            if links and isinstance(links, dict):
                one_note_web_url = links.get("oneNoteWebUrl")
                if one_note_web_url and isinstance(one_note_web_url, dict):
                    href = one_note_web_url.get("href")
                    if href:
                        notebook_web_url = href
 
            # Note: The API returns "name" not "displayName"
            display_name = data.get("name") or data.get("displayName") or "Unnamed"
           
            # Log ALL fields from the response for debugging
            logger.info(f"=== Full response for notebook (source={source}) ===")
            logger.info(f"Display name: {display_name}")
            logger.info(f"All available fields: {list(data.keys())}")
            logger.info(f"Full data: {json.dumps(data, indent=2, default=str)}")
            logger.info(f"=== End response ===")
           
            # Determine if notebook is truly shared
            # Only trust the source of discovery - if it came from sharedWithMe, it's shared
            api_is_shared = data.get("isShared", False)
            is_from_shared_source = (source == "shared")
           
            # Mark as shared if either the API says so OR it came from sharedWithMe endpoint
            is_shared = api_is_shared or is_from_shared_source
           
            # Log shared detection details
            logger.info(
                f"Shared detection for '{display_name}': "
                f"api_is_shared={api_is_shared}, "
                f"source={source}, "
                f"FINAL is_shared={is_shared}"
            )
           
            normalized = NormalizedNotebook(
                id=data.get("id"),
                display_name=display_name,
                site_id=site_id,
                sections_url=data.get("sectionsUrl", ""),
                section_groups_url=data.get("sectionGroupsUrl"),
                web_url=notebook_web_url,
                user_role=data.get("userRole", "Unknown"),
                is_shared=is_shared,
                created_by=created_by,
                last_modified_datetime=data.get("lastModifiedTime") or data.get("lastModifiedDateTime")
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
            result = await self.normalize_notebook(candidate.web_url, source=candidate.source)
            if result:
                normalized.append(result)
            else:
                logger.warning(f"Failed to normalize: {candidate.display_name}")
 
        logger.info(f"Successfully normalized {len(normalized)}/{len(candidates)} notebooks")
        return normalized
 