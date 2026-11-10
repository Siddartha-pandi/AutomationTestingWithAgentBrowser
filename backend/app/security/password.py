"""Cryptographic password hashing and verification using scrypt with unique salt."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """Hashes a password with scrypt and a cryptographically secure 16-byte salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt + digest).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against the stored scrypt hash in constant time."""
    try:
        raw = base64.urlsafe_b64decode(stored_hash.encode("ascii"))
        if len(raw) < 17:
            return False
        salt = raw[:16]
        expected_digest = raw[16:]
        actual_digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False

