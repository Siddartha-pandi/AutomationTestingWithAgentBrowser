"""REST API endpoints for Environments (/api/v1/environments).

Strict multi-tenant project isolation and AES-256 encrypted environment variables.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.v1.projects import resolve_project_id, user_has_project_access
from backend.app.db.session import get_db
from backend.app.models.project import Environment, Project, ProjectMember
from backend.app.models.user import User
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission
from backend.app.security.secret_manager import SecretManager

router = APIRouter(prefix="/environments", tags=["Environments"])


class EnvironmentCreateSchema(BaseModel):
    project_id: UUID | str
    name: str = Field(..., min_length=2, max_length=80)
    base_url: str = Field(..., min_length=5, max_length=512)
    allowed_domains: list[str] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)


class EnvironmentUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    base_url: str | None = Field(default=None, min_length=5, max_length=512)
    allowed_domains: list[str] | None = None
    variables: dict[str, str] | None = None


def _format_environment_response(env: Environment) -> dict[str, Any]:
    """Formats safe environment metadata, exposing variable keys without leaking raw secret values."""
    variable_keys: list[str] = []
    if env.variables_encrypted:
        try:
            raw_json = SecretManager.decrypt(env.variables_encrypted)
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                variable_keys = list(parsed.keys())
        except Exception:
            pass

    return {
        "id": str(env.id),
        "project_id": str(env.project_id),
        "name": env.name,
        "base_url": env.base_url,
        "allowed_domains": env.allowed_domains or [],
        "variable_keys": variable_keys,
        "variables_count": len(variable_keys),
        "created_at": env.created_at.isoformat() if env.created_at else None,
    }


@router.get("", response_model=list[dict[str, Any]])
def list_environments(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("environments:read")),
) -> list[dict[str, Any]]:
    """List execution environments with security domain restrictions and project isolation."""
    query = db.query(Environment)

    if not current_user.is_superuser:
        user_projects = (
            db.query(Project.id)
            .filter(
                (Project.owner_id == current_user.id)
                | (Project.members.any(ProjectMember.user_id == current_user.id))
            )
            .subquery()
        )
        query = query.filter(Environment.project_id.in_(user_projects))

    if project_id:
        proj = resolve_project_id(db, project_id, current_user.id, is_superuser=current_user.is_superuser)
        if proj:
            query = query.filter(Environment.project_id == proj.id)
        else:
            return []

    envs = query.order_by(Environment.created_at.desc()).all()
    return [_format_environment_response(e) for e in envs]


@router.get("/{environment_id}", response_model=dict[str, Any])
def get_environment(
    environment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("environments:read")),
) -> dict[str, Any]:
    """Retrieve detailed environment configuration with project isolation verification."""
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if not env or not user_has_project_access(db, env.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")

    return _format_environment_response(env)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_environment(
    payload: EnvironmentCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("environments:write")),
) -> dict[str, Any]:
    """Create a new execution environment tier with encrypted variables."""
    project = resolve_project_id(db, payload.project_id, current_user.id, is_superuser=current_user.is_superuser)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target project not found")

    encrypted_vars: str | None = None
    if payload.variables:
        encrypted_vars = SecretManager.encrypt(json.dumps(payload.variables))

    new_env = Environment(
        project_id=project.id,
        name=payload.name.strip(),
        base_url=payload.base_url.strip(),
        allowed_domains=payload.allowed_domains or [],
        variables_encrypted=encrypted_vars,
    )
    db.add(new_env)
    db.commit()
    db.refresh(new_env)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="environment.created",
        resource_type="environment",
        resource_id=str(new_env.id),
        details={"name": new_env.name, "base_url": new_env.base_url, "project_id": str(project.id)},
    )

    return _format_environment_response(new_env)


@router.put("/{environment_id}")
def update_environment(
    environment_id: UUID,
    payload: EnvironmentUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("environments:write")),
) -> dict[str, Any]:
    """Update environment base URL, allowed domains, or encrypted configuration variables."""
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if not env or not user_has_project_access(db, env.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")

    if payload.name is not None:
        env.name = payload.name.strip()
    if payload.base_url is not None:
        env.base_url = payload.base_url.strip()
    if payload.allowed_domains is not None:
        env.allowed_domains = payload.allowed_domains
    if payload.variables is not None:
        env.variables_encrypted = SecretManager.encrypt(json.dumps(payload.variables))

    db.commit()
    db.refresh(env)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="environment.updated",
        resource_type="environment",
        resource_id=str(env.id),
        details={"name": env.name, "base_url": env.base_url},
    )

    return _format_environment_response(env)


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(
    environment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("environments:write")),
) -> None:
    """Permanently delete an execution environment."""
    env = db.query(Environment).filter(Environment.id == environment_id).first()
    if not env or not user_has_project_access(db, env.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found")

    env_id_str = str(env.id)
    env_name = env.name
    db.delete(env)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="environment.deleted",
        resource_type="environment",
        resource_id=env_id_str,
        details={"name": env_name},
    )
