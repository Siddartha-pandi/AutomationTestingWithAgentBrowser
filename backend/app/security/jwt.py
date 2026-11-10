"""RFC 7519 compliant JSON Web Token (JWT) issuance and validation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from backend.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ISSUER = "automation-testing-with-agent-browser"


def create_access_token(
    user_id: UUID | str,
    email: str,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generates a signed JWT bearer token containing user identity and permission claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.token_expiry_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "roles": roles or [],
        "permissions": permissions or [],
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes, verifies signature, and asserts non-expiration of a JWT token.

    Raises:
        jwt.PyJWTError: If signature is invalid, token expired, or claims are malformed.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        options={"require": ["sub", "exp", "iat"]},
    )

