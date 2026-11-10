"""Pydantic schemas and structural validation for React Flow visual workflows.

Defines the directed workflow graph, nodes, edges, action configs, and graph topology.
Zero AI models or heuristics.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlowActionType(str, Enum):
    """Supported deterministic browser and flow control actions."""

    NAVIGATE = "navigate"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_ATTRIBUTE = "extract_attribute"
    EXTRACT_TABLE = "extract_table"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    SET_VARIABLE = "set_variable"
    SCREENSHOT = "screenshot"
    APPROVAL_GATE = "approval_gate"
    STOP = "stop"


class ElementTarget(BaseModel):
    """Specification of an element to interact with, by profile or resilient selector."""

    logical_id: str | None = None
    selector: str | None = None
    element_profile_id: UUID | None = None

    @model_validator(mode="after")
    def validate_target_provided(self) -> ElementTarget:
        if not self.logical_id and not self.selector and not self.element_profile_id:
            raise ValueError("ElementTarget must specify at least one of 'logical_id', 'selector', or 'element_profile_id'")
        return self


class FlowNode(BaseModel):
    """Visual workflow canvas node (React Flow compatible)."""

    id: str = Field(min_length=1, max_length=64)
    type: str = Field(default="action", pattern="^(action|condition|loop|trigger|stop)$")
    action: FlowActionType | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    on_error: str = Field(default="stop", pattern="^(stop|continue|retry)$")
    retry_count: int = Field(default=0, ge=0, le=5)

    @model_validator(mode="after")
    def validate_node_action(self) -> FlowNode:
        if self.type == "action" and not self.action:
            raise ValueError(f"Action node '{self.id}' must specify an action type")
        return self


class FlowEdge(BaseModel):
    """Visual workflow canvas edge connecting nodes (React Flow compatible)."""

    id: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=64)
    target: str = Field(min_length=1, max_length=64)
    source_handle: str | None = None  # e.g., 'true', 'false', 'default', 'loop_body', 'loop_exit'
    label: str | None = None


class FlowGraphDefinition(BaseModel):
    """Validated structured workflow graph stored as immutable JSON in PostgreSQL."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    start_node_id: str = Field(min_length=1, max_length=64)
    nodes: list[FlowNode] = Field(min_length=1)
    edges: list[FlowEdge] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_graph_topology(self) -> FlowGraphDefinition:
        node_ids = {n.id for n in self.nodes}

        # 1. Uniqueness of node IDs
        if len(node_ids) != len(self.nodes):
            raise ValueError("Duplicate node IDs found in flow graph")

        # 2. Start node must exist
        if self.start_node_id not in node_ids:
            raise ValueError(f"Start node ID '{self.start_node_id}' does not exist in flow graph nodes")

        # 3. All edge endpoints must exist
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge '{edge.id}' source '{edge.source}' does not exist in nodes")
            if edge.target not in node_ids:
                raise ValueError(f"Edge '{edge.id}' target '{edge.target}' does not exist in nodes")

        return self

