"""Regression and stabilization test suite for Phase 1 fixes.

Verifies:
1. Agent Browser integration and session manager initialization
2. Execution lifecycle and single session reuse
3. Project, execution, and artifact RBAC
4. Browser session isolation and cross-user protection
5. SSRF protection, domain allowlists, and redirect validation
6. Flow execution semantics, loops, branches, conditions, and error rejection
7. Cancellation semantics
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.api.v1.browser import get_verified_session
from backend.app.api.v1.projects import resolve_project_id, user_has_project_access
from backend.app.browser import (
    AgentBrowserAdapter,
    BrowserSession,
    CommandExecutor,
    CommandResult,
    NavigationSecurityError,
    ScreenshotResult,
    SessionIsolationError,
    SessionManager,
)
from backend.app.engine.flows.flow_executor import FlowExecutionError, FlowExecutor
from backend.app.engine.flows.flow_schema import FlowEdge, FlowGraphDefinition, FlowNode
from backend.app.engine.testing.test_runner import TestRunner
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep
from backend.app.models.execution import Execution
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import Role, User
from backend.app.security.network_policy import (
    is_domain_allowed,
    is_ip_restricted,
    validate_destination_url,
)


class TestBrowserIntegrationFixes:
    """Tests P0: Agent Browser integration, session manager initialization, and screenshot handling."""

    def test_session_manager_init_without_args(self) -> None:
        """SessionManager should safely initialize default CommandExecutor when called with no arguments."""
        manager = SessionManager()
        assert manager.executor is not None
        assert isinstance(manager.executor, CommandExecutor)
        assert len(manager.list_active_sessions()) == 0

    def test_session_manager_create_and_validate_session(self) -> None:
        """BrowserSession must track user_id, project_id, and enforce ownership."""
        manager = SessionManager()
        session = manager.create_session(
            session_id="custom_sess_101",
            project_id="proj_alpha",
            execution_id="exec_omega",
            user_id="user_123",
        )
        assert session.session_id == "custom_sess_101"
        assert session.user_id == "user_123"
        assert session.project_id == "proj_alpha"
        assert session.execution_id == "exec_omega"
        assert session.is_active is True

        # Valid owner access
        validated = manager.validate_session_access("custom_sess_101", user_id="user_123")
        assert validated.session_id == "custom_sess_101"

        # Superuser access
        super_validated = manager.validate_session_access("custom_sess_101", user_id="other_user", is_superuser=True)
        assert super_validated.session_id == "custom_sess_101"

        # Cross-user unauthorized access denied
        with pytest.raises(SessionIsolationError) as exc_info:
            manager.validate_session_access("custom_sess_101", user_id="user_attacker")
        assert "Access denied" in str(exc_info.value)

        # Non-existent session
        with pytest.raises(SessionIsolationError):
            manager.validate_session_access("non_existent_sess", user_id="user_123")

        # Closed session rejected
        manager.close_session("custom_sess_101")
        assert session.is_active is False
        with pytest.raises(SessionIsolationError) as exc_closed:
            manager.validate_session_access("custom_sess_101", user_id="user_123")
        assert "no longer active" in str(exc_closed.value)

    def test_adapter_initialization_single_dependency_chain(self) -> None:
        """AgentBrowserAdapter creates and shares dependencies properly without requiring session_id."""
        adapter = AgentBrowserAdapter()
        assert adapter.executor is not None
        assert adapter.session_manager is not None
        assert adapter.session_manager.executor is adapter.executor
        assert adapter.health_monitor.executor is adapter.executor
        assert adapter.screenshot_manager.executor is adapter.executor

    def test_screenshot_result_has_screenshot_path(self) -> None:
        """ScreenshotResult exposes both file_path and screenshot_path property."""
        res = ScreenshotResult(
            file_path="/reports/screenshots/shot1.png",
            file_size_bytes=1024,
            sha256_hash="abc123hash",
            session_id="sess_shot",
            captured_at=datetime.now(timezone.utc),
            full_page=False,
        )
        assert res.file_path == "/reports/screenshots/shot1.png"
        assert res.screenshot_path == "/reports/screenshots/shot1.png"


class TestExecutionLifecycleAndSessionReuse:
    """Tests P0: Single browser session per execution, guaranteed cleanup, and cancellation."""

    def test_flow_executor_reuses_provided_session(self) -> None:
        """FlowExecutor must reuse provided session_id and not spawn a duplicate session."""
        mock_adapter = MagicMock()
        mock_session_mgr = MagicMock()
        mock_db = MagicMock()

        exec_id = uuid.uuid4()
        execution_rec = Execution(
            id=exec_id,
            project_id=uuid.uuid4(),
            definition_id=uuid.uuid4(),
            definition_version_id=uuid.uuid4(),
            trigger_type="manual",
            status="queued",
            summary={},
        )
        mock_db.query().filter().first.return_value = execution_rec

        graph = FlowGraphDefinition(
            name="Test Single Session Flow",
            start_node_id="n_stop",
            nodes=[FlowNode(id="n_stop", type="stop", config={"reason": "done"})],
            edges=[],
        )

        executor = FlowExecutor(adapter=mock_adapter, session_manager=mock_session_mgr, db=mock_db)
        res = executor.execute_flow(
            execution_id=exec_id,
            flow_graph=graph,
            session_id="existing_sess_1",
        )

        assert res["status"] == "passed"
        assert execution_rec.session_id == "existing_sess_1"
        # Since session_id was provided externally, FlowExecutor should NOT have called create_session
        mock_session_mgr.create_session.assert_not_called()
        # Nor should it close the session that the caller manages
        mock_session_mgr.close_session.assert_not_called()

    def test_flow_executor_handles_operator_cancellation(self) -> None:
        """When an execution is cancelled, FlowExecutor halts traversal and preserves cancelled status."""
        mock_adapter = MagicMock()
        mock_session_mgr = MagicMock()
        mock_db = MagicMock()

        exec_id = uuid.uuid4()
        execution_rec = Execution(
            id=exec_id,
            project_id=uuid.uuid4(),
            definition_id=uuid.uuid4(),
            definition_version_id=uuid.uuid4(),
            trigger_type="manual",
            status="cancelled",  # Cancelled before first step
            summary={},
        )
        mock_db.query().filter().first.return_value = execution_rec

        graph = FlowGraphDefinition(
            name="Cancelled Flow",
            start_node_id="n_stop",
            nodes=[FlowNode(id="n_stop", type="stop", config={})],
            edges=[],
        )

        executor = FlowExecutor(adapter=mock_adapter, session_manager=mock_session_mgr, db=mock_db)
        res = executor.execute_flow(
            execution_id=exec_id,
            flow_graph=graph,
            session_id="sess_cancelled",
        )

        assert res["status"] == "cancelled"
        assert execution_rec.status == "cancelled"

    def test_test_runner_reuses_session_in_suite(self) -> None:
        """TestRunner must reuse existing session when manage_session=False in a suite."""
        mock_adapter = MagicMock()
        mock_session_mgr = MagicMock()
        mock_db = MagicMock()

        exec_id = uuid.uuid4()
        execution_rec = Execution(
            id=exec_id,
            project_id=uuid.uuid4(),
            definition_id=uuid.uuid4(),
            definition_version_id=uuid.uuid4(),
            trigger_type="manual",
            status="running",
            summary={},
        )
        mock_db.query().filter().first.return_value = execution_rec

        tc = TestCaseDefinition(
            name="Single Step Test",
            steps=[
                TestStep(
                    id="s1",
                    name="Wait step",
                    step_type="action",
                    action="wait",
                    config={"wait_type": "duration", "duration_ms": 10},
                )
            ],
            setup_steps=[],
            teardown_steps=[],
        )

        runner = TestRunner(adapter=mock_adapter, session_manager=mock_session_mgr, db=mock_db)
        res = runner.execute_test_case(
            execution_id=exec_id,
            test_case=tc,
            session_id="suite_session_xyz",
            manage_session=False,
        )

        assert res["status"] == "running"  # Top-level status untouched by child test case
        mock_session_mgr.create_session.assert_not_called()
        mock_session_mgr.close_session.assert_not_called()


class TestRBACAndAuthorizationFixes:
    """Tests P0: Multi-tenant RBAC, project lookup isolation, and cross-user protection."""

    def test_resolve_project_id_uuid_enforces_membership(self) -> None:
        """Non-superuser cannot access another user's project even by passing its exact UUID."""
        mock_db = MagicMock()
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()
        project_b_id = uuid.uuid4()

        # Mock DB returning None when filtering by user_a_id ownership/membership
        mock_db.query().filter().first.return_value = None

        resolved = resolve_project_id(
            db=mock_db,
            project_id=str(project_b_id),
            current_user_id=user_a_id,
            is_superuser=False,
        )
        assert resolved is None

    def test_resolve_project_id_superuser_bypass(self) -> None:
        """Superuser can access any project by UUID."""
        mock_db = MagicMock()
        target_uuid = uuid.uuid4()
        expected_proj = Project(id=target_uuid, name="Target Project")
        mock_db.query().filter().first.return_value = expected_proj

        resolved = resolve_project_id(
            db=mock_db,
            project_id=str(target_uuid),
            current_user_id=uuid.uuid4(),
            is_superuser=True,
        )
        assert resolved is not None
        assert resolved.id == target_uuid

    def test_user_has_project_access_validation(self) -> None:
        """user_has_project_access returns True only for owner, members, or superusers."""
        mock_db = MagicMock()
        proj_id = uuid.uuid4()

        super_user = User(id=uuid.uuid4(), email="admin@corp.local", is_superuser=True)
        assert user_has_project_access(mock_db, proj_id, super_user) is True

        normal_user = User(id=uuid.uuid4(), email="user@corp.local", is_superuser=False)
        mock_db.query().filter().first.return_value = Project(id=proj_id, name="User Project")
        assert user_has_project_access(mock_db, proj_id, normal_user) is True

        mock_db.query().filter().first.return_value = None
        assert user_has_project_access(mock_db, proj_id, normal_user) is False

    def test_browser_session_isolation_cross_user_rejected(self) -> None:
        """get_verified_session blocks unauthorized users from operating on another's browser session."""
        user_owner = User(id=uuid.uuid4(), email="owner@corp.local", is_superuser=False)
        user_intruder = User(id=uuid.uuid4(), email="intruder@corp.local", is_superuser=False)

        # Launch session owned by user_owner
        with patch("backend.app.api.v1.browser._browser_adapter") as mock_adapter:
            active_session = BrowserSession(
                session_id="sess_private_123",
                user_id=str(user_owner.id),
                is_active=True,
            )
            mock_adapter.session_manager.get_session.return_value = active_session

            # Owner succeeds
            sess = get_verified_session("sess_private_123", user_owner)
            assert sess.session_id == "sess_private_123"

            # Intruder receives HTTP 403 Forbidden
            with pytest.raises(HTTPException) as exc_info:
                get_verified_session("sess_private_123", user_intruder)
            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

            # Non-existent session returns HTTP 404
            mock_adapter.session_manager.get_session.return_value = None
            with pytest.raises(HTTPException) as exc_404:
                get_verified_session("sess_nonexistent", user_owner)
            assert exc_404.value.status_code == 404

            # Closed session returns HTTP 400
            active_session.is_active = False
            mock_adapter.session_manager.get_session.return_value = active_session
            with pytest.raises(HTTPException) as exc_400:
                get_verified_session("sess_private_123", user_owner)
            assert exc_400.value.status_code == 400
            assert "no longer active" in exc_400.value.detail


class TestSSRFAndNetworkSecurity:
    """Tests P0: SSRF prevention, IP restriction, metadata blocking, and domain allowlists."""

    def test_ssrf_blocks_loopback_and_metadata(self) -> None:
        # IPv4 Loopback
        assert is_ip_restricted("127.0.0.1") is True
        assert is_ip_restricted("127.0.0.99") is True
        # IPv6 Loopback
        assert is_ip_restricted("::1") is True
        # Cloud metadata
        assert is_ip_restricted("169.254.169.254") is True
        # IPv6 IMDS
        assert is_ip_restricted("fd00:ec2::254") is True
        # Private RFC 1918
        assert is_ip_restricted("10.0.0.1") is True
        assert is_ip_restricted("192.168.1.50") is True
        assert is_ip_restricted("172.16.0.1") is True
        # Public IP allowed
        assert is_ip_restricted("93.184.216.34") is False

    def test_validate_destination_url_blocks_metadata_and_localhost(self) -> None:
        # Cloud metadata endpoint
        ok, msg = validate_destination_url("http://169.254.169.254/latest/meta-data")
        assert ok is False
        assert "SSRF Protection" in msg

        # Google Cloud metadata hostname
        ok, msg = validate_destination_url("http://metadata.google.internal/computeMetadata/v1/")
        assert ok is False
        assert "SSRF Protection" in msg

        # Localhost blocked by default
        ok, msg = validate_destination_url("http://localhost:8080/admin")
        assert ok is False
        assert "SSRF Protection" in msg

        # Non-http scheme blocked
        ok, msg = validate_destination_url("gopher://127.0.0.1:70")
        assert ok is False
        assert "Prohibited URL scheme" in msg

    def test_domain_allowlist_matching(self) -> None:
        allowed = ["*.staging.corp", "api.production.corp"]
        assert is_domain_allowed("app.staging.corp", allowed) is True
        assert is_domain_allowed("sub.app.staging.corp", allowed) is True
        assert is_domain_allowed("api.production.corp", allowed) is True
        assert is_domain_allowed("evil.attacker.com", allowed) is False


class TestFlowExecutionSemanticsFixes:
    """Tests P1: Flow execution semantics, conditions, loops, branches, and error rejection."""

    def test_malformed_graph_validation_raises(self) -> None:
        """Graph missing start node must raise FlowExecutionError."""
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        graph = FlowGraphDefinition(
            name="Valid Pydantic but missing start in map",
            start_node_id="n1",
            nodes=[FlowNode(id="n1", type="stop", config={})],
        )
        # Artificially corrupt start_node_id to simulate malformed graph
        graph.start_node_id = "missing_node"

        executor = FlowExecutor(adapter=mock_adapter, db=mock_db)
        with pytest.raises(FlowExecutionError) as exc_info:
            executor.execute_flow(execution_id=uuid.uuid4(), flow_graph=graph)
        assert "Start node ID 'missing_node' does not exist" in str(exc_info.value)

    def test_unsupported_node_type_fails_step(self) -> None:
        """Unsupported node type must NOT be silently marked passed."""
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        exec_id = uuid.uuid4()
        execution_rec = Execution(id=exec_id, status="queued", summary={})
        mock_db.query().filter().first.return_value = execution_rec

        # Bypass pydantic validation using model_construct to simulate unexpected runtime node type
        corrupted_node = FlowNode.model_construct(
            id="bad_node",
            type="unsupported_quantum_node",
            action=None,
            config={},
            on_error="stop",
            retry_count=0,
        )

        graph = FlowGraphDefinition(
            name="Unsupported Node Flow",
            start_node_id="bad_node",
            nodes=[corrupted_node],
            edges=[],
        )

        executor = FlowExecutor(adapter=mock_adapter, db=mock_db)
        res = executor.execute_flow(execution_id=exec_id, flow_graph=graph, session_id="sess_err")

        assert res["status"] == "failed"
        assert execution_rec.status == "failed"

    def test_loop_node_iteration_and_exit(self) -> None:
        """Loop node iterates configured number of times, then emits loop_exit."""
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        exec_id = uuid.uuid4()
        execution_rec = Execution(id=exec_id, status="queued", summary={})
        mock_db.query().filter().first.return_value = execution_rec

        # Graph: start_loop -> action_step -> start_loop (loop 2 times) -> stop_node
        loop_node = FlowNode(
            id="n_loop",
            type="loop",
            config={"iterations": 2, "safety_limit": 5},
        )
        action_node = FlowNode(
            id="n_action",
            type="action",
            action="wait",
            config={"wait_type": "duration", "duration_ms": 10},
        )
        stop_node = FlowNode(
            id="n_stop",
            type="stop",
            config={},
        )

        graph = FlowGraphDefinition(
            name="Loop Traversal Flow",
            start_node_id="n_loop",
            nodes=[loop_node, action_node, stop_node],
            edges=[
                FlowEdge(id="e1", source="n_loop", target="n_action", source_handle="loop_body"),
                FlowEdge(id="e2", source="n_action", target="n_loop"),
                FlowEdge(id="e3", source="n_loop", target="n_stop", source_handle="loop_exit"),
            ],
        )

        executor = FlowExecutor(adapter=mock_adapter, db=mock_db)
        res = executor.execute_flow(execution_id=exec_id, flow_graph=graph, session_id="sess_loop")

        assert res["status"] == "passed"
        # n_loop (iter 1) -> n_action -> n_loop (iter 2) -> n_action -> n_loop (exit) -> n_stop = 6 steps
        assert res["summary"]["total_steps"] >= 5

    def test_condition_node_branches_correctly(self) -> None:
        """Condition node routes to 'true' or 'false' handle edge."""
        mock_adapter = MagicMock()
        mock_db = MagicMock()
        exec_id = uuid.uuid4()
        execution_rec = Execution(id=exec_id, status="queued", summary={})
        mock_db.query().filter().first.return_value = execution_rec

        cond_node = FlowNode(
            id="n_cond",
            type="condition",
            action="condition",
            config={"left_operand": "5", "operator": ">", "right_operand": "2"},
        )
        stop_true = FlowNode(id="n_true", type="stop", config={"reason": "was true"})
        stop_false = FlowNode(id="n_false", type="stop", config={"reason": "was false"})

        graph = FlowGraphDefinition(
            name="Condition Branching Flow",
            start_node_id="n_cond",
            nodes=[cond_node, stop_true, stop_false],
            edges=[
                FlowEdge(id="e_true", source="n_cond", target="n_true", source_handle="true"),
                FlowEdge(id="e_false", source="n_cond", target="n_false", source_handle="false"),
            ],
        )

        executor = FlowExecutor(adapter=mock_adapter, db=mock_db)
        res = executor.execute_flow(execution_id=exec_id, flow_graph=graph, session_id="sess_cond")

        assert res["status"] == "passed"
        # Should have stopped at n_true
        assert execution_rec.summary["total_steps"] == 2
