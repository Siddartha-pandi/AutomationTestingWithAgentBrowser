"""Tests for Phase 7: Testing Automation Engine.

Verifies the 13 deterministic assertions, setup/teardown execution lifecycle,
canonical business tests migration, test suites, and PostgreSQL reporting.
Zero AI models or heuristics.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import SessionLocal
from backend.app.engine.flows.flow_schema import ElementTarget, FlowActionType
from backend.app.engine.testing.assertion_engine import AssertionEngine
from backend.app.engine.testing.legacy_migration import (
    get_dashboard_test_definition,
    get_fvr_status_test_definition,
    get_login_test_definition,
    get_referral_test_definition,
    seed_legacy_test_cases,
)
from backend.app.engine.testing.test_runner import TestRunner
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep, TestSuiteDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.security.jwt import create_access_token
from backend.main import app


class TestAssertionEngineUnit:
    """Verifies all 13 deterministic assertions with mock browser states."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        return MagicMock(spec=AgentBrowserAdapter)

    def test_visibility_and_enabled_assertions(self, mock_adapter: MagicMock) -> None:
        engine = AssertionEngine(mock_adapter)

        # 1. element_visible
        mock_adapter.is_visible.return_value = True
        res = engine.evaluate_assertion("sess-1", "element_visible", selector="#submit-btn")
        assert res.passed is True
        assert res.actual is True

        mock_adapter.is_visible.return_value = False
        res = engine.evaluate_assertion("sess-1", "element_visible", selector="#submit-btn")
        assert res.passed is False

        # 2. element_hidden
        mock_adapter.is_visible.return_value = False
        res = engine.evaluate_assertion("sess-1", "element_hidden", selector="#modal-overlay")
        assert res.passed is True

        # 3. element_enabled
        mock_adapter.is_enabled.return_value = True
        res = engine.evaluate_assertion("sess-1", "element_enabled", selector="#input-email")
        assert res.passed is True

        # 4. element_disabled
        mock_adapter.is_enabled.return_value = False
        res = engine.evaluate_assertion("sess-1", "element_disabled", selector="#btn-locked")
        assert res.passed is True

    def test_text_and_attribute_assertions(self, mock_adapter: MagicMock) -> None:
        engine = AssertionEngine(mock_adapter)

        # 5. text_equals
        mock_adapter.extract_text.return_value = "Submit Application"
        res = engine.evaluate_assertion("sess-1", "text_equals", selector="button", expected="Submit Application")
        assert res.passed is True

        res_fail = engine.evaluate_assertion("sess-1", "text_equals", selector="button", expected="Cancel")
        assert res_fail.passed is False

        # 6. text_contains
        mock_adapter.extract_text.return_value = "Welcome back, Siddhartha Pandi!"
        res = engine.evaluate_assertion("sess-1", "text_contains", selector="#greeting", expected="Siddhartha")
        assert res.passed is True

        # 7. attribute_equals
        mock_adapter.get_attribute.return_value = "btn-primary active"
        res = engine.evaluate_assertion(
            "sess-1", "attribute_equals", selector="#btn", expected="btn-primary active", attribute_name="class"
        )
        assert res.passed is True

    def test_url_count_table_and_title_assertions(self, mock_adapter: MagicMock) -> None:
        engine = AssertionEngine(mock_adapter)

        # 8. url_equals
        mock_adapter.get_url.return_value = "https://app.local/dashboard"
        res = engine.evaluate_assertion("sess-1", "url_equals", expected="https://app.local/dashboard")
        assert res.passed is True

        # 9. url_contains
        res = engine.evaluate_assertion("sess-1", "url_contains", expected="/dashboard")
        assert res.passed is True

        # 10. element_count
        mock_adapter.get_count.return_value = 4
        res = engine.evaluate_assertion("sess-1", "element_count", selector=".kpi-card", expected=4)
        assert res.passed is True

        # 11. value_equals
        mock_adapter.get_value.return_value = "referral_john"
        res = engine.evaluate_assertion("sess-1", "value_equals", selector="#code", expected="referral_john")
        assert res.passed is True

        # 12. table_contains
        mock_adapter.evaluate.return_value = [
            ["ID", "Status", "Timestamp"],
            ["CASE-99281", "Verified", "2026-11-10"],
        ]
        res = engine.evaluate_assertion("sess-1", "table_contains", selector="table#results", expected="CASE-99281")
        assert res.passed is True

        # 13. page_title_equals
        mock_adapter.get_title.return_value = "Executive Analytics Dashboard"
        res = engine.evaluate_assertion("sess-1", "page_title_equals", expected="Executive Analytics Dashboard")
        assert res.passed is True


class TestTestRunnerExecutionLifecycle:
    """Verifies setup execution, step execution, and guaranteed teardown cleanup."""

    @pytest.fixture
    def test_context(self) -> tuple[SessionLocal, uuid.UUID, uuid.UUID, uuid.UUID]:
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"tester_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="Testing Engine Project", owner_id=user.id)
            db.add(project)
            db.flush()

            automation = AutomationDefinition(
                project_id=project.id,
                type="test",
                name="Lifecycle Test Case",
                status="published",
                created_by=user.id,
            )
            db.add(automation)
            db.flush()

            version = DefinitionVersion(
                definition_id=automation.id,
                version_num=1,
                definition_json={},
                checksum_sha256="dummy_sha",
                is_published=True,
            )
            db.add(version)
            db.flush()

            execution = Execution(
                project_id=project.id,
                definition_id=automation.id,
                definition_version_id=version.id,
                trigger_type="manual",
                status="queued",
                summary={},
            )
            db.add(execution)
            db.commit()

            return db, user.id, project.id, execution.id

    def test_teardown_always_executes_on_assertion_failure(
        self,
        test_context: tuple[SessionLocal, uuid.UUID, uuid.UUID, uuid.UUID],
    ) -> None:
        """Guarantees that teardown steps always execute even when a prior assertion fails."""
        db, user_id, project_id, execution_id = test_context

        test_case = TestCaseDefinition(
            name="Teardown Guarantee Test",
            setup_steps=[
                TestStep(
                    id="setup_nav",
                    name="Setup: Navigate",
                    step_type="action",
                    action=FlowActionType.NAVIGATE,
                    config={"url": "https://app.local"},
                )
            ],
            steps=[
                TestStep(
                    id="assert_fail",
                    name="Failing Assertion",
                    step_type="assertion",
                    assertion="url_equals",
                    expected="https://other.local",
                    on_failure="stop",
                )
            ],
            teardown_steps=[
                TestStep(
                    id="teardown_cleanup",
                    name="Teardown: Clear Session",
                    step_type="action",
                    action=FlowActionType.SET_VARIABLE,
                    config={"variable_name": "cleaned", "value_template": "true"},
                )
            ],
        )

        mock_adapter = MagicMock(spec=AgentBrowserAdapter)
        mock_adapter.navigate.return_value = MagicMock(stdout="Navigated to https://app.local")
        mock_adapter.get_url.return_value = "https://app.local"  # Will fail url_equals
        mock_adapter.screenshot.return_value = MagicMock(screenshot_path="reports/screenshots/err.png")

        mock_session_mgr = MagicMock(spec=SessionManager)
        mock_session_mgr.create_session.return_value = MagicMock(session_id="test-sess-fail")

        runner = TestRunner(
            adapter=mock_adapter,
            session_manager=mock_session_mgr,
            db=db,
        )

        result = runner.execute_test_case(execution_id=execution_id, test_case=test_case)
        assert result["status"] == "failed"

        # Verify ExecutionStep records in PostgreSQL: setup, failed assertion, and teardown must ALL be present!
        db.expire_all()
        exec_record = db.query(Execution).filter(Execution.id == execution_id).first()
        assert exec_record.status == "failed"
        assert len(exec_record.steps) == 3

        step_types = [s.step_type for s in exec_record.steps]
        assert "setup:action" in step_types
        assert "test:assertion" in step_types
        assert "teardown:action" in step_types  # Proves teardown ran!


class TestLegacyBusinessMigration:
    """Verifies migration of the 4 canonical business test definitions."""

    def test_canonical_test_definitions_structure(self) -> None:
        login_test = get_login_test_definition()
        assert len(login_test.steps) == 6
        assert any(s.assertion == "url_contains" for s in login_test.steps)

        referral_test = get_referral_test_definition()
        assert len(referral_test.steps) == 6
        assert any(s.assertion == "text_contains" for s in referral_test.steps)

        fvr_test = get_fvr_status_test_definition()
        assert len(fvr_test.steps) == 4
        assert any(s.assertion == "table_contains" for s in fvr_test.steps)

        dashboard_test = get_dashboard_test_definition()
        assert len(dashboard_test.steps) == 3
        assert any(s.assertion == "page_title_equals" for s in dashboard_test.steps)
        assert any(s.assertion == "element_count" for s in dashboard_test.steps)

    def test_seed_legacy_test_cases_into_postgres(self) -> None:
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"migrator_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="Legacy Seeding Project", owner_id=user.id)
            db.add(project)
            db.commit()

            created_ids = seed_legacy_test_cases(db=db, project_id=project.id, user_id=user.id)
            assert len(created_ids) == 4

            # Idempotency check: running seed again returns existing IDs without duplicate errors
            re_seeded_ids = seed_legacy_test_cases(db=db, project_id=project.id, user_id=user.id)
            assert re_seeded_ids == created_ids


class TestTestingAPI:
    """Integration tests for Test Case and Test Suite endpoints."""

    @pytest.fixture
    def test_context(self) -> tuple[TestClient, str, uuid.UUID]:
        client = TestClient(app)
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"api_test_dev_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="API Test Suite Project", owner_id=user.id)
            db.add(project)
            db.commit()

            token = create_access_token(
                user_id=user.id,
                email=user.email,
                roles=["developer"],
                permissions=["tests:read", "tests:create_edit", "tests:execute", "executions:trigger", "reports:read"],
            )

            return client, token, project.id

    def test_test_case_crud_and_seed_lifecycle(
        self,
        test_context: tuple[TestClient, str, uuid.UUID],
    ) -> None:
        client, token, project_id = test_context
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Seed legacy test cases via API
        seed_res = client.post("/api/v1/tests/seed-legacy", json={"project_id": str(project_id)}, headers=headers)
        assert seed_res.status_code == 200
        seeded = seed_res.json()
        assert len(seeded) == 4
        test_case_ids = [s["id"] for s in seeded]

        # 2. List test cases
        list_res = client.get(f"/api/v1/tests?project_id={project_id}", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 4

        # 3. Create Test Suite referencing seeded test cases
        suite_payload = {
            "project_id": str(project_id),
            "name": "Full Regression Suite",
            "description": "Comprehensive regression suite covering Login, Referral, FVR, and Dashboard",
            "test_suite": {
                "name": "Full Regression Suite",
                "test_case_ids": test_case_ids,
                "execution_mode": "sequential",
                "stop_on_failure": False,
            },
        }

        suite_res = client.post("/api/v1/test-suites", json=suite_payload, headers=headers)
        assert suite_res.status_code == 201
        created_suite = suite_res.json()
        suite_id = created_suite["id"]
        assert created_suite["name"] == "Full Regression Suite"

        # 4. Get Test Suite Detail
        get_suite_res = client.get(f"/api/v1/test-suites/{suite_id}", headers=headers)
        assert get_suite_res.status_code == 200
        assert get_suite_res.json()["id"] == suite_id

