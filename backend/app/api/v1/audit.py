"""Audit logs query, compliance export, and data retention endpoints."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.audit import AuditLog
from backend.app.schemas.audit import AuditLogResponse
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import require_permission
from backend.app.security.retention import purge_expired_artifacts

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])


def _apply_audit_filters(
    query,
    user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """Applies standardized filters to the AuditLog SQLAlchemy query."""
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    return query


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user=Depends(require_permission("audit_logs:read", "audit:read")),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Queries system audit records with optional action/resource/user filtering. Requires audit_logs:read."""
    query = db.query(AuditLog)
    query = _apply_audit_filters(
        query,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )

    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/export")
def export_audit_logs(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=2000, ge=1, le=10000),
    current_user=Depends(require_permission("audit_logs:read", "audit:read")),
    db: Session = Depends(get_db),
) -> Response:
    """Exports audit logs for external compliance audit in CSV or structured JSON format."""
    query = db.query(AuditLog)
    query = _apply_audit_filters(
        query,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    if format == "json":
        json_data = [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "client_ip": log.client_ip,
                "details": log.details,
            }
            for log in logs
        ]
        return Response(
            content=json.dumps(json_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )

    # Default CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp (UTC)", "User ID", "Action", "Resource Type", "Resource ID", "Client IP", "Details"])

    for log in logs:
        ts = log.timestamp.isoformat() if log.timestamp else ""
        details_str = json.dumps(log.details) if isinstance(log.details, dict) else str(log.details or "")
        writer.writerow([
            ts,
            str(log.user_id) if log.user_id else "SYSTEM",
            log.action,
            log.resource_type,
            log.resource_id or "",
            log.client_ip or "",
            details_str,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.post("/retention/purge")
def trigger_retention_purge(
    log_days: int = Query(default=90, ge=1, le=3650),
    screenshot_days: int = Query(default=30, ge=1, le=365),
    dom_days: int = Query(default=14, ge=1, le=365),
    current_user=Depends(require_permission("roles:manage", "users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers enterprise data retention policy purge of expired logs and artifacts."""
    if not (current_user.is_superuser or any(r.name in ("owner", "admin") for r in getattr(current_user, "roles", []))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace administrators can trigger retention purges")

    counts = purge_expired_artifacts(
        db=db,
        log_days=log_days,
        screenshot_days=screenshot_days,
        dom_days=dom_days,
    )

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="retention.purge_executed",
        resource_type="system",
        resource_id="retention_policy",
        details={
            "log_retention_days": log_days,
            "screenshot_retention_days": screenshot_days,
            "dom_retention_days": dom_days,
            "purged": counts,
        },
    )

    return {
        "status": "completed",
        "purged": counts,
        "policy_horizons": {
            "log_days": log_days,
            "screenshot_days": screenshot_days,
            "dom_days": dom_days,
        },
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
