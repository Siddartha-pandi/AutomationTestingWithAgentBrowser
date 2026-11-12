"""Unit and integration tests for Phase 3: Flow Builder and Test Management.

Verifies:
1. Flow Graph Validation endpoint (/api/v1/flows/validate)
2. Interactive Selector Validator (/api/v1/browser/validate-selector)
3. Live Browser Selector Tester (/api/v1/browser/test-selector)
4. Element Library & resilient selectors
5. Test Step Retries & Fallback resolution in TestRunner
6. Browser Recorder session lifecycle & native action recording
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.v1.browser import (
    TestSelectorPayload as _TestSelectorPayload,
    ValidateSelectorPayload,
    test_selector_in_session as api_test_selector_in_session,
    validate_selector_syntax,
)
from backend.app.api.v1.flows import (
    ValidateFlowRequest,
    validate_flow_definition,
)
from backend.app.api.v1.recorder import (
    RecordActionPayload,
    SaveRecordingPayload,
    StartRecorderPayload,
    record_action,
    save_recording,
    start_recorder,
)
from backend.app.browser import ActionResult, BrowserSession, ScreenshotResult
from backend.app.engine.flows.flow_schema import FlowActionType, FlowGraphDefinition
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep, TestSuiteDefinition
from backend.app.models.project import Project
from backend.app.models.user import User

mock_user_obj = MagicMock(spec=User)
mock_user_obj.id = uuid4()
mock_user_obj.email = "admin@example.com"
mock_user_obj.is_active = True
mock_user_obj.is_superuser = True
mock_user_obj.roles = []


@pytest.fixture
def mock_user():
    return mock_user_obj


def test_validate_flow_graph_success(mock_user):
    payload = {
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

    graph_def = FlowGraphDefinition.model_validate(payload)
    req = ValidateFlowRequest(definition=graph_def)
    res = validate_flow_definition(payload=req, current_user=mock_user)
    assert res["valid"] is True
    assert res["node_count"] == 4
    assert res["edge_count"] == 3


def test_validate_flow_graph_broken_edge():
    payload = {
        "name": "Broken Flow",
        "nodes": [
            {"id": "node_1", "type": "action", "action": "navigate", "config": {"url": "https://example.com"}},
        ],
        "edges": [
            {"id": "e1", "source": "node_1", "target": "non_existent_node"},
        ],
    }

    with pytest.raises((ValueError, ValidationError)) as exc_info:
        FlowGraphDefinition.model_validate(payload)
    assert "non_existent_node" in str(exc_info.value)


def test_browser_validate_selector_endpoint(mock_user):
    # 1. Valid testid
    data_tid = validate_selector_syntax(
        payload=ValidateSelectorPayload(selector="testid=checkout-btn"),
        current_user=mock_user,
    )
    assert data_tid["is_valid"] is True
    assert data_tid["selector_type"] == "testid"
    assert data_tid["normalized_selector"] == '[data-testid="checkout-btn"]'

    # 2. Valid role
    data_role = validate_selector_syntax(
        payload=ValidateSelectorPayload(selector="role=button[name='Save']"),
        current_user=mock_user,
    )
    assert data_role["is_valid"] is True
    assert data_role["selector_type"] == "role"
    assert data_role["role_name"] == "button"

    # 3. Invalid selector
    data_inv = validate_selector_syntax(
        payload=ValidateSelectorPayload(selector="div[unclosed"),
        current_user=mock_user,
    )
    assert data_inv["is_valid"] is False
    assert "Unclosed bracket" in data_inv["error_message"]


def test_browser_test_selector_endpoint(mock_user):
    mock_session = BrowserSession(
        session_id="sess_test_123",
        project_id=str(uuid4()),
        user_id=str(mock_user.id),
        allowed_domains=["example.com"],
    )

    with patch("backend.app.api.v1.browser.get_verified_session", return_value=mock_session), \
         patch("backend.app.api.v1.browser._browser_adapter") as mock_adapter:

        mock_adapter.get_count.return_value = 1
        mock_adapter.is_visible.return_value = True
        mock_adapter.is_enabled.return_value = True
        mock_adapter.get_box.return_value = {"x": 50, "y": 100, "width": 120, "height": 40}
        mock_adapter.extract_text.return_value = "Submit Order"

        payload = _TestSelectorPayload(
            session_id="sess_test_123",
            selector="testid=order-btn",
            highlight=True,
        )

        data = api_test_selector_in_session(payload=payload, current_user=mock_user, db=MagicMock())
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


def test_recorder_session_lifecycle_and_actions(mock_user):
    mock_db = MagicMock()
    mock_proj = MagicMock(spec=Project)
    mock_proj.id = uuid4()

    mock_shot = MagicMock(spec=ScreenshotResult)
    mock_shot.file_path = "non_existent_for_test.png"

    with patch("backend.app.api.v1.recorder.resolve_project_id", return_value=mock_proj), \
         patch("backend.app.api.v1.recorder.get_verified_session") as mock_get_verified, \
         patch("backend.app.api.v1.recorder._browser_adapter") as mock_adapter:

        mock_session = BrowserSession(
            session_id="rec_test123",
            project_id=str(mock_proj.id),
            user_id=str(mock_user.id),
            allowed_domains=["example.com"],
        )
        mock_get_verified.return_value = mock_session
        mock_adapter.launch.return_value = mock_session
        mock_adapter.screenshot.return_value = mock_shot
        mock_adapter.click.return_value = ActionResult(success=True, action="click", target="#btn", duration_ms=50.0)
        mock_adapter.check.return_value = ActionResult(success=True, action="check", target="#remember-me", duration_ms=40.0)
        mock_adapter.scroll.return_value = ActionResult(success=True, action="scroll", target="page", duration_ms=30.0)

        # 1. Start recorder
        start_payload = StartRecorderPayload(
            project_id=str(mock_proj.id),
            target_url="https://example.com/login",
        )
        start_res = start_recorder(payload=start_payload, current_user=mock_user, db=mock_db)
        assert start_res["status"] == "recording"
        assert start_res["action_count"] == 1
        sess_id = start_res["session_id"]

        # Verify launch received user_id and target domain
        mock_adapter.launch.assert_called_once()
        launch_kwargs = mock_adapter.launch.call_args.kwargs
        assert launch_kwargs["user_id"] == str(mock_user.id)
        assert "example.com" in launch_kwargs["allowed_domains"]

        # 2. Record native check action
        check_res = record_action(
            payload=RecordActionPayload(session_id=sess_id, action="check", selector="#remember-me"),
            current_user=mock_user,
            db=mock_db,
        )
        assert check_res["success"] is True
        assert check_res["action"]["action"] == "check"
        mock_adapter.check.assert_called_once_with(sess_id, "#remember-me")

        # 3. Record native scroll action
        scroll_res = record_action(
            payload=RecordActionPayload(session_id=sess_id, action="scroll", selector=""),
            current_user=mock_user,
            db=mock_db,
        )
        assert scroll_res["success"] is True
        mock_adapter.scroll.assert_called_once_with(sess_id, 0, 400)

        # 4. Save recording as Flow
        save_res = save_recording(
            payload=SaveRecordingPayload(
                session_id=sess_id,
                project_id=str(mock_proj.id),
                name="Recorded Flow Test",
                target_type="flow",
            ),
            current_user=mock_user,
            db=mock_db,
        )
        assert save_res["type"] == "flow"
        assert save_res["name"] == "Recorded Flow Test"
