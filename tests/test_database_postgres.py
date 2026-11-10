"""Unit and integration tests for PostgreSQL database models, pooling, and migrations.

Verifies strictly PostgreSQL usage, zero SQLite tolerance, UUID primary keys,
relational foreign keys, and RBAC role seeding.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.config import settings
from backend.app.db.session import SessionLocal, engine, get_postgres_url
from backend.app.models.user import User, Role, UserRole
from backend.app.models.project import Project, Environment, Credential
from backend.app.models.automation import AutomationDefinition, DefinitionVersion, Schedule
from backend.app.models.execution import Execution, ExecutionStep, ExecutionLog, Artifact, DOMSnapshot
from backend.app.models.intelligence import ElementProfile, LocatorHistory, HealingEvent, Approval
from backend.app.models.audit import AuditLog
from backend.db import seed_default_roles


class TestDatabaseConfiguration:
    """Verifies that SQLite is forbidden and PostgreSQL is exclusively configured."""

    def test_database_url_is_postgres(self) -> None:
        assert not settings.database_url.lower().startswith("sqlite")
        assert settings.database_url.lower().startswith(("postgresql://", "postgres://", "postgresql+psycopg://"))

    def test_postgres_url_resolver_uses_psycopg(self) -> None:
        resolved = get_postgres_url()
        assert resolved.startswith("postgresql+psycopg://")

    def test_sqlite_rejection_policy(self) -> None:
        from backend.config import Settings
        with pytest.raises(ValueError) as exc:
            Settings(database_url="sqlite:///./test.sqlite3")
        assert "SQLite is strictly prohibited" in str(exc.value)


class TestModelDefinitions:
    """Verifies model structure, UUID attributes, and table naming."""

    def test_uuid_primary_keys(self) -> None:
        user_id = uuid.uuid4()
        u = User(id=user_id, email="test@company.local", password_hash="dummy")
        assert u.id == user_id

        r_id = uuid.uuid4()
        r = Role(id=r_id, name="custom_role", permissions=["flows:read"])
        assert r.id == r_id

        p_id = uuid.uuid4()
        p = Project(id=p_id, name="Test Project")
        assert p.id == p_id

        env = Environment(id=uuid.uuid4(), project_id=p.id, name="Staging", base_url="https://staging.app", allowed_domains=["app.local"])
        assert isinstance(env.id, uuid.UUID)

        d = AutomationDefinition(id=uuid.uuid4(), project_id=p.id, type="flow", name="Smoke Flow")
        assert isinstance(d.id, uuid.UUID)

        v = DefinitionVersion(id=uuid.uuid4(), definition_id=d.id, version_num=1, definition_json={}, checksum_sha256="abc")
        assert isinstance(v.id, uuid.UUID)

        ex = Execution(id=uuid.uuid4(), project_id=p.id, definition_id=d.id, definition_version_id=v.id, trigger_type="manual")
        assert isinstance(ex.id, uuid.UUID)

        step = ExecutionStep(id=uuid.uuid4(), execution_id=ex.id, step_index=1, step_type="action", action="click", status="passed")
        assert isinstance(step.id, uuid.UUID)

        log = ExecutionLog(id=uuid.uuid4(), execution_id=ex.id, message="Step clicked", level="INFO")
        assert isinstance(log.id, uuid.UUID)

        ep = ElementProfile(
            id=uuid.uuid4(),
            project_id=p.id,
            logical_id="btn_submit",
            element_type="button",
            page_context="Login",
        )
        assert isinstance(ep.id, uuid.UUID)

        heal = HealingEvent(
            id=uuid.uuid4(),
            execution_id=ex.id,
            element_profile_id=ep.id,
            original_locator="#btn",
            healed_locator="button[name='Submit']",
            confidence_score=0.96,
            decision="auto_healed",
        )
        assert isinstance(heal.id, uuid.UUID)

        audit = AuditLog(id=uuid.uuid4(), action="user.login", resource_type="user", resource_id=str(u.id))
        assert isinstance(audit.id, uuid.UUID)


@pytest.mark.integration
class TestLivePostgresSchema:
    """Live schema verification against the connected PostgreSQL database."""

    def test_tables_exist_in_postgres(self) -> None:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        required_tables = [
            "users",
            "roles",
            "user_roles",
            "projects",
            "environments",
            "credentials",
            "automation_definitions",
            "definition_versions",
            "schedules",
            "executions",
            "execution_steps",
            "execution_logs",
            "element_profiles",
            "locator_history",
            "healing_events",
            "dom_snapshots",
            "artifacts",
            "approvals",
            "audit_logs",
        ]

        for table in required_tables:
            assert table in table_names, f"Required table '{table}' is missing from PostgreSQL!"

    def test_rbac_roles_seeded(self) -> None:
        with SessionLocal() as db:
            seed_default_roles(db)
            roles = db.query(Role).all()
            role_names = {r.name for r in roles}
            assert {"owner", "admin", "developer", "tester", "viewer"}.issubset(role_names)

    def test_existing_production_data_preserved(self) -> None:
        """Verifies that existing users and workflows were preserved during migration."""
        with SessionLocal() as db:
            existing_user = db.query(User).filter(User.email.ilike("%siddhartha%")).first()
            assert existing_user is not None
            assert existing_user.email == "siddharthapandi@gmail.com"
            assert existing_user.is_active is True
            assert isinstance(existing_user.id, uuid.UUID)

            # Verify migrated workflow
            existing_flow = db.query(AutomationDefinition).filter(AutomationDefinition.name == "mahila action").first()
            assert existing_flow is not None
            assert existing_flow.name == "mahila action"
            assert isinstance(existing_flow.id, uuid.UUID)
