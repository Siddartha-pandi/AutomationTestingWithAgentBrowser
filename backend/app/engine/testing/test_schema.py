"""Pydantic schemas and structural validation for Testing Automation.

Defines Test Cases, Setup/Teardown steps, 13 deterministic Assertions,
Parameterized Test Data, and Test Suites.
Zero AI models or heuristics.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.engine.flows.flow_schema import ElementTarget, FlowActionType


class TestStep(BaseModel):
    """Discrete step within a test case: either an interactive browser action or an assertion."""

    __test__ = False

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    step_type: str = Field(default="action", pattern="^(action|assertion)$")
    action: FlowActionType | None = None
    assertion: str | None = Field(
        default=None,
        pattern="^(element_visible|element_hidden|element_enabled|element_disabled|text_equals|text_contains|attribute_equals|url_equals|url_contains|element_count|value_equals|table_contains|page_title_equals)$",
    )
    target: ElementTarget | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    expected: Any = None
    attribute_name: str | None = None
    on_failure: str = Field(default="stop", pattern="^(stop|continue)$")
    retries: int = Field(default=0, ge=0, le=5)

    @model_validator(mode="after")
    def validate_step_consistency(self) -> TestStep:
        if self.step_type == "action" and not self.action:
            raise ValueError(f"Action step '{self.id}' must specify an action type")
        if self.step_type == "assertion" and not self.assertion:
            raise ValueError(f"Assertion step '{self.id}' must specify one of the 13 assertion types")
        return self


class TestCaseDefinition(BaseModel):
    """Complete specification of a deterministic Test Case."""

    __test__ = False

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    setup_steps: list[TestStep] = Field(default_factory=list)
    steps: list[TestStep] = Field(min_length=1)
    teardown_steps: list[TestStep] = Field(default_factory=list)
    test_data: list[dict[str, Any]] = Field(default_factory=list)  # Parameterized datasets


class TestSuiteDefinition(BaseModel):
    """Ordered collection of Test Cases for regression execution."""

    __test__ = False

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    test_case_ids: list[UUID] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    execution_mode: str = Field(default="sequential", pattern="^(sequential|parallel_isolated)$")
    stop_on_failure: bool = False

