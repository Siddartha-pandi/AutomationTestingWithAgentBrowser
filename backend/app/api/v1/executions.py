"""Execution tracking and reporting endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session, joinedload

from backend.app.db.session import get_db
from backend.app.models.execution import Artifact, Execution, ExecutionLog, ExecutionStep
from backend.app.models.project import Project, ProjectMember
from backend.app.api.v1.projects import resolve_project_id, user_has_project_access
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

    if not current_user.is_superuser:
        user_projects = (
            db.query(Project.id)
            .filter(
                (Project.owner_id == current_user.id)
                | (Project.members.any(ProjectMember.user_id == current_user.id))
            )
            .subquery()
        )
        query = query.filter(Execution.project_id.in_(user_projects))

    if project_id:
        proj = resolve_project_id(db, project_id, current_user.id, is_superuser=current_user.is_superuser)
        if proj:
            query = query.filter(Execution.project_id == proj.id)
        else:
            return []

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
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
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
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution.status in ("passed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with terminal status '{execution.status}'",
        )

    execution.status = "cancelled"

    # Revoke background Celery task if tracked
    if isinstance(execution.summary, dict) and execution.summary.get("celery_task_id"):
        try:
            from backend.app.worker.celery_app import celery_app
            celery_app.control.revoke(
                execution.summary["celery_task_id"],
                terminate=True,
                signal="SIGTERM",
            )
        except Exception as rev_err:
            logger.warning("Failed to revoke Celery task %s: %s", execution.summary.get("celery_task_id"), rev_err)

    # Terminate and close associated browser session if present
    if execution.session_id:
        try:
            from backend.app.browser import SessionManager
            SessionManager().close_session(execution.session_id)
        except Exception as sess_err:
            logger.warning("Failed to close browser session %s on cancel: %s", execution.session_id, sess_err)

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
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

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
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

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
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
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


@router.get("/{execution_id}/logs", response_model=dict[str, Any])
def get_execution_logs(
    execution_id: UUID,
    level: str | None = Query(default=None, pattern="^(DEBUG|INFO|WARNING|ERROR)$"),
    search: str | None = Query(default=None),
    step_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves structured diagnostic logs for an execution with level and keyword filtering."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    query = db.query(ExecutionLog).filter(ExecutionLog.execution_id == execution_id)
    if level:
        query = query.filter(ExecutionLog.level == level)
    if search:
        query = query.filter(ExecutionLog.message.ilike(f"%{search}%"))
    if step_id:
        query = query.filter(ExecutionLog.step_id == step_id)

    total_count = query.count()
    logs = query.order_by(ExecutionLog.timestamp.asc()).offset(offset).limit(limit).all()

    return {
        "execution_id": str(execution_id),
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": str(l.id),
                "step_id": str(l.step_id) if l.step_id else None,
                "level": l.level,
                "message": l.message,
                "is_redacted": l.is_redacted,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            }
            for l in logs
        ],
    }


@router.get("/{execution_id}/logs/download")
def download_execution_logs(
    execution_id: UUID,
    format: str = Query(default="txt", pattern="^(txt|json)$"),
    level: str | None = Query(default=None, pattern="^(DEBUG|INFO|WARNING|ERROR)$"),
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> Response:
    """Exports and downloads full redacted diagnostic execution logs."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    query = db.query(ExecutionLog).filter(ExecutionLog.execution_id == execution_id)
    if level:
        query = query.filter(ExecutionLog.level == level)
    logs = query.order_by(ExecutionLog.timestamp.asc()).all()

    if format == "json":
        log_payload = [
            {
                "id": str(l.id),
                "step_id": str(l.step_id) if l.step_id else None,
                "level": l.level,
                "message": l.message,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            }
            for l in logs
        ]
        return Response(
            content=json.dumps(log_payload, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=execution_{execution_id}_logs.json"},
        )

    # Plain text format
    lines = []
    for l in logs:
        ts = l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "UNKNOWN"
        lines.append(f"[{ts}] [{l.level.ljust(7)}] {l.message}")
    content = "\n".join(lines) if lines else "No execution logs recorded."

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=execution_{execution_id}_logs.txt"},
    )


@router.get("/{execution_id}/viewport")
def get_execution_viewport(
    execution_id: UUID,
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
):
    """Retrieves live viewport screenshot if execution is active, or latest captured step snapshot."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution or not user_has_project_access(db, execution.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # 1. If session is actively running, attempt real-time capture
    if execution.session_id and execution.status in ("running", "queued"):
        try:
            from backend.app.browser import AgentBrowserAdapter
            adapter = AgentBrowserAdapter()
            scr = adapter.screenshot(execution.session_id)
            scr_path = getattr(scr, "screenshot_path", str(scr))
            if scr_path and Path(scr_path).is_file():
                return FileResponse(scr_path, media_type="image/png")
        except Exception as err:
            logger.debug("Active session live viewport capture skipped/failed: %s", err)

    # 2. Check latest recorded step screenshot
    latest_step = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.execution_id == execution_id, ExecutionStep.screenshot_path.isnot(None))
        .order_by(ExecutionStep.step_index.desc())
        .first()
    )
    if latest_step and latest_step.screenshot_path and Path(latest_step.screenshot_path).is_file():
        return FileResponse(latest_step.screenshot_path, media_type="image/png")

    # 3. Check latest screenshot artifact
    latest_artifact = (
        db.query(Artifact)
        .filter(Artifact.execution_id == execution_id, Artifact.artifact_type == "screenshot")
        .order_by(Artifact.created_at.desc())
        .first()
    )
    if latest_artifact and latest_artifact.file_path and Path(latest_artifact.file_path).is_file():
        return FileResponse(latest_artifact.file_path, media_type="image/png")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No viewport screenshot available for this execution")


