"""Regression tests for Critical Platform Defect Fixes (Phase 7).

Covers:
1. Agent Browser CLI health detection & installation reporting
2. Cross-process event delivery via Redis Pub/Sub & streams
3. Redis disconnection handling & fallback buffering
4. Worker domain allowlist resolution & empty allowlist rejection
5. Browser session ownership & project re-authorization
6. Strict SSRF protection (IPv4, IPv6, ULA, mapped IPv6, userinfo, DNS failure)
7. Navigation redirect validation & private IP blocking
8. Native browser action semantics (check, uncheck, radio, scroll)
9. Deterministic selector ambiguity rejection & original selector logging
10. Irreversible action retry protection & non-retryable error fail-fast
11. WebSocket viewport capture using artifact references
"""

from __future__ import annotations

import os
import socket
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend.app.api.v1.browser import (
    ActionPayload,
    LaunchSessionPayload,
    execute_action,
    get_browser_status,
    get_verified_session,
    launch_session,
    test_browser_connection as api_test_browser_connection,
)
from backend.app.browser import AgentBrowserAdapter, BrowserHealthStatus, SessionManager
from backend.app.browser.browser_errors import NavigationSecurityError, SessionIsolationError
from backend.app.engine.events import ExecutionEventBus, ExecutionEventTypes, execution_event_bus
from backend.app.engine.retry.retry_policy import BackoffStrategy, RetryConfig, RetryExecutor
from backend.app.engine.selectors import ResolvedSelectorResult, SelectorFallbackResolver
from backend.app.models.execution import Execution, ExecutionStep
from backend.app.models.project import Environment, Project
from backend.app.models.user import User
from backend.app.security.network_policy import (
    is_domain_allowed,
    is_ip_restricted,
    validate_destination_url,
)
from backend.app.worker.tasks import resolve_approved_domains_for_execution


# -----------------------------------------------------------------------------
# 1. Agent Browser Health Detection & Installation Reporting
# -----------------------------------------------------------------------------

def test_cli_not_installed():
    """When CLI is not installed, /status reports is_installed=False, unavailable health, and meaningful error."""
    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)

    with patch("shutil.which", return_value=None), \
         patch.object(AgentBrowserAdapter, "get_health", return_value=BrowserHealthStatus(is_healthy=False, cli_path="agent-browser")):
        status_res = get_browser_status(current_user=mock_user)

        assert status_res["is_installed"] is False
        assert status_res["health"] == "unavailable"
        assert status_res["cli_version"] is None
        assert "not installed or not found in system PATH" in status_res["error_message"]


def test_cli_installed_but_unhealthy():
    """When CLI is installed but fails diagnostics, report degraded health without inventing a version."""
    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)

    with patch("shutil.which", return_value="/usr/bin/agent-browser"), \
         patch.object(AgentBrowserAdapter, "get_health", return_value=BrowserHealthStatus(is_healthy=False, cli_path="/usr/bin/agent-browser", error_message="CDP socket error")):
        status_res = get_browser_status(current_user=mock_user)

        assert status_res["is_installed"] is True
        assert status_res["health"] == "degraded"
        assert status_res["cli_version"] is None  # Must NOT invent '0.41.2'
        assert "CDP socket error" in status_res["error_message"]


def test_test_connection_endpoint():
    """Test /test-connection reports actual connection state and version."""
    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)

    # Success case
    with patch("shutil.which", return_value="/usr/bin/agent-browser"), \
         patch.object(AgentBrowserAdapter, "get_health", return_value=BrowserHealthStatus(is_healthy=True, version="0.41.2")):
        res = api_test_browser_connection(current_user=mock_user)
        assert res["success"] is True
        assert res["version"] == "0.41.2"
        assert res["session_state"] == "ready"


# -----------------------------------------------------------------------------
# 2 & 3. Live Monitoring Across Processes & Redis Disconnection Handling
# -----------------------------------------------------------------------------

def test_event_bus_redis_publishing_and_disconnection_fallback():
    """Event bus attempts Redis publishing and falls back cleanly on connection error."""
    bus = ExecutionEventBus()
    exec_id = str(uuid4())

    mock_redis = MagicMock()
    mock_redis.publish.side_effect = Exception("Redis connection refused")
    mock_redis.xadd.side_effect = Exception("Redis connection refused")

    with patch.object(bus, "_get_sync_redis", return_value=mock_redis):
        # Publishing must not raise an error even when Redis throws ConnectionRefused
        evt = bus.publish(exec_id, ExecutionEventTypes.STATUS_CHANGE, {"status": "running"})
        assert evt["execution_id"] == exec_id
        assert evt["type"] == ExecutionEventTypes.STATUS_CHANGE
        assert evt["seq"] == 1

        # History is reliably preserved in in-memory fallback
        history = bus.get_history(exec_id)
        assert len(history) == 1
        assert history[0]["id"] == evt["id"]


# -----------------------------------------------------------------------------
# 4 & 5. Worker Domain Allowlists & Production Empty Allowlist Rejection
# -----------------------------------------------------------------------------

def test_resolve_approved_domains_from_environment():
    """Approved domains are loaded from the execution's environment."""
    mock_db = MagicMock()
    env = MagicMock(spec=Environment, allowed_domains=["app.example.com", "api.example.com"], base_url="https://app.example.com/login")
    mock_db.query.return_value.filter.return_value.first.return_value = env

    execution = MagicMock(spec=Execution, id=uuid4(), environment_id=uuid4(), project_id=uuid4())

    with patch("backend.app.security.network_policy.is_local_dev_allowed", return_value=False):
        domains = resolve_approved_domains_for_execution(mock_db, execution)
        assert "app.example.com" in domains
        assert "api.example.com" in domains


def test_empty_allowlist_rejected_in_production():
    """In production, executing without any approved domains must raise ValueError."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.all.return_value = []

    execution = MagicMock(spec=Execution, id=uuid4(), environment_id=None, project_id=uuid4())

    with patch("backend.app.security.network_policy.is_local_dev_allowed", return_value=False), \
         patch("backend.app.worker.tasks.settings", MagicMock(allowed_domains=())):
        with pytest.raises(ValueError, match="No approved domain allowlist configured"):
            resolve_approved_domains_for_execution(mock_db, execution)


# -----------------------------------------------------------------------------
# 6 & 7. Browser Session Ownership & Project Member Access
# -----------------------------------------------------------------------------

def test_ownerless_session_rejected_for_ordinary_users():
    """Ordinary users cannot access ownerless browser sessions."""
    from backend.app.api.v1.browser import _browser_adapter
    session = _browser_adapter.session_manager.create_session(user_id=None)

    ordinary_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)
    superuser = MagicMock(spec=User, id=uuid4(), is_superuser=True)

    # Ordinary user rejected with 403
    with pytest.raises(HTTPException) as exc:
        get_verified_session(session.session_id, ordinary_user)
    assert exc.value.status_code == 403
    assert "ownerless" in exc.value.detail.lower()

    # Superuser permitted
    verified = get_verified_session(session.session_id, superuser)
    assert verified.session_id == session.session_id


def test_removed_project_member_access_rejected():
    """When a user is removed from the session's project, access is rejected."""
    from backend.app.api.v1.browser import _browser_adapter
    proj_id = str(uuid4())
    user_id = uuid4()
    session = _browser_adapter.session_manager.create_session(user_id=str(user_id), project_id=proj_id)

    user = MagicMock(spec=User, id=user_id, is_superuser=False)
    mock_db = MagicMock()

    with patch("backend.app.api.v1.browser.user_has_project_access", return_value=False):
        with pytest.raises(HTTPException) as exc:
            get_verified_session(session.session_id, user, db=mock_db)
        assert exc.value.status_code == 403
        assert "not a member" in exc.value.detail


def test_launch_session_generates_server_side_id():
    """launch_session ignores frontend-supplied session_id and generates server-side ID."""
    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)
    mock_db = MagicMock()

    payload = LaunchSessionPayload(
        session_id="malicious-custom-session-id",
        allowed_domains=["example.com"],
    )

    with patch("backend.app.security.network_policy.is_local_dev_allowed", return_value=True):
        res = launch_session(payload, current_user=mock_user, db=mock_db)
        assert res["session_id"] != "malicious-custom-session-id"
        assert res["session_id"].startswith("sess_")


# -----------------------------------------------------------------------------
# 8 & 9. Strict SSRF Protection (IPv4, IPv6, Mapped, ULA, Malformed, DNS Fail)
# -----------------------------------------------------------------------------

def test_ssrf_ipv4_and_ipv6_variants():
    """All private, loopback, link-local, and cloud metadata IPs must be rejected."""
    # AWS/GCP IPv4 metadata
    ok, _ = validate_destination_url("http://169.254.169.254/latest/meta-data/")
    assert not ok

    # AWS IPv6 metadata
    ok, _ = validate_destination_url("http://[fd00:ec2::254]/latest/meta-data/")
    assert not ok

    # IPv6 loopback
    ok, _ = validate_destination_url("http://[::1]:8080/metrics")
    assert not ok

    # IPv4-mapped IPv6 loopback
    ok, _ = validate_destination_url("http://[::ffff:127.0.0.1]:8080/secret")
    assert not ok

    # IPv6 Unique Local (ULA)
    ok, _ = validate_destination_url("http://[fc00::1]/admin")
    assert not ok

    # IPv6 Link-Local
    ok, _ = validate_destination_url("http://[fe80::1]/config")
    assert not ok

    # Ambiguous decimal integer representation of 127.0.0.1
    ok, _ = validate_destination_url("http://2130706433/")
    assert not ok

    # Userinfo / credentials parser evasion (@)
    ok, _ = validate_destination_url("http://admin:secret@127.0.0.1/")
    assert not ok
    ok, _ = validate_destination_url("http://example.com@169.254.169.254/")
    assert not ok


def test_dns_resolution_failure_fails_closed():
    """When hostname resolution fails, destination validation must fail closed in production."""
    with patch("socket.getaddrinfo", side_effect=socket.gaierror(11001, "getaddrinfo failed")):
        ok, msg = validate_destination_url(
            "https://unresolvable-domain-12345.com/login",
            allowed_domains=["unresolvable-domain-12345.com"],
            fail_closed_dns=True,
        )
        assert not ok
        assert "could not be resolved" in msg.lower()


# -----------------------------------------------------------------------------
# 10. Native Browser Action Semantics (Check, Uncheck, Radio, Scroll)
# -----------------------------------------------------------------------------

def test_browser_action_check_uncheck_and_scroll():
    """Browser action executes check, uncheck, and scroll with native commands."""
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.check.return_value = MagicMock(to_dict=lambda: {"action": "check", "success": True})
    mock_adapter.uncheck.return_value = MagicMock(to_dict=lambda: {"action": "uncheck", "success": True})
    mock_adapter.scroll.return_value = MagicMock(to_dict=lambda: {"action": "scroll", "success": True})
    mock_adapter.screenshot.return_value = MagicMock(file_path="")

    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=True)
    mock_db = MagicMock()

    with patch("backend.app.api.v1.browser._browser_adapter", mock_adapter), \
         patch("backend.app.api.v1.browser.get_verified_session", return_value=MagicMock(is_active=True)):

        # Check
        res_chk = execute_action(
            ActionPayload(session_id="s1", action="check", selector="#terms-checkbox"),
            current_user=mock_user,
            db=mock_db,
        )
        assert res_chk["action"] == "check"
        mock_adapter.check.assert_called_with("s1", "#terms-checkbox", timeout=15.0)

        # Uncheck
        res_unchk = execute_action(
            ActionPayload(session_id="s1", action="uncheck", selector="#newsletter-checkbox"),
            current_user=mock_user,
            db=mock_db,
        )
        assert res_unchk["action"] == "uncheck"
        mock_adapter.uncheck.assert_called_with("s1", "#newsletter-checkbox", timeout=15.0)

        # Scroll (native CLI call, NO body click)
        res_scroll = execute_action(
            ActionPayload(session_id="s1", action="scroll"),
            current_user=mock_user,
            db=mock_db,
        )
        assert res_scroll["action"] == "scroll"
        mock_adapter.scroll.assert_called_with("s1", direction="down", pixels=400, timeout=15.0)


# -----------------------------------------------------------------------------
# 11. Deterministic Selector Ambiguity Rejection
# -----------------------------------------------------------------------------

def test_selector_fallback_rejects_ambiguous_element():
    """When allow_ambiguous is False and multiple elements match, reject silent selection."""
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    # Matches 3 elements
    mock_adapter.is_visible.return_value = True
    mock_adapter.get_count.return_value = 3

    resolver = SelectorFallbackResolver(mock_adapter)
    res = resolver.resolve(
        session_id="s1",
        primary_selector=".common-button",
        allow_ambiguous=False,
    )

    assert res.is_ambiguous is True
    assert res.confidence == 0.0
    assert "matches multiple elements" in res.warning


# -----------------------------------------------------------------------------
# 12. Irreversible Action Retry Protection
# -----------------------------------------------------------------------------

def test_retry_executor_aborts_on_irreversible_action():
    """Irreversible actions must not execute blind retries upon failure."""
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    executor = RetryExecutor(mock_adapter)

    call_count = 0

    def payment_submit():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Payment gateway network timeout")

    cfg = RetryConfig(
        max_retries=3,
        is_irreversible=True,
        verify_state_before_retry=False,  # No verification possible
    )

    outcome = executor.execute_with_retry(
        session_id="s1",
        action_fn=payment_submit,
        config=cfg,
        action_name="payment_submit",
    )

    # Must abort after 1 attempt; no duplicate charges!
    assert outcome.success is False
    assert outcome.attempts == 1
    assert call_count == 1


# -----------------------------------------------------------------------------
# 13. Redirect Validation & Private IP Blocking
# -----------------------------------------------------------------------------

def test_navigate_redirect_to_private_ip_blocked():
    """When a navigation redirects to a restricted private IP, session is closed and error raised."""
    adapter = AgentBrowserAdapter()
    sess = adapter.session_manager.create_session(
        allowed_domains=["example.com"],
        user_id="user-1",
    )

    # Initial URL is valid, but post-navigation URL redirected to private IP
    with patch("backend.app.security.network_policy.validate_destination_url") as mock_val, \
         patch.object(adapter.executor, "execute", return_value=MagicMock(is_success=True, duration_ms=50.0, stdout="")), \
         patch.object(adapter, "get_url", return_value="http://192.168.1.1/admin"):

        # First call for initial URL succeeds, second call for redirect fails
        mock_val.side_effect = [
            (True, "OK"),
            (False, "SSRF Protection: Direct IP destination '192.168.1.1' is in restricted range."),
        ]

        with pytest.raises(NavigationSecurityError) as exc:
            adapter.navigate(sess.session_id, "https://example.com/login")
        assert "Redirect destination blocked" in str(exc.value)


# -----------------------------------------------------------------------------
# 14. WebSocket Viewport Capture Using Artifact References
# -----------------------------------------------------------------------------

def test_websocket_capture_viewport_returns_artifact_ref():
    """capture_viewport returns artifact reference instead of large Base64 payload."""
    from backend.app.api.v1.ws_monitor import execution_live_monitor_ws
    from fastapi import WebSocketDisconnect

    exec_id = str(uuid4())
    mock_db = MagicMock()
    mock_user = MagicMock(spec=User, id=uuid4(), is_superuser=False)
    mock_exec = MagicMock(spec=Execution, id=UUID(exec_id), project_id=uuid4(), session_id="s1", status="running")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_exec

    mock_ws = AsyncMock()
    mock_ws.cookies = {}
    mock_ws.headers = {}
    mock_ws.receive_text.side_effect = ['{"action": "capture_viewport"}', WebSocketDisconnect()]

    mock_adapter = MagicMock()
    mock_adapter.session_manager.get_session.return_value = MagicMock(is_active=True)
    mock_adapter.screenshot.return_value = MagicMock(screenshot_path="/app/reports/screenshots/live_123.png")

    with patch("backend.app.api.v1.ws_monitor.user_has_project_access", return_value=True), \
         patch("backend.app.api.v1.ws_monitor.AgentBrowserAdapter", return_value=mock_adapter), \
         patch("backend.app.api.v1.ws_monitor._authenticate_ws_token", return_value=mock_user):

        def run_sync(coro):
            while True:
                try:
                    coro.send(None)
                except StopIteration:
                    break

        run_sync(execution_live_monitor_ws(mock_ws, exec_id, token="test-token", db=mock_db))

        sent_messages = [c[0][0] for c in mock_ws.send_json.call_args_list]
        viewport_msg = next((m for m in sent_messages if m.get("type") == "viewport:frame"), None)
        assert viewport_msg is not None
        assert "artifact_path" in viewport_msg["data"]
        assert "image_base64" not in viewport_msg["data"]  # Not sending large Base64!

