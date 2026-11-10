"""REST API endpoints for Test & Flow Reports (/api/v1/reports)."""

from __future__ import annotations

import csv
import io
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.execution import Execution
from backend.app.models.user import User
from backend.app.api.v1.projects import resolve_project_id
from backend.app.security.rbac import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
def get_reports_summary(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve aggregated execution and assertion statistics."""
    query = db.query(Execution)
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(Execution.project_id == proj.id)

    total_runs = query.count()
    completed_runs = query.filter(Execution.status == "completed").count()
    failed_runs = query.filter(Execution.status == "failed").count()

    success_rate = (
        round((completed_runs / total_runs) * 100, 1) if total_runs > 0 else 100.0
    )

    return {
        "total_executions": total_runs,
        "completed_executions": completed_runs,
        "failed_executions": failed_runs,
        "success_rate_percent": success_rate,
        "active_environments": ["Development", "Testing", "Staging", "Production"],
    }


@router.get("/export-csv")
def export_reports_csv(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Generate and export a CSV report of recent execution results."""
    query = db.query(Execution).order_by(Execution.created_at.desc()).limit(100)
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(Execution.project_id == proj.id)

    executions = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Execution ID", "Trigger Type", "Status", "Started At", "Duration (ms)"])

    for e in executions:
        writer.writerow([
            str(e.id),
            e.trigger_type,
            e.status,
            e.started_at.isoformat() if e.started_at else "",
            e.duration_ms or 0.0,
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=execution_report.csv"},
    )
