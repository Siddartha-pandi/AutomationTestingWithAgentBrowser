"""Element profiles catalog and management endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.intelligence import ElementProfile, LocatorHistory
from backend.app.models.project import Project
from backend.app.api.v1.projects import resolve_project_id
from backend.app.schemas.intelligence import (
    ElementProfileCreate,
    ElementProfileResponse,
    ElementProfileUpdate,
)
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/elements", tags=["Element Profiles"])


@router.post("", response_model=ElementProfileResponse, status_code=status.HTTP_201_CREATED)
def create_element_profile(
    payload: ElementProfileCreate,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> ElementProfileResponse:
    """Registers a new deterministic element profile for a project."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    existing = (
        db.query(ElementProfile)
        .filter(
            ElementProfile.project_id == project.id,
            ElementProfile.logical_id == payload.logical_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An element profile with logical_id '{payload.logical_id}' already exists in this project",
        )

    profile = ElementProfile(
        project_id=project.id,
        logical_id=payload.logical_id,
        description=payload.description,
        element_type=payload.element_type,
        page_context=payload.page_context,
        original_text=payload.original_text,
        stable_attributes=payload.stable_attributes,
        structural_fingerprint=payload.structural_fingerprint,
    )
    db.add(profile)
    db.flush()

    # Seed initial locator if stable attributes contain selector
    attrs = payload.stable_attributes
    if "data-testid" in attrs:
        db.add(LocatorHistory(
            element_profile_id=profile.id,
            locator_type="stable_attribute",
            locator_value=f"[data-testid='{attrs['data-testid']}']",
            success_count=1,
        ))
    elif "id" in attrs:
        db.add(LocatorHistory(
            element_profile_id=profile.id,
            locator_type="id",
            locator_value=f"#{attrs['id']}",
            success_count=1,
        ))

    db.commit()
    db.refresh(profile)

    log_audit_event(
        db=db,
        action="element_profile.created",
        resource_type="element_profile",
        resource_id=str(profile.id),
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={"logical_id": profile.logical_id, "project_id": str(payload.project_id)},
    )

    return ElementProfileResponse.model_validate(profile)


@router.get("", response_model=list[ElementProfileResponse])
def list_element_profiles(
    project_id: str = Query(...),
    page_context: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ElementProfileResponse]:
    """Lists element profiles registered within a project."""
    proj = resolve_project_id(db, project_id)
    if not proj:
        return []

    query = (
        db.query(ElementProfile)
        .options(joinedload(ElementProfile.history))
        .filter(ElementProfile.project_id == proj.id)
    )
    if page_context:
        query = query.filter(ElementProfile.page_context == page_context)

    profiles = query.order_by(ElementProfile.logical_id.asc()).offset(skip).limit(limit).all()
    return [ElementProfileResponse.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=ElementProfileResponse)
def get_element_profile(
    profile_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ElementProfileResponse:
    """Retrieves an element profile with its full locator history."""
    profile = (
        db.query(ElementProfile)
        .options(joinedload(ElementProfile.history))
        .filter(ElementProfile.id == profile_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element profile not found")
    return ElementProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=ElementProfileResponse)
def update_element_profile(
    profile_id: UUID,
    payload: ElementProfileUpdate,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> ElementProfileResponse:
    """Updates an existing element profile metadata."""
    profile = (
        db.query(ElementProfile)
        .options(joinedload(ElementProfile.history))
        .filter(ElementProfile.id == profile_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element profile not found")

    if payload.description is not None:
        profile.description = payload.description
    if payload.original_text is not None:
        profile.original_text = payload.original_text
    if payload.stable_attributes is not None:
        profile.stable_attributes = payload.stable_attributes
    if payload.structural_fingerprint is not None:
        profile.structural_fingerprint = payload.structural_fingerprint

    db.commit()
    db.refresh(profile)

    log_audit_event(
        db=db,
        action="element_profile.updated",
        resource_type="element_profile",
        resource_id=str(profile.id),
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={"logical_id": profile.logical_id},
    )

    return ElementProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element_profile(
    profile_id: UUID,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> None:
    """Deletes an element profile."""
    profile = db.query(ElementProfile).filter(ElementProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element profile not found")

    logical_id = profile.logical_id
    project_id = profile.project_id
    db.delete(profile)
    db.commit()

    log_audit_event(
        db=db,
        action="element_profile.deleted",
        resource_type="element_profile",
        resource_id=str(profile_id),
        user_id=current_user.id,
        client_ip=request.client.host if request.client else None,
        details={"logical_id": logical_id, "project_id": str(project_id)},
    )

