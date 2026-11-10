"""Pydantic schemas for DOM extraction and element profiles."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ElementProfileCreate(BaseModel):
    """Schema for registering a new element profile."""

    project_id: UUID | str
    logical_id: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=256)
    element_type: str = Field(min_length=1, max_length=64)  # button, input, select, link
    page_context: str = Field(min_length=1, max_length=120)  # e.g. "Referral Dashboard"
    original_text: str | None = None
    stable_attributes: dict[str, Any] = Field(default_factory=dict)
    structural_fingerprint: dict[str, Any] = Field(default_factory=dict)


class ElementProfileUpdate(BaseModel):
    """Schema for updating an existing element profile."""

    description: str | None = None
    original_text: str | None = None
    stable_attributes: dict[str, Any] | None = None
    structural_fingerprint: dict[str, Any] | None = None


class LocatorHistoryItem(BaseModel):
    """Historical selector record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    locator_type: str
    locator_value: str
    success_count: int
    last_verified_at: datetime


class ElementProfileResponse(BaseModel):
    """Public representation of an element profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    logical_id: str
    description: str | None = None
    element_type: str
    page_context: str
    original_text: str | None = None
    stable_attributes: dict[str, Any] = Field(default_factory=dict)
    structural_fingerprint: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    history: list[LocatorHistoryItem] = Field(default_factory=list)


class DOMExtractRequest(BaseModel):
    """Request payload to extract DOM from an active browser session."""

    session_id: str = Field(min_length=1, max_length=64)
    selector: str | None = None


class DOMExtractResponse(BaseModel):
    """Full snapshot of page elements and metadata."""

    page_url: str
    route_path: str
    page_title: str
    timestamp: str
    total_elements: int
    elements: list[dict[str, Any]] = Field(default_factory=list)


class HealingEventResponse(BaseModel):
    """Public representation of a self-healing event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    element_profile_id: UUID
    original_locator: str
    healed_locator: str
    confidence_score: float
    scoring_breakdown: dict[str, Any] = Field(default_factory=dict)
    decision: str
    is_approved: bool
    timestamp: datetime


class ApprovalResponse(BaseModel):
    """Public representation of a pending or resolved self-healing approval."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    healing_event_id: UUID
    requested_by: UUID | None = None
    approved_by: UUID | None = None
    status: str  # pending, approved, rejected
    comment: str | None = None
    responded_at: datetime | None = None
    created_at: datetime
    healing_event: HealingEventResponse | None = None


class ApprovalActionRequest(BaseModel):
    """Request payload to approve or reject a pending self-healing recovery."""

    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = Field(default=None, max_length=512)


class ResolveElementRequest(BaseModel):
    """Request to deterministically resolve/self-heal an element in a live browser session."""

    session_id: str = Field(min_length=1, max_length=64)
    element_profile_id: UUID
    original_locator: str = Field(min_length=1, max_length=512)
    action: str = Field(default="click", max_length=32)
    is_destructive: bool = False
    execution_id: UUID | None = None


class ResolveElementResponse(BaseModel):
    """Deterministic resolution result."""

    success: bool
    decision: str
    original_locator: str
    healed_locator: str | None = None
    confidence_score: float
    scoring_breakdown: dict[str, Any] = Field(default_factory=dict)
    candidate_node: dict[str, Any] | None = None
    approval_id: UUID | None = None
    healing_event_id: UUID | None = None
    error_message: str | None = None


