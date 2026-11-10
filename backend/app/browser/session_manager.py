"""Session isolation manager for Agent Browser executions.

Ensures each automated flow or test runs in an isolated browser context
with its own storage, cookies, cache, and lifecycle management.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser_errors import SessionIsolationError
from .command_executor import CommandExecutor

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Represents an active, isolated Agent Browser session."""

    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: str | None = None
    execution_id: str | None = None
    allowed_domains: list[str] = field(default_factory=list)
    session_dir: Path | None = None
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "project_id": self.project_id,
            "execution_id": self.execution_id,
            "allowed_domains": self.allowed_domains,
            "session_dir": str(self.session_dir) if self.session_dir else None,
            "is_active": self.is_active,
        }


class SessionManager:
    """Manages browser sessions and guarantees isolation across concurrent executions."""

    def __init__(
        self,
        executor: CommandExecutor,
        base_storage_dir: Path | str = "./reports",
    ) -> None:
        self.executor = executor
        self.base_storage_dir = Path(base_storage_dir).resolve()
        self._active_sessions: dict[str, BrowserSession] = {}

    def create_session(
        self,
        session_id: str | None = None,
        project_id: str | None = None,
        execution_id: str | None = None,
        allowed_domains: list[str] | None = None,
    ) -> BrowserSession:
        """Creates and tracks a new isolated browser session."""
        # Sanitize session ID to alphanumeric, dashes, and underscores per CLI requirements
        raw_id = session_id or f"sess_{uuid.uuid4().hex[:16]}"
        safe_id = "".join(c for c in raw_id if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            safe_id = f"sess_{uuid.uuid4().hex[:16]}"

        if safe_id in self._active_sessions and self._active_sessions[safe_id].is_active:
            raise SessionIsolationError(
                safe_id,
                "A session with this identifier is already active. Concurrent reuse violates isolation.",
            )

        # Create session-specific scratch directory for downloads and artifacts
        session_dir = self.base_storage_dir / "sessions" / safe_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session = BrowserSession(
            session_id=safe_id,
            project_id=project_id,
            execution_id=execution_id,
            allowed_domains=allowed_domains or self.executor.allowed_domains,
            session_dir=session_dir,
            is_active=True,
        )

        self._active_sessions[safe_id] = session
        logger.info("Initialized isolated Agent Browser session: %s", safe_id)
        return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        """Retrieves session metadata if tracked."""
        return self._active_sessions.get(session_id)

    def list_active_sessions(self) -> list[BrowserSession]:
        """Returns all currently tracked active sessions."""
        return [s for s in self._active_sessions.values() if s.is_active]

    def query_cli_sessions(self) -> list[str]:
        """Queries the agent-browser CLI daemon for live registered sessions."""
        try:
            res = self.executor.execute(["session", "list"], parse_json=True, timeout=10.0)
            if isinstance(res.json_data, list):
                return [str(item) for item in res.json_data]
            if isinstance(res.json_data, dict) and "sessions" in res.json_data:
                return [str(item) for item in res.json_data["sessions"]]
            # Fallback parsing from stdout lines
            return [line.strip() for line in res.stdout.splitlines() if line.strip() and not line.startswith("=")]
        except Exception as err:
            logger.warning("Failed to query CLI sessions: %s", err)
            return list(self._active_sessions.keys())

    def close_session(self, session_id: str, cleanup_dir: bool = False) -> None:
        """Gracefully closes the browser session in the CLI daemon and cleans up state."""
        logger.info("Closing Agent Browser session: %s", session_id)
        try:
            self.executor.execute(["close"], session_id=session_id, timeout=10.0)
        except Exception as err:
            logger.warning("Error closing session '%s' via CLI: %s", session_id, err)

        session = self._active_sessions.get(session_id)
        if session:
            session.is_active = False
            if cleanup_dir and session.session_dir and session.session_dir.exists():
                try:
                    shutil.rmtree(session.session_dir, ignore_errors=True)
                except Exception as clean_err:
                    logger.warning("Failed to remove session directory: %s", clean_err)

    def close_all(self) -> None:
        """Closes all active sessions and signals the CLI daemon to terminate."""
        logger.info("Terminating all active Agent Browser sessions...")
        for sess_id in list(self._active_sessions.keys()):
            self.close_session(sess_id)
        try:
            self.executor.execute(["close", "--all"], timeout=15.0)
        except Exception as err:
            logger.warning("Notice on close --all: %s", err)

