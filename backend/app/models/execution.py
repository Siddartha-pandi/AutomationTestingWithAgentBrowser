"""Execution tracking, step results, logs, and verified artifact metadata."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class Execution(Base):
    """Represents a discrete run of a flow or test suite pinned to an immutable version."""

    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    definition_id = Column(UUID(as_uuid=True), ForeignKey("automation_definitions.id", ondelete="CASCADE"), index=True, nullable=False)
    definition_version_id = Column(UUID(as_uuid=True), ForeignKey("definition_versions.id", ondelete="RESTRICT"), nullable=False)
    environment_id = Column(UUID(as_uuid=True), ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    trigger_type = Column(String(32), index=True, nullable=False)  # manual, scheduled, api
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), index=True, default="queued", nullable=False)  # queued, running, passed, failed, cancelled, blocked
    session_id = Column(String(64), index=True, nullable=True)  # Isolated Agent Browser session id
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Float, nullable=True)
    summary = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="executions")
    definition = relationship("AutomationDefinition", back_populates="executions")
    definition_version = relationship("DefinitionVersion", back_populates="executions")
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan", order_by="ExecutionStep.step_index.asc()")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan", order_by="ExecutionLog.timestamp.asc()")
    artifacts = relationship("Artifact", back_populates="execution", cascade="all, delete-orphan")
    dom_snapshots = relationship("DOMSnapshot", back_populates="execution", cascade="all, delete-orphan")
    healing_events = relationship("HealingEvent", back_populates="execution", cascade="all, delete-orphan")


class ExecutionStep(Base):
    """Step-level outcome, duration, inputs, and results."""

    __tablename__ = "execution_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True, nullable=False)
    step_index = Column(Integer, nullable=False)
    node_id = Column(String(64), nullable=True)
    step_type = Column(String(64), nullable=False)  # action, assertion, condition, extract
    action = Column(String(64), nullable=False)  # click, fill, navigate, assert_text, etc.
    status = Column(String(32), index=True, nullable=False)  # passed, failed, skipped, running
    input_data = Column(JSONB, default=dict, nullable=False)  # Redacted parameters
    result_data = Column(JSONB, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, default=0.0, nullable=False)
    screenshot_path = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    execution = relationship("Execution", back_populates="steps")


class ExecutionLog(Base):
    """Redacted execution log stream record."""

    __tablename__ = "execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("execution_steps.id", ondelete="CASCADE"), nullable=True)
    level = Column(String(16), default="INFO", nullable=False)  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    is_redacted = Column(Boolean, default=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    execution = relationship("Execution", back_populates="logs")


class Artifact(Base):
    """Metadata indexing binary artifacts stored on approved local storage."""

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True, nullable=False)
    artifact_type = Column(String(32), index=True, nullable=False)  # screenshot, har, trace, dom, pdf
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(64), nullable=False)
    sha256_hash = Column(String(64), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    execution = relationship("Execution", back_populates="artifacts")


class DOMSnapshot(Base):
    """Extracted DOM snapshot record stored in private file storage."""

    __tablename__ = "dom_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True, nullable=False)
    page_url = Column(String(1024), nullable=False)
    snapshot_path = Column(String(512), nullable=False)
    element_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    execution = relationship("Execution", back_populates="dom_snapshots")

