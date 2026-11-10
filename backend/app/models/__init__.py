"""SQLAlchemy ORM models package for AutomationTestingWithAgentBrowser."""

from backend.app.models.audit import AuditLog
from backend.app.models.automation import AutomationDefinition, DefinitionVersion, Schedule
from backend.app.models.execution import Artifact, DOMSnapshot, Execution, ExecutionLog, ExecutionStep
from backend.app.models.intelligence import Approval, ElementProfile, HealingEvent, LocatorHistory
from backend.app.models.project import Credential, Environment, Project
from backend.app.models.user import Role, User, UserRole

__all__ = [
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

