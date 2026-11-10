"""Pydantic schemas for Test Case and Test Suite management endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.engine.testing.test_schema import TestCaseDefinition, TestSuiteDefinition


class TestCaseCreateRequest(BaseModel):
    """Payload to create a new deterministic test case definition draft."""

    project_id: UUID | str
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    test_case: TestCaseDefinition


class TestCaseUpdateRequest(BaseModel):
    """Payload to update an existing test case definition draft."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    test_case: TestCaseDefinition | None = None


class TestCaseResponse(BaseModel):
    """Public representation of a test case definition."""

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


class TestSuiteCreateRequest(BaseModel):
    """Payload to create an aggregate test suite for regression execution."""

    project_id: UUID | str
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    test_suite: TestSuiteDefinition


class TestSuiteResponse(BaseModel):
    """Public representation of an aggregate test suite."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    definition: dict[str, Any] | None = None


class ExecuteTestRequest(BaseModel):
    """Payload to trigger execution of a test case or suite."""

    version_id: UUID | None = None
    environment_id: UUID | None = None
    test_data_row: dict[str, Any] = Field(default_factory=dict)
    async_exec: bool = False


class SeedLegacyTestsRequest(BaseModel):
    """Payload to migrate canonical business tests into a project."""

    project_id: UUID | str

