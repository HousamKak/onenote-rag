"""Document models for OneNote content."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
 
 
class DocumentMetadata(BaseModel):
    """Metadata for a OneNote document."""
 
    page_id: str = Field(..., description="OneNote page ID")
    page_title: str = Field(..., description="Page title")
    section_name: str = Field(..., description="Section name")
    notebook_name: str = Field(..., description="Notebook name")
    created_date: Optional[datetime] = Field(None, description="Creation date")
    modified_date: Optional[datetime] = Field(None, description="Last modified date")
    author: Optional[str] = Field(None, description="Page author")
    tags: List[str] = Field(default_factory=list, description="Page tags")
    url: Optional[str] = Field(None, description="OneNote web URL")
   
    # Image metadata
    has_images: bool = Field(default=False, description="Whether document has images")
    image_count: int = Field(default=0, description="Number of images in document")
 
 
class Document(BaseModel):
    """Represents a processed OneNote document."""
 
    id: str = Field(..., description="Unique document ID (same as page_id)")
    page_id: str = Field(..., description="OneNote page ID (same as id)")
    content: str = Field(..., description="Document text content")
    html_content: Optional[str] = Field(None, description="Original HTML content from OneNote")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
 
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc-123",
                "page_id": "doc-123",
                "content": "This is the page content...",
                "html_content": "<html>...</html>",
                "metadata": {
                    "page_id": "page-456",
                    "page_title": "Meeting Notes",
                    "section_name": "Work",
                    "notebook_name": "My Notebook",
                    "tags": ["meeting", "important"],
                    "has_images": True,
                    "image_count": 2
                }
            }
        }
 
 
 