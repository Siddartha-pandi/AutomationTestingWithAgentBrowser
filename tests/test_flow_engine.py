"""Tests for Phase 6: Visual Flow Automation Engine.

Verifies React Flow DAG validation, variable interpolation, action registry dispatch,
graph execution traversal, branching, step logging, and PostgreSQL version pinning.
Zero AI models or heuristics.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import SessionLocal
from backend.app.engine.flows.action_registry import ActionRegistry
from backend.app.engine.flows.flow_executor import FlowExecutor
from backend.app.engine.flows.flow_schema import ElementTarget, FlowActionType, FlowEdge, FlowGraphDefinition, FlowNode
from backend.app.engine.flows.variable_scope import VariableScope
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.security.jwt import create_access_token
from backend.main import app


class TestFlowSchemaAndValidation:
    """Unit tests for React Flow Pydantic graph models and topological integrity."""

    def test_valid_flow_graph_definition(self) -> None:
        graph = FlowGraphDefinition(
            name="Login Workflow",
            start_node_id="node_1",
            nodes=[
                FlowNode(
                    id="node_1",
                    type="action",
                    action=FlowActionType.NAVIGATE,
                    config={"url": "https://app.local/login"},
                    position={"x": 0.0, "y": 0.0},
                ),
                FlowNode(
                    id="node_2",
                    type="action",
                    action=FlowActionType.FILL,
                    config={"target": {"selector": "#username"}, "value": "testuser"},
                    position={"x": 0.0, "y": 100.0},
                ),
                FlowNode(
                    id="node_3",
                    type="stop",
                    config={"reason": "Completed"},
                    position={"x": 0.0, "y": 200.0},
                ),
            ],
            edges=[
                FlowEdge(id="e1-2", source="node_1", target="node_2"),
                FlowEdge(id="e2-3", source="node_2", target="node_3"),
            ],
            variables={"env": "staging"},
        )

        assert graph.name == "Login Workflow"
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2

    def test_missing_start_node_raises_validation_error(self) -> None:
        with pytest.raises(ValueError, match="Start node ID 'missing_node' does not exist"):
            FlowGraphDefinition(
                name="Invalid Flow",
                start_node_id="missing_node",
                nodes=[
                    FlowNode(id="node_1", type="stop", config={}),
                ],
            )

    def test_orphan_edge_target_raises_validation_error(self) -> None:
        with pytest.raises(ValueError, match="Edge 'e1' target 'non_existent' does not exist"):
            FlowGraphDefinition(
                name="Broken Edge Flow",
                start_node_id="node_1",
                nodes=[
                    FlowNode(id="node_1", type="stop", config={}),
                ],
                edges=[
                    FlowEdge(id="e1", source="node_1", target="non_existent"),
                ],
            )


class TestVariableScopeAndInterpolation:
    """Unit tests for safe template substitution and condition evaluation."""

    def test_template_interpolation(self) -> None:
        scope = VariableScope(initial_vars={"app_url": "https://app.local", "username": "admin"})
        scope.set_step_output("extract_node", {"token": "jwt_secret_token_123"})

        # Simple variable
        assert scope.interpolate("Welcome to {{app_url}}") == "Welcome to https://app.local"
        # Step output
        assert scope.interpolate("Bearer {{extract_node.token}}") == "Bearer jwt_secret_token_123"
        # Built-in uuid
        res_uuid = scope.interpolate("Order-{{$uuid}}")
        assert res_uuid.startswith("Order-")
        assert len(res_uuid) > 10

    def test_condition_evaluation(self) -> None:
        # String equality
        assert VariableScope.evaluate_condition("success", "==", "success") is True
        assert VariableScope.evaluate_condition("active", "!=", "inactive") is True

        # Containment
        assert VariableScope.evaluate_condition("Welcome John", "contains", "John") is True
        assert VariableScope.evaluate_condition("Error 404", "not_contains", "200") is True

        # Numerical comparison
        assert VariableScope.evaluate_condition("100", ">", "50") is True
        assert VariableScope.evaluate_condition("25", "<=", "25") is True
        assert VariableScope.evaluate_condition("5", ">", "10") is False

        # Empty checks
        assert VariableScope.evaluate_condition("", "empty", "") is True
        assert VariableScope.evaluate_condition("data", "not_empty", "") is True


class TestActionRegistry:
    """Unit tests for action dispatch and element resolution."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        return MagicMock(spec=AgentBrowserAdapter)

    def test_navigate_action(self, mock_adapter: MagicMock) -> None:
        registry = ActionRegistry(mock_adapter)
        scope = VariableScope(initial_vars={"domain": "https://example.com"})

        mock_adapter.navigate.return_value = MagicMock(stdout="Navigated to https://example.com")
        result = registry.execute_action(
            action=FlowActionType.NAVIGATE,
            session_id="session-1",
            config={"url": "{{domain}}/login", "timeout_ms": 5000},
            scope=scope,
        )

        assert result.status == "passed"
        assert result.result_data["url"] == "https://example.com/login"
        mock_adapter.navigate.assert_called_once_with(
            "session-1", url="https://example.com/login", wait_until="load", timeout_ms=5000
        )

    def test_condition_action_branching(self, mock_adapter: MagicMock) -> None:
        registry = ActionRegistry(mock_adapter)
        scope = VariableScope(initial_vars={"status_code": "200"})

        # Match -> next_handle = 'true'
        res_true = registry.execute_action(
            action=FlowActionType.CONDITION,
            session_id="session-1",
            config={"left_operand": "{{status_code}}", "operator": "==", "right_operand": "200"},
            scope=scope,
        )
        assert res_true.status == "passed"
        assert res_true.next_handle == "true"

        # Mismatch -> next_handle = 'false'
        res_false = registry.execute_action(
            action=FlowActionType.CONDITION,
            session_id="session-1",
            config={"left_operand": "{{status_code}}", "operator": "==", "right_operand": "500"},
            scope=scope,
        )
        assert res_false.status == "passed"
        assert res_false.next_handle == "false"

    def test_extended_browser_actions(self, mock_adapter: MagicMock) -> None:
        registry = ActionRegistry(mock_adapter)
        scope = VariableScope()

        # Hover
        mock_adapter.is_visible.return_value = True
        mock_adapter.hover.return_value = MagicMock(is_success=True, duration_ms=10.0)
        res_hover = registry.execute_action(
            action=FlowActionType.HOVER,
            session_id="sess-1",
            config={"target": {"selector": "#menu-btn"}},
            scope=scope,
        )
        assert res_hover.status == "passed"
        assert res_hover.result_data["hovered"] is True

        # Check
        mock_adapter.check.return_value = MagicMock(is_success=True, duration_ms=12.0)
        res_check = registry.execute_action(
            action=FlowActionType.CHECK,
            session_id="sess-1",
            config={"target": {"selector": "input#agree"}},
            scope=scope,
        )
        assert res_check.status == "passed"
        assert res_check.result_data["checked"] is True

        # Scroll
        mock_adapter.scroll.return_value = MagicMock(is_success=True, duration_ms=15.0)
        res_scroll = registry.execute_action(
            action=FlowActionType.SCROLL,
            session_id="sess-1",
            config={"direction": "down", "amount": 500},
            scope=scope,
        )
        assert res_scroll.status == "passed"
        assert res_scroll.result_data["direction"] == "down"

        # Back & Forward
        mock_adapter.back.return_value = MagicMock(is_success=True, duration_ms=8.0)
        res_back = registry.execute_action(action=FlowActionType.BROWSER_BACK, session_id="sess-1", config={}, scope=scope)
        assert res_back.status == "passed"

    def test_data_operations(self, mock_adapter: MagicMock) -> None:
        registry = ActionRegistry(mock_adapter)
        scope = VariableScope(initial_vars={"user_name": "Alice"})

        # String Operation (Upper)
        res_str = registry.execute_action(
            action=FlowActionType.STRING_OP,
            session_id="sess-1",
            config={"operation": "upper", "input": "{{user_name}}", "output_variable": "upper_name"},
            scope=scope,
        )
        assert res_str.status == "passed"
        assert scope.get("upper_name") == "ALICE"

        # Number Operation (Multiply)
        res_num = registry.execute_action(
            action=FlowActionType.NUMBER_OP,
            session_id="sess-1",
            config={"operation": "multiply", "a": 5, "b": 10, "output_variable": "total"},
            scope=scope,
        )
        assert res_num.status == "passed"
        assert scope.get("total") == 50.0

        # JSON Operation (Parse)
        res_json = registry.execute_action(
            action=FlowActionType.JSON_OP,
            session_id="sess-1",
            config={"operation": "parse", "input": '{"status": "active", "code": 200}', "output_variable": "parsed"},
            scope=scope,
        )
        assert res_json.status == "passed"
        assert scope.get("parsed") == {"status": "active", "code": 200}

        # Array Operation (Push)
        res_arr = registry.execute_action(
            action=FlowActionType.ARRAY_OP,
            session_id="sess-1",
            config={"operation": "push", "array": ["alpha", "beta"], "item": "gamma", "output_variable": "new_arr"},
            scope=scope,
        )
        assert res_arr.status == "passed"
        assert scope.get("new_arr") == ["alpha", "beta", "gamma"]

    def test_switch_action_routing(self, mock_adapter: MagicMock) -> None:
        registry = ActionRegistry(mock_adapter)
        scope = VariableScope(initial_vars={"env": "production"})

        res = registry.execute_action(
            action=FlowActionType.SWITCH,
            session_id="sess-1",
            config={"expression": "{{env}}", "cases": ["staging", "production", "dev"]},
            scope=scope,
        )
        assert res.status == "passed"
        assert res.next_handle == "production"


class TestFlowExecutor:
    """Tests for DAG workflow execution and step logging."""

    @pytest.fixture
    def test_context(self) -> tuple[SessionLocal, uuid.UUID, uuid.UUID, uuid.UUID]:
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"flow_dev_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="Flow Executor Test Project", owner_id=user.id)
            db.add(project)
            db.flush()

            automation = AutomationDefinition(
                project_id=project.id,
                type="flow",
                name="DAG Linear Flow",
                status="published",
                created_by=user.id,
            )
            db.add(automation)
            db.flush()

            version = DefinitionVersion(
                definition_id=automation.id,
                version_num=1,
                definition_json={"nodes": [], "edges": []},
                checksum_sha256="dummy_sha256",
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

    def test_linear_flow_execution_success(
        self,
        test_context: tuple[SessionLocal, uuid.UUID, uuid.UUID, uuid.UUID],
    ) -> None:
        db, user_id, project_id, execution_id = test_context

        # Define 3-node graph: Navigate -> Set Variable -> Stop
        graph = FlowGraphDefinition(
            name="Linear Flow Test",
            start_node_id="step_1",
            nodes=[
                FlowNode(
                    id="step_1",
                    type="action",
                    action=FlowActionType.NAVIGATE,
                    config={"url": "https://company.local/dashboard"},
                ),
                FlowNode(
                    id="step_2",
                    type="action",
                    action=FlowActionType.SET_VARIABLE,
                    config={"variable_name": "extracted_title", "value_template": "Dashboard Home"},
                ),
                FlowNode(
                    id="step_3",
                    type="stop",
                    config={"reason": "Workflow complete"},
                ),
            ],
            edges=[
                FlowEdge(id="e1-2", source="step_1", target="step_2"),
                FlowEdge(id="e2-3", source="step_2", target="step_3"),
            ],
        )

        mock_adapter = MagicMock(spec=AgentBrowserAdapter)
        mock_adapter.navigate.return_value = MagicMock(stdout="Success")
        mock_session_mgr = MagicMock(spec=SessionManager)
        mock_session_mgr.create_session.return_value = MagicMock(session_id="test-session-uuid")

        executor = FlowExecutor(
            adapter=mock_adapter,
            session_manager=mock_session_mgr,
            db=db,
        )

        result = executor.execute_flow(execution_id=execution_id, flow_graph=graph)
        assert result["status"] == "passed"

        # Verify Execution was updated in PostgreSQL
        db.expire_all()
        exec_record = db.query(Execution).filter(Execution.id == execution_id).first()
        assert exec_record.status == "passed"
        assert exec_record.duration_ms is not None
        assert len(exec_record.steps) == 3
        assert exec_record.steps[0].action == "navigate"
        assert exec_record.steps[1].action == "set_variable"
        assert len(exec_record.logs) == 3


class TestFlowAPI:
    """Integration tests for Flow Automation API endpoints."""

    @pytest.fixture
    def test_context(self) -> tuple[TestClient, str, uuid.UUID]:
        client = TestClient(app)
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"api_flow_user_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="API Flow Project", owner_id=user.id)
            db.add(project)
            db.commit()

            token = create_access_token(
                user_id=user.id,
                email=user.email,
                roles=["developer"],
                permissions=["flows:read", "flows:create_edit", "flows:execute", "executions:cancel", "reports:read"],
            )

            return client, token, project.id

    def test_flow_crud_and_publish_lifecycle(
        self,
        test_context: tuple[TestClient, str, uuid.UUID],
    ) -> None:
        client, token, project_id = test_context
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Flow Draft
        create_payload = {
            "project_id": str(project_id),
            "name": "Referral Submission Flow",
            "description": "Visual automation flow for referral testing",
            "definition": {
                "name": "Referral Flow Canvas",
                "start_node_id": "start_nav",
                "nodes": [
                    {
                        "id": "start_nav",
                        "type": "action",
                        "action": "navigate",
                        "config": {"url": "https://app.local/referral"},
                    },
                    {
                        "id": "end_stop",
                        "type": "stop",
                        "config": {"reason": "End"},
                    },
                ],
                "edges": [
                    {"id": "e_start_end", "source": "start_nav", "target": "end_stop"},
                ],
                "variables": {},
            },
        }

        create_res = client.post("/api/v1/flows", json=create_payload, headers=headers)
        assert create_res.status_code == 201
        flow = create_res.json()
        flow_id = flow["id"]
        assert flow["name"] == "Referral Submission Flow"
        assert flow["status"] == "draft"

        # 2. Get Flow Detail
        get_res = client.get(f"/api/v1/flows/{flow_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Referral Submission Flow"

        # 3. Update Flow
        update_res = client.put(
            f"/api/v1/flows/{flow_id}",
            json={"name": "Referral Submission Flow (Updated)"},
            headers=headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Referral Submission Flow (Updated)"

        # 4. Publish Version
        publish_res = client.post(f"/api/v1/flows/{flow_id}/publish", headers=headers)
        assert publish_res.status_code == 200
        pub = publish_res.json()
        assert pub["is_published"] is True
        assert pub["version_num"] >= 1
        assert len(pub["checksum_sha256"]) == 64

        # 5. List Flows
        list_res = client.get(f"/api/v1/flows?project_id={project_id}", headers=headers)
        assert list_res.status_code == 200
        flows = list_res.json()
        assert any(f["id"] == flow_id for f in flows)

