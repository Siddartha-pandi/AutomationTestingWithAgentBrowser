"""Audit logs query endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.audit import AuditLog
from backend.app.schemas.audit import AuditLogResponse
from backend.app.security.rbac import require_permission

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    current_user=Depends(require_permission("audit_logs:read")),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Queries system audit records with optional action/resource filtering. Requires audit_logs:read."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return [AuditLogResponse.model_validate(log) for log in logs]

