"""Authentication endpoints for registration, login, profile, and logout."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.security.audit import log_audit_event
from backend.app.security.jwt import create_access_token
from backend.app.security.password import hash_password, verify_password
from backend.app.security.rbac import get_current_user, get_user_permissions
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Registers a new user, provisions default project and role, and returns access token."""
    email = payload.email.lower().strip()

    # Check for existing email
    if db.query(User).filter(User.email == email).first():
        log_audit_event(
            db=db,
            action="user.register_conflict",
            resource_type="user",
            client_ip=request.client.host if request.client else None,
            details={"email": email},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address is already registered",
        )

    # Determine role: First user becomes 'owner' & superuser; others become 'developer'
    user_count = db.query(User).count()
    is_first_user = user_count == 0
    assigned_role_name = "owner" if is_first_user else "developer"

    role = db.query(Role).filter(Role.name == assigned_role_name).first()
    if not role:
        # Fallback if roles not yet seeded
        role = Role(name=assigned_role_name, permissions=["*"] if is_first_user else ["flows:create_edit"])
        db.add(role)
        db.flush()

    new_user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name or email.split("@")[0].capitalize(),
        is_active=True,
        is_superuser=is_first_user,
        roles=[role],
    )
    db.add(new_user)
    db.flush()

    # Automatically create user's initial project
    project_name = f"{new_user.full_name}'s Workspace"
    initial_project = Project(
        name=project_name,
        description="Default organization workspace",
        owner_id=new_user.id,
    )
    db.add(initial_project)
    db.commit()
    db.refresh(new_user)

    roles_list = [r.name for r in new_user.roles]
    permissions_list = list(get_user_permissions(new_user))

    token = create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        roles=roles_list,
        permissions=permissions_list,
    )

    # Set secure HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in HTTPS production
        samesite="lax",
        max_age=settings.token_expiry_minutes * 60,
    )

    log_audit_event(
        db=db,
        action="user.registered",
        resource_type="user",
        resource_id=str(new_user.id),
        user_id=new_user.id,
        client_ip=request.client.host if request.client else None,
        details={"email": email, "role": assigned_role_name},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.token_expiry_minutes * 60,
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticates user credentials, sets HTTP-only cookie, and returns signed JWT."""
    email = payload.email.lower().strip()
    client_ip = request.client.host if request.client else None

    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.email == email)
        .first()
    )

    if not user or not verify_password(payload.password, user.password_hash):
        log_audit_event(
            db=db,
            action="user.login_failed",
            resource_type="user",
            client_ip=client_ip,
            details={"email": email, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        log_audit_event(
            db=db,
            action="user.login_blocked",
            resource_type="user",
            resource_id=str(user.id),
            client_ip=client_ip,
            details={"email": email, "reason": "account_inactive"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )

    roles_list = [r.name for r in user.roles]
    permissions_list = list(get_user_permissions(user))

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=roles_list,
        permissions=permissions_list,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.token_expiry_minutes * 60,
    )

    log_audit_event(
        db=db,
        action="user.login_success",
        resource_type="user",
        resource_id=str(user.id),
        user_id=user.id,
        client_ip=client_ip,
        details={"email": email},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.token_expiry_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns profile and role claims of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Clears the session cookie and logs logout event."""
    response.delete_cookie(key="access_token")
    log_audit_event(
        db=db,
        action="user.logout",
        resource_type="user",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
    )
    return {"message": "Successfully logged out"}

