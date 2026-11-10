"""Roles query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import Role
from backend.app.schemas.auth import RoleResponse
from backend.app.security.rbac import get_current_user

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleResponse])
def list_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoleResponse]:
    """Returns available RBAC roles and their associated permissions."""
    roles = db.query(Role).order_by(Role.name.asc()).all()
    return [RoleResponse.model_validate(r) for r in roles]

