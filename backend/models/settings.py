"""
Settings model for database storage.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SettingCreate(BaseModel):
    """Model for creating a new setting."""
    key: str
    value: str
    is_sensitive: bool = False
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    """Model for updating an existing setting."""
    value: str


class Setting(BaseModel):
    """Model for a setting stored in database."""
    id: int
    key: str
    value: str
    is_sensitive: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingResponse(BaseModel):
    """Model for returning settings to frontend (masks sensitive values)."""
    key: str
    value: str  # Will be masked if sensitive
    is_sensitive: bool
    description: Optional[str]
    has_value: bool  # Indicates if a value is set (for sensitive fields)
