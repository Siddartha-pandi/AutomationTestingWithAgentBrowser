"""Immutable audit logging utility for security compliance."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def log_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: UUID | None = None,
    client_ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Persists an immutable audit log entry for critical actions."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            client_ip=client_ip,
            details=details or {},
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        logger.info("AUDIT: [%s] on %s:%s by user %s", action, resource_type, resource_id, user_id)
        return audit_entry
    except Exception as err:
        logger.error("Failed to persist audit log: %s", err)
        db.rollback()
        raise

