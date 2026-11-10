"""Deterministic assertion engine for test automation.

Implements 13 rigorous deterministic assertions comparing expected vs actual application state.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.app.browser import AgentBrowserAdapter

logger = logging.getLogger(__name__)


@dataclass
class AssertionResult:
    """Outcome of a single deterministic assertion evaluation."""

    passed: bool
    assertion_type: str
    expected: Any
    actual: Any
    message: str


class AssertionEngine:
    """Evaluates deterministic assertions against an active browser session."""

    def __init__(self, adapter: AgentBrowserAdapter) -> None:
        self.adapter = adapter

    def evaluate_assertion(
        self,
        session_id: str,
        assertion_type: str,
        selector: str | None = None,
        expected: Any = None,
        attribute_name: str | None = None,
    ) -> AssertionResult:
        """Dispatches and evaluates one of the 13 deterministic assertions."""
        handler_map = {
            "element_visible": self._assert_element_visible,
            "element_hidden": self._assert_element_hidden,
            "element_enabled": self._assert_element_enabled,
            "element_disabled": self._assert_element_disabled,
            "text_equals": self._assert_text_equals,
            "text_contains": self._assert_text_contains,
            "attribute_equals": self._assert_attribute_equals,
            "url_equals": self._assert_url_equals,
            "url_contains": self._assert_url_contains,
            "element_count": self._assert_element_count,
            "value_equals": self._assert_value_equals,
            "table_contains": self._assert_table_contains,
            "page_title_equals": self._assert_page_title_equals,
        }

        handler = handler_map.get(assertion_type)
        if not handler:
            return AssertionResult(
                passed=False,
                assertion_type=assertion_type,
                expected=expected,
                actual=None,
                message=f"Unsupported assertion type '{assertion_type}'",
            )

        try:
            return handler(session_id, selector=selector, expected=expected, attribute_name=attribute_name)
        except Exception as err:
            logger.error("Error evaluating assertion '%s': %s", assertion_type, err)
            return AssertionResult(
                passed=False,
                assertion_type=assertion_type,
                expected=expected,
                actual=None,
                message=f"Assertion failed with exception: {err}",
            )

    # 1. Element Visible
    def _assert_element_visible(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "element_visible", True, False, "Selector is required for element_visible assertion")
        visible = self.adapter.is_visible(session_id, selector)
        passed = (visible is True)
        msg = f"Element '{selector}' is visible" if passed else f"Expected element '{selector}' to be visible, but it was not"
        return AssertionResult(passed, "element_visible", True, visible, msg)

    # 2. Element Hidden
    def _assert_element_hidden(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "element_hidden", True, False, "Selector is required for element_hidden assertion")
        visible = self.adapter.is_visible(session_id, selector)
        passed = (visible is False)
        msg = f"Element '{selector}' is hidden" if passed else f"Expected element '{selector}' to be hidden, but it is visible"
        return AssertionResult(passed, "element_hidden", False, visible, msg)

    # 3. Element Enabled
    def _assert_element_enabled(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "element_enabled", True, False, "Selector is required for element_enabled assertion")
        enabled = self.adapter.is_enabled(session_id, selector)
        passed = (enabled is True)
        msg = f"Element '{selector}' is enabled" if passed else f"Expected element '{selector}' to be enabled, but it was disabled"
        return AssertionResult(passed, "element_enabled", True, enabled, msg)

    # 4. Element Disabled
    def _assert_element_disabled(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "element_disabled", False, False, "Selector is required for element_disabled assertion")
        enabled = self.adapter.is_enabled(session_id, selector)
        passed = (enabled is False)
        msg = f"Element '{selector}' is disabled" if passed else f"Expected element '{selector}' to be disabled, but it is enabled"
        return AssertionResult(passed, "element_disabled", False, enabled, msg)

    # 5. Text Equals
    def _assert_text_equals(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "text_equals", expected, None, "Selector is required for text_equals assertion")
        actual_text = self.adapter.extract_text(session_id, selector).strip()
        exp_text = str(expected).strip() if expected is not None else ""
        passed = (actual_text == exp_text)
        msg = f"Text matches expected '{exp_text}'" if passed else f"Text mismatch: Expected '{exp_text}', got '{actual_text}'"
        return AssertionResult(passed, "text_equals", exp_text, actual_text, msg)

    # 6. Text Contains
    def _assert_text_contains(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "text_contains", expected, None, "Selector is required for text_contains assertion")
        actual_text = self.adapter.extract_text(session_id, selector)
        exp_substr = str(expected) if expected is not None else ""
        passed = (exp_substr in actual_text)
        msg = f"Element text contains '{exp_substr}'" if passed else f"Substring mismatch: Element text '{actual_text}' does not contain '{exp_substr}'"
        return AssertionResult(passed, "text_contains", exp_substr, actual_text, msg)

    # 7. Attribute Equals
    def _assert_attribute_equals(self, session_id: str, selector: str | None, expected: Any, attribute_name: str | None = None, **kwargs) -> AssertionResult:
        if not selector or not attribute_name:
            return AssertionResult(False, "attribute_equals", expected, None, "Selector and attribute_name are required")
        actual_val = self.adapter.get_attribute(session_id, selector, attribute_name)
        exp_val = str(expected) if expected is not None else ""
        passed = (str(actual_val or "") == exp_val)
        msg = f"Attribute '{attribute_name}' equals '{exp_val}'" if passed else f"Attribute mismatch for '{attribute_name}': Expected '{exp_val}', got '{actual_val}'"
        return AssertionResult(passed, "attribute_equals", exp_val, actual_val, msg)

    # 8. URL Equals
    def _assert_url_equals(self, session_id: str, expected: Any, **kwargs) -> AssertionResult:
        actual_url = self.adapter.get_url(session_id)
        exp_url = str(expected) if expected is not None else ""
        passed = (actual_url.rstrip("/") == exp_url.rstrip("/"))
        msg = f"URL equals '{exp_url}'" if passed else f"URL mismatch: Expected '{exp_url}', got '{actual_url}'"
        return AssertionResult(passed, "url_equals", exp_url, actual_url, msg)

    # 9. URL Contains
    def _assert_url_contains(self, session_id: str, expected: Any, **kwargs) -> AssertionResult:
        actual_url = self.adapter.get_url(session_id)
        exp_substr = str(expected) if expected is not None else ""
        passed = (exp_substr in actual_url)
        msg = f"URL contains '{exp_substr}'" if passed else f"URL does not contain '{exp_substr}': current URL is '{actual_url}'"
        return AssertionResult(passed, "url_contains", exp_substr, actual_url, msg)

    # 10. Element Count
    def _assert_element_count(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "element_count", expected, None, "Selector is required for element_count assertion")
        actual_count = self.adapter.get_count(session_id, selector)
        exp_count = int(expected) if expected is not None else 0
        passed = (actual_count == exp_count)
        msg = f"Element count for '{selector}' is {actual_count}" if passed else f"Element count mismatch for '{selector}': Expected {exp_count}, got {actual_count}"
        return AssertionResult(passed, "element_count", exp_count, actual_count, msg)

    # 11. Value Equals
    def _assert_value_equals(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "value_equals", expected, None, "Selector is required for value_equals assertion")
        actual_val = self.adapter.get_value(session_id, selector)
        exp_val = str(expected) if expected is not None else ""
        passed = (actual_val == exp_val)
        msg = f"Input value matches '{exp_val}'" if passed else f"Input value mismatch: Expected '{exp_val}', got '{actual_val}'"
        return AssertionResult(passed, "value_equals", exp_val, actual_val, msg)

    # 12. Table Contains Expected Data
    def _assert_table_contains(self, session_id: str, selector: str | None, expected: Any, **kwargs) -> AssertionResult:
        if not selector:
            return AssertionResult(False, "table_contains", expected, None, "Selector is required for table_contains assertion")

        js_code = f"""(() => {{
            const table = document.querySelector("{selector}");
            if (!table) return [];
            return Array.from(table.querySelectorAll("tr")).map(r =>
                Array.from(r.querySelectorAll("td, th")).map(c => c.innerText.trim())
            );
        }})()"""
        rows = self.adapter.evaluate(session_id, js_code)
        exp_str = str(expected) if expected is not None else ""

        # Flatten rows into searchable strings
        row_strings = [" | ".join(r) for r in rows] if isinstance(rows, list) else []
        passed = any(exp_str in r for r in row_strings)
        msg = f"Table contains expected record '{exp_str}'" if passed else f"Table does not contain '{exp_str}'. Extracted rows: {len(row_strings)}"
        return AssertionResult(passed, "table_contains", exp_str, row_strings, msg)

    # 13. Page Title Equals
    def _assert_page_title_equals(self, session_id: str, expected: Any, **kwargs) -> AssertionResult:
        actual_title = self.adapter.get_title(session_id).strip()
        exp_title = str(expected).strip() if expected is not None else ""
        passed = (actual_title == exp_title)
        msg = f"Page title matches '{exp_title}'" if passed else f"Page title mismatch: Expected '{exp_title}', got '{actual_title}'"
        return AssertionResult(passed, "page_title_equals", exp_title, actual_title, msg)

