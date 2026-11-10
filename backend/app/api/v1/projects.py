"""REST API endpoints for workspace Projects (/api/v1/projects)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.project import Project, ProjectMember
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

    model_config = ConfigDict(from_attributes=True)


def resolve_project_id(
    db: Session,
    project_id: UUID | str | None,
    current_user_id: UUID | None = None,
) -> Project | None:
    """Resolves a project UUID or alias slug (e.g. 'p1-default') to an existing Project model."""
    if not project_id or project_id == "p1-default":
        if current_user_id:
            proj = (
                db.query(Project)
                .filter(
                    (Project.owner_id == current_user_id)
                    | (Project.members.any(ProjectMember.user_id == current_user_id))
                )
                .first()
            )
            if proj:
                return proj
            return None
        # Fallback when running without user context (e.g. CLI or internal test runners)
        return db.query(Project).first()

    if isinstance(project_id, str):
        try:
            parsed_uuid = UUID(project_id)
            proj = db.query(Project).filter(Project.id == parsed_uuid).first()
            if proj:
                return proj
        except ValueError:
            pass

        # Try to find by name for this user
        if current_user_id:
            proj = (
                db.query(Project)
                .filter(
                    (Project.name == project_id)
                    & (
                        (Project.owner_id == current_user_id)
                        | (Project.members.any(ProjectMember.user_id == current_user_id))
                    )
                )
                .first()
            )
            if proj:
                return proj
        return None

    if isinstance(project_id, UUID):
        return db.query(Project).filter(Project.id == project_id).first()

    return None


@router.get("", response_model=list[dict[str, Any]])
def list_projects(
    all: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all workspace projects accessible to user (owned or member of)."""
    if current_user.is_superuser and all:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
    else:
        projects = (
            db.query(Project)
            .filter(
                (Project.owner_id == current_user.id)
                | (Project.members.any(ProjectMember.user_id == current_user.id))
            )
            .order_by(Project.created_at.desc())
            .all()
        )

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


class ProjectMemberAddSchema(BaseModel):
    user_id: UUID
    role: str = "viewer"  # admin, editor, runner, viewer


@router.get("/{project_id}/members")
def list_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all team members assigned to a project."""
    proj = resolve_project_id(db, project_id, current_user.id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    members = db.query(ProjectMember).filter(ProjectMember.project_id == proj.id).all()
    return [
        {
            "id": str(m.id),
            "project_id": str(m.project_id),
            "user_id": str(m.user_id),
            "role": m.role,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in members
    ]


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: str,
    payload: ProjectMemberAddSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage", "create")),
) -> dict[str, Any]:
    """Assign a user to a project with a specific access role."""
    proj = resolve_project_id(db, project_id, current_user.id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already a member
    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == proj.id, ProjectMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        existing.role = payload.role
        db.commit()
        db.refresh(existing)
        return {"id": str(existing.id), "status": "updated", "role": existing.role}

    member = ProjectMember(
        project_id=proj.id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="project_member_added",
        resource=f"Project:{proj.id}",
        details={"member_user_id": str(payload.user_id), "role": payload.role},
        result="success",
    )

    return {"id": str(member.id), "status": "created", "role": member.role}


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: str,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:manage", "create")),
):
    """Remove a user from a project."""
    proj = resolve_project_id(db, project_id, current_user.id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == proj.id, ProjectMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()

