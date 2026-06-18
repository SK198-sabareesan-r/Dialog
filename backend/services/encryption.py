"""
Encryption Service — Fernet-based encryption for stored credentials
"""

import json
import os
from cryptography.fernet import Fernet
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_cipher():
    """Get or generate encryption key."""
    key = settings.ENCRYPTION_KEY
    if not key:
        # Auto-generate if not set (dev only — log a warning)
        key = Fernet.generate_key().decode()
        logger.warning(
            "ENCRYPTION_KEY not set in .env — generated a temporary key. "
            "Set ENCRYPTION_KEY in production to persist encrypted data across restarts."
        )
    else:
        # Ensure it's bytes
        if isinstance(key, str):
            key = key.encode()
    return Fernet(key)


_cipher = None


def get_cipher():
    global _cipher
    if _cipher is None:
        _cipher = _get_cipher()
    return _cipher


def encrypt_credentials(credentials: dict) -> str:
    """Encrypt a credentials dict → base64 string for DB storage."""
    plaintext = json.dumps(credentials).encode("utf-8")
    return get_cipher().encrypt(plaintext).decode("utf-8")


def decrypt_credentials(encrypted: str) -> dict:
    """Decrypt a stored credential string → dict."""
    try:
        plaintext = get_cipher().decrypt(encrypted.encode("utf-8"))
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decrypt credentials: {e}")
        raise ValueError("Could not decrypt credentials — check ENCRYPTION_KEY")
