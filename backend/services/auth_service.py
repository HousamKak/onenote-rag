"""Authentication service for handling Microsoft OAuth and JWT token validation."""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
 
import jwt
from jwt import PyJWTError
from jose import JWTError, jwt as jose_jwt
import requests
 
logger = logging.getLogger(__name__)
 
 
class AuthService:
    """Service for handling OAuth authentication and token validation."""
 
    def __init__(self, client_id: str, tenant_id: str, client_secret: str):
        """
        Initialize the authentication service.
 
        Args:
            client_id: Microsoft Azure AD application (client) ID
            tenant_id: Microsoft Azure AD tenant ID
            client_secret: Microsoft Azure AD client secret (for web app flow)
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.token_endpoint = f"{self.authority}/oauth2/v2.0/token"
        self.authorize_endpoint = f"{self.authority}/oauth2/v2.0/authorize"
 
        # Cache for Microsoft's public signing keys
        self._signing_keys: Optional[Dict] = None
        self._keys_last_fetched: Optional[datetime] = None
 
    def get_authorization_url(
        self, redirect_uri: str, state: str, scopes: list[str], prompt: str = "select_account"
    ) -> str:
        """
        Generate the Microsoft OAuth authorization URL.
 
        Args:
            redirect_uri: Where Microsoft will redirect after authentication
            state: Random state string for CSRF protection
            scopes: List of permission scopes to request
            prompt: OAuth prompt parameter (default: select_account)
                - "select_account": Always show account picker
                - "login": Force re-authentication
                - "consent": Force consent screen
                - "none": Silent auth (will fail if user not signed in)
 
        Returns:
            Full authorization URL to redirect user to
        """
        scope_string = " ".join(scopes)
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": scope_string,
            "state": state,
            "prompt": prompt,  # Force account selection
        }
 
        query_string = "&".join([f"{k}={requests.utils.quote(v)}" for k, v in params.items()])
        return f"{self.authorize_endpoint}?{query_string}"
 
    async def acquire_token_by_code(
        self, code: str, redirect_uri: str, scopes: list[str]
    ) -> Dict:
        """
        Exchange an authorization code for access and refresh tokens.
 
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Must match the redirect_uri used in authorization
            scopes: List of permission scopes
 
        Returns:
            Dictionary containing:
                - access_token: Token for accessing Microsoft Graph
                - refresh_token: Token for refreshing access token
                - expires_in: Seconds until access token expires
                - id_token: JWT containing user information
                - token_type: Usually "Bearer"
 
        Raises:
            Exception: If token exchange fails
        """
        scope_string = " ".join(scopes)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope_string,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
 
        try:
            response = requests.post(self.token_endpoint, data=data)
            response.raise_for_status()
            token_response = response.json()
 
            logger.info(f"Successfully acquired tokens for user")
            return token_response
 
        except requests.HTTPError as e:
            logger.error(f"Failed to acquire token: {e.response.text}")
            raise Exception(f"Token acquisition failed: {e.response.text}")
 
    async def refresh_access_token(self, refresh_token: str, scopes: list[str]) -> Dict:
        """
        Refresh an expired access token using a refresh token.
 
        Args:
            refresh_token: The refresh token
            scopes: List of permission scopes
 
        Returns:
            Dictionary containing new access_token and updated token info
 
        Raises:
            Exception: If token refresh fails
        """
        scope_string = " ".join(scopes)
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope_string,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
 
        try:
            response = requests.post(self.token_endpoint, data=data)
            response.raise_for_status()
            token_response = response.json()
 
            logger.info("Successfully refreshed access token")
            return token_response
 
        except requests.HTTPError as e:
            logger.error(f"Failed to refresh token: {e.response.text}")
            raise Exception(f"Token refresh failed: {e.response.text}")
 
    def _get_signing_keys(self) -> Dict:
        """
        Fetch Microsoft's public signing keys for JWT validation.
 
        Returns:
            Dictionary mapping key IDs (kid) to signing keys
 
        Raises:
            Exception: If keys cannot be fetched
        """
        # Cache keys for 24 hours
        if (
            self._signing_keys
            and self._keys_last_fetched
            and (datetime.utcnow() - self._keys_last_fetched) < timedelta(hours=24)
        ):
            return self._signing_keys
 
        # Fetch keys from Microsoft
        keys_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        try:
            response = requests.get(keys_url)
            response.raise_for_status()
            jwks = response.json()
 
            # Build key mapping
            self._signing_keys = {key["kid"]: key for key in jwks.get("keys", [])}
            self._keys_last_fetched = datetime.utcnow()
 
            logger.info(f"Fetched {len(self._signing_keys)} signing keys from Microsoft")
            return self._signing_keys
 
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch signing keys: {e}")
            raise Exception("Cannot validate tokens without signing keys")
 
    def validate_token(self, token: str) -> Dict:
        """
        Validate a JWT access token or ID token.
 
        Args:
            token: JWT token string
 
        Returns:
            Dictionary containing token claims (user_id, email, etc.)
 
        Raises:
            Exception: If token is invalid or expired
        """
        try:
            # Decode header without validation to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
 
            if not kid:
                raise Exception("Token missing 'kid' header")
 
            # Get signing key
            signing_keys = self._get_signing_keys()
            if kid not in signing_keys:
                # Refresh keys in case they've been rotated
                self._signing_keys = None
                signing_keys = self._get_signing_keys()
 
                if kid not in signing_keys:
                    raise Exception(f"Signing key {kid} not found")
 
            # Validate and decode token
            key = signing_keys[kid]
            claims = jose_jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
            )
 
            logger.debug(f"Token validated for user: {claims.get('oid', claims.get('sub'))}")
            return claims
 
        except JWTError as e:
            logger.error(f"JWT validation failed: {e}")
            raise Exception(f"Invalid token: {str(e)}")
        except PyJWTError as e:
            logger.error(f"JWT decoding failed: {e}")
            raise Exception(f"Invalid token: {str(e)}")
 
    def extract_user_info(self, claims: Dict) -> Dict:
        """
        Extract user information from token claims.
 
        Args:
            claims: Decoded JWT claims
 
        Returns:
            Dictionary with user_id, email, name
        """
        return {
            "user_id": claims.get("oid") or claims.get("sub"),  # Object ID or subject
            "email": claims.get("email") or claims.get("preferred_username"),
            "name": claims.get("name"),
        }
 