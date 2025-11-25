"""
Notebook models for OneNote notebook management.

Supports both owned and shared notebooks with user preferences.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Notebook(BaseModel):
    """
    Represents a OneNote notebook (owned or shared).

    Enhanced to support shared notebooks via Microsoft Graph API's
    getNotebookFromWebUrl endpoint.
    """

    # Core identifiers
    id: str = Field(..., description="OneNote notebook ID")
    user_id: str = Field(..., description="User ID who owns/accesses this notebook")

    # Display information
    display_name: str = Field(..., description="Notebook display name")
    created_datetime: Optional[datetime] = Field(None, description="Creation date")
    last_modified_datetime: Optional[datetime] = Field(None, description="Last modified date")

    # Shared notebook support (NEW)
    site_id: str = Field(..., description="SharePoint site ID (required for site-scoped API access)")
    is_shared: bool = Field(default=False, description="Whether this is a shared notebook")
    user_role: Optional[str] = Field(None, description="User's role: Owner, Contributor, or Reader")
    shared_by: Optional[str] = Field(None, description="Display name of notebook owner (if shared)")

    # Discovery metadata (NEW)
    web_url: Optional[str] = Field(None, description="OneNote web URL")
    sections_url: Optional[str] = Field(None, description="API endpoint for sections")

    # User preference (NEW)
    is_selected: bool = Field(default=True, description="Whether user wants to sync this notebook")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1-af85c8b8-8998-47db-a4b3-abeb291fba11",
                "user_id": "user-123",
                "display_name": "Personal Notes",
                "site_id": "contoso.sharepoint.com,9bedfee2-863c-49d0-aef7-dc02dde749de,02ab0198-6a10-4e96-b4b4-def8b2ae4aed",
                "is_shared": False,
                "user_role": "Owner",
                "is_selected": True,
                "web_url": "https://onedrive.live.com/...",
                "sections_url": "https://graph.microsoft.com/v1.0/sites/.../onenote/notebooks/.../sections"
            }
        }


class NotebookCandidate(BaseModel):
    """
    Temporary model for discovered notebooks before normalization.

    Used during discovery phase before calling getNotebookFromWebUrl.
    """
    display_name: str
    web_url: str
    source: str = Field(..., description="Discovery source: owned, recent, or shared")
    last_modified_datetime: Optional[datetime] = None


class NormalizedNotebook(BaseModel):
    """
    Result from getNotebookFromWebUrl API call.

    Contains all information needed to access the notebook.
    """
    id: str
    display_name: str
    site_id: str
    sections_url: str
    section_groups_url: Optional[str] = None
    web_url: str
    user_role: str
    is_shared: bool
    created_by: Optional[str] = None  # Display name of creator
    last_modified_datetime: Optional[datetime] = None


class NotebookSelectionRequest(BaseModel):
    """Request to update which notebooks to sync."""
    notebook_ids: list[str] = Field(..., description="List of notebook IDs to sync")


class NotebookStatus(BaseModel):
    """Sync status for a notebook."""
    id: str
    display_name: str
    is_selected: bool
    sync_status: str = Field(..., description="Status: syncing, completed, error, never_synced")
    last_synced_at: Optional[datetime] = None
    page_count: int = 0
    section_count: int = 0
    error_message: Optional[str] = None
