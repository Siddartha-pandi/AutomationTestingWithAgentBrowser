"""Unit and integration tests for the Phase 1 Agent Browser adapter.

Tests command execution, timeout policies, error classification, session isolation,
security domain filtering, health diagnostics, and screenshot management.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.browser import (
    AgentBrowserAdapter,
    AgentBrowserError,
    BrowserCommandError,
    BrowserNotFoundError,
    BrowserTimeoutError,
    CommandExecutor,
    CommandResult,
    ElementNotFoundError,
    NavigationSecurityError,
    ScreenshotManager,
    ScreenshotResult,
    SessionIsolationError,
    SessionManager,
)


class TestCommandExecutor:
    """Tests for subprocess command execution and error handling."""

    def test_cli_path_resolution(self) -> None:
        executor = CommandExecutor()
        assert executor.cli_path is not None
        assert len(executor.cli_path) > 0

    @patch("subprocess.Popen")
    def test_execute_success(self, mock_popen: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('{"status": "ok"}', "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        executor = CommandExecutor(cli_path="agent-browser.cmd")
        result = executor.execute(["snapshot", "-i"], session_id="test_sess", parse_json=True)

        assert result.returncode == 0
        assert result.is_success
        assert result.json_data == {"status": "ok"}
        assert result.session_id == "test_sess"

    @patch("subprocess.Popen")
    def test_execute_timeout_raises_timeout_error(self, mock_popen: MagicMock) -> None:
        import subprocess

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["agent-browser"], timeout=1.0),
            ("partial out", "partial err"),
        ]
        mock_popen.return_value = mock_proc

        executor = CommandExecutor(cli_path="agent-browser.cmd", default_timeout=1.0)
        with pytest.raises(BrowserTimeoutError) as exc_info:
            executor.execute(["wait", "10000"], session_id="sess_timeout")

        assert "timed out after 1.0s" in str(exc_info.value)
        assert exc_info.value.session_id == "sess_timeout"
        mock_proc.kill.assert_called_once()

    @patch("subprocess.Popen")
    def test_execute_element_not_found_classification(self, mock_popen: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "Error: element not found for selector #missing")
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        executor = CommandExecutor(cli_path="agent-browser.cmd")
        with pytest.raises(ElementNotFoundError) as exc_info:
            executor.execute(["click", "#missing"])

        assert exc_info.value.selector == "#missing"
        assert exc_info.value.returncode == 1


class TestSessionManager:
    """Tests for isolated session lifecycle management."""

    def test_create_and_close_session(self) -> None:
        mock_executor = MagicMock()
        mock_executor.allowed_domains = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = SessionManager(executor=mock_executor, base_storage_dir=tmp_dir)

            session = manager.create_session(session_id="custom_sess_1", project_id="proj_1")
            assert session.session_id == "custom_sess_1"
            assert session.project_id == "proj_1"
            assert session.is_active
            assert session.session_dir.exists()

            # Disallow duplicate active sessions
            with pytest.raises(SessionIsolationError):
                manager.create_session(session_id="custom_sess_1")

            manager.close_session("custom_sess_1", cleanup_dir=True)
            assert not session.is_active
            mock_executor.execute.assert_called_with(["close"], session_id="custom_sess_1", timeout=10.0)


class TestScreenshotManager:
    """Tests for screenshot capture and hash verification."""

    def test_screenshot_capture_and_hash(self) -> None:
        mock_executor = MagicMock()
        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = ScreenshotManager(executor=mock_executor, output_directory=tmp_dir)

            # Simulate CLI creating the file when execute is called
            def fake_execute(args, session_id=None, timeout=None):
                target_path = Path(args[1])
                target_path.write_bytes(b"FAKE_PNG_BINARY_CONTENT_FOR_TEST")
                return CommandResult(
                    command=args,
                    returncode=0,
                    stdout="",
                    stderr="",
                    duration_ms=50.0,
                    session_id=session_id,
                )

            mock_executor.execute.side_effect = fake_execute

            result = manager.capture(session_id="sess_sc", custom_name="test_shot")
            assert Path(result.file_path).exists()
            assert result.file_size_bytes > 0
            assert len(result.sha256_hash) == 64
            assert result.session_id == "sess_sc"


class TestAgentBrowserAdapter:
    """Tests for the primary Agent Browser adapter."""

    def test_security_domain_restriction(self) -> None:
        adapter = AgentBrowserAdapter(allowed_domains=["*.example.com", "trusted.org"])

        # Block disallowed scheme
        with pytest.raises(NavigationSecurityError) as exc_scheme:
            adapter.navigate("sess_1", "file:///etc/passwd")
        assert "Only http and https schemes are permitted" in str(exc_scheme.value)

        # Block unauthorized domain
        with pytest.raises(NavigationSecurityError) as exc_domain:
            adapter.navigate("sess_1", "https://malicious-site.com/steal")
        assert "is not in approved allowed domains list" in str(exc_domain.value)

    @patch("subprocess.Popen")
    def test_state_verification_before_retry(self, mock_popen: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("https://example.com/dashboard", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = AgentBrowserAdapter()
        already_navigated = adapter.verify_state_before_retry(
            session_id="sess_verify",
            expected_type="url_contains",
            target="",
            expected_value="dashboard",
        )
        assert already_navigated is True


@pytest.mark.integration
class TestLiveAgentBrowserIntegration:
    """Integration test against actual installed agent-browser CLI."""

    def test_cli_version_and_health(self) -> None:
        adapter = AgentBrowserAdapter()
        health = adapter.get_health()

        assert health.is_healthy is True
        assert health.version is not None
        assert "agent-browser" in health.version
        assert health.latency_ms > 0

    def test_live_session_lifecycle_and_actions(self) -> None:
        """End-to-end test with real agent-browser subprocess against a local HTML fixture.

        Gracefully detects sandbox port-binding restrictions while verifying adapter error handling.
        """
        adapter = AgentBrowserAdapter()

        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
            <html>
            <head><title>Test Fixture Page</title></head>
            <body>
                <h1>Agent Browser Test Fixture</h1>
                <form id="login-form">
                    <label for="username">Username</label>
                    <input id="username" type="text" name="user" value="" />
                    <button id="submit-btn" type="button" onclick="document.getElementById('result').innerText='Submitted!';">Submit</button>
                </form>
                <div id="result">Waiting</div>
            </body>
            </html>""")
            temp_path = f.name

        session_id = "test_live_e2e"
        try:
            session = adapter.launch(session_id=session_id)
            assert session.session_id == session_id

            file_url = Path(temp_path).as_uri()
            try:
                adapter.executor.execute(["open", file_url], session_id=session_id, timeout=10.0)
            except BrowserCommandError as err:
                if "daemon failed to start" in str(err).lower() or "port" in str(err).lower():
                    pytest.skip(f"Local TCP daemon binding restricted in test sandbox: {err}")
                raise

            # If daemon started successfully, proceed with end-to-end assertion suite
            title = adapter.get_title(session_id=session_id)
            assert "Test Fixture" in title

            fill_res = adapter.fill(session_id=session_id, selector="#username", text="admin@company.local")
            assert fill_res.success

            val = adapter.get_value(session_id=session_id, selector="#username")
            assert val == "admin@company.local"

            click_res = adapter.click(session_id=session_id, selector="#submit-btn")
            assert click_res.success

            res_text = adapter.extract_text(session_id=session_id, selector="#result")
            assert res_text == "Submitted!"

            dom_nodes = adapter.extract_dom(session_id=session_id)
            assert len(dom_nodes) > 0

            shot = adapter.screenshot(session_id=session_id, custom_name="e2e_fixture")
            assert Path(shot.file_path).exists()
            assert shot.file_size_bytes > 0
            assert len(shot.sha256_hash) == 64

        finally:
            adapter.close(session_id=session_id, cleanup_dir=True)
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestAdapterMethodsMocked:
    """Tests all high-level adapter methods with mocked subprocess executor."""

    @pytest.fixture
    def adapter_with_mock(self) -> AgentBrowserAdapter:
        adapter = AgentBrowserAdapter()
        adapter.executor = MagicMock()
        adapter.executor.allowed_domains = []
        adapter.session_manager = MagicMock()
        adapter.session_manager.get_session.return_value = None
        adapter.screenshot_manager = MagicMock()
        return adapter

    def test_navigation_and_actions(self, adapter_with_mock: AgentBrowserAdapter) -> None:
        adapter = adapter_with_mock
        adapter.executor.execute.return_value = CommandResult(
            command=["agent-browser"], returncode=0, stdout="done", stderr="", duration_ms=25.0
        )

        res_nav = adapter.navigate("s1", "https://example.com/login")
        assert res_nav.success
        assert res_nav.action == "navigate"

        res_click = adapter.click("s1", "#btn-login")
        assert res_click.success
        assert res_click.action == "click"

        res_dbl = adapter.dblclick("s1", ".row-item")
        assert res_dbl.success

        res_fill = adapter.fill("s1", "#email", "user@company.com")
        assert res_fill.success

        res_type = adapter.type_text("s1", "#notes", "Automated entry")
        assert res_type.success

        res_select = adapter.select("s1", "#country", "US")
        assert res_select.success

    def test_inspection_methods(self, adapter_with_mock: AgentBrowserAdapter) -> None:
        adapter = adapter_with_mock

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="Page Title", stderr="", duration_ms=10.0
        )
        assert adapter.get_title("s1") == "Page Title"

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="https://app.com/home", stderr="", duration_ms=10.0
        )
        assert adapter.get_url("s1") == "https://app.com/home"

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="Submit", stderr="", duration_ms=10.0
        )
        assert adapter.extract_text("s1", "#btn") == "Submit"

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="primary", stderr="", duration_ms=10.0
        )
        assert adapter.get_attribute("s1", "#btn", "class") == "primary"

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="5", stderr="", duration_ms=10.0
        )
        assert adapter.get_count("s1", "table tr") == 5

    def test_state_checks(self, adapter_with_mock: AgentBrowserAdapter) -> None:
        adapter = adapter_with_mock

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="true", stderr="", duration_ms=10.0, json_data=True
        )
        assert adapter.is_visible("s1", "#modal") is True
        assert adapter.is_enabled("s1", "#btn") is True
        assert adapter.is_checked("s1", "#chk") is True

    def test_wait_and_evaluate(self, adapter_with_mock: AgentBrowserAdapter) -> None:
        adapter = adapter_with_mock

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="ok", stderr="", duration_ms=10.0
        )
        assert adapter.wait_for("s1", 1000) is True

        adapter.executor.execute.return_value = CommandResult(
            command=[], returncode=0, stdout="100", stderr="", duration_ms=10.0, json_data=100
        )
        assert adapter.evaluate("s1", "window.innerWidth") == 100
