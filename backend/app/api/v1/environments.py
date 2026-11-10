"""REST API endpoints for Environments (/api/v1/environments)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.project import Environment, Project
from backend.app.models.user import User
from backend.app.api.v1.projects import resolve_project_id
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

router = APIRouter(prefix="/environments", tags=["Environments"])


class EnvironmentCreateSchema(BaseModel):
    project_id: UUID | str
    name: str = Field(..., min_length=2, max_length=80)
    base_url: str = Field(..., min_length=5, max_length=512)
    allowed_domains: list[str] = Field(default_factory=list)


@router.get("", response_model=list[dict[str, Any]])
def list_environments(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List execution environments with security domain restrictions."""
    query = db.query(Environment)
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(Environment.project_id == proj.id)
    envs = query.all()
    return [
        {
            "id": str(e.id),
            "project_id": str(e.project_id),
            "name": e.name,
            "base_url": e.base_url,
            "allowed_domains": e.allowed_domains or [],
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in envs
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_environment(
    payload: EnvironmentCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("create")),
) -> dict[str, Any]:
    """Create a new execution environment tier."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Target project not found")

    new_env = Environment(
        project_id=project.id,
        name=payload.name.strip(),
        base_url=payload.base_url.strip(),
        allowed_domains=payload.allowed_domains or [],
    )
    db.add(new_env)
    db.commit()
    db.refresh(new_env)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="environment_created",
        resource=f"Environment:{new_env.id}",
        details={"name": new_env.name, "base_url": new_env.base_url},
        result="success",
    )

    return {
        "id": str(new_env.id),
        "name": new_env.name,
        "base_url": new_env.base_url,
        "allowed_domains": new_env.allowed_domains,
    }
