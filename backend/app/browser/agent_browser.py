"""Primary Python Adapter for Agent Browser CLI automation.

Exposes deterministic, type-safe methods for browser interaction,
session management, and verification without any AI dependencies.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .browser_errors import (
    AgentBrowserError,
    BrowserCommandError,
    BrowserTimeoutError,
    ElementNotFoundError,
    NavigationSecurityError,
)
from .browser_health import BrowserHealthMonitor, BrowserHealthStatus
from .command_executor import CommandExecutor, CommandResult
from .screenshot_manager import ScreenshotManager, ScreenshotResult
from .session_manager import BrowserSession, SessionManager

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Standard outcome of a browser interaction action."""

    success: bool
    action: str
    target: str
    duration_ms: float
    output: str = ""
    error_message: str | None = None
    state_after: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "target": self.target,
            "duration_ms": round(self.duration_ms, 2),
            "output": self.output,
            "error_message": self.error_message,
            "state_after": self.state_after,
        }


class AgentBrowserAdapter:
    """High-level Python adapter communicating with the Agent Browser CLI engine."""

    def __init__(
        self,
        cli_path: str | None = None,
        default_timeout: float = 30.0,
        base_storage_dir: str = "./reports",
        allowed_domains: list[str] | None = None,
    ) -> None:
        self.executor = CommandExecutor(
            cli_path=cli_path,
            default_timeout=default_timeout,
            allowed_domains=allowed_domains or [],
            agent_home_dir=f"{base_storage_dir}/agent_home",
        )
        self.session_manager = SessionManager(
            executor=self.executor,
            base_storage_dir=base_storage_dir,
        )
        self.health_monitor = BrowserHealthMonitor(executor=self.executor)
        self.screenshot_manager = ScreenshotManager(
            executor=self.executor,
            output_directory=f"{base_storage_dir}/screenshots",
        )

    # -------------------------------------------------------------------------
    # Lifecycle & Sessions
    # -------------------------------------------------------------------------

    def launch(
        self,
        session_id: str | None = None,
        project_id: str | None = None,
        execution_id: str | None = None,
        allowed_domains: list[str] | None = None,
    ) -> BrowserSession:
        """Initializes a new isolated browser session."""
        session = self.session_manager.create_session(
            session_id=session_id,
            project_id=project_id,
            execution_id=execution_id,
            allowed_domains=allowed_domains,
        )
        logger.info("Launched isolated session: %s", session.session_id)
        return session

    def close(self, session_id: str, cleanup_dir: bool = False) -> None:
        """Closes the specified browser session."""
        self.session_manager.close_session(session_id=session_id, cleanup_dir=cleanup_dir)

    def close_all(self) -> None:
        """Closes all browser sessions and terminates the daemon."""
        self.session_manager.close_all()

    def get_health(self) -> BrowserHealthStatus:
        """Returns health diagnostics of the Agent Browser subsystem."""
        return self.health_monitor.check_health()

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def navigate(
        self,
        session_id: str,
        url: str,
        timeout: float = 30.0,
    ) -> ActionResult:
        """Navigates to the specified URL after verifying security policy and domain allowlist."""
        # Security: validate URL structure and allowed domains
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise NavigationSecurityError(url, "Only http and https schemes are permitted.")

        session = self.session_manager.get_session(session_id)
        active_domains = session.allowed_domains if session else self.executor.allowed_domains
        if active_domains:
            hostname = parsed.hostname or ""
            allowed = False
            for pattern in active_domains:
                pattern = pattern.strip().lower()
                if pattern in ("*", "*.*", "all"):
                    allowed = True
                    break
                if pattern.startswith("*."):
                    base = pattern[2:]
                    if hostname == base or hostname.endswith(f".{base}"):
                        allowed = True
                        break
                elif hostname == pattern:
                    allowed = True
                    break
            if not allowed:
                raise NavigationSecurityError(
                    url,
                    f"Domain '{hostname}' is not in approved allowed domains list: {active_domains}",
                )

        res = self.executor.execute(["open", url], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="navigate",
            target=url,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    # -------------------------------------------------------------------------
    # DOM Extraction & Snapshots
    # -------------------------------------------------------------------------

    def snapshot(
        self,
        session_id: str,
        interactive_only: bool = True,
        compact: bool = True,
        depth: int | None = None,
        selector: str | None = None,
    ) -> dict[str, Any]:
        """Extracts the accessibility tree snapshot with references (@e1, @e2)."""
        args = ["snapshot"]
        if interactive_only:
            args.append("-i")
        if compact:
            args.append("-c")
        if depth is not None:
            args.extend(["-d", str(depth)])
        if selector:
            args.extend(["-s", selector])

        res = self.executor.execute(args, session_id=session_id, parse_json=True)
        if isinstance(res.json_data, dict):
            return res.json_data
        return {"raw_snapshot": res.stdout, "nodes": []}

    def extract_dom(
        self,
        session_id: str,
        selector: str | None = None,
        max_depth: int = 10,
    ) -> list[dict[str, Any]]:
        """Deep deterministic DOM extraction of elements, hierarchy, ARIA properties, and labels.

        Uses base64-encoded deterministic JavaScript via `eval -b` to guarantee zero escaping issues.
        """
        js_extractor = f"""(() => {{
            const root = {f'document.querySelector({json.dumps(selector)}) || document.body' if selector else 'document.body'};
            if (!root) return [];

            function isVisible(el) {{
                if (!el || el.nodeType !== 1) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0' && el.offsetWidth > 0 && el.offsetHeight > 0;
            }}

            const elements = [];
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null);
            let current = walker.currentNode;
            let counter = 0;

            while (current && counter < 500) {{
                counter++;
                const el = current;
                const tag = el.tagName.toLowerCase();
                if (['script', 'style', 'noscript', 'svg', 'path'].includes(tag)) {{
                    current = walker.nextNode();
                    continue;
                }}

                const rect = el.getBoundingClientRect();
                const visible = isVisible(el);

                // Collect stable attributes
                const stableAttrs = {{}};
                for (const attr of ['id', 'name', 'data-testid', 'type', 'role', 'aria-label', 'placeholder', 'title', 'href', 'value']) {{
                    if (el.hasAttribute(attr)) {{
                        stableAttrs[attr] = el.getAttribute(attr);
                    }}
                }}

                // Associated label
                let associatedLabel = null;
                if (el.id) {{
                    const labelEl = document.querySelector(`label[for="${{el.id}}"]`);
                    if (labelEl) associatedLabel = labelEl.innerText.trim();
                }}
                if (!associatedLabel && el.closest('label')) {{
                    associatedLabel = el.closest('label').innerText.trim();
                }}

                // Ancestors path
                const ancestors = [];
                let parent = el.parentElement;
                let depth = 0;
                while (parent && parent !== document.body && depth < 5) {{
                    ancestors.push({{
                        tag: parent.tagName.toLowerCase(),
                        id: parent.id || null,
                        role: parent.getAttribute('role') || null,
                        className: parent.className ? String(parent.className).slice(0, 50) : null
                    }});
                    parent = parent.parentElement;
                    depth++;
                }}

                // Sibling info
                const prevSibling = el.previousElementSibling ? el.previousElementSibling.tagName.toLowerCase() : null;
                const nextSibling = el.nextElementSibling ? el.nextElementSibling.tagName.toLowerCase() : null;

                // Direct or visible text
                let directText = '';
                for (const child of el.childNodes) {{
                    if (child.nodeType === 3) directText += child.nodeValue;
                }}
                directText = directText.trim().slice(0, 200);

                elements.push({{
                    tag: tag,
                    role: el.getAttribute('role') || null,
                    aria_label: el.getAttribute('aria-label') || null,
                    text: directText || (el.innerText ? el.innerText.trim().slice(0, 200) : ''),
                    stable_attributes: stableAttrs,
                    associated_label: associatedLabel,
                    ancestors: ancestors,
                    siblings: {{ prev: prevSibling, next: nextSibling }},
                    is_visible: visible,
                    is_enabled: !el.disabled,
                    box: {{ x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) }}
                }});

                current = walker.nextNode();
            }}
            return elements;
        }})();"""

        encoded_js = base64.b64encode(js_extractor.encode("utf-8")).decode("utf-8")
        res = self.executor.execute(["eval", "-b", encoded_js], session_id=session_id, parse_json=True)
        if isinstance(res.json_data, dict) and "data" in res.json_data and "result" in res.json_data["data"]:
            result = res.json_data["data"]["result"]
            if isinstance(result, list):
                return result
        if isinstance(res.json_data, list):
            return res.json_data
        return []

    # -------------------------------------------------------------------------
    # Core User Actions
    # -------------------------------------------------------------------------

    def click(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Clicks an element by selector or reference."""
        res = self.executor.execute(["click", selector], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="click",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def dblclick(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Double clicks an element by selector or reference."""
        res = self.executor.execute(["dblclick", selector], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="dblclick",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def fill(self, session_id: str, selector: str, text: str, timeout: float = 15.0) -> ActionResult:
        """Clears and fills an input element."""
        res = self.executor.execute(["fill", selector, text], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="fill",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def type_text(self, session_id: str, selector: str, text: str, timeout: float = 15.0) -> ActionResult:
        """Types text into an element keystroke by keystroke."""
        res = self.executor.execute(["type", selector, text], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="type",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def select(self, session_id: str, selector: str, value: str, timeout: float = 15.0) -> ActionResult:
        """Selects an option in a dropdown element by value or visible label."""
        res = self.executor.execute(["select", selector, value], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="select",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def hover(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Hovers over the specified element."""
        res = self.executor.execute(["hover", selector], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="hover",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def right_click(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Performs a context menu / right click on the target element."""
        res = self.executor.execute(["click", selector, "--button", "right"], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="right_click",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def check(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Checks a checkbox or radio button if not already checked."""
        res = self.executor.execute(["check", selector], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="check",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def uncheck(self, session_id: str, selector: str, timeout: float = 15.0) -> ActionResult:
        """Unchecks a checkbox if currently checked."""
        res = self.executor.execute(["uncheck", selector], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="uncheck",
            target=selector,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def scroll(
        self,
        session_id: str,
        direction: str = "down",
        amount: int = 400,
        selector: str | None = None,
        timeout: float = 15.0,
    ) -> ActionResult:
        """Scrolls the page or element in the specified direction."""
        args = ["scroll", direction, str(amount)]
        if selector:
            args.extend(["-s", selector])
        res = self.executor.execute(args, session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="scroll",
            target=selector or direction,
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def back(self, session_id: str, timeout: float = 15.0) -> ActionResult:
        """Navigates back in browser history."""
        res = self.executor.execute(["back"], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="back",
            target="history.back",
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def forward(self, session_id: str, timeout: float = 15.0) -> ActionResult:
        """Navigates forward in browser history."""
        res = self.executor.execute(["forward"], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="forward",
            target="history.forward",
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    def reload(self, session_id: str, timeout: float = 15.0) -> ActionResult:
        """Reloads the current page."""
        res = self.executor.execute(["reload"], session_id=session_id, timeout=timeout)
        return ActionResult(
            success=res.is_success,
            action="reload",
            target="page.reload",
            duration_ms=res.duration_ms,
            output=res.stdout.strip(),
        )

    # -------------------------------------------------------------------------
    # Getters & Inspection
    # -------------------------------------------------------------------------

    def extract_text(self, session_id: str, selector: str, timeout: float = 10.0) -> str:
        """Retrieves inner text content of an element."""
        res = self.executor.execute(["get", "text", selector], session_id=session_id, timeout=timeout)
        return res.stdout.strip()

    def get_attribute(self, session_id: str, selector: str, attr_name: str, timeout: float = 10.0) -> str | None:
        """Retrieves a specific attribute value of an element."""
        res = self.executor.execute(["get", "attr", selector, attr_name], session_id=session_id, timeout=timeout)
        val = res.stdout.strip()
        return None if val in ("null", "undefined", "") else val

    def get_value(self, session_id: str, selector: str, timeout: float = 10.0) -> str:
        """Retrieves the value of an input element."""
        res = self.executor.execute(["get", "value", selector], session_id=session_id, timeout=timeout)
        return res.stdout.strip()

    def get_html(self, session_id: str, selector: str, timeout: float = 10.0) -> str:
        """Retrieves inner HTML of an element."""
        res = self.executor.execute(["get", "html", selector], session_id=session_id, timeout=timeout)
        return res.stdout.strip()

    def get_title(self, session_id: str, timeout: float = 10.0) -> str:
        """Retrieves the current page title."""
        res = self.executor.execute(["get", "title"], session_id=session_id, timeout=timeout)
        return res.stdout.strip()

    def get_url(self, session_id: str, timeout: float = 10.0) -> str:
        """Retrieves the current browser URL."""
        res = self.executor.execute(["get", "url"], session_id=session_id, timeout=timeout)
        return res.stdout.strip()

    def get_count(self, session_id: str, selector: str, timeout: float = 10.0) -> int:
        """Counts elements matching the given selector."""
        res = self.executor.execute(["get", "count", selector], session_id=session_id, timeout=timeout)
        try:
            return int(res.stdout.strip())
        except ValueError:
            return 0

    # -------------------------------------------------------------------------
    # State Verifications (True / False)
    # -------------------------------------------------------------------------

    def is_visible(self, session_id: str, selector: str, timeout: float = 10.0) -> bool:
        """Determines if the target element is visible."""
        try:
            res = self.executor.execute(["is", "visible", selector], session_id=session_id, timeout=timeout, parse_json=True)
            if isinstance(res.json_data, bool):
                return res.json_data
            return "true" in res.stdout.lower()
        except Exception:
            return False

    def is_enabled(self, session_id: str, selector: str, timeout: float = 10.0) -> bool:
        """Determines if the target element is enabled."""
        try:
            res = self.executor.execute(["is", "enabled", selector], session_id=session_id, timeout=timeout, parse_json=True)
            if isinstance(res.json_data, bool):
                return res.json_data
            return "true" in res.stdout.lower()
        except Exception:
            return False

    def is_checked(self, session_id: str, selector: str, timeout: float = 10.0) -> bool:
        """Determines if the target checkbox or radio is checked."""
        try:
            res = self.executor.execute(["is", "checked", selector], session_id=session_id, timeout=timeout, parse_json=True)
            if isinstance(res.json_data, bool):
                return res.json_data
            return "true" in res.stdout.lower()
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Waiting & Synchronization
    # -------------------------------------------------------------------------

    def wait_for(self, session_id: str, target: str | int, timeout_ms: int = 10000) -> bool:
        """Waits for an element selector or duration in milliseconds."""
        timeout_seconds = (timeout_ms / 1000.0) + 5.0
        try:
            res = self.executor.execute(["wait", str(target)], session_id=session_id, timeout=timeout_seconds)
            return res.is_success
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Screenshots
    # -------------------------------------------------------------------------

    def screenshot(
        self,
        session_id: str,
        custom_name: str | None = None,
        step_index: int | None = None,
        full_page: bool = False,
        timeout: float = 15.0,
    ) -> ScreenshotResult:
        """Captures a screenshot artifact and calculates SHA-256 integrity hash."""
        return self.screenshot_manager.capture(
            session_id=session_id,
            custom_name=custom_name,
            step_index=step_index,
            full_page=full_page,
            timeout=timeout,
        )

    # -------------------------------------------------------------------------
    # JavaScript Evaluation
    # -------------------------------------------------------------------------

    def evaluate(self, session_id: str, js_code: str, timeout: float = 15.0) -> Any:
        """Executes JavaScript deterministically using base64 encoding to prevent shell escaping."""
        encoded = base64.b64encode(js_code.encode("utf-8")).decode("utf-8")
        res = self.executor.execute(["eval", "-b", encoded], session_id=session_id, timeout=timeout, parse_json=True)
        if isinstance(res.json_data, dict) and "data" in res.json_data and "result" in res.json_data["data"]:
            return res.json_data["data"]["result"]
        return res.json_data if res.json_data is not None else res.stdout.strip()

    # -------------------------------------------------------------------------
    # State Verification Before Retry Policy
    # -------------------------------------------------------------------------

    def verify_state_before_retry(
        self,
        session_id: str,
        expected_type: str,
        target: str,
        expected_value: Any = None,
    ) -> bool:
        """Checks if a potentially timed-out action already took effect.

        Guarantees that blind retries do not trigger duplicate submissions or side effects.
        """
        try:
            if expected_type == "url_contains":
                current_url = self.get_url(session_id)
                return str(expected_value) in current_url
            if expected_type == "element_visible":
                return self.is_visible(session_id, target)
            if expected_type == "element_hidden":
                return not self.is_visible(session_id, target)
            if expected_type == "value_equals":
                val = self.get_value(session_id, target)
                return val == str(expected_value)
            if expected_type == "text_contains":
                txt = self.extract_text(session_id, target)
                return str(expected_value) in txt
        except Exception as err:
            logger.warning("Error verifying state before retry: %s", err)
        return False
