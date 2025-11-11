"""Token storage service for managing user authentication tokens."""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from threading import Lock

from models.user import TokenData

logger = logging.getLogger(__name__)


class TokenStore:
    """
    In-memory token storage for user sessions.

    This is suitable for single-server deployments. For production multi-server
    deployments, consider using Redis or a database-backed store.
    """

    def __init__(self):
        """Initialize the token store."""
        self._tokens: Dict[str, TokenData] = {}
        self._lock = Lock()

    def set_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        token_type: str = "Bearer",
        scope: Optional[str] = None,
        id_token: Optional[str] = None,
    ) -> None:
        """
        Store tokens for a user.

        Args:
            user_id: User identifier
            access_token: Microsoft Graph access token
            refresh_token: Refresh token for obtaining new access tokens
            expires_in: Seconds until access token expires
            token_type: Token type (usually "Bearer")
            scope: Granted scopes
            id_token: Optional ID token with user claims
        """
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        token_data = TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_at=expires_at,
            scope=scope,
            id_token=id_token,
        )

        with self._lock:
            self._tokens[user_id] = token_data
            logger.info(f"Stored tokens for user {user_id}, expires at {expires_at}")

    def get_tokens(self, user_id: str) -> Optional[TokenData]:
        """
        Retrieve tokens for a user.

        Args:
            user_id: User identifier

        Returns:
            TokenData if found, None otherwise
        """
        with self._lock:
            return self._tokens.get(user_id)

    def update_access_token(
        self, user_id: str, access_token: str, expires_in: int
    ) -> None:
        """
        Update just the access token (after refresh).

        Args:
            user_id: User identifier
            access_token: New access token
            expires_in: Seconds until new access token expires
        """
        with self._lock:
            if user_id in self._tokens:
                token_data = self._tokens[user_id]
                token_data.access_token = access_token
                token_data.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                logger.info(f"Updated access token for user {user_id}")
            else:
                logger.warning(f"Cannot update token for unknown user {user_id}")

    def delete_tokens(self, user_id: str) -> None:
        """
        Delete tokens for a user (logout).

        Args:
            user_id: User identifier
        """
        with self._lock:
            if user_id in self._tokens:
                del self._tokens[user_id]
                logger.info(f"Deleted tokens for user {user_id}")

    def clear_expired_tokens(self) -> None:
        """Remove all expired tokens from the store."""
        with self._lock:
            expired_users = [
                user_id
                for user_id, token_data in self._tokens.items()
                if token_data.is_expired()
            ]

            for user_id in expired_users:
                del self._tokens[user_id]

            if expired_users:
                logger.info(f"Cleared {len(expired_users)} expired tokens")

    def get_user_count(self) -> int:
        """
        Get the number of users with stored tokens.

        Returns:
            Count of users
        """
        with self._lock:
            return len(self._tokens)
