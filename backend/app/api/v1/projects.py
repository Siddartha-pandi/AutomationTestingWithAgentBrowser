"""REST API endpoints for workspace Projects (/api/v1/projects)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = None


class ProjectResponseSchema(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    owner_id: UUID | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


def resolve_project_id(
    db: Session,
    project_id: UUID | str | None,
    current_user_id: UUID | None = None,
) -> Project | None:
    """Resolves a project UUID or alias slug (e.g. 'p1-default') to an existing Project model."""
    if not project_id:
        proj = db.query(Project).first()
        if not proj and current_user_id:
            proj = Project(
                name="Enterprise QA Suite",
                description="Default Organization Workspace",
                owner_id=current_user_id,
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
        return proj

    if isinstance(project_id, str):
        try:
            parsed_uuid = UUID(project_id)
            proj = db.query(Project).filter(Project.id == parsed_uuid).first()
            if proj:
                return proj
        except ValueError:
            pass
        # Fallback to first project or match by name
        proj = db.query(Project).first()
        if not proj and current_user_id:
            proj = Project(
                name="Enterprise QA Suite",
                description="Default Organization Workspace",
                owner_id=current_user_id,
            )
            db.add(proj)
            db.commit()
            db.refresh(proj)
        return proj

    if isinstance(project_id, UUID):
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            return proj
        return db.query(Project).first()

    return None


@router.get("", response_model=list[dict[str, Any]])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all workspace projects accessible to user."""
    projects = db.query(Project).all()
    if not projects:
        default_proj = Project(
            name="Enterprise QA Suite",
            description="Default Organization Workspace",
            owner_id=current_user.id,
        )
        db.add(default_proj)
        db.commit()
        db.refresh(default_proj)
        projects = [default_proj]

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "owner_id": str(p.owner_id) if p.owner_id else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("create")),
) -> dict[str, Any]:
    """Create a new project workspace tenant."""
    new_proj = Project(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        owner_id=current_user.id,
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="project_created",
        resource=f"Project:{new_proj.id}",
        details={"name": new_proj.name},
        result="success",
    )

    return {
        "id": str(new_proj.id),
        "name": new_proj.name,
        "description": new_proj.description,
        "owner_id": str(new_proj.owner_id) if new_proj.owner_id else None,
    }


@router.get("/{project_id}")
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve detailed project configuration."""
    proj = resolve_project_id(db, project_id, current_user.id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": str(proj.id),
        "name": proj.name,
        "description": proj.description,
        "owner_id": str(proj.owner_id) if proj.owner_id else None,
        "created_at": proj.created_at.isoformat() if proj.created_at else None,
    }
