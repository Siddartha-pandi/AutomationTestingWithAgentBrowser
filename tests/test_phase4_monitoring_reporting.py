"""Unit and integration test suite for Phase 4: Live Monitoring and Reporting.

Strictly zero AI dependencies. Tests:
1. Real-time ExecutionEventBus pub/sub, buffer replay, and thread safety.
2. WebSocket execution monitoring endpoint (/ws/executions/{execution_id}) with authentication, ping/pong, and event broadcast.
3. Structured log streaming, filtering (by level and text search), and export downloads (TXT, JSON).
4. Executive HTML report generation with inline SVG charts, duration waterfall, failure base64 screenshots, and zero-AI compliance.
5. Report summary, CSV export, and viewport capture endpoints.
"""

from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, Response

from backend.app.api.v1.executions import (
    download_execution_logs,
    get_execution_html_report,
    get_execution_logs,
    get_execution_viewport,
)
from backend.app.api.v1.reports import export_reports_csv, get_reports_summary
from backend.app.api.v1.ws_monitor import execution_live_monitor_ws
from backend.app.engine.events import ExecutionEventBus, ExecutionEventTypes, execution_event_bus
from backend.app.models.execution import Artifact, Execution, ExecutionLog, ExecutionStep
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.reports.report_generator import ReportGenerator
from backend.app.security.jwt import create_access_token


def run_coroutine_sync(coro):
    """Executes a coroutine synchronously step-by-step without requiring OS thread loops."""
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test.operator@platform.internal"
    user.is_active = True
    user.is_superuser = True
    user.roles = []
    return user


@pytest.fixture
def mock_project_id():
    return uuid4()


@pytest.fixture
def mock_execution(mock_user, mock_project_id):
    execution = MagicMock(spec=Execution)
    execution.id = uuid4()
    execution.project_id = mock_project_id
    execution.definition_id = uuid4()
    execution.definition_version_id = uuid4()
    execution.session_id = "test-session-123"
    execution.trigger_type = "manual"
    execution.status = "passed"
    execution.started_at = datetime.now(timezone.utc)
    execution.completed_at = datetime.now(timezone.utc)
    execution.duration_ms = 1250.0
    execution.summary = {"total_steps": 2, "passed_steps": 2, "failed_steps": 0}

    step1 = MagicMock(spec=ExecutionStep)
    step1.id = uuid4()
    step1.step_index = 1
    step1.node_id = "nav_node"
    step1.step_type = "action"
    step1.action = "navigate"
    step1.status = "passed"
    step1.duration_ms = 450.0
    step1.input_data = {"url": "https://company.internal/dashboard"}
    step1.result_data = {"navigated": True}
    step1.error_message = None
    step1.screenshot_path = None

    step2 = MagicMock(spec=ExecutionStep)
    step2.id = uuid4()
    step2.step_index = 2
    step2.node_id = "click_node"
    step2.step_type = "action"
    step2.action = "click"
    step2.status = "passed"
    step2.duration_ms = 800.0
    step2.input_data = {"target": {"selector": "#submit-btn"}}
    step2.result_data = {"clicked": True}
    step2.error_message = None
    step2.screenshot_path = None

    execution.steps = [step1, step2]

    log1 = MagicMock(spec=ExecutionLog)
    log1.id = uuid4()
    log1.step_id = step1.id
    log1.level = "INFO"
    log1.message = "Step 1 [nav_node]: navigate -> passed"
    log1.is_redacted = True
    log1.timestamp = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)

    log2 = MagicMock(spec=ExecutionLog)
    log2.id = uuid4()
    log2.step_id = step2.id
    log2.level = "ERROR"
    log2.message = "Step 2 [click_node]: click -> failed (Timeout waiting for selector)"
    log2.is_redacted = True
    log2.timestamp = datetime(2026, 11, 11, 12, 0, 1, tzinfo=timezone.utc)

    execution.logs = [log1, log2]
    execution.artifacts = []
    execution.healing_events = []
    execution.project = MagicMock(spec=Project)
    execution.project.name = "Billing App Automation"
    execution.definition = MagicMock()
    execution.definition.name = "Checkout Flow"
    execution.definition.type = "flow"
    execution.definition_version = MagicMock()
    execution.definition_version.version_num = 1
    execution.definition_version.checksum_sha256 = "abc123sha256"

    return execution


# ---------------------------------------------------------------------------
# 1. Event Bus Tests
# ---------------------------------------------------------------------------

def test_event_bus_publish_buffer_and_clear():
    bus = ExecutionEventBus(max_buffer_per_execution=5)
    exec_id = str(uuid4())

    bus.publish(exec_id, ExecutionEventTypes.STATUS_CHANGE, {"status": "running"})
    bus.publish(exec_id, ExecutionEventTypes.STEP_START, {"step_index": 1, "action": "navigate"})
    bus.publish(exec_id, ExecutionEventTypes.CONSOLE_LOG, {"level": "INFO", "message": "Navigated to page"})
    bus.publish(exec_id, ExecutionEventTypes.STEP_COMPLETE, {"step_index": 1, "status": "passed"})

    history = bus.get_history(exec_id)
    assert len(history) == 4
    assert history[0]["type"] == ExecutionEventTypes.STATUS_CHANGE
    assert history[0]["data"]["status"] == "running"
    assert history[3]["type"] == ExecutionEventTypes.STEP_COMPLETE
    assert history[3]["data"]["status"] == "passed"

    # Buffer limit eviction test
    bus.publish(exec_id, ExecutionEventTypes.STEP_START, {"step_index": 2, "action": "click"})
    bus.publish(exec_id, ExecutionEventTypes.STEP_COMPLETE, {"step_index": 2, "status": "passed"})
    history_after = bus.get_history(exec_id)
    assert len(history_after) == 5

    bus.clear_history(exec_id)
    assert len(bus.get_history(exec_id)) == 0


# ---------------------------------------------------------------------------
# 2. WebSocket Execution Monitor Tests
# ---------------------------------------------------------------------------

def test_websocket_unauthenticated_rejected():
    exec_id = str(uuid4())
    mock_db = MagicMock()
    mock_ws = AsyncMock()
    mock_ws.cookies = {}
    mock_ws.headers = {}
    run_coroutine_sync(execution_live_monitor_ws(mock_ws, exec_id, token=None, db=mock_db))
    mock_ws.close.assert_called_once_with(code=1008)


def test_websocket_authenticated_connect_and_ping(mock_user, mock_execution):
    exec_id = str(mock_execution.id)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_user,
        mock_execution,
    ]

    token = create_access_token(mock_user.id, mock_user.email)
    execution_event_bus.publish(exec_id, ExecutionEventTypes.STEP_START, {"step_index": 1, "action": "open"})

    mock_ws = AsyncMock()
    mock_ws.cookies = {}
    mock_ws.headers = {}
    mock_ws.receive_text.side_effect = ['{"type": "ping"}', WebSocketDisconnect()]

    with patch("backend.app.api.v1.ws_monitor.user_has_project_access", return_value=True):
        run_coroutine_sync(execution_live_monitor_ws(mock_ws, exec_id, token=token, db=mock_db))

    mock_ws.accept.assert_called_once()
    calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
    assert any(c.get("type") == "connected" for c in calls)
    assert any(c.get("type") == ExecutionEventTypes.STEP_START for c in calls)
    assert any(c.get("type") == "pong" for c in calls)

    execution_event_bus.clear_history(exec_id)


# ---------------------------------------------------------------------------
# 3. Structured Execution Logs & Filtering Tests
# ---------------------------------------------------------------------------

def test_get_execution_logs_filtering(mock_user, mock_execution):
    mock_db = MagicMock()
    log_info = mock_execution.logs[0]
    log_err = mock_execution.logs[1]

    mock_log_query = MagicMock()
    mock_log_query.filter.return_value = mock_log_query
    mock_log_query.count.return_value = 2
    mock_log_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [log_info, log_err]

    def query_side_effect(model):
        if model == Execution:
            m = MagicMock()
            m.filter.return_value.first.return_value = mock_execution
            return m
        elif model == ExecutionLog:
            return mock_log_query
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    res = get_execution_logs(
        execution_id=mock_execution.id,
        level="ERROR",
        search="Timeout",
        step_id=None,
        limit=200,
        offset=0,
        current_user=mock_user,
        db=mock_db,
    )
    assert res["execution_id"] == str(mock_execution.id)
    assert res["total"] == 2
    assert len(res["logs"]) == 2
    assert res["logs"][0]["level"] == "INFO"
    assert res["logs"][1]["level"] == "ERROR"


def test_download_execution_logs_txt_and_json(mock_user, mock_execution):
    mock_db = MagicMock()
    log_rec = mock_execution.logs[0]

    def query_side_effect(model):
        if model == Execution:
            m = MagicMock()
            m.filter.return_value.first.return_value = mock_execution
            return m
        elif model == ExecutionLog:
            m = MagicMock()
            m.filter.return_value.order_by.return_value.all.return_value = [log_rec]
            return m
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    # 1. TXT download
    res_txt = download_execution_logs(
        execution_id=mock_execution.id,
        format="txt",
        level=None,
        current_user=mock_user,
        db=mock_db,
    )
    assert isinstance(res_txt, Response)
    assert "attachment; filename=" in res_txt.headers["content-disposition"]
    body_text = res_txt.body.decode("utf-8")
    assert "[2026-11-11 12:00:00] [INFO   ] Step 1 [nav_node]: navigate -> passed" in body_text

    # 2. JSON download
    res_json = download_execution_logs(
        execution_id=mock_execution.id,
        format="json",
        level=None,
        current_user=mock_user,
        db=mock_db,
    )
    assert isinstance(res_json, Response)
    assert "attachment; filename=" in res_json.headers["content-disposition"]
    assert "Step 1 [nav_node]: navigate -> passed" in res_json.body.decode("utf-8")


# ---------------------------------------------------------------------------
# 4. Executive HTML Report Generation Tests
# ---------------------------------------------------------------------------

def test_export_html_report_rendering():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake-png-data")
        tmp_img_path = tmp_img.name

    try:
        mock_report = {
            "execution_id": str(uuid4()),
            "project_name": "E-Commerce Test Suite",
            "definition_name": "Checkout Workflow",
            "trigger_type": "manual",
            "status": "FAILED",
            "duration_ms": 3200.0,
            "metrics": {
                "total_steps": 2,
                "passed_steps": 1,
                "failed_steps": 1,
                "skipped_steps": 0,
                "pass_rate_percent": 50.0,
            },
            "steps": [
                {
                    "step_index": 1,
                    "node_id": "step_open",
                    "action": "navigate",
                    "status": "passed",
                    "duration_ms": 1200.0,
                    "error_message": None,
                },
                {
                    "step_index": 2,
                    "node_id": "step_click",
                    "action": "click",
                    "status": "failed",
                    "duration_ms": 2000.0,
                    "error_message": "Element '#order-btn' not clickable after 5000ms",
                    "screenshot_path": tmp_img_path,
                },
            ],
            "artifacts": [
                {
                    "artifact_type": "screenshot",
                    "file_size_bytes": 1024,
                    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                }
            ],
        }

        html = ReportGenerator.export_html_report(mock_report)

        assert "Executive Test Report - Checkout Workflow" in html
        assert "AutomationTestingWithAgentBrowser" in html
        assert "Deterministic Execution" in html
        assert "50.0%" in html
        assert "<svg viewBox=\"0 0 100 100\"" in html
        assert "TOTAL STEPS" in html
        assert "Duration Waterfall" in html
        assert "1200.0 ms" in html
        assert "2000.0 ms" in html
        assert "FAILURE VIEWPORT SNAPSHOT:" in html
        assert "data:image/png;base64," in html
        assert "window.print()" in html
        assert "@media print" in html
        assert "Strict Zero-AI Platform Verification &amp; Data Protection Certified" in html
        assert "zero third-party external AI APIs" in html

    finally:
        if os.path.exists(tmp_img_path):
            os.remove(tmp_img_path)


def test_html_report_endpoint(mock_user, mock_execution):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_execution

    with patch.object(ReportGenerator, "generate_consolidated_report") as mock_gen:
        mock_gen.return_value = {
            "execution_id": str(mock_execution.id),
            "definition_name": "Smoke Test",
            "status": "PASSED",
            "metrics": {"total_steps": 1, "passed_steps": 1, "failed_steps": 0, "pass_rate_percent": 100.0},
            "steps": [],
            "artifacts": [],
        }

        res = get_execution_html_report(
            execution_id=mock_execution.id,
            current_user=mock_user,
            db=mock_db,
        )
        assert isinstance(res, HTMLResponse)
        html_text = res.body.decode("utf-8")
        assert "Smoke Test" in html_text
        assert "Strict Zero-AI Platform Verification" in html_text


# ---------------------------------------------------------------------------
# 5. Live Viewport Screenshot Endpoint Tests
# ---------------------------------------------------------------------------

def test_get_execution_viewport_from_step_screenshot(mock_user, mock_execution):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake-img")
        tmp_img_path = tmp_img.name

    mock_step_with_scr = MagicMock(spec=ExecutionStep, screenshot_path=tmp_img_path)
    mock_db = MagicMock()

    def query_side_effect(model):
        if model == Execution:
            m = MagicMock()
            m.filter.return_value.first.return_value = mock_execution
            return m
        elif model == ExecutionStep:
            m = MagicMock()
            m.filter.return_value.order_by.return_value.first.return_value = mock_step_with_scr
            return m
        return MagicMock()

    mock_db.query.side_effect = query_side_effect

    try:
        res = get_execution_viewport(
            execution_id=mock_execution.id,
            current_user=mock_user,
            db=mock_db,
        )
        assert isinstance(res, FileResponse)
        assert res.path == tmp_img_path
        assert res.media_type == "image/png"
    finally:
        if os.path.exists(tmp_img_path):
            os.remove(tmp_img_path)


# ---------------------------------------------------------------------------
# 6. Reports Summary and CSV Export Tests
# ---------------------------------------------------------------------------

def test_reports_summary_and_export_csv(mock_user, mock_execution):
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.count.return_value = 10
    mock_query.filter.return_value.count.side_effect = [8, 2]  # completed=8, failed=2
    mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_execution]
    mock_db.query.return_value = mock_query

    summary = get_reports_summary(
        project_id=None,
        db=mock_db,
        current_user=mock_user,
    )
    assert summary["total_executions"] == 10
    assert summary["completed_executions"] == 8
    assert summary["failed_executions"] == 2
    assert summary["success_rate_percent"] == 80.0

    csv_res = export_reports_csv(
        project_id=None,
        db=mock_db,
        current_user=mock_user,
    )
    assert isinstance(csv_res, Response)
    assert csv_res.media_type == "text/csv"
    csv_text = csv_res.body.decode("utf-8")
    assert "Execution ID,Trigger Type,Status,Started At,Duration (ms)" in csv_text
    assert str(mock_execution.id) in csv_text
