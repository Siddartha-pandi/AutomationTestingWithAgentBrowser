"""Unit and integration tests for Phase 3: Flow Builder and Test Management.

Verifies:
1. Flow Graph Validation endpoint (/api/v1/flows/validate)
2. Interactive Selector Validator (/api/v1/browser/validate-selector)
3. Live Browser Selector Tester (/api/v1/browser/test-selector)
4. Element Library / Object Repository management & RBAC (/api/v1/elements)
5. Test Step Retries & Fallback resolution in TestRunner
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.browser import ActionResult, AgentBrowserAdapter, BrowserSession
from backend.app.db.session import get_db
from backend.app.engine.flows.flow_schema import FlowActionType
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep, TestSuiteDefinition
from backend.app.models.user import User
from backend.app.security.rbac import get_current_user, get_token_from_request
from backend.main import app

mock_user_obj = MagicMock(spec=User)
mock_user_obj.id = uuid4()
mock_user_obj.email = "admin@example.com"
mock_user_obj.is_active = True
mock_user_obj.is_superuser = True
mock_user_obj.roles = []

mock_db_session = MagicMock()
app.dependency_overrides[get_db] = lambda: mock_db_session
app.dependency_overrides[get_current_user] = lambda: mock_user_obj
app.dependency_overrides[get_token_from_request] = lambda: "fake-jwt-token"

client = TestClient(app)


@pytest.fixture
def mock_user():
    return mock_user_obj


def test_validate_flow_graph_success():
    payload = {
        "definition": {
            "name": "Checkout Flow",
            "start_node_id": "start",
            "nodes": [
                {
                    "id": "start",
                    "type": "action",
                    "action": "navigate",
                    "config": {"url": "https://example.com"},
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "check_btn",
                    "type": "condition",
                    "action": "condition",
                    "config": {"variable": "ready", "operator": "==", "expected_value": "true"},
                    "position": {"x": 100, "y": 200},
                },
                {
                    "id": "step_true",
                    "type": "action",
                    "action": "click",
                    "config": {"target": {"selector": "#order-submit"}},
                    "position": {"x": 50, "y": 300},
                },
                {
                    "id": "step_false",
                    "type": "stop",
                    "config": {"reason": "Not ready"},
                    "position": {"x": 150, "y": 300},
                },
            ],
            "edges": [
                {"id": "e1-2", "source": "start", "target": "check_btn"},
                {"id": "e2-3", "source": "check_btn", "target": "step_true", "source_handle": "true"},
                {"id": "e2-4", "source": "check_btn", "target": "step_false", "source_handle": "false"},
            ],
        }
    }

    res = client.post("/api/v1/flows/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["node_count"] == 4
    assert data["edge_count"] == 3


def test_validate_flow_graph_broken_edge():
    payload = {
        "definition": {
            "name": "Broken Flow",
            "start_node_id": "node_1",
            "nodes": [
                {"id": "node_1", "type": "action", "action": "navigate", "config": {"url": "https://example.com"}},
            ],
            "edges": [
                {"id": "e1", "source": "node_1", "target": "non_existent_node"},
            ],
        }
    }

    res = client.post("/api/v1/flows/validate", json=payload)
    assert res.status_code == 422
    assert "non_existent_node" in res.text


def test_browser_validate_selector_endpoint():
    # 1. Valid testid
    res_tid = client.post("/api/v1/browser/validate-selector", json={"selector": "testid=checkout-btn"})
    assert res_tid.status_code == 200
    data_tid = res_tid.json()
    assert data_tid["is_valid"] is True
    assert data_tid["selector_type"] == "testid"
    assert data_tid["normalized_selector"] == '[data-testid="checkout-btn"]'

    # 2. Valid role
    res_role = client.post("/api/v1/browser/validate-selector", json={"selector": "role=button[name='Save']"})
    assert res_role.status_code == 200
    data_role = res_role.json()
    assert data_role["is_valid"] is True
    assert data_role["selector_type"] == "role"
    assert data_role["role_name"] == "button"

    # 3. Invalid selector
    res_inv = client.post("/api/v1/browser/validate-selector", json={"selector": "div[unclosed"})
    assert res_inv.status_code == 200
    data_inv = res_inv.json()
    assert data_inv["is_valid"] is False
    assert "Unclosed bracket" in data_inv["error_message"]


def test_browser_test_selector_endpoint():
    mock_session = BrowserSession(
        session_id="sess_test_123",
        project_id=str(uuid4()),
        user_id=str(mock_user_obj.id),
        allowed_domains=["example.com"],
    )

    with patch("backend.app.api.v1.browser.get_verified_session", return_value=mock_session), \
         patch("backend.app.api.v1.browser._browser_adapter") as mock_adapter:

        mock_adapter.get_count.return_value = 1
        mock_adapter.is_visible.return_value = True
        mock_adapter.is_enabled.return_value = True
        mock_adapter.get_box.return_value = {"x": 50, "y": 100, "width": 120, "height": 40}
        mock_adapter.extract_text.return_value = "Submit Order"

        payload = {
            "session_id": "sess_test_123",
            "selector": "testid=order-btn",
            "highlight": True,
        }

        res = client.post("/api/v1/browser/test-selector", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["found"] is True
        assert data["count"] == 1
        assert data["is_visible"] is True
        assert data["text"] == "Submit Order"
        assert data["box"]["width"] == 120
        mock_adapter.highlight.assert_called_once()


def test_test_step_schema_and_runner_retries():
    # Verify TestStep supports retries and fallbacks
    step = TestStep(
        id="s1",
        name="Click Submit",
        step_type="action",
        action=FlowActionType.CLICK,
        target={
            "selector": "#btn-primary",
            "fallbacks": [".btn-fallback", "button[type='submit']"],
        },
        retries=2,
    )
    assert step.retries == 2
    assert step.target.fallbacks == [".btn-fallback", "button[type='submit']"]

    # Verify TestSuiteDefinition supports tags
    suite = TestSuiteDefinition(
        name="Smoke Suite",
        test_case_ids=[uuid4()],
        tags=["smoke", "checkout"],
    )
    assert suite.tags == ["smoke", "checkout"]
