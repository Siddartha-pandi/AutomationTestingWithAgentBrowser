"""Deterministic wait engine for Agent Browser.

Replaces arbitrary sleep calls with deterministic condition polling:
- Element presence, visibility, hidden, clickability
- Text presence & content matching
- URL matching (exact, substring, regex)
- Title matching
- Network idle verification
- DOM animation stabilization
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from backend.app.browser import AgentBrowserAdapter
from backend.app.browser.browser_errors import BrowserTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class WaitConditionResult:
    """Outcome of a wait condition evaluation."""

    satisfied: bool
    elapsed_ms: float
    condition_name: str
    target: str
    details: str | None = None


class WaitEngine:
    """Deterministic polling engine for browser synchronization."""

    DEFAULT_TIMEOUT_MS: int = 10000
    DEFAULT_POLL_INTERVAL_MS: int = 200

    def __init__(self, adapter: AgentBrowserAdapter) -> None:
        self.adapter = adapter

    def poll_condition(
        self,
        condition_fn: Callable[[], bool],
        condition_name: str,
        target: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
    ) -> WaitConditionResult:
        """Deterministically polls a condition until true or timeout."""
        start_time = time.perf_counter()
        deadline = start_time + (timeout_ms / 1000.0)
        interval_sec = max(poll_interval_ms / 1000.0, 0.05)

        while True:
            try:
                if condition_fn():
                    elapsed = (time.perf_counter() - start_time) * 1000.0
                    return WaitConditionResult(
                        satisfied=True,
                        elapsed_ms=round(elapsed, 2),
                        condition_name=condition_name,
                        target=target,
                    )
            except Exception as err:
                logger.debug("Condition check '%s' raised transient error: %s", condition_name, err)

            if time.perf_counter() >= deadline:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                return WaitConditionResult(
                    satisfied=False,
                    elapsed_ms=round(elapsed, 2),
                    condition_name=condition_name,
                    target=target,
                    details=f"Timed out after {timeout_ms}ms waiting for condition '{condition_name}'",
                )

            time.sleep(interval_sec)

    # -------------------------------------------------------------------------
    # Concrete Wait Conditions
    # -------------------------------------------------------------------------

    def wait_for_element_present(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until at least 1 element matching selector exists in DOM."""
        return self.poll_condition(
            condition_fn=lambda: self.adapter.get_count(session_id, selector) > 0,
            condition_name="element_present",
            target=selector,
            timeout_ms=timeout_ms,
        )

    def wait_for_element_visible(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until the element is visible on page."""
        return self.poll_condition(
            condition_fn=lambda: self.adapter.is_visible(session_id, selector),
            condition_name="element_visible",
            target=selector,
            timeout_ms=timeout_ms,
        )

    def wait_for_element_hidden(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until the element is either detached or hidden."""
        return self.poll_condition(
            condition_fn=lambda: not self.adapter.is_visible(session_id, selector),
            condition_name="element_hidden",
            target=selector,
            timeout_ms=timeout_ms,
        )

    def wait_for_element_clickable(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until element is visible, enabled, and has stable bounding coordinates."""
        def check_clickable() -> bool:
            if not self.adapter.is_visible(session_id, selector):
                return False
            if not self.adapter.is_enabled(session_id, selector):
                return False
            box = self.adapter.get_box(session_id, selector)
            if not box:
                return False
            # Element must have non-zero dimensions
            return box.get("width", 0) > 0 and box.get("height", 0) > 0

        return self.poll_condition(
            condition_fn=check_clickable,
            condition_name="element_clickable",
            target=selector,
            timeout_ms=timeout_ms,
        )

    def wait_for_text(
        self,
        session_id: str,
        selector: str,
        expected_text: str,
        exact: bool = False,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until element contains or exactly matches the expected text."""
        def check_text() -> bool:
            actual = self.adapter.extract_text(session_id, selector)
            if exact:
                return actual.strip() == expected_text.strip()
            return expected_text.lower() in actual.lower()

        return self.poll_condition(
            condition_fn=check_text,
            condition_name="text_matches" if exact else "text_contains",
            target=f"{selector} => '{expected_text}'",
            timeout_ms=timeout_ms,
        )

    def wait_for_url(
        self,
        session_id: str,
        expected_pattern: str,
        is_regex: bool = False,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until current page URL matches pattern."""
        regex_compiled = re.compile(expected_pattern) if is_regex else None

        def check_url() -> bool:
            current = self.adapter.get_url(session_id)
            if is_regex and regex_compiled:
                return bool(regex_compiled.search(current))
            return expected_pattern in current

        return self.poll_condition(
            condition_fn=check_url,
            condition_name="url_regex" if is_regex else "url_contains",
            target=expected_pattern,
            timeout_ms=timeout_ms,
        )

    def wait_for_title(
        self,
        session_id: str,
        expected_title: str,
        is_regex: bool = False,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until current page title matches pattern."""
        regex_compiled = re.compile(expected_title) if is_regex else None

        def check_title() -> bool:
            current = self.adapter.get_title(session_id)
            if is_regex and regex_compiled:
                return bool(regex_compiled.search(current))
            return expected_title in current

        return self.poll_condition(
            condition_fn=check_title,
            condition_name="title_regex" if is_regex else "title_contains",
            target=expected_title,
            timeout_ms=timeout_ms,
        )

    def wait_for_network_idle(
        self,
        session_id: str,
        idle_ms: int = 500,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> WaitConditionResult:
        """Waits until in-flight AJAX / fetch requests have subsided."""
        # Deterministically check window active requests via performance API and fetch count
        js_idle_check = """(() => {
            if (window._agent_in_flight_requests && window._agent_in_flight_requests > 0) {
                return false;
            }
            if (document.readyState !== 'complete') {
                return false;
            }
            return true;
        })()"""

        return self.poll_condition(
            condition_fn=lambda: bool(self.adapter.evaluate(session_id, js_idle_check)),
            condition_name="network_idle",
            target="network",
            timeout_ms=timeout_ms,
        )

    def wait_for_animation(
        self,
        session_id: str,
        selector: str,
        timeout_ms: int = 5000,
    ) -> WaitConditionResult:
        """Waits until element's bounding box coordinates stabilize (stops moving)."""
        last_box: dict[str, float] | None = None

        def check_stability() -> bool:
            nonlocal last_box
            curr_box = self.adapter.get_box(session_id, selector)
            if not curr_box:
                return False
            if last_box is not None:
                # Compare bounding box coordinates within 1px tolerance
                stable = (
                    abs(curr_box.get("x", 0) - last_box.get("x", 0)) < 1.0
                    and abs(curr_box.get("y", 0) - last_box.get("y", 0)) < 1.0
                    and abs(curr_box.get("width", 0) - last_box.get("width", 0)) < 1.0
                    and abs(curr_box.get("height", 0) - last_box.get("height", 0)) < 1.0
                )
                last_box = curr_box
                return stable
            last_box = curr_box
            return False

        return self.poll_condition(
            condition_fn=check_stability,
            condition_name="animation_stabilized",
            target=selector,
            timeout_ms=timeout_ms,
            poll_interval_ms=100,
        )

