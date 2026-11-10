"""Unit and integration tests for Celery background execution workers, Beat schedules, and tasks.

Validates asynchronous dispatch, worker execution, cron evaluation, and PostgreSQL recording.
Strictly zero AI dependencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.engine.flows.flow_schema import FlowEdge, FlowGraphDefinition, FlowNode
from backend.app.engine.testing.test_schema import (
    TestCaseDefinition,
    TestStep,
)
from backend.app.models.automation import AutomationDefinition, DefinitionVersion, Schedule
from backend.app.models.execution import Execution
from backend.app.models.project import Environment, Project
from backend.app.models.user import Role, User
from backend.app.security.jwt import create_access_token
from backend.app.worker.celery_app import celery_app
from backend.app.worker.tasks import (
    cleanup_retention_task,
    execute_flow_task,
    execute_test_case_task,
    schedule_checker_task,
)
from backend.config import settings
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_eager_celery():
    """Forces Celery to run synchronously in memory during tests without requiring a live Redis server."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = settings.celery_task_always_eager


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup_data(db_session):
    """Creates a project, environment, user, and authorization token for worker tests."""
    proj = Project(
        name=f"Worker Project {uuid.uuid4().hex[:6]}",
        description="Worker testing workspace",
    )
    db_session.add(proj)

    env = Environment(
        project=proj,
        name="Worker Staging",
        base_url="https://worker.staging.local",
        allowed_domains=["worker.staging.local"],
    )
    db_session.add(env)

    user = User(
        email=f"worker.tester.{uuid.uuid4().hex[:6]}@company.internal",
        password_hash="mocked_hash",
        full_name="Celery Worker Operator",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    owner_role = db_session.query(Role).filter(Role.name == "owner").first()
    if owner_role:
        user.roles.append(owner_role)

    db_session.commit()
    db_session.refresh(proj)
    db_session.refresh(env)
    db_session.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email, roles=["owner"])

    return {
        "project": proj,
        "environment": env,
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


class TestCeleryConfiguration:
    """Verifies Celery configuration, registered tasks, and Beat schedules."""

    def test_celery_task_registrations(self):
        registered = celery_app.tasks.keys()
        assert "worker.execute_flow" in registered
        assert "worker.execute_test_case" in registered
        assert "worker.execute_test_suite" in registered
        assert "worker.schedule_checker" in registered
        assert "worker.cleanup_retention" in registered

    def test_celery_beat_schedule_configured(self):
        beat_sched = celery_app.conf.beat_schedule
        assert "evaluate-scheduled-automations-every-minute" in beat_sched
        assert beat_sched["evaluate-scheduled-automations-every-minute"]["task"] == "worker.schedule_checker"
        assert beat_sched["evaluate-scheduled-automations-every-minute"]["schedule"] == 60.0

        assert "daily-artifact-retention-cleanup" in beat_sched
        assert beat_sched["daily-artifact-retention-cleanup"]["task"] == "worker.cleanup_retention"


class TestCeleryFlowWorkerExecution:
    """Verifies that flow execution tasks process correctly and update PostgreSQL."""

    def test_execute_flow_task_eager_run(self, db_session, test_setup_data):
        proj = test_setup_data["project"]
        user = test_setup_data["user"]

        # Create flow graph with navigate -> screenshot
        graph = FlowGraphDefinition(
            name="Async Worker Flow",
            nodes=[
                FlowNode(
                    id="node_start",
                    type="action",
                    action="navigate",
                    config={"url": "https://worker.staging.local/home"},
                ),
                FlowNode(
                    id="node_end",
                    type="action",
                    action="screenshot",
                    config={"filename": "home_capture.png"},
                ),
            ],
            edges=[FlowEdge(id="e1", source="node_start", target="node_end")],
            start_node_id="node_start",
        )

        flow = AutomationDefinition(
            project_id=proj.id,
            type="flow",
            name="Async Worker Flow",
            status="published",
            created_by=user.id,
        )
        db_session.add(flow)
        db_session.flush()

        version = DefinitionVersion(
            definition_id=flow.id,
            version_num=1,
            definition_json=graph.model_dump(),
            checksum_sha256="abc123workerflowhash",
            is_published=True,
        )
        db_session.add(version)
        db_session.flush()

        flow.current_version_id = version.id

        # Create Execution record
        exec_record = Execution(
            project_id=proj.id,
            definition_id=flow.id,
            definition_version_id=version.id,
            trigger_type="manual",
            triggered_by=user.id,
            status="queued",
            summary={},
        )
        db_session.add(exec_record)
        db_session.commit()
        db_session.refresh(exec_record)

        # Mock browser adapter execution
        with patch("backend.app.worker.tasks.AgentBrowserAdapter") as mock_adapter_cls, \
             patch("backend.app.worker.tasks.SessionManager") as mock_session_cls:
            mock_adapter = MagicMock()
            mock_adapter.navigate.return_value = MagicMock(stdout="", returncode=0, success=True)
            mock_adapter.screenshot.return_value = MagicMock(screenshot_path="./reports/home_capture.png")
            mock_adapter_cls.return_value = mock_adapter

            mock_session = MagicMock()
            mock_session.create_session.return_value = MagicMock(session_id="sess-worker-123")
            mock_session_cls.return_value = mock_session

            # Dispatch task asynchronously through Celery (runs eager)
            task_result = execute_flow_task.delay(str(exec_record.id))
            assert task_result.successful()

            # Verify execution was updated in PostgreSQL
            db_session.refresh(exec_record)
            assert exec_record.status in ("completed", "passed")
            assert exec_record.completed_at is not None
            assert exec_record.duration_ms is not None
            assert len(exec_record.steps) == 2


class TestCeleryTestCaseWorkerExecution:
    """Verifies that test case execution tasks process correctly and update PostgreSQL."""

    def test_execute_test_case_task_eager_run(self, db_session, test_setup_data):
        proj = test_setup_data["project"]
        user = test_setup_data["user"]

        tc = TestCaseDefinition(
            name="Async Worker Assertion Test",
            steps=[
                TestStep(
                    id="s1",
                    name="Navigate to status",
                    step_type="action",
                    action="navigate",
                    config={"url": "https://worker.staging.local/status"},
                ),
                TestStep(
                    id="s2",
                    name="Assert page title",
                    step_type="assertion",
                    assertion="page_title_equals",
                    expected="System Health",
                ),
            ],
        )

        test_def = AutomationDefinition(
            project_id=proj.id,
            type="test",
            name="Async Assertion Test",
            status="published",
            created_by=user.id,
        )
        db_session.add(test_def)
        db_session.flush()

        version = DefinitionVersion(
            definition_id=test_def.id,
            version_num=1,
            definition_json=tc.model_dump(),
            checksum_sha256="abc123workertesthash",
            is_published=True,
        )
        db_session.add(version)
        db_session.flush()

        test_def.current_version_id = version.id

        exec_record = Execution(
            project_id=proj.id,
            definition_id=test_def.id,
            definition_version_id=version.id,
            trigger_type="manual",
            triggered_by=user.id,
            status="queued",
            summary={},
        )
        db_session.add(exec_record)
        db_session.commit()
        db_session.refresh(exec_record)

        with patch("backend.app.worker.tasks.AgentBrowserAdapter") as mock_adapter_cls, \
             patch("backend.app.worker.tasks.SessionManager") as mock_session_cls:
            mock_adapter = MagicMock()
            mock_adapter.navigate.return_value = MagicMock(stdout="", returncode=0, success=True)
            mock_adapter.get_title.return_value = "System Health"
            mock_adapter.screenshot.return_value = MagicMock(screenshot_path="./reports/test_capture.png")
            mock_adapter_cls.return_value = mock_adapter

            mock_session = MagicMock()
            mock_session.create_session.return_value = MagicMock(session_id="sess-worker-test-456")
            mock_session_cls.return_value = mock_session

            task_result = execute_test_case_task.delay(str(exec_record.id))
            assert task_result.successful()

            db_session.refresh(exec_record)
            assert exec_record.status in ("completed", "passed")
            assert exec_record.completed_at is not None
            assert len(exec_record.steps) == 2


class TestCeleryScheduleChecker:
    """Verifies that the periodic schedule evaluator discovers due cron jobs and enqueues executions."""

    def test_schedule_checker_dispatches_due_execution(self, db_session, test_setup_data):
        proj = test_setup_data["project"]
        env = test_setup_data["environment"]
        user = test_setup_data["user"]

        # 1. Create a flow definition
        graph = FlowGraphDefinition(
            name="Scheduled Cron Flow",
            nodes=[
                FlowNode(
                    id="n1",
                    type="action",
                    action="navigate",
                    config={"url": "https://worker.staging.local/cron"},
                )
            ],
            edges=[],
            start_node_id="n1",
        )
        flow = AutomationDefinition(
            project_id=proj.id,
            type="flow",
            name="Scheduled Cron Flow",
            status="published",
            created_by=user.id,
        )
        db_session.add(flow)
        db_session.flush()

        version = DefinitionVersion(
            definition_id=flow.id,
            version_num=1,
            definition_json=graph.model_dump(),
            checksum_sha256="checksumcron99",
            is_published=True,
        )
        db_session.add(version)
        db_session.flush()
        flow.current_version_id = version.id

        # 2. Create a Schedule that was due 10 minutes ago
        past_run = datetime.now(timezone.utc) - timedelta(minutes=10)
        schedule = Schedule(
            definition_id=flow.id,
            environment_id=env.id,
            cron_expression="*/5 * * * *",  # Every 5 minutes
            timezone="Asia/Kolkata",
            is_enabled=True,
            last_run_at=past_run,
        )
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)

        # 3. Run schedule_checker_task
        with patch("backend.app.worker.tasks.execute_flow_task.delay") as mock_flow_delay:
            result = schedule_checker_task()

            assert result["evaluated_count"] >= 1
            assert result["triggered_count"] >= 1
            assert mock_flow_delay.called

            # Check schedule updated in database
            db_session.refresh(schedule)
            assert schedule.last_run_at is not None
            assert schedule.last_run_at > past_run


class TestSchedulesAPI:
    """Verifies REST endpoints for schedule management."""

    def test_schedules_crud_lifecycle(self, db_session, test_setup_data):
        headers = test_setup_data["headers"]
        proj = test_setup_data["project"]
        env = test_setup_data["environment"]

        # Create flow first
        graph = FlowGraphDefinition(
            name="API Test Flow",
            nodes=[FlowNode(id="n1", type="action", action="wait", config={"seconds": 1})],
            edges=[],
            start_node_id="n1",
        )
        flow = AutomationDefinition(
            project_id=proj.id,
            type="flow",
            name="API Test Flow",
            status="published",
        )
        db_session.add(flow)
        db_session.flush()

        version = DefinitionVersion(
            definition_id=flow.id,
            version_num=1,
            definition_json=graph.model_dump(),
            checksum_sha256="apischedulehash",
            is_published=True,
        )
        db_session.add(version)
        db_session.commit()

        # 1. Create schedule with invalid cron -> 400
        bad_res = client.post(
            "/api/v1/schedules",
            json={
                "definition_id": str(flow.id),
                "environment_id": str(env.id),
                "cron_expression": "invalid cron text",
            },
            headers=headers,
        )
        assert bad_res.status_code == 400

        # 2. Create schedule with valid cron -> 201
        res = client.post(
            "/api/v1/schedules",
            json={
                "definition_id": str(flow.id),
                "environment_id": str(env.id),
                "cron_expression": "0 9 * * 1-5",
                "timezone": "Asia/Kolkata",
                "is_enabled": True,
            },
            headers=headers,
        )
        assert res.status_code == 201
        sched_data = res.json()
        sched_id = sched_data["id"]
        assert sched_data["cron_expression"] == "0 9 * * 1-5"
        assert sched_data["is_enabled"] is True

        # 3. List schedules
        list_res = client.get("/api/v1/schedules", headers=headers)
        assert list_res.status_code == 200
        assert any(s["id"] == sched_id for s in list_res.json())

        # 4. Patch schedule
        patch_res = client.patch(
            f"/api/v1/schedules/{sched_id}",
            json={"is_enabled": False, "cron_expression": "*/10 * * * *"},
            headers=headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["is_enabled"] is False
        assert patch_res.json()["cron_expression"] == "*/10 * * * *"

        # 5. Delete schedule -> 204
        del_res = client.delete(f"/api/v1/schedules/{sched_id}", headers=headers)
        assert del_res.status_code == 204


class TestRetentionCleanupTask:
    """Verifies that the periodic retention task runs without error."""

    def test_cleanup_retention_task_execution(self):
        result = cleanup_retention_task(retention_days=30)
        assert isinstance(result, dict)
        assert "logs" in result
        assert "artifacts" in result
        assert "dom_snapshots" in result
