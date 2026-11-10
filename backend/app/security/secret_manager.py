"""AES-256-GCM authenticated encryption for credential secrets and environment variables."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config import settings


def _get_encryption_key() -> bytes:
    """Derives a deterministic 256-bit encryption key from application configuration."""
    raw_key = os.getenv("APP_ENCRYPTION_KEY") or settings.jwt_secret
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


def encrypt_secret(plain_text: str) -> str:
    """Encrypts plain text using AES-256-GCM. Returns base64 encoded nonce + ciphertext."""
    if not plain_text:
        return ""
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(encrypted_text: str) -> str:
    """Decrypts base64 encoded AES-256-GCM ciphertext."""
    if not encrypted_text:
        return ""
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    raw = base64.urlsafe_b64decode(encrypted_text.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("Malformed ciphertext: insufficient length for nonce and tag")
    nonce = raw[:12]
    ciphertext = raw[12:]
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted.decode("utf-8")


class SecretManager:
    """Static helper class for encrypting and decrypting secrets."""

    @staticmethod
    def encrypt(plain_text: str) -> str:
        return encrypt_secret(plain_text)

    @staticmethod
    def decrypt(encrypted_text: str) -> str:
        return decrypt_secret(encrypted_text)


