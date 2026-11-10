"""Structured error hierarchy for Agent Browser CLI operations.

Every exception carries context (command, session_id, return code, stdout, stderr)
to prevent ambiguous silent failures and enable deterministic recovery policies.
"""

from __future__ import annotations

from typing import Any


class AgentBrowserError(Exception):
    """Base exception for all Agent Browser errors."""

    def __init__(self, message: str, session_id: str | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.session_id = session_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "session_id": self.session_id,
            "details": self.details,
        }


class BrowserNotFoundError(AgentBrowserError):
    """Raised when the Agent Browser CLI executable cannot be found in PATH or config."""

    def __init__(self, cli_path: str, message: str | None = None) -> None:
        msg = message or f"Agent Browser CLI executable not found at: '{cli_path}'"
        super().__init__(msg, details={"cli_path": cli_path})
        self.cli_path = cli_path


class BrowserTimeoutError(AgentBrowserError):
    """Raised when a CLI command exceeds its explicit timeout window.

    Explicitly prevents blind retries without prior state verification.
    """

    def __init__(
        self,
        command: list[str],
        timeout_seconds: float,
        session_id: str | None = None,
        partial_stdout: str = "",
        partial_stderr: str = "",
    ) -> None:
        cmd_str = " ".join(command)
        message = (
            f"Agent Browser command timed out after {timeout_seconds:.1f}s: {cmd_str}. "
            "Blind retry prohibited: browser state must be verified before retrying."
        )
        super().__init__(
            message,
            session_id=session_id,
            details={
                "command": cmd_str,
                "timeout_seconds": timeout_seconds,
                "partial_stdout": partial_stdout[:500],
                "partial_stderr": partial_stderr[:500],
            },
        )
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.partial_stdout = partial_stdout
        self.partial_stderr = partial_stderr


class BrowserCommandError(AgentBrowserError):
    """Raised when an Agent Browser CLI command exits with a non-zero exit code."""

    def __init__(
        self,
        command: list[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
        session_id: str | None = None,
    ) -> None:
        cmd_str = " ".join(command)
        err_excerpt = (stderr.strip() or stdout.strip() or "Unknown CLI error")[:400]
        message = f"Agent Browser command failed (exit code {returncode}): {cmd_str}\nError: {err_excerpt}"
        super().__init__(
            message,
            session_id=session_id,
            details={
                "command": cmd_str,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            },
        )
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ElementNotFoundError(BrowserCommandError):
    """Raised when a requested element selector or reference cannot be found or is ambiguous."""

    def __init__(
        self,
        selector: str,
        command: list[str],
        returncode: int = 1,
        stdout: str = "",
        stderr: str = "",
        session_id: str | None = None,
    ) -> None:
        super().__init__(command, returncode, stdout, stderr, session_id=session_id)
        self.selector = selector
        self.message = f"Element not found or ambiguous for selector: '{selector}'"
        self.details["selector"] = selector


class SessionIsolationError(AgentBrowserError):
    """Raised when session isolation is compromised, conflicting, or fails to clean up."""

    def __init__(self, session_id: str, reason: str) -> None:
        super().__init__(
            f"Session isolation failure for session '{session_id}': {reason}",
            session_id=session_id,
            details={"reason": reason},
        )
        self.reason = reason


class HealthCheckFailedError(AgentBrowserError):
    """Raised when browser daemon health checks fail or daemon is unresponsive."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Browser health check failed: {reason}", details=details)
        self.reason = reason


class NavigationSecurityError(AgentBrowserError):
    """Raised when a requested URL violates domain allowlists, company policy, or SSRF rules."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            f"Navigation blocked by company security policy for URL '{url}': {reason}",
            details={"url": url, "reason": reason},
        )
        self.url = url
        self.reason = reason

