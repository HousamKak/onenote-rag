"""
Encryption utilities for sensitive data.
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from pathlib import Path

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key_file: str = "./data/.encryption_key"):
        """
        Initialize encryption service.

        Args:
            key_file: Path to store/load encryption key
        """
        self.key_file = key_file
        self._ensure_key_directory()
        self.cipher = self._load_or_create_cipher()

    def _ensure_key_directory(self) -> None:
        """Ensure the key file directory exists."""
        key_dir = Path(self.key_file).parent
        key_dir.mkdir(parents=True, exist_ok=True)

    def _load_or_create_cipher(self) -> Fernet:
        """
        Load existing encryption key or create a new one.

        Returns:
            Fernet cipher instance
        """
        key_path = Path(self.key_file)

        if key_path.exists():
            # Load existing key
            with open(key_path, "rb") as f:
                key = f.read()
            logger.info("Loaded existing encryption key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(key_path, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod
            logger.info("Generated new encryption key")

        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(encrypted_bytes).decode()

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""

        try:
            encrypted_bytes = base64.b64decode(encrypted.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError("Failed to decrypt value")

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted.

        Args:
            value: String to check

        Returns:
            True if value appears to be encrypted
        """
        if not value:
            return False

        try:
            # Try to base64 decode and decrypt
            encrypted_bytes = base64.b64decode(value.encode())
            self.cipher.decrypt(encrypted_bytes)
            return True
        except Exception:
            return False
