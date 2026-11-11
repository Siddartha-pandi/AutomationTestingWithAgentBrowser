"""Agent Browser integration package.

Provides a deterministic, safe, subprocess-based Python adapter for Agent Browser CLI.
Zero AI processing, strict timeout handling, session isolation, and state verification.
"""

from .agent_browser import ActionResult, AgentBrowserAdapter
from .browser_errors import (
    AgentBrowserError,
    BrowserCommandError,
    BrowserNotFoundError,
    BrowserTimeoutError,
    ElementNotFoundError,
    HealthCheckFailedError,
    NavigationSecurityError,
    SessionIsolationError,
)
from .browser_health import BrowserHealthMonitor, BrowserHealthStatus
from .command_executor import CommandExecutor, CommandResult
from .screenshot_manager import ScreenshotManager, ScreenshotResult
from .session_manager import BrowserSession, SessionManager

__all__ = [
    "ActionResult",
    "AgentBrowserAdapter",
    "AgentBrowserError",
    "BrowserCommandError",
    "BrowserNotFoundError",
    "BrowserTimeoutError",
    "ElementNotFoundError",
    "HealthCheckFailedError",
    "NavigationSecurityError",
    "SessionIsolationError",
    "BrowserHealthMonitor",
    "BrowserHealthStatus",
    "CommandExecutor",
    "CommandResult",
    "ScreenshotManager",
    "ScreenshotResult",
    "BrowserSession",
    "SessionManager",
]

