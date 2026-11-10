"""Subprocess execution engine for Agent Browser CLI.

Handles process lifecycle, timeouts, structured output parsing, environment isolation,
and error classification with zero AI dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .browser_errors import (
    BrowserCommandError,
    BrowserNotFoundError,
    BrowserTimeoutError,
    ElementNotFoundError,
)

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Structured result of an Agent Browser CLI invocation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    session_id: str | None = None
    json_data: Any | None = None
    timed_out: bool = False

    @property
    def is_success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": " ".join(self.command),
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": round(self.duration_ms, 2),
            "session_id": self.session_id,
            "has_json": self.json_data is not None,
            "timed_out": self.timed_out,
        }


class CommandExecutor:
    """Executes Agent Browser CLI commands securely with isolation and strict timeouts."""

    DEFAULT_TIMEOUT: float = 30.0

    def __init__(
        self,
        cli_path: str | None = None,
        default_timeout: float = DEFAULT_TIMEOUT,
        allowed_domains: list[str] | None = None,
        agent_home_dir: Path | str | None = None,
    ) -> None:
        self.cli_path = self._resolve_cli_path(cli_path)
        self.default_timeout = default_timeout
        self.allowed_domains = allowed_domains or []
        self.agent_home_dir = (
            Path(agent_home_dir).resolve()
            if agent_home_dir
            else Path("./reports/agent_home").resolve()
        )
        self.agent_home_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _resolve_cli_path(cls, explicit_path: str | None) -> str:
        """Locates the agent-browser binary on Windows or POSIX systems."""
        candidate = explicit_path or os.getenv("AGENT_BROWSER_CLI")
        if candidate:
            resolved = shutil.which(candidate) or candidate
            if Path(resolved).exists() or shutil.which(candidate):
                return resolved

        # Windows-specific search paths
        if os.name == "nt":
            npm_path = Path(os.environ.get("APPDATA", "")) / "npm" / "agent-browser.cmd"
            if npm_path.exists():
                return str(npm_path)

            npm_ps1 = Path(os.environ.get("APPDATA", "")) / "npm" / "agent-browser.ps1"
            if npm_ps1.exists():
                return str(npm_ps1)

        # Standard PATH lookup
        found = shutil.which("agent-browser")
        if found:
            return found

        # Fallback to direct name (will raise BrowserNotFoundError on execution if missing)
        return "agent-browser.cmd" if os.name == "nt" else "agent-browser"

    @classmethod
    def _resolve_executable_path(cls) -> str | None:
        """Locates system Chrome/Chromium executable on Windows or Linux."""
        candidate = (
            os.getenv("AGENT_BROWSER_EXECUTABLE_PATH")
            or os.getenv("CHROME_BIN")
            or os.getenv("CHROMIUM_PATH")
        )
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return str(candidate)

        # Linux common paths
        if os.name != "nt":
            for p in (
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/snap/bin/chromium",
            ):
                if Path(p).exists() or shutil.which(p):
                    return p

        # Windows common paths
        if os.name == "nt":
            for env_key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
                base = os.environ.get(env_key)
                if base:
                    for rel in (
                        "Google/Chrome/Application/chrome.exe",
                        "Microsoft/Edge/Application/msedge.exe",
                    ):
                        target = Path(base) / rel
                        if target.exists():
                            return str(target)
        return None

    def execute(
        self,
        args: list[str],
        session_id: str | None = None,
        timeout: float | None = None,
        parse_json: bool = False,
        extra_env: dict[str, str] | None = None,
        stdin_input: str | None = None,
    ) -> CommandResult:
        """Executes an agent-browser command with session isolation and timeout protection.

        Args:
            args: Command arguments (e.g. ['open', 'https://example.com'] or ['snapshot', '-i']).
            session_id: Optional session identifier for isolated browser context.
            timeout: Maximum seconds to wait before terminating the process.
            parse_json: When True, ensures --json flag is passed and parses JSON output.
            extra_env: Additional environment variables for the execution.
            stdin_input: Optional text input piped to stdin.

        Returns:
            CommandResult containing stdout, stderr, execution duration, and parsed JSON.

        Raises:
            BrowserNotFoundError: If CLI executable cannot be found.
            BrowserTimeoutError: If process exceeds timeout limit (prohibits blind retry).
            ElementNotFoundError: If selector failed to resolve.
            BrowserCommandError: For general non-zero return codes.
        """
        resolved_timeout = timeout if timeout is not None else self.default_timeout

        cmd = [self.cli_path]
        if session_id:
            cmd.extend(["--session", session_id])
        exec_path = self._resolve_executable_path()
        if exec_path and "--executable-path" not in args:
            cmd.extend(["--executable-path", exec_path])
        if parse_json and "--json" not in args:
            cmd.append("--json")
        cmd.extend(args)

        # Build clean environment with security policies
        env = os.environ.copy()
        if self.agent_home_dir:
            env["USERPROFILE"] = str(self.agent_home_dir)
            env["HOME"] = str(self.agent_home_dir)
        if self.allowed_domains:
            env["AGENT_BROWSER_ALLOWED_DOMAINS"] = ",".join(self.allowed_domains)
        if session_id:
            env["AGENT_BROWSER_SESSION"] = session_id
        if extra_env:
            env.update(extra_env)

        start_time = time.perf_counter()
        logger.debug("Executing Agent Browser CLI: %s (timeout: %.1fs)", " ".join(cmd), resolved_timeout)

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin_input is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            try:
                stdout, stderr = process.communicate(
                    input=stdin_input,
                    timeout=resolved_timeout,
                )
            except subprocess.TimeoutExpired:
                # Terminate aggressively to prevent orphaned browser worker
                process.kill()
                partial_out, partial_err = process.communicate()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.error("Agent Browser command timed out: %s", " ".join(cmd))
                raise BrowserTimeoutError(
                    command=cmd,
                    timeout_seconds=resolved_timeout,
                    session_id=session_id,
                    partial_stdout=partial_out,
                    partial_stderr=partial_err,
                ) from None

        except FileNotFoundError as err:
            raise BrowserNotFoundError(cli_path=self.cli_path) from err

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        returncode = process.returncode

        json_data: Any | None = None
        if parse_json and stdout.strip():
            # 1. Try direct full parse
            try:
                json_data = json.loads(stdout.strip())
            except json.JSONDecodeError:
                # 2. Try scanning line-by-line from earliest possible valid JSON (skipping CLI banner/log lines)
                lines = stdout.strip().splitlines()
                for i in range(len(lines)):
                    candidate = "\n".join(lines[i:]).strip()
                    if candidate.startswith(("{", "[")):
                        try:
                            json_data = json.loads(candidate)
                            break
                        except json.JSONDecodeError:
                            continue

        result = CommandResult(
            command=cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            session_id=session_id,
            json_data=json_data,
        )

        # Classify errors
        if returncode != 0:
            error_text = f"{stderr} {stdout}".lower()

            # Automatic recovery: install Chrome if missing and retry once
            if ("chrome not found" in error_text or "auto-launch failed" in error_text) and not getattr(self, "_install_attempted", False):
                self._install_attempted = True
                logger.warning("Chrome not found for agent-browser. Running 'agent-browser install'...")
                try:
                    install_proc = subprocess.run(
                        [self.cli_path, "install"],
                        timeout=180,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    logger.info("agent-browser install finished with exit code %s", install_proc.returncode)
                    return self.execute(
                        args=args,
                        session_id=session_id,
                        timeout=timeout,
                        parse_json=parse_json,
                        extra_env=extra_env,
                        stdin_input=stdin_input,
                    )
                except Exception as install_err:
                    logger.error("Automatic agent-browser install failed: %s", install_err)

            if any(term in error_text for term in ["element not found", "no element", "cannot find", "ambiguous"]):
                selector_hint = args[1] if len(args) > 1 else "unknown"
                raise ElementNotFoundError(
                    selector=selector_hint,
                    command=cmd,
                    returncode=returncode,
                    stdout=stdout,
                    stderr=stderr,
                    session_id=session_id,
                )
            raise BrowserCommandError(
                command=cmd,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                session_id=session_id,
            )

        return result
