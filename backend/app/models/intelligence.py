"""Deterministic element profiles, locator history, self-healing events, and approvals."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class ElementProfile(Base):
    """Logical element profile maintaining multi-factor identity and structural context."""

    __tablename__ = "element_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    logical_id = Column(String(120), index=True, nullable=False)  # e.g. "referral_submit"
    description = Column(String(256), nullable=True)
    element_type = Column(String(64), nullable=False)  # button, input, select, link
    page_context = Column(String(120), index=True, nullable=False)  # e.g. "Referral Dashboard"
    original_text = Column(String(256), nullable=True)
    stable_attributes = Column(JSONB, default=dict, nullable=False)
    structural_fingerprint = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "logical_id", name="uq_project_logical_id"),
    )

    project = relationship("Project", back_populates="element_profiles")
    history = relationship("LocatorHistory", back_populates="element_profile", cascade="all, delete-orphan", order_by="LocatorHistory.success_count.desc()")
    healing_events = relationship("HealingEvent", back_populates="element_profile", cascade="all, delete-orphan")


class LocatorHistory(Base):
    """Historical verification of successful selectors for a given element profile."""

    __tablename__ = "locator_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    element_profile_id = Column(UUID(as_uuid=True), ForeignKey("element_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    locator_type = Column(String(32), nullable=False)  # role_name, stable_attr, css, text
    locator_value = Column(String(512), nullable=False)
    success_count = Column(Integer, default=1, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    element_profile = relationship("ElementProfile", back_populates="history")


class HealingEvent(Base):
    """Deterministic self-healing record documenting recovery from DOM mutations."""

    __tablename__ = "healing_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id", ondelete="CASCADE"), index=True, nullable=False)
    element_profile_id = Column(UUID(as_uuid=True), ForeignKey("element_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    original_locator = Column(String(512), nullable=False)
    healed_locator = Column(String(512), nullable=False)
    confidence_score = Column(Float, nullable=False)  # e.g. 0.96 (96%)
    scoring_breakdown = Column(JSONB, default=dict, nullable=False)
    decision = Column(String(32), index=True, nullable=False)  # auto_healed, requires_approval, rejected
    is_approved = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    execution = relationship("Execution", back_populates="healing_events")
    element_profile = relationship("ElementProfile", back_populates="healing_events")
    approval = relationship("Approval", back_populates="healing_event", uselist=False, cascade="all, delete-orphan")


class Approval(Base):
    """Human approval gate for self-healing actions within the 85-94% confidence tier or destructive steps."""

    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    healing_event_id = Column(UUID(as_uuid=True), ForeignKey("healing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), index=True, default="pending", nullable=False)  # pending, approved, rejected
    comment = Column(Text, nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    healing_event = relationship("HealingEvent", back_populates="approval")

