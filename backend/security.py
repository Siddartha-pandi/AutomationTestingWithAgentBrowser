from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings
from .db import get_db


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.urlsafe_b64encode(salt + digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(stored.encode())
        actual = hashlib.scrypt(password.encode(), salt=raw[:16], n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, raw[16:])
    except (ValueError, TypeError):
        return False


def create_token(user_id: int) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + settings.token_expiry_minutes * 60}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(settings.jwt_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Any = Depends(get_db),
) -> int:
    try:
        encoded, signature = credentials.credentials.split(".", 1)
        expected = hmac.new(settings.jwt_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "==="))
        if not hmac.compare_digest(signature, expected) or payload["exp"] < time.time():
            raise ValueError
        user_id = int(payload["sub"])
        from .db import execute
        if not execute(db, "SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
            raise ValueError
        return user_id
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
