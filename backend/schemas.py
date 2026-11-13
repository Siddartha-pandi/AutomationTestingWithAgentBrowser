"""Legacy schema re-export for backwards compatibility.

Canonical domain schemas are organized inside backend.app.schemas.
"""

from __future__ import annotations

from backend.app.schemas.legacy import (
    AuthRequest,
    AuthResponse,
    RunResponse,
    WorkflowCreate,
    WorkflowResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)

__all__ = [
    "AuthRequest",
    "AuthResponse",
    "RunResponse",
    "WorkflowCreate",
    "WorkflowResponse",
    "WorkspaceCreate",
    "WorkspaceResponse",
]
