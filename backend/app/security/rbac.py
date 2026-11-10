"""Role-Based Access Control (RBAC) dependencies and permission guards for FastAPI."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.user import Role, User
from backend.app.security.jwt import decode_access_token

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    cookie_token: str | None = Cookie(default=None, alias="access_token"),
) -> str:
    """Extracts JWT token from Authorization header or HTTP-only secure cookie."""
    if auth and auth.credentials:
        return auth.credentials
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    """Validates JWT token and resolves the active User from PostgreSQL with roles preloaded."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_uuid = UUID(user_id_str)
    except (jwt.PyJWTError, ValueError) as err:
        logger.warning("Token verification failed: %s", err)
        raise credentials_exception from err

    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_uuid)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled",
        )

    return user


def get_user_permissions(user: User) -> set[str]:
    """Flattens all permissions from all roles assigned to the user."""
    if user.is_superuser:
        return {"*"}  # Superuser has wildcard permission
    permissions: set[str] = set()
    for role in user.roles:
        if isinstance(role.permissions, list):
            permissions.update(role.permissions)
    return permissions


def require_permission(*required_permissions: str) -> Callable[[User], User]:
    """Dependency factory enforcing that the authenticated user possesses at least one of the specified permissions."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        permissions = get_user_permissions(current_user)
        if "*" in permissions or any(p in permissions for p in required_permissions):
            return current_user

        # Implied permissions: edit/publish implies read; executions:trigger implies flows:execute
        for req in required_permissions:
            if req == "flows:read" and ("flows:create_edit" in permissions or "flows:publish" in permissions):
                return current_user
            if req == "tests:read" and "tests:create_edit" in permissions:
                return current_user
            if req == "flows:execute" and "executions:trigger" in permissions:
                return current_user

        logger.warning(
            "Access denied: User %s lacks permission '%s'. User permissions: %s",
            current_user.email,
            required_permissions,
            permissions,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires permission: '{required_permissions}'",
        )

    return permission_checker


def require_role(*required_roles: str) -> Callable[[User], User]:
    """Dependency factory enforcing that the user has at least one of the specified roles."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_role_names = {r.name for r in current_user.roles}
        if any(role in user_role_names for role in required_roles):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation restricted to roles: {list(required_roles)}",
        )

    return role_checker


def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Enforces that the authenticated user is a system superuser or owner."""
    user_roles = {r.name for r in current_user.roles}
    if current_user.is_superuser or "owner" in user_roles:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser or Owner administrative privilege required",
    )

