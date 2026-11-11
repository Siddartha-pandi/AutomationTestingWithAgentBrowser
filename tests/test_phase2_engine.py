"""Unit and integration tests for Phase 2: Automation Engine Reliability.

Verifies:
1. Native Selector System (parsing, normalization, deterministic validation)
2. Multi-tier deterministic selector fallback resolver
3. Extended browser actions (press_key, keyboard_type, focus, clear, drag_and_drop, upload, scroll_into_view)
4. Deterministic Wait Engine (presence, visibility, hidden, clickability, text, url, title, animation, network idle)
5. Retry & Recovery Policy (backoff calculations, transient retry, non-retryable errors, pre-retry state verification)
6. ActionRegistry integration for new deterministic actions and enriched execution telemetry.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.browser import ActionResult, AgentBrowserAdapter
from backend.app.browser.browser_errors import (
    BrowserCommandError,
    ElementNotFoundError,
    NavigationSecurityError,
)
from backend.app.engine.flows.action_registry import ActionRegistry, StepExecutionResult
from backend.app.engine.flows.flow_schema import FlowActionType
from backend.app.engine.flows.variable_scope import VariableScope
from backend.app.engine.retry import (
    BackoffStrategy,
    RetryConfig,
    RetryExecutor,
    RetryOutcome,
)
from backend.app.engine.selectors import (
    ParsedSelector,
    ResolvedSelectorResult,
    SelectorFallbackResolver,
    SelectorType,
    parse_selector,
    validate_selector,
)
from backend.app.engine.waits import WaitConditionResult, WaitEngine


# =============================================================================
# 1. Native Selector System: Parsing & Normalization
# =============================================================================


def test_parse_selector_types():
    # Ref selector
    ref = parse_selector("@e42")
    assert ref.selector_type == SelectorType.REF
    assert ref.normalized_selector == "@e42"

    # Text selectors (exact and partial)
    t1 = parse_selector("text=Submit")
    assert t1.selector_type == SelectorType.TEXT
    assert t1.normalized_selector == "text=Submit"
    assert t1.text_content == "Submit"
    assert not t1.exact_match

    t2 = parse_selector('text="Submit Order"')
    assert t2.selector_type == SelectorType.TEXT
    assert t2.normalized_selector == 'text="Submit Order"'
    assert t2.text_content == "Submit Order"
    assert t2.exact_match

    # Test ID selectors
    tid1 = parse_selector("testid=checkout-btn")
    assert tid1.selector_type == SelectorType.TEST_ID
    assert tid1.normalized_selector == '[data-testid="checkout-btn"]'

    tid2 = parse_selector('[data-cy="login-form"]')
    assert tid2.selector_type == SelectorType.TEST_ID
    assert tid2.normalized_selector == '[data-cy="login-form"]'

    # Role selectors
    r1 = parse_selector("role=button")
    assert r1.selector_type == SelectorType.ROLE
    assert r1.role_name == "button"

    r2 = parse_selector('role=button[name="Save"]')
    assert r2.selector_type == SelectorType.ROLE
    assert r2.role_name == "button"
    assert r2.role_options.get("name") == "Save"

    # XPath selectors
    xp1 = parse_selector("//div[@class='card']")
    assert xp1.selector_type == SelectorType.XPATH
    assert xp1.normalized_selector == "xpath=//div[@class='card']"

    xp2 = parse_selector("xpath=//button[text()='OK']")
    assert xp2.selector_type == SelectorType.XPATH
    assert xp2.normalized_selector == "xpath=//button[text()='OK']"

    # CSS selector default
    css = parse_selector("#main-content .item:first-child")
    assert css.selector_type == SelectorType.CSS
    assert css.normalized_selector == "#main-content .item:first-child"


# =============================================================================
# 2. Selector Validation
# =============================================================================


def test_validate_selector():
    # Valid selectors
    valid_cases = [
        "#app",
        "button.btn-primary",
        "@e1",
        "text=Welcome",
        'text="Exact match"',
        "testid=submit",
        "role=button",
        'role=button[name="OK"]',
        "xpath=//div[@id='test']",
        "input[placeholder='Search...']",
    ]
    for case in valid_cases:
        is_valid, err = validate_selector(case)
        assert is_valid is True, f"Expected '{case}' to be valid, got error: {err}"

    # Invalid selectors
    invalid_cases = [
        "",
        "   ",
        "role=notarealrole",
        "div[unclosed",
        'button[name="unclosed',
        "xpath=//div[@id=",
        "> button",
        "xpath=//div/",
    ]
    for case in invalid_cases:
        is_valid, err = validate_selector(case)
        assert is_valid is False, f"Expected '{case}' to be invalid"


# =============================================================================
# 3. Deterministic Selector Fallback Resolver
# =============================================================================


def test_selector_fallback_resolver_primary_succeeds():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.is_visible.return_value = True

    resolver = SelectorFallbackResolver(mock_adapter)
    res = resolver.resolve(session_id="sess-1", primary_selector="#submit-btn")

    assert res.resolved_selector == "#submit-btn"
    assert res.tier == "primary"
    assert res.healed is False


def test_selector_fallback_resolver_configured_fallback():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    # Primary fails visibility and count, fallback succeeds
    def mock_is_visible(session_id, sel):
        return sel == ".btn-submit-backup"

    mock_adapter.is_visible.side_effect = mock_is_visible
    mock_adapter.get_count.return_value = 0

    resolver = SelectorFallbackResolver(mock_adapter)
    res = resolver.resolve(
        session_id="sess-1",
        primary_selector="#submit-btn",
        configured_fallbacks=[".btn-submit-backup", "button[type='submit']"],
    )

    assert res.resolved_selector == ".btn-submit-backup"
    assert res.tier == "configured_fallback"
    assert "#submit-btn" in res.attempted_selectors
    assert ".btn-submit-backup" in res.attempted_selectors


def test_selector_fallback_resolver_testid_variants():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    # Primary [data-testid="login-btn"] fails, but [data-cy="login-btn"] variant exists
    def mock_is_visible(session_id, sel):
        return sel == '[data-cy="login-btn"]'

    mock_adapter.is_visible.side_effect = mock_is_visible
    mock_adapter.get_count.return_value = 0

    resolver = SelectorFallbackResolver(mock_adapter)
    res = resolver.resolve(session_id="sess-1", primary_selector="testid=login-btn")

    assert res.resolved_selector == '[data-cy="login-btn"]'
    assert res.tier == "variant"


# =============================================================================
# 4. Deterministic Wait Engine
# =============================================================================


def test_wait_engine_element_visible_success():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    # Becomes visible on 2nd poll
    mock_adapter.is_visible.side_effect = [False, True]

    wait_engine = WaitEngine(mock_adapter)
    res = wait_engine.wait_for_element_visible("sess-1", "#modal", timeout_ms=1000)

    assert res.satisfied is True
    assert res.condition_name == "element_visible"
    assert res.target == "#modal"


def test_wait_engine_timeout():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.is_visible.return_value = False

    wait_engine = WaitEngine(mock_adapter)
    res = wait_engine.wait_for_element_visible("sess-1", "#never-appears", timeout_ms=200)

    assert res.satisfied is False
    assert "Timed out after 200ms" in (res.details or "")


def test_wait_engine_wait_for_text():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.extract_text.side_effect = ["Loading...", "Welcome, John!"]

    wait_engine = WaitEngine(mock_adapter)
    res = wait_engine.wait_for_text("sess-1", "#greeting", expected_text="Welcome", exact=False, timeout_ms=1000)

    assert res.satisfied is True
    assert res.condition_name == "text_contains"


def test_wait_engine_wait_for_url():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.get_url.side_effect = ["https://app.com/login", "https://app.com/dashboard"]

    wait_engine = WaitEngine(mock_adapter)
    res = wait_engine.wait_for_url("sess-1", expected_pattern="/dashboard", timeout_ms=1000)

    assert res.satisfied is True
    assert res.condition_name == "url_contains"


def test_wait_engine_wait_for_element_clickable():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.is_visible.return_value = True
    mock_adapter.is_enabled.return_value = True
    mock_adapter.get_box.return_value = {"x": 100, "y": 200, "width": 80, "height": 30}

    wait_engine = WaitEngine(mock_adapter)
    res = wait_engine.wait_for_element_clickable("sess-1", "#action-btn", timeout_ms=1000)

    assert res.satisfied is True
    assert res.condition_name == "element_clickable"


# =============================================================================
# 5. Retry and Recovery Policy
# =============================================================================


def test_retry_policy_backoff_calculation():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    executor = RetryExecutor(mock_adapter)

    cfg_fixed = RetryConfig(max_retries=3, initial_delay_sec=1.0, backoff_strategy=BackoffStrategy.FIXED)
    assert executor.calculate_delay(1, cfg_fixed) == 1.0
    assert executor.calculate_delay(3, cfg_fixed) == 1.0

    cfg_linear = RetryConfig(max_retries=3, initial_delay_sec=0.5, backoff_strategy=BackoffStrategy.LINEAR)
    assert executor.calculate_delay(1, cfg_linear) == 0.5
    assert executor.calculate_delay(2, cfg_linear) == 1.0
    assert executor.calculate_delay(3, cfg_linear) == 1.5

    cfg_exp = RetryConfig(max_retries=3, initial_delay_sec=0.5, backoff_strategy=BackoffStrategy.EXPONENTIAL)
    assert executor.calculate_delay(1, cfg_exp) == 0.5
    assert executor.calculate_delay(2, cfg_exp) == 1.0
    assert executor.calculate_delay(3, cfg_exp) == 2.0


def test_retry_policy_recovers_after_transient_failure():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    executor = RetryExecutor(mock_adapter)

    attempts = 0

    def flaky_operation():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise BrowserCommandError("Transient element not attached to DOM")
        return "success_val"

    cfg = RetryConfig(max_retries=2, initial_delay_sec=0.01)
    outcome = executor.execute_with_retry("sess-1", flaky_operation, cfg, action_name="click_flaky")

    assert outcome.success is True
    assert outcome.result == "success_val"
    assert outcome.attempts == 2
    assert outcome.recovered_via_retry is True


def test_retry_policy_fails_fast_on_security_violation():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    executor = RetryExecutor(mock_adapter)

    def security_blocked():
        raise NavigationSecurityError("http://127.0.0.1", "Loopback destination blocked")

    cfg = RetryConfig(max_retries=3, initial_delay_sec=0.01)
    outcome = executor.execute_with_retry("sess-1", security_blocked, cfg, action_name="navigate")

    assert outcome.success is False
    assert outcome.attempts == 1  # Should not retry
    assert isinstance(outcome.last_error, NavigationSecurityError)


def test_retry_policy_state_verification_avoids_duplicate():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.verify_state_before_retry.return_value = True
    executor = RetryExecutor(mock_adapter)

    def timeout_but_succeeded():
        raise BrowserCommandError("Timeout waiting for response")

    cfg = RetryConfig(
        max_retries=2,
        initial_delay_sec=0.01,
        verify_state_before_retry=True,
        expected_state_type="url_contains",
        expected_state_target="/order-confirmation",
    )
    outcome = executor.execute_with_retry("sess-1", timeout_but_succeeded, cfg, action_name="submit_order")

    assert outcome.success is True
    assert outcome.recovered_via_retry is True
    assert outcome.side_effect_prevented is True


# =============================================================================
# 6. ActionRegistry: New Deterministic Actions
# =============================================================================


def test_action_registry_new_deterministic_actions():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.is_visible.return_value = True

    registry = ActionRegistry(mock_adapter)
    scope = VariableScope()

    # 1. PRESS_KEY
    res_press = registry.execute_action(
        action=FlowActionType.PRESS_KEY,
        session_id="sess-1",
        config={"key": "Enter"},
        scope=scope,
    )
    assert res_press.status == "passed"
    mock_adapter.press_key.assert_called_with("sess-1", key="Enter")

    # 2. KEYBOARD_TYPE
    res_kb = registry.execute_action(
        action=FlowActionType.KEYBOARD_TYPE,
        session_id="sess-1",
        config={"text": "Hello World"},
        scope=scope,
    )
    assert res_kb.status == "passed"
    mock_adapter.keyboard_type.assert_called_with("sess-1", text="Hello World")

    # 3. FOCUS
    res_focus = registry.execute_action(
        action=FlowActionType.FOCUS,
        session_id="sess-1",
        config={"target": {"selector": "#username"}},
        scope=scope,
    )
    assert res_focus.status == "passed"
    mock_adapter.focus.assert_called_with("sess-1", selector="#username")

    # 4. CLEAR
    res_clear = registry.execute_action(
        action=FlowActionType.CLEAR,
        session_id="sess-1",
        config={"target": {"selector": "#username"}},
        scope=scope,
    )
    assert res_clear.status == "passed"
    mock_adapter.clear.assert_called_with("sess-1", selector="#username")

    # 5. DRAG_AND_DROP
    res_drag = registry.execute_action(
        action=FlowActionType.DRAG_AND_DROP,
        session_id="sess-1",
        config={
            "source": {"selector": "#card-1"},
            "destination": {"selector": "#col-done"},
        },
        scope=scope,
    )
    assert res_drag.status == "passed"
    mock_adapter.drag_and_drop.assert_called_with("sess-1", source_selector="#card-1", target_selector="#col-done")

    # 6. SCROLL_INTO_VIEW
    res_siv = registry.execute_action(
        action=FlowActionType.SCROLL_INTO_VIEW,
        session_id="sess-1",
        config={"target": {"selector": "#footer"}},
        scope=scope,
    )
    assert res_siv.status == "passed"
    mock_adapter.scroll_into_view.assert_called_with("sess-1", selector="#footer")

    # 7. EVALUATE_JS
    mock_adapter.evaluate.return_value = 42
    res_eval = registry.execute_action(
        action=FlowActionType.EVALUATE_JS,
        session_id="sess-1",
        config={"script": "return 40 + 2", "variable_name": "computed_val"},
        scope=scope,
    )
    assert res_eval.status == "passed"
    assert scope.get("computed_val") == 42


def test_action_registry_step_retries_and_diagnostics():
    mock_adapter = MagicMock(spec=AgentBrowserAdapter)
    mock_adapter.is_visible.return_value = True
    mock_adapter.get_console_logs.return_value = ["[ERROR] Uncaught ReferenceError: foo is not defined"]

    calls = 0

    def failing_click(session_id, selector, timeout=15.0):
        nonlocal calls
        calls += 1
        if calls < 2:
            raise BrowserCommandError("Element not clickable at point (100, 200)")
        return ActionResult(success=True, action="click", target=selector, duration_ms=25.0)

    mock_adapter.click.side_effect = failing_click

    registry = ActionRegistry(mock_adapter)
    scope = VariableScope()

    # With retry_count = 2, step should retry and pass
    res = registry.execute_action(
        action=FlowActionType.CLICK,
        session_id="sess-1",
        config={"target": {"selector": "#retry-btn"}, "retry_count": 2, "retry_delay_sec": 0.01},
        scope=scope,
    )
    assert res.status == "passed"
    assert res.retries_attempted == 2
    assert res.duration_ms > 0

