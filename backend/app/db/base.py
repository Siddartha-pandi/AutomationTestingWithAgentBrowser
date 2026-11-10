"""Base database imports and metadata registration for Alembic migrations."""

from .session import Base

# Import all models here so that Base.metadata has a complete catalog
from backend.app.models.user import User, Role, UserRole
from backend.app.models.project import Project, Environment, Credential
from backend.app.models.automation import AutomationDefinition, DefinitionVersion, Schedule
from backend.app.models.execution import Execution, ExecutionStep, ExecutionLog, Artifact, DOMSnapshot
from backend.app.models.intelligence import ElementProfile, LocatorHistory, HealingEvent, Approval
from backend.app.models.audit import AuditLog

__all__ = [
    "Base",
    "User",
    "Role",
    "UserRole",
    "Project",
    "Environment",
    "Credential",
    "AutomationDefinition",
    "DefinitionVersion",
    "Schedule",
    "Execution",
    "ExecutionStep",
    "ExecutionLog",
    "Artifact",
    "DOMSnapshot",
    "ElementProfile",
    "LocatorHistory",
    "HealingEvent",
    "Approval",
    "AuditLog",
]

