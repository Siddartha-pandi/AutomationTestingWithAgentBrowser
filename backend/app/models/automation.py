"""Automation definitions, immutable versions, and execution schedules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class AutomationDefinition(Base):
    """Container entity representing a flow workflow or a test suite definition."""

    __tablename__ = "automation_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    type = Column(String(32), index=True, nullable=False)  # 'flow' or 'test'
    name = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="draft", nullable=False)  # draft, published, archived
    current_version_id = Column(UUID(as_uuid=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="definitions")
    versions = relationship("DefinitionVersion", back_populates="definition", cascade="all, delete-orphan", order_by="DefinitionVersion.version_num.desc()")
    schedules = relationship("Schedule", back_populates="definition", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="definition")


class DefinitionVersion(Base):
    """Immutable published version of an automation flow or test definition."""

    __tablename__ = "definition_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id = Column(UUID(as_uuid=True), ForeignKey("automation_definitions.id", ondelete="CASCADE"), index=True, nullable=False)
    version_num = Column(Integer, nullable=False)
    definition_json = Column(JSONB, nullable=False)  # Validated React Flow DAG or Test Steps/Assertions
    checksum_sha256 = Column(String(64), nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("definition_id", "version_num", name="uq_definition_version_num"),
    )

    definition = relationship("AutomationDefinition", back_populates="versions")
    executions = relationship("Execution", back_populates="definition_version")


class Schedule(Base):
    """Cron-based execution schedule pinned to an environment and definition."""

    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id = Column(UUID(as_uuid=True), ForeignKey("automation_definitions.id", ondelete="CASCADE"), index=True, nullable=False)
    environment_id = Column(UUID(as_uuid=True), ForeignKey("environments.id", ondelete="CASCADE"), nullable=False)
    cron_expression = Column(String(64), nullable=False)  # standard cron, e.g. "0 9 * * 1-5"
    timezone = Column(String(64), default="Asia/Kolkata", nullable=False)
    is_enabled = Column(Boolean, default=True, index=True, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    definition = relationship("AutomationDefinition", back_populates="schedules")
    environment = relationship("Environment", back_populates="schedules")

