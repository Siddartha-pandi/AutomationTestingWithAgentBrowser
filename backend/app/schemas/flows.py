"""Pydantic schemas for visual workflow definitions, versioning, and executions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.engine.flows.flow_schema import FlowGraphDefinition


class FlowCreateRequest(BaseModel):
    """Payload to create a new flow automation definition draft."""

    project_id: UUID | str
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    definition: FlowGraphDefinition


class FlowUpdateRequest(BaseModel):
    """Payload to update an existing flow automation draft."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    definition: FlowGraphDefinition | None = None


class FlowResponse(BaseModel):
    """Public representation of an automation workflow."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    type: str
    name: str
    description: str | None = None
    status: str
    current_version_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    definition: dict[str, Any] | None = None
    version_count: int = 0


class PublishVersionResponse(BaseModel):
    """Result of publishing an immutable flow version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    definition_id: UUID
    version_num: int
    checksum_sha256: str
    is_published: bool
    published_at: datetime | None = None
    created_at: datetime


class ExecuteFlowRequest(BaseModel):
    """Payload to trigger execution of a flow."""

    version_id: UUID | None = None
    environment_id: UUID | None = None
    initial_variables: dict[str, Any] = Field(default_factory=dict)
    async_exec: bool = False


class ExecutionStepResponse(BaseModel):
    """Public step log and artifact representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_index: int
    node_id: str | None = None
    step_type: str
    action: str
    status: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    result_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    duration_ms: float
    screenshot_path: str | None = None
    created_at: datetime


class ExecutionLogResponse(BaseModel):
    """Public stream log line."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    step_id: UUID | None = None
    level: str
    message: str
    timestamp: datetime


class ExecutionDetailResponse(BaseModel):
    """Public execution report including summary, steps, and logs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    definition_id: UUID
    definition_version_id: UUID
    environment_id: UUID | None = None
    trigger_type: str
    status: str
    session_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    steps: list[ExecutionStepResponse] = Field(default_factory=list)
    logs: list[ExecutionLogResponse] = Field(default_factory=list)

