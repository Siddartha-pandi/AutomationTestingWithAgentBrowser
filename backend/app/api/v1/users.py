"""User management endpoints with RBAC enforcement."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.user import Role, User
from backend.app.schemas.auth import AssignRoleRequest, UserResponse
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> list[UserResponse]:
    """Lists system users with pagination. Requires users:manage permission."""
    users = (
        db.query(User)
        .options(joinedload(User.roles))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Retrieves a single user's profile. Allowed for self or users:manage."""
    if current_user.id != user_id and not (current_user.is_superuser or any(r.name in ("owner", "admin") for r in current_user.roles)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    target = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(target)


@router.post("/{user_id}/roles", response_model=UserResponse)
def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Assigns an RBAC role to a user. Requires users:manage."""
    target_user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{payload.role_name}' not found")

    if role not in target_user.roles:
        target_user.roles.append(role)
        db.commit()
        db.refresh(target_user)

        log_audit_event(
            db=db,
            action="role.assigned",
            resource_type="user",
            resource_id=str(target_user.id),
            user_id=current_user.id,
            client_ip=request.client.host if request.client else None,
            details={"assigned_role": payload.role_name},
        )

    return UserResponse.model_validate(target_user)


@router.delete("/{user_id}/roles/{role_name}", response_model=UserResponse)
def remove_role(
    user_id: UUID,
    role_name: str,
    request: Request,
    current_user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Removes an RBAC role from a user. Requires users:manage."""
    target_user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = db.query(Role).filter(Role.name == role_name).first()
    if role and role in target_user.roles:
        target_user.roles.remove(role)
        db.commit()
        db.refresh(target_user)

        log_audit_event(
            db=db,
            action="role.removed",
            resource_type="user",
            resource_id=str(target_user.id),
            user_id=current_user.id,
            client_ip=request.client.host if request.client else None,
            details={"removed_role": role_name},
        )

    return UserResponse.model_validate(target_user)

