"""REST API endpoints for downloading, viewing, and verifying binary execution artifacts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.execution import Artifact, Execution
from backend.app.api.v1.projects import user_has_project_access
from backend.app.reports.artifact_manager import ArtifactManager, ArtifactSecurityError
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])
artifact_manager = ArtifactManager()


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    artifact_type: str
    file_path: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact_metadata(
    artifact_id: UUID,
    current_user=Depends(require_permission("reports:read", "artifacts:download")),
    db: Session = Depends(get_db),
) -> ArtifactResponse:
    """Retrieves metadata and SHA-256 hash for an artifact."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    execution = db.query(Execution).filter(Execution.id == artifact.execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    return ArtifactResponse.model_validate(artifact)


@router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: UUID,
    request: Request,
    current_user=Depends(require_permission("artifacts:download")),
    db: Session = Depends(get_db),
):
    """Securely downloads an artifact binary with SHA-256 header and path traversal protection."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    execution = db.query(Execution).filter(Execution.id == artifact.execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    try:
        safe_path = artifact_manager.get_safe_artifact_path(artifact)
    except ArtifactSecurityError as sec_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(sec_err))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing from storage")

    log_audit_event(
        db,
        user_id=current_user.id,
        action="artifact:download",
        resource_type="artifact",
        resource_id=str(artifact.id),
        client_ip=request.client.host if request.client else None,
        details={"type": artifact.artifact_type, "sha256": artifact.sha256_hash},
    )

    filename = Path(artifact.file_path).name
    return FileResponse(
        path=str(safe_path),
        media_type=artifact.mime_type or "application/octet-stream",
        filename=filename,
        headers={"X-SHA256-Checksum": artifact.sha256_hash},
    )


@router.get("/{artifact_id}/view")
def view_artifact(
    artifact_id: UUID,
    current_user=Depends(require_permission("reports:read", "artifacts:download")),
    db: Session = Depends(get_db),
):
    """Streams artifact inline for browser display (e.g., screenshots or DOM inspection)."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    execution = db.query(Execution).filter(Execution.id == artifact.execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    try:
        safe_path = artifact_manager.get_safe_artifact_path(artifact)
    except ArtifactSecurityError as sec_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(sec_err))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing from storage")

    return FileResponse(
        path=str(safe_path),
        media_type=artifact.mime_type or "application/octet-stream",
        headers={"X-SHA256-Checksum": artifact.sha256_hash},
    )


@router.get("/{artifact_id}/verify")
def verify_artifact(
    artifact_id: UUID,
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Audits the cryptographic SHA-256 hash of on-disk artifact against PostgreSQL index."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    is_valid = artifact_manager.verify_artifact_integrity(artifact)
    return {
        "artifact_id": str(artifact.id),
        "sha256_indexed": artifact.sha256_hash,
        "is_intact": is_valid,
        "verified_at": datetime.now().isoformat(),
    }

