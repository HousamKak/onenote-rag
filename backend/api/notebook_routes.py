"""
API routes for notebook discovery, selection, and management.

Endpoints:
- GET /api/notebooks/discover - Discover all accessible notebooks
- POST /api/notebooks/select - Update notebook selection preferences
- GET /api/notebooks/status - Get sync status for all notebooks
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from models.user import UserContext
from models.notebook import (
    Notebook,
    NormalizedNotebook,
    NotebookSelectionRequest,
    NotebookStatus
)
from services.onenote_discovery_service import OneNoteDiscoveryService
from services.notebook_db import NotebookDB
from middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])

# Global notebook database service (initialized in main.py)
notebook_db: NotebookDB = None


def set_notebook_db(db: NotebookDB):
    """Set the global notebook database service."""
    global notebook_db
    notebook_db = db


def get_notebook_db() -> NotebookDB:
    """Dependency to get notebook database."""
    if notebook_db is None:
        raise HTTPException(status_code=500, detail="Notebook database not initialized")
    return notebook_db


@router.get("/discover")
async def discover_notebooks(
    user: UserContext = Depends(get_current_user),
    db: NotebookDB = Depends(get_notebook_db)
):
    """
    Discover all accessible notebooks (owned + shared).

    This endpoint:
    1. Discovers notebooks from 3 sources (owned, recent, shared)
    2. Normalizes each via getNotebookFromWebUrl to get siteId
    3. Stores/updates in database
    4. Returns list with current selection state

    Returns:
        {
            "notebooks": [...],
            "total": int,
            "by_source": {"owned": int, "recent": int, "shared": int}
        }
    """
    try:
        logger.info(f"Discovering notebooks for user {user.user_id}")

        # Create discovery service with user's access token
        discovery_service = OneNoteDiscoveryService(access_token=user.access_token)

        # Discover and normalize all notebooks
        normalized_notebooks = await discovery_service.discover_and_normalize_all()

        logger.info(f"Discovered {len(normalized_notebooks)} notebooks")

        # Convert to Notebook model and store in database
        notebooks_response = []
        source_counts = {"owned": 0, "recent": 0, "shared": 0}

        for norm_nb in normalized_notebooks:
            # Create Notebook model
            notebook = Notebook(
                id=norm_nb.id,
                user_id=user.user_id,
                display_name=norm_nb.display_name,
                created_datetime=None,  # Not always available
                last_modified_datetime=norm_nb.last_modified_datetime,
                site_id=norm_nb.site_id,
                is_shared=norm_nb.is_shared,
                user_role=norm_nb.user_role,
                shared_by=norm_nb.created_by if norm_nb.is_shared else None,
                web_url=norm_nb.web_url,
                sections_url=norm_nb.sections_url,
                is_selected=True  # Default to selected on first discovery
            )

            # Check if notebook already exists in database
            existing = db.get_notebook(notebook.id, user.user_id)
            if existing:
                # Preserve user's selection preference
                notebook.is_selected = existing.is_selected

            # Upsert to database
            db.upsert_notebook(notebook)

            # Add to response
            notebooks_response.append({
                "id": notebook.id,
                "displayName": notebook.display_name,
                "siteId": notebook.site_id,
                "isShared": notebook.is_shared,
                "userRole": notebook.user_role,
                "sharedBy": notebook.shared_by,
                "webUrl": notebook.web_url,
                "lastModifiedDateTime": notebook.last_modified_datetime.isoformat() if notebook.last_modified_datetime else None,
                "isSelected": notebook.is_selected
            })

            # Count by source (approximate based on shared status)
            if notebook.is_shared:
                source_counts["shared"] += 1
            else:
                source_counts["owned"] += 1

        return {
            "notebooks": notebooks_response,
            "total": len(notebooks_response),
            "by_source": source_counts
        }

    except Exception as e:
        logger.error(f"Error discovering notebooks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to discover notebooks: {str(e)}")


@router.post("/select")
async def select_notebooks(
    request: NotebookSelectionRequest,
    user: UserContext = Depends(get_current_user),
    db: NotebookDB = Depends(get_notebook_db)
):
    """
    Update which notebooks the user wants to sync.

    This updates the is_selected flag in the database for the specified notebooks.
    Deselects all notebooks first, then selects the specified ones.

    Request:
        {
            "notebook_ids": ["id1", "id2", ...]
        }

    Returns:
        {
            "success": true,
            "selected": int,
            "message": str
        }
    """
    try:
        logger.info(f"Updating notebook selection for user {user.user_id}: {len(request.notebook_ids)} notebooks")

        # Update selection in database
        db.update_selection(user.user_id, request.notebook_ids)

        return {
            "success": True,
            "selected": len(request.notebook_ids),
            "message": f"Successfully updated selection. {len(request.notebook_ids)} notebook(s) selected for sync."
        }

    except Exception as e:
        logger.error(f"Error updating notebook selection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update selection: {str(e)}")


@router.get("/status")
async def get_notebook_status(
    user: UserContext = Depends(get_current_user),
    db: NotebookDB = Depends(get_notebook_db)
):
    """
    Get sync status for all notebooks.

    Returns:
        {
            "notebooks": [
                {
                    "id": str,
                    "displayName": str,
                    "isSelected": bool,
                    "syncStatus": str,
                    "lastSyncedAt": str|null,
                    "pageCount": int,
                    "sectionCount": int,
                    "errorMessage": str|null
                },
                ...
            ]
        }
    """
    try:
        logger.info(f"Getting notebook status for user {user.user_id}")

        # Get status from database
        statuses = db.get_notebook_status(user.user_id)

        # Convert to response format
        notebooks = []
        for status in statuses:
            notebooks.append({
                "id": status.id,
                "displayName": status.display_name,
                "isSelected": status.is_selected,
                "syncStatus": status.sync_status,
                "lastSyncedAt": status.last_synced_at.isoformat() if status.last_synced_at else None,
                "pageCount": status.page_count,
                "sectionCount": status.section_count,
                "errorMessage": status.error_message
            })

        return {
            "notebooks": notebooks
        }

    except Exception as e:
        logger.error(f"Error getting notebook status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/list")
async def list_notebooks(
    user: UserContext = Depends(get_current_user),
    db: NotebookDB = Depends(get_notebook_db),
    selected_only: bool = False
):
    """
    List all notebooks for the user from database.

    Query Parameters:
        selected_only: If true, only return selected notebooks

    Returns:
        {
            "notebooks": [...]
        }
    """
    try:
        logger.info(f"Listing notebooks for user {user.user_id} (selected_only={selected_only})")

        # Get notebooks from database
        notebooks = db.get_notebooks_for_user(user.user_id, selected_only=selected_only)

        # Convert to response format
        notebooks_response = []
        for nb in notebooks:
            notebooks_response.append({
                "id": nb.id,
                "displayName": nb.display_name,
                "siteId": nb.site_id,
                "isShared": nb.is_shared,
                "userRole": nb.user_role,
                "sharedBy": nb.shared_by,
                "webUrl": nb.web_url,
                "isSelected": nb.is_selected,
                "lastModifiedDateTime": nb.last_modified_datetime.isoformat() if nb.last_modified_datetime else None
            })

        return {
            "notebooks": notebooks_response
        }

    except Exception as e:
        logger.error(f"Error listing notebooks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list notebooks: {str(e)}")
