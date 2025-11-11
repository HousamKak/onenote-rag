"""User models for authentication and authorization."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UserContext:
    """Context object containing authenticated user information."""

    user_id: str  # Azure AD user ID (oid or sub claim)
    email: Optional[str] = None
    name: Optional[str] = None
    access_token: str = ""  # User's Microsoft Graph access token

    def __repr__(self) -> str:
        return f"UserContext(user_id={self.user_id}, email={self.email})"


@dataclass
class TokenData:
    """Token data for a user session."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime = None
    scope: Optional[str] = None
    id_token: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return True
        # Add 5 minute buffer to avoid edge cases
        return datetime.utcnow() >= self.expires_at - datetime.timedelta(minutes=5)
