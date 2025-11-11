"""Authentication middleware for FastAPI."""
import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.user import UserContext, TokenData
from services.auth_service import AuthService
from services.token_store import TokenStore

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=True)


# Global instances (will be initialized in main.py)
auth_service: Optional[AuthService] = None
token_store: Optional[TokenStore] = None


def initialize_auth(service: AuthService, store: TokenStore):
    """
    Initialize global auth service and token store.

    Args:
        service: Configured AuthService instance
        store: Configured TokenStore instance
    """
    global auth_service, token_store
    auth_service = service
    token_store = store
    logger.info("Authentication middleware initialized")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserContext:
    """
    FastAPI dependency that extracts and validates user from Bearer token.

    This dependency should be added to any endpoint that requires authentication.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        UserContext containing user_id, email, and access token

    Raises:
        HTTPException: If token is invalid, expired, or user not found

    Example:
        @router.get("/protected")
        async def protected_endpoint(user: UserContext = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not auth_service or not token_store:
        logger.error("Auth service not initialized")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not configured",
        )

    token = credentials.credentials

    try:
        # Validate the token and extract claims
        claims = auth_service.validate_token(token)
        user_info = auth_service.extract_user_info(claims)
        user_id = user_info["user_id"]

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user's stored tokens
        token_data = token_store.get_tokens(user_id)

        if not token_data:
            # User has a valid ID token but no stored session
            # This might happen if server restarted or token store was cleared
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if access token is expired and refresh if needed
        if token_data.is_expired():
            logger.info(f"Access token expired for user {user_id}, refreshing...")
            try:
                # Refresh the token
                scopes = token_data.scope.split(" ") if token_data.scope else [
                    "User.Read",
                    "Notes.Read",
                    "Notes.Read.All"
                ]
                new_token_response = await auth_service.refresh_access_token(
                    token_data.refresh_token, scopes
                )

                # Update stored tokens
                token_store.update_access_token(
                    user_id,
                    new_token_response["access_token"],
                    new_token_response["expires_in"],
                )

                # Get updated token data
                token_data = token_store.get_tokens(user_id)
                logger.info(f"Successfully refreshed token for user {user_id}")

            except Exception as e:
                logger.error(f"Failed to refresh token for user {user_id}: {e}")
                # Refresh token expired or invalid - user needs to re-authenticate
                token_store.delete_tokens(user_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired. Please sign in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Return user context with fresh access token
        return UserContext(
            user_id=user_id,
            email=user_info.get("email"),
            name=user_info.get("name"),
            access_token=token_data.access_token,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_state() -> str:
    """
    Generate a random state string for OAuth CSRF protection.

    Returns:
        Random secure string
    """
    return secrets.token_urlsafe(32)
