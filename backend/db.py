"""PostgreSQL database access, initialization, and connection lifecycle.

Strictly PostgreSQL only. SQLite support has been completely removed per company architecture.
Delegates to SQLAlchemy 2.0 ORM while preserving backward-compatible execution helpers.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine, get_db
from backend.app.models.user import Role
from backend.config import settings

logger = logging.getLogger(__name__)


def is_postgres() -> bool:
    """Always returns True; non-PostgreSQL databases are prohibited."""
    return True


def connect() -> Session:
    """Returns a new SQLAlchemy session connected to PostgreSQL."""
    return SessionLocal()


def execute(db: Any, query: str, parameters: tuple[Any, ...] = ()) -> Any:
    """Executes a SQL query against PostgreSQL, converting SQLite-style ? placeholders to %s or :params."""
    if isinstance(db, Session):
        # Convert ? to positional / named parameter if needed
        # SQLAlchemy text() with dict or params
        if "?" in query:
            # Replace ? with :p0, :p1, ...
            parts = query.split("?")
            new_query = ""
            param_dict = {}
            for i in range(len(parts) - 1):
                param_name = f"p{i}"
                new_query += parts[i] + f":{param_name}"
                param_dict[param_name] = parameters[i] if i < len(parameters) else None
            new_query += parts[-1]
            result = db.execute(text(new_query), param_dict)
        else:
            result = db.execute(text(query), parameters if isinstance(parameters, dict) else {})
        return _SQLAlchemyCursorAdapter(result)

    # Raw connection fallback
    return db.execute(query, parameters)


class _SQLAlchemyCursorAdapter:
    """Wraps SQLAlchemy CursorResult to provide fetchone() and fetchall() dict dictionaries."""

    def __init__(self, result: Any) -> None:
        self._result = result

    def fetchone(self) -> dict[str, Any] | None:
        row = self._result.fetchone()
        if row is None:
            return None
        return dict(row._mapping)

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self._result.fetchall()
        return [dict(r._mapping) for r in rows]


def seed_default_roles(db: Session) -> None:
    """Seeds the standard RBAC roles if they do not already exist."""
    default_roles = [
        (
            "owner",
            "Full system owner with all permissions across all projects, settings, and users.",
            [
                "users:manage",
                "roles:manage",
                "environments:write",
                "credentials:manage",
                "flows:create_edit",
                "flows:publish",
                "tests:create_edit",
                "executions:trigger",
                "executions:cancel",
                "healing:approve",
                "reports:read",
                "artifacts:download",
                "audit_logs:read",
            ],
        ),
        (
            "admin",
            "Organization administrator managing users, environments, credentials, and projects.",
            [
                "users:manage",
                "environments:write",
                "credentials:manage",
                "flows:create_edit",
                "flows:publish",
                "tests:create_edit",
                "executions:trigger",
                "executions:cancel",
                "healing:approve",
                "reports:read",
                "artifacts:download",
            ],
        ),
        (
            "developer",
            "Workflow and test author with permissions to create, edit, and publish definitions.",
            [
                "flows:create_edit",
                "flows:publish",
                "tests:create_edit",
                "executions:trigger",
                "executions:cancel",
                "healing:approve",
                "reports:read",
                "artifacts:download",
            ],
        ),
        (
            "tester",
            "Quality assurance engineer executing workflows, inspecting steps, and analyzing reports.",
            [
                "tests:create_edit",
                "executions:trigger",
                "executions:cancel",
                "reports:read",
                "artifacts:download",
            ],
        ),
        (
            "viewer",
            "Read-only stakeholder viewing test reports, trends, and execution summaries.",
            [
                "reports:read",
            ],
        ),
    ]

    for role_name, description, permissions in default_roles:
        existing = db.query(Role).filter(Role.name == role_name).first()
        if not existing:
            role = Role(name=role_name, description=description, permissions=permissions)
            db.add(role)
    db.commit()


def seed_default_admin(db: Session) -> None:
    """Seeds the default organization administrator if no users exist."""
    from backend.app.models.project import Project
    from backend.app.models.user import User
    from backend.app.security.password import hash_password

    admin_email = "admin@company.internal"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        owner_role = db.query(Role).filter(Role.name == "owner").first()
        admin = User(
            email=admin_email,
            password_hash=hash_password("AdminPass123!"),
            full_name="Lead Administrator",
            is_active=True,
            is_superuser=True,
            roles=[owner_role] if owner_role else [],
        )
        db.add(admin)
        db.flush()

        default_project = db.query(Project).filter(Project.name == "Enterprise QA Suite").first()
        if not default_project:
            default_project = Project(
                name="Enterprise QA Suite",
                description="Default Organization Workspace",
                owner_id=admin.id,
            )
            db.add(default_project)
        db.commit()


def initialize() -> None:
    """Initializes the PostgreSQL database schema and verifies connectivity."""
    logger.info("Initializing PostgreSQL database schema with SQLAlchemy 2.0...")
    try:
        # Create all registered tables if they do not exist
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL database tables verified.")

        # Seed roles and default admin
        with SessionLocal() as session:
            seed_default_roles(session)
            seed_default_admin(session)
            logger.info("RBAC standard roles and default admin seeded.")
    except Exception as err:
        logger.error("Error initializing PostgreSQL database: %s", err)
        raise
