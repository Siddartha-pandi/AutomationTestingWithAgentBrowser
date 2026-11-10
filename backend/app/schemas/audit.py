"""Pydantic schemas for immutable security audit logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Audit log record response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    client_ip: str | None = None
    details: dict[str, Any]
    timestamp: datetime

