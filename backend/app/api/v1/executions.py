"""Execution tracking and reporting endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.execution import Execution
from backend.app.api.v1.projects import resolve_project_id
from backend.app.schemas.flows import ExecutionDetailResponse
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["Executions & Reports"])


@router.get("", response_model=list[ExecutionDetailResponse])
def list_executions(
    project_id: str | None = None,
    definition_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(queued|running|passed|failed|cancelled|blocked)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> list[ExecutionDetailResponse]:
    """Lists execution runs with step summaries and status filters."""
    query = (
        db.query(Execution)
        .options(joinedload(Execution.steps), joinedload(Execution.logs))
    )
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(Execution.project_id == proj.id)
    if definition_id:
        query = query.filter(Execution.definition_id == definition_id)
    if status_filter:
        query = query.filter(Execution.status == status_filter)

    executions = query.order_by(Execution.created_at.desc()).offset(offset).limit(limit).all()
    return [ExecutionDetailResponse.model_validate(e) for e in executions]


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution_detail(
    execution_id: UUID,
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> ExecutionDetailResponse:
    """Retrieves full execution report with step-level metrics and log streams."""
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.steps), joinedload(Execution.logs))
        .filter(Execution.id == execution_id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    return ExecutionDetailResponse.model_validate(execution)


@router.post("/{execution_id}/cancel", response_model=ExecutionDetailResponse)
def cancel_execution(
    execution_id: UUID,
    request: Request,
    current_user=Depends(require_permission("executions:cancel")),
    db: Session = Depends(get_db),
) -> ExecutionDetailResponse:
    """Cancels a queued or actively running execution."""
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.steps), joinedload(Execution.logs))
        .filter(Execution.id == execution_id)
        .first()
    )
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution.status in ("passed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with terminal status '{execution.status}'",
        )

    execution.status = "cancelled"
    log_audit_event(
        db,
        user_id=current_user.id,
        action="execution:cancel",
        resource_type="execution",
        resource_id=str(execution.id),
        client_ip=request.client.host if request.client else None,
        details={"status": "cancelled"},
    )

    db.commit()
    db.refresh(execution)
    return ExecutionDetailResponse.model_validate(execution)


@router.get("/{execution_id}/report", response_model=dict)
def get_execution_report(
    execution_id: UUID,
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> dict:
    """Returns the consolidated executive report in structured JSON format."""
    from backend.app.reports.report_generator import ReportGenerator

    try:
        report = ReportGenerator.generate_consolidated_report(db, execution_id)
        return report
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{execution_id}/report/html")
def get_execution_html_report(
    execution_id: UUID,
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
):
    """Generates and downloads the standalone executive HTML report."""
    from fastapi.responses import HTMLResponse
    from backend.app.reports.report_generator import ReportGenerator

    try:
        report = ReportGenerator.generate_consolidated_report(db, execution_id)
        html_content = ReportGenerator.export_html_report(report)
        return HTMLResponse(content=html_content)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/{execution_id}/artifacts", response_model=list[dict])
def list_execution_artifacts(
    execution_id: UUID,
    current_user=Depends(require_permission("reports:read", "artifacts:download")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Lists all verified artifacts and cryptographic hashes associated with an execution."""
    from backend.app.models.execution import Artifact

    artifacts = (
        db.query(Artifact)
        .filter(Artifact.execution_id == execution_id)
        .order_by(Artifact.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(a.id),
            "execution_id": str(a.execution_id),
            "artifact_type": a.artifact_type,
            "file_size_bytes": a.file_size_bytes,
            "mime_type": a.mime_type,
            "sha256_hash": a.sha256_hash,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ]

