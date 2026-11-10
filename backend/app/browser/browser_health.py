"""Health monitoring and diagnostics for the Agent Browser CLI engine.

Monitors binary availability, version compatibility, daemon status, and session responsiveness.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .command_executor import CommandExecutor

logger = logging.getLogger(__name__)


@dataclass
class BrowserHealthStatus:
    """Diagnostic health summary of the Agent Browser automation subsystem."""

    is_healthy: bool
    version: str | None = None
    cli_path: str = ""
    daemon_running: bool = False
    active_sessions_count: int = 0
    latency_ms: float = 0.0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_healthy": self.is_healthy,
            "version": self.version,
            "cli_path": self.cli_path,
            "daemon_running": self.daemon_running,
            "active_sessions_count": self.active_sessions_count,
            "latency_ms": round(self.latency_ms, 2),
            "error_message": self.error_message,
        }


class BrowserHealthMonitor:
    """Monitors and inspects the health of the local Agent Browser CLI and daemon."""

    def __init__(self, executor: CommandExecutor) -> None:
        self.executor = executor

    def check_health(self, check_daemon: bool = True) -> BrowserHealthStatus:
        """Executes a diagnostic health check against the CLI."""
        cli_path = self.executor.cli_path
        try:
            # Step 1: Version verification
            version_res = self.executor.execute(["--version"], timeout=5.0)
            version_str = version_res.stdout.strip()

            daemon_running = False
            sessions_count = 0

            # Step 2: Daemon inspection if requested
            if check_daemon:
                try:
                    info_res = self.executor.execute(["session", "info"], parse_json=True, timeout=5.0)
                    daemon_running = True
                    if isinstance(info_res.json_data, dict):
                        daemon_running = info_res.json_data.get("daemon_running", True)
                except Exception:
                    # Daemon might not be active if no session opened yet; CLI itself is healthy
                    daemon_running = False

                try:
                    list_res = self.executor.execute(["session", "list"], parse_json=True, timeout=5.0)
                    if isinstance(list_res.json_data, list):
                        sessions_count = len(list_res.json_data)
                except Exception:
                    sessions_count = 0

            return BrowserHealthStatus(
                is_healthy=True,
                version=version_str,
                cli_path=cli_path,
                daemon_running=daemon_running,
                active_sessions_count=sessions_count,
                latency_ms=version_res.duration_ms,
            )

        except Exception as err:
            logger.error("Browser health check failed: %s", err)
            return BrowserHealthStatus(
                is_healthy=False,
                cli_path=cli_path,
                error_message=str(err),
            )

    def is_session_responsive(self, session_id: str, timeout: float = 5.0) -> bool:
        """Verifies if an existing session is responsive by querying its current page URL."""
        try:
            res = self.executor.execute(["get", "url"], session_id=session_id, timeout=timeout)
            return res.is_success
        except Exception:
            return False

