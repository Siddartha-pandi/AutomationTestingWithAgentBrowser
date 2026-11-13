"""Legacy backwards-compatibility schemas for initial API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user_id: int


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    definition: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workspace_id: int
    name: str
    definition: dict[str, Any]
    enabled: bool


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    workflow_id: int
    status: str
    report: dict[str, Any]
    started_at: datetime | None

