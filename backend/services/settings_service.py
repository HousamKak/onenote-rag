"""
Settings management service with encryption support.
"""
import logging
import os
from typing import Optional, List, Dict, Any
from .database import DatabaseService
from .encryption import EncryptionService

logger = logging.getLogger(__name__)


# Settings that should be encrypted
SENSITIVE_KEYS = {
    "openai_api_key",
    "langchain_api_key"
}


class SettingsService:
    """Service for managing application settings with encryption."""

    def __init__(
        self,
        db_service: DatabaseService,
        encryption_service: EncryptionService
    ):
        """
        Initialize settings service.

        Args:
            db_service: Database service instance
            encryption_service: Encryption service instance
        """
        self.db = db_service
        self.encryption = encryption_service
        self._initialize_default_settings()

    def _initialize_default_settings(self) -> None:
        """Initialize default settings with descriptions."""
        defaults = [
            {
                "key": "openai_api_key",
                "description": "OpenAI API key for embeddings and LLM",
                "is_sensitive": True
            },
            {
                "key": "langchain_api_key",
                "description": "LangChain/LangSmith API key for tracing",
                "is_sensitive": True
            },
            {
                "key": "langchain_project",
                "description": "LangSmith project name",
                "is_sensitive": False
            },
            {
                "key": "langchain_tracing_v2",
                "description": "Enable LangSmith tracing (true/false)",
                "is_sensitive": False
            },
            {
                "key": "microsoft_client_id",
                "description": "Microsoft Azure AD Client ID for OAuth",
                "is_sensitive": False
            },
            {
                "key": "microsoft_tenant_id",
                "description": "Microsoft Azure AD Tenant ID",
                "is_sensitive": False
            },
            {
                "key": "oauth_redirect_uri",
                "description": "OAuth redirect URI for authentication callbacks",
                "is_sensitive": False
            },
            {
                "key": "oauth_scopes",
                "description": "OAuth scopes (space-separated)",
                "is_sensitive": False
            },
            {
                "key": "chunk_size",
                "description": "Document chunk size for processing",
                "is_sensitive": False
            },
            {
                "key": "chunk_overlap",
                "description": "Overlap between document chunks",
                "is_sensitive": False
            },
            {
                "key": "enable_startup_sync",
                "description": "Auto-sync OneNote on startup (true/false)",
                "is_sensitive": False
            },
            {
                "key": "embedding_provider",
                "description": "Embedding provider (openai)",
                "is_sensitive": False
            }
        ]

        # Only create if they don't exist (don't overwrite existing values)
        for default in defaults:
            existing = self.db.get_setting(default["key"])
            if not existing:
                # Check if value exists in environment variables
                env_value = os.getenv(default["key"].upper())
                if env_value:
                    # Migrate from .env to database
                    self.set_setting(
                        key=default["key"],
                        value=env_value,
                        description=default.get("description")
                    )
                    logger.info(f"Migrated {default['key']} from .env to database")

    def get_setting(self, key: str, decrypt: bool = True) -> Optional[str]:
        """
        Get a setting value.

        Args:
            key: Setting key
            decrypt: Whether to decrypt sensitive values

        Returns:
            Setting value or None if not found
        """
        setting = self.db.get_setting(key)
        if not setting:
            # Fallback to environment variable
            return os.getenv(key.upper())

        value = setting["value"]

        # Decrypt if sensitive and requested
        if decrypt and key in SENSITIVE_KEYS and value:
            try:
                value = self.encryption.decrypt(value)
            except Exception as e:
                logger.error(f"Failed to decrypt {key}: {str(e)}")
                return None

        return value

    def get_all_settings(self, mask_sensitive: bool = True) -> List[Dict[str, Any]]:
        """
        Get all settings.

        Args:
            mask_sensitive: Whether to mask sensitive values

        Returns:
            List of settings with values (includes all defaults even if not in DB)
        """
        # Define all expected settings with descriptions
        all_defaults = {
            "openai_api_key": {"description": "OpenAI API key for embeddings and LLM", "is_sensitive": True},
            "langchain_api_key": {"description": "LangChain/LangSmith API key for tracing", "is_sensitive": True},
            "langchain_project": {"description": "LangSmith project name", "is_sensitive": False},
            "langchain_tracing_v2": {"description": "Enable LangSmith tracing (true/false)", "is_sensitive": False},
            "microsoft_client_id": {"description": "Microsoft Azure AD Client ID", "is_sensitive": False},
            "microsoft_client_secret": {"description": "Microsoft Azure AD Client Secret", "is_sensitive": True},
            "microsoft_tenant_id": {"description": "Microsoft Azure AD Tenant ID", "is_sensitive": False},
            "microsoft_graph_token": {"description": "Microsoft Graph API Bearer Token (optional)", "is_sensitive": True},
            "use_azure_ad_auth": {"description": "Use Azure AD authentication (true) or Manual Token (false)", "is_sensitive": False},
            "chunk_size": {"description": "Document chunk size for processing", "is_sensitive": False},
            "chunk_overlap": {"description": "Overlap between document chunks", "is_sensitive": False},
            "enable_startup_sync": {"description": "Auto-sync OneNote on startup (true/false)", "is_sensitive": False},
            "embedding_provider": {"description": "Embedding provider (openai)", "is_sensitive": False}
        }
        
        # Get existing settings from database
        db_settings = {s["key"]: s for s in self.db.get_all_settings()}
        result = []

        # Process all default settings
        for key, default_info in all_defaults.items():
            is_sensitive = key in SENSITIVE_KEYS
            
            # Check if setting exists in database
            if key in db_settings:
                db_setting = db_settings[key]
                value = db_setting["value"]
                description = db_setting.get("description") or default_info["description"]
                has_value = bool(value)
                
                # Mask or decrypt sensitive values
                if mask_sensitive and is_sensitive:
                    value = "********" if has_value else ""
                elif is_sensitive and value:
                    try:
                        value = self.encryption.decrypt(value)
                    except Exception:
                        value = ""
            else:
                # Setting not in DB, check environment variable
                env_value = os.getenv(key.upper())
                value = env_value or ""
                description = default_info["description"]
                has_value = bool(env_value)
                
                # Mask sensitive env values
                if mask_sensitive and is_sensitive and has_value:
                    value = "********"

            result.append({
                "key": key,
                "value": value,
                "is_sensitive": is_sensitive,
                "description": description,
                "has_value": has_value
            })

        return result

    def set_setting(
        self,
        key: str,
        value: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            description: Optional description

        Returns:
            Updated setting
        """
        is_sensitive = key in SENSITIVE_KEYS

        # Encrypt sensitive values
        if is_sensitive and value:
            value = self.encryption.encrypt(value)

        return self.db.set_setting(
            key=key,
            value=value,
            is_sensitive=is_sensitive,
            description=description
        )

    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting.

        Args:
            key: Setting key

        Returns:
            True if deleted
        """
        return self.db.delete_setting(key)

    def get_settings_dict(self) -> Dict[str, str]:
        """
        Get all settings as a dictionary (decrypted).

        Returns:
            Dictionary of key-value pairs
        """
        settings = self.db.get_all_settings()
        result = {}

        for setting in settings:
            key = setting["key"]
            value = setting["value"]

            # Decrypt sensitive values
            if key in SENSITIVE_KEYS and value:
                try:
                    value = self.encryption.decrypt(value)
                except Exception:
                    continue

            result[key] = value

        return result
