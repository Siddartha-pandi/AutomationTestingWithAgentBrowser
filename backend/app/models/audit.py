"""Immutable system and security audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class AuditLog(Base):
    """Immutable audit trail for security events, credential access, and definition changes."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action = Column(String(80), index=True, nullable=False)  # e.g. "flow.published", "credential.decrypted"
    resource_type = Column(String(64), index=True, nullable=False)  # automation_definition, credential, role
    resource_id = Column(String(64), index=True, nullable=True)
    client_ip = Column(String(64), nullable=True)
    details = Column(JSONB, default=dict, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), index=True, nullable=False)

    user = relationship("User", back_populates="audit_logs")

