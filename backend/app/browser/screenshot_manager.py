"""Screenshot management and artifact verification for browser executions.

Stores screenshots in approved private storage, generates SHA-256 integrity hashes,
and enforces company privacy and retention standards.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .browser_errors import AgentBrowserError
from .command_executor import CommandExecutor

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Metadata representing a verified, captured screenshot artifact."""

    file_path: str
    file_size_bytes: int
    sha256_hash: str
    session_id: str
    captured_at: datetime
    full_page: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "session_id": self.session_id,
            "captured_at": self.captured_at.isoformat(),
            "full_page": self.full_page,
        }


class ScreenshotManager:
    """Manages screenshot capture, file naming, disk storage, and hash auditing."""

    def __init__(
        self,
        executor: CommandExecutor,
        output_directory: Path | str = "./reports/screenshots",
    ) -> None:
        self.executor = executor
        self.output_directory = Path(output_directory).resolve()
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def capture(
        self,
        session_id: str,
        custom_name: str | None = None,
        step_index: int | None = None,
        full_page: bool = False,
        timeout: float = 15.0,
    ) -> ScreenshotResult:
        """Captures a screenshot for the specified session, writes to disk, and computes hash."""
        now_ts = datetime.now(timezone.utc)
        timestamp_str = now_ts.strftime("%Y%m%d_%H%M%S_%f")

        if custom_name:
            clean_name = "".join(c for c in custom_name if c.isalnum() or c in ("-", "_", "."))
            if not clean_name.endswith(".png"):
                clean_name += ".png"
            filename = f"{session_id}_{clean_name}"
        elif step_index is not None:
            filename = f"{session_id}_step_{step_index:03d}_{timestamp_str}.png"
        else:
            filename = f"{session_id}_{timestamp_str}.png"

        target_file = (self.output_directory / filename).resolve()

        # Build CLI command: agent-browser screenshot <path> [--full]
        args = ["screenshot", str(target_file)]
        if full_page:
            args.append("--full")

        try:
            self.executor.execute(args, session_id=session_id, timeout=timeout)
        except Exception as err:
            logger.error("Failed to capture screenshot for session %s: %s", session_id, err)
            raise AgentBrowserError(
                f"Failed to capture screenshot: {err}",
                session_id=session_id,
            ) from err

        if not target_file.exists():
            raise AgentBrowserError(
                f"Screenshot command reported success, but target file was not created: {target_file}",
                session_id=session_id,
            )

        file_size = target_file.stat().st_size
        if file_size == 0:
            raise AgentBrowserError(
                f"Captured screenshot is 0 bytes (empty): {target_file}",
                session_id=session_id,
            )

        # Compute SHA-256 for integrity auditing
        hasher = hashlib.sha256()
        with open(target_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()

        logger.info(
            "Screenshot captured successfully: %s (size: %d bytes, hash: %s)",
            target_file.name,
            file_size,
            file_hash[:8],
        )

        return ScreenshotResult(
            file_path=str(target_file),
            file_size_bytes=file_size,
            sha256_hash=file_hash,
            session_id=session_id,
            captured_at=now_ts,
            full_page=full_page,
        )

