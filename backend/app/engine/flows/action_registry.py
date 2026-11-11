"""Deterministic action registry for workflow step execution.

Dispatches each FlowActionType to its deterministic handler using AgentBrowserAdapter,
SelfHealingEngine, and VariableScope. Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.browser import AgentBrowserAdapter
from backend.app.browser.browser_errors import BrowserCommandError, ElementNotFoundError

BrowserActionError = BrowserCommandError
from backend.app.engine.flows.flow_schema import FlowActionType
from backend.app.engine.flows.variable_scope import VariableScope
from backend.app.engine.retry import BackoffStrategy, RetryConfig, RetryExecutor
from backend.app.engine.selectors import (
    ParsedSelector,
    ResolvedSelectorResult,
    SelectorFallbackResolver,
    SelectorType,
    parse_selector,
    validate_selector,
)
from backend.app.engine.waits import WaitConditionResult, WaitEngine
from backend.app.intelligence.element_profile import ElementProfileData
from backend.app.intelligence.self_healing import SelfHealingEngine
from backend.app.models.intelligence import ElementProfile

logger = logging.getLogger(__name__)


@dataclass
class StepExecutionResult:
    """Outcome of executing a single workflow node action."""

    status: str  # 'passed', 'failed', 'requires_approval', 'skipped'
    result_data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    next_handle: str = "default"  # 'default', 'true', 'false', 'loop_body', 'loop_exit'
    screenshot_path: str | None = None
    healed_locator: str | None = None
    duration_ms: float = 0.0
    actual_selector: str | None = None
    fallback_tier: str | None = None
    retries_attempted: int = 1
    console_logs: list[str] = field(default_factory=list)


class ActionRegistry:
    """Central registry of deterministic browser and control flow action handlers."""

    def __init__(self, adapter: AgentBrowserAdapter, db: Session | None = None) -> None:
        self.adapter = adapter
        self.db = db
        self.healing_engine = SelfHealingEngine(adapter, db=db)
        self.selector_resolver = SelectorFallbackResolver(adapter, db=db)
        self.wait_engine = WaitEngine(adapter)
        self.retry_executor = RetryExecutor(adapter)

    def resolve_target_selector(
        self,
        session_id: str,
        target_config: dict[str, Any],
        action_name: str = "click",
        execution_id: UUID | None = None,
        is_destructive: bool = False,
    ) -> tuple[str, str | None]:
        """Resolves resilient locator using element profiles, multi-tier fallback, and deterministic self-healing.

        Returns (resolved_selector, healed_locator_or_None).
        """
        logical_id = target_config.get("logical_id")
        element_profile_id = target_config.get("element_profile_id")
        raw_selector = target_config.get("selector") or ""
        fallbacks = target_config.get("fallbacks") or []

        if not logical_id and not element_profile_id and not raw_selector:
            raise ElementNotFoundError("No target selector or logical ID specified in action config")

        # Multi-tier resolution through selector subsystem
        resolution = self.selector_resolver.resolve(
            session_id=session_id,
            primary_selector=raw_selector,
            configured_fallbacks=fallbacks,
            logical_id=logical_id,
            element_profile_id=element_profile_id,
            execution_id=execution_id,
            is_destructive=is_destructive,
        )

        healed = resolution.resolved_selector if resolution.healed else None
        logger.info(
            "Selector resolution for action '%s': original='%s', resolved='%s' (tier: %s), attempted=%s",
            action_name,
            raw_selector,
            resolution.resolved_selector,
            resolution.tier,
            resolution.attempted_selectors,
        )
        return resolution.resolved_selector, healed
    def execute_action(
        self,
        action: FlowActionType,
        session_id: str,
        config: dict[str, Any],
        scope: VariableScope,
        execution_id: UUID | None = None,
    ) -> StepExecutionResult:
        """Dispatches action execution deterministically with timing, retries, and error telemetry."""
        handler_map: dict[FlowActionType, Callable[..., StepExecutionResult]] = {
            FlowActionType.NAVIGATE: self._handle_navigate,
            FlowActionType.CLICK: self._handle_click,
            FlowActionType.DOUBLE_CLICK: self._handle_double_click,
            FlowActionType.RIGHT_CLICK: self._handle_right_click,
            FlowActionType.HOVER: self._handle_hover,
            FlowActionType.FILL: self._handle_fill,
            FlowActionType.TYPE: self._handle_type,
            FlowActionType.SELECT: self._handle_select,
            FlowActionType.CHECK: self._handle_check,
            FlowActionType.UNCHECK: self._handle_uncheck,
            FlowActionType.SCROLL: self._handle_scroll,
            FlowActionType.SCROLL_INTO_VIEW: self._handle_scroll_into_view,
            FlowActionType.PRESS_KEY: self._handle_press_key,
            FlowActionType.KEYBOARD_TYPE: self._handle_keyboard_type,
            FlowActionType.FOCUS: self._handle_focus,
            FlowActionType.CLEAR: self._handle_clear,
            FlowActionType.DRAG_AND_DROP: self._handle_drag_and_drop,
            FlowActionType.UPLOAD_FILE: self._handle_upload_file,
            FlowActionType.EVALUATE_JS: self._handle_evaluate_js,
            FlowActionType.EXTRACT_TEXT: self._handle_extract_text,
            FlowActionType.EXTRACT_ATTRIBUTE: self._handle_extract_attribute,
            FlowActionType.EXTRACT_TABLE: self._handle_extract_table,
            FlowActionType.WAIT: self._handle_wait,
            FlowActionType.WAIT_UNTIL: self._handle_wait_until,
            FlowActionType.WAIT_FOR_ELEMENT: self._handle_wait_for_element,
            FlowActionType.WAIT_FOR_URL: self._handle_wait_for_url,
            FlowActionType.WAIT_FOR_TEXT: self._handle_wait_for_text,
            FlowActionType.WAIT_FOR_NETWORK_IDLE: self._handle_wait_for_network_idle,
            FlowActionType.BROWSER_BACK: self._handle_browser_back,
            FlowActionType.BROWSER_FORWARD: self._handle_browser_forward,
            FlowActionType.REFRESH: self._handle_refresh,
            FlowActionType.CONDITION: self._handle_condition,
            FlowActionType.SWITCH: self._handle_switch,
            FlowActionType.SET_VARIABLE: self._handle_set_variable,
            FlowActionType.STRING_OP: self._handle_string_op,
            FlowActionType.NUMBER_OP: self._handle_number_op,
            FlowActionType.JSON_OP: self._handle_json_op,
            FlowActionType.DATE_OP: self._handle_date_op,
            FlowActionType.ARRAY_OP: self._handle_array_op,
            FlowActionType.SCREENSHOT: self._handle_screenshot,
            FlowActionType.STOP: self._handle_stop,
        }

        handler = handler_map.get(action)
        if not handler:
            return StepExecutionResult(
                status="failed",
                error_message=f"No handler registered for action '{action.value}'",
            )

        retries = int(config.get("retries", config.get("retry_count", 0)))
        start_t = time.perf_counter()

        def run_op() -> StepExecutionResult:
            return handler(session_id, config, scope, execution_id)

        try:
            if retries > 0:
                retry_cfg = RetryConfig(
                    max_retries=retries,
                    initial_delay_sec=float(config.get("retry_delay_sec", 0.5)),
                )
                outcome = self.retry_executor.execute_with_retry(
                    session_id=session_id,
                    action_fn=run_op,
                    config=retry_cfg,
                    action_name=action.value,
                )
                if outcome.success and isinstance(outcome.result, StepExecutionResult):
                    res = outcome.result
                    res.retries_attempted = outcome.attempts
                    res.duration_ms = outcome.total_elapsed_ms
                    return res
                elif outcome.last_error:
                    raise outcome.last_error

            res = run_op()
            res.duration_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            return res
        except Exception as err:
            logger.error("Error executing action '%s': %s", action.value, err)
            duration_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            c_logs: list[str] = []
            try:
                c_logs = self.adapter.get_console_logs(session_id)
            except Exception:
                pass
            return StepExecutionResult(
                status="failed",
                error_message=str(err),
                duration_ms=duration_ms,
                console_logs=c_logs,
            )

    def _handle_navigate(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        raw_url = str(config.get("url", ""))
        url = str(scope.interpolate(raw_url))
        timeout_ms = int(config.get("timeout_ms", 30000))
        wait_until = str(config.get("wait_until", "load"))

        res = self.adapter.navigate(session_id, url=url, wait_until=wait_until, timeout_ms=timeout_ms)
        stdout_val = getattr(res, "stdout", "") if hasattr(res, "stdout") else (res.get("stdout", "") if isinstance(res, dict) else str(res))
        return StepExecutionResult(status="passed", result_data={"url": url, "stdout": str(stdout_val)})

    def _handle_click(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="click", execution_id=execution_id)
        res = self.adapter.click(session_id, selector=selector)
        return StepExecutionResult(
            status="passed",
            result_data={"selector": selector, "healed": bool(healed_loc)},
            healed_locator=healed_loc,
        )

    def _handle_double_click(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="double_click", execution_id=execution_id)
        # Double click via native Agent Browser CLI command
        self.adapter.dblclick(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector}, healed_locator=healed_loc)

    def _handle_fill(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        raw_val = config.get("value", "")
        interpolated_val = str(scope.interpolate(raw_val))
        is_secret = bool(config.get("is_secret", False))

        if is_secret:
            scope.set("__secret_val__", interpolated_val, is_secret=True)

        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="fill", execution_id=execution_id)
        self.adapter.fill(session_id, selector=selector, text=interpolated_val)

        return StepExecutionResult(
            status="passed",
            result_data={"selector": selector, "filled": True, "is_secret": is_secret},
            healed_locator=healed_loc,
        )

    def _handle_type(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        text = str(scope.interpolate(config.get("text", "")))
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="type", execution_id=execution_id)
        self.adapter.fill(session_id, selector=selector, text=text)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "typed": True}, healed_locator=healed_loc)

    def _handle_select(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        value = str(scope.interpolate(config.get("value", "")))
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="select", execution_id=execution_id)
        self.adapter.select(session_id, selector=selector, value=value)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "value": value}, healed_locator=healed_loc)

    def _handle_extract_text(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        var_name = config.get("variable_name") or "extracted_text"
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="extract_text", execution_id=execution_id)
        extracted = self.adapter.extract_text(session_id, selector=selector)
        scope.set(var_name, extracted)
        return StepExecutionResult(
            status="passed",
            result_data={"variable_name": var_name, "extracted_text": extracted},
            healed_locator=healed_loc,
        )

    def _handle_extract_attribute(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        attr_name = config.get("attribute_name", "value")
        var_name = config.get("variable_name") or f"extracted_{attr_name}"
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="extract_attribute", execution_id=execution_id)
        val = self.adapter.get_attribute(session_id, selector=selector, attribute_name=attr_name)
        scope.set(var_name, val)
        return StepExecutionResult(
            status="passed",
            result_data={"variable_name": var_name, "attribute": attr_name, "value": val},
            healed_locator=healed_loc,
        )

    def _handle_extract_table(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        var_name = config.get("variable_name") or "extracted_table"
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="extract_table", execution_id=execution_id)

        # Evaluate table extraction via DOM script inside Agent Browser
        js_code = f"""(() => {{
            const table = document.querySelector("{selector}");
            if (!table) return [];
            const rows = Array.from(table.querySelectorAll("tr"));
            return rows.map(r => Array.from(r.querySelectorAll("td, th")).map(c => c.innerText.trim()));
        }})()"""
        table_data = self.adapter.evaluate(session_id, expression=js_code)
        scope.set(var_name, table_data)
        return StepExecutionResult(
            status="passed",
            result_data={"variable_name": var_name, "row_count": len(table_data) if isinstance(table_data, list) else 0},
            healed_locator=healed_loc,
        )

    def _handle_wait(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        wait_type = config.get("wait_type", "duration")
        if wait_type == "selector":
            selector = str(scope.interpolate(config.get("selector", "")))
            timeout_ms = int(config.get("timeout_ms", 10000))
            self.adapter.wait_for_selector(session_id, selector=selector, timeout_ms=timeout_ms)
            return StepExecutionResult(status="passed", result_data={"wait_type": "selector", "selector": selector})
        else:
            duration_ms = int(config.get("duration_ms", 1000))
            time.sleep(duration_ms / 1000.0)
            return StepExecutionResult(status="passed", result_data={"wait_type": "duration", "duration_ms": duration_ms})

    def _handle_condition(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        left_raw = config.get("left_operand", "")
        left = scope.interpolate(left_raw)
        operator = config.get("operator", "==")
        right_raw = config.get("right_operand", "")
        right = scope.interpolate(right_raw)

        is_true = VariableScope.evaluate_condition(left, operator, right)
        next_handle = "true" if is_true else "false"

        return StepExecutionResult(
            status="passed",
            result_data={"left": left, "operator": operator, "right": right, "evaluated_to": is_true},
            next_handle=next_handle,
        )

    def _handle_set_variable(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        var_name = config.get("variable_name", "")
        template = config.get("value_template", "")
        interpolated = scope.interpolate(template)
        scope.set(var_name, interpolated)
        return StepExecutionResult(status="passed", result_data={"variable_name": var_name, "value": interpolated})

    def _handle_screenshot(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        caption = str(scope.interpolate(config.get("caption", "screenshot")))
        res = self.adapter.screenshot(session_id)
        path = str(getattr(res, "screenshot_path", res))
        return StepExecutionResult(status="passed", result_data={"caption": caption, "file_path": path}, screenshot_path=path)

    def _handle_stop(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        reason = str(scope.interpolate(config.get("reason", "Workflow stopped normally")))
        return StepExecutionResult(status="passed", result_data={"reason": reason}, next_handle="stop")

    def _handle_right_click(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="right_click", execution_id=execution_id)
        res = self.adapter.right_click(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "right_clicked": True}, healed_locator=healed_loc)

    def _handle_hover(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="hover", execution_id=execution_id)
        res = self.adapter.hover(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "hovered": True}, healed_locator=healed_loc)

    def _handle_check(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="check", execution_id=execution_id)
        res = self.adapter.check(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "checked": True}, healed_locator=healed_loc)

    def _handle_uncheck(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="uncheck", execution_id=execution_id)
        res = self.adapter.uncheck(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "unchecked": True}, healed_locator=healed_loc)

    def _handle_scroll(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        direction = str(config.get("direction", "down")).lower()
        amount = int(config.get("amount", 400))
        target = config.get("target") or {}
        selector = target.get("selector")
        res = self.adapter.scroll(session_id, direction=direction, amount=amount, selector=selector)
        return StepExecutionResult(status="passed", result_data={"direction": direction, "amount": amount, "target": selector})

    def _handle_scroll_into_view(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="scroll_into_view", execution_id=execution_id)
        self.adapter.scroll_into_view(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "scrolled_into_view": True}, healed_locator=healed_loc)

    def _handle_press_key(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        raw_key = config.get("key", "Enter")
        key = str(scope.interpolate(raw_key))
        self.adapter.press_key(session_id, key=key)
        return StepExecutionResult(status="passed", result_data={"key": key, "pressed": True})

    def _handle_keyboard_type(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        raw_text = config.get("text", "")
        text = str(scope.interpolate(raw_text))
        self.adapter.keyboard_type(session_id, text=text)
        return StepExecutionResult(status="passed", result_data={"text_length": len(text), "keyboard_typed": True})

    def _handle_focus(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="focus", execution_id=execution_id)
        self.adapter.focus(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "focused": True}, healed_locator=healed_loc)

    def _handle_clear(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="clear", execution_id=execution_id)
        self.adapter.clear(session_id, selector=selector)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "cleared": True}, healed_locator=healed_loc)

    def _handle_drag_and_drop(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        source_target = config.get("source") or config.get("source_target") or {}
        dest_target = config.get("destination") or config.get("destination_target") or {}
        src_sel, _ = self.resolve_target_selector(session_id, source_target, action_name="drag_source", execution_id=execution_id)
        dst_sel, _ = self.resolve_target_selector(session_id, dest_target, action_name="drag_target", execution_id=execution_id)
        self.adapter.drag_and_drop(session_id, source_selector=src_sel, target_selector=dst_sel)
        return StepExecutionResult(status="passed", result_data={"source": src_sel, "destination": dst_sel, "dragged": True})

    def _handle_upload_file(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        raw_files = config.get("files") or [config.get("file_path")]
        file_paths = [str(scope.interpolate(f)) for f in raw_files if f]
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="upload", execution_id=execution_id)
        self.adapter.upload(session_id, selector=selector, file_paths=file_paths)
        return StepExecutionResult(status="passed", result_data={"selector": selector, "files": file_paths, "uploaded": True}, healed_locator=healed_loc)

    def _handle_evaluate_js(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        raw_script = str(config.get("script") or config.get("expression") or "")
        script = str(scope.interpolate(raw_script))
        var_name = config.get("variable_name")
        res = self.adapter.evaluate(session_id, js_code=script)
        if var_name:
            scope.set(var_name, res)
        return StepExecutionResult(status="passed", result_data={"variable_name": var_name, "result": res})

    def _handle_wait_for_element(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        state = config.get("state", "visible")  # 'visible', 'hidden', 'present', 'clickable'
        timeout_ms = int(config.get("timeout_ms", 10000))
        raw_sel = target.get("selector") or ""
        selector, healed_loc = self.resolve_target_selector(session_id, target, action_name="wait_for_element", execution_id=execution_id) if raw_sel else ("", None)

        if state == "clickable":
            w_res = self.wait_engine.wait_for_element_clickable(session_id, selector, timeout_ms=timeout_ms)
        elif state == "hidden":
            w_res = self.wait_engine.wait_for_element_hidden(session_id, selector, timeout_ms=timeout_ms)
        elif state == "present":
            w_res = self.wait_engine.wait_for_element_present(session_id, selector, timeout_ms=timeout_ms)
        else:
            w_res = self.wait_engine.wait_for_element_visible(session_id, selector, timeout_ms=timeout_ms)

        if not w_res.satisfied:
            raise BrowserActionError(w_res.details or f"Wait for element '{selector}' in state '{state}' timed out")

        return StepExecutionResult(status="passed", result_data={"selector": selector, "state": state, "elapsed_ms": w_res.elapsed_ms}, healed_locator=healed_loc)

    def _handle_wait_for_url(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        raw_pattern = config.get("url_pattern", "")
        pattern = str(scope.interpolate(raw_pattern))
        is_regex = bool(config.get("is_regex", False))
        timeout_ms = int(config.get("timeout_ms", 10000))

        w_res = self.wait_engine.wait_for_url(session_id, expected_pattern=pattern, is_regex=is_regex, timeout_ms=timeout_ms)
        if not w_res.satisfied:
            raise BrowserActionError(w_res.details or f"Wait for URL matching '{pattern}' timed out")

        return StepExecutionResult(status="passed", result_data={"pattern": pattern, "is_regex": is_regex, "elapsed_ms": w_res.elapsed_ms})

    def _handle_wait_for_text(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        selector = target.get("selector") or "body"
        raw_text = config.get("text", "")
        text = str(scope.interpolate(raw_text))
        exact = bool(config.get("exact", False))
        timeout_ms = int(config.get("timeout_ms", 10000))

        w_res = self.wait_engine.wait_for_text(session_id, selector=selector, expected_text=text, exact=exact, timeout_ms=timeout_ms)
        if not w_res.satisfied:
            raise BrowserActionError(w_res.details or f"Wait for text '{text}' on selector '{selector}' timed out")

        return StepExecutionResult(status="passed", result_data={"selector": selector, "text": text, "exact": exact, "elapsed_ms": w_res.elapsed_ms})

    def _handle_wait_for_network_idle(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        timeout_ms = int(config.get("timeout_ms", 10000))
        w_res = self.wait_engine.wait_for_network_idle(session_id, timeout_ms=timeout_ms)
        if not w_res.satisfied:
            raise BrowserActionError(w_res.details or "Wait for network idle timed out")

        return StepExecutionResult(status="passed", result_data={"network_idle": True, "elapsed_ms": w_res.elapsed_ms})

    def _handle_browser_back(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        res = self.adapter.back(session_id)
        return StepExecutionResult(status="passed", result_data={"navigated_back": True})

    def _handle_browser_forward(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        res = self.adapter.forward(session_id)
        return StepExecutionResult(status="passed", result_data={"navigated_forward": True})

    def _handle_refresh(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        res = self.adapter.reload(session_id)
        return StepExecutionResult(status="passed", result_data={"reloaded": True})

    def _handle_wait_until(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        target = config.get("target") or {}
        raw_selector = target.get("selector") or ""
        timeout_ms = int(config.get("timeout_ms", 10000))
        condition_type = config.get("condition", "visible")

        if condition_type == "visible":
            w_res = self.wait_engine.wait_for_element_visible(session_id, raw_selector, timeout_ms=timeout_ms)
        elif condition_type == "hidden":
            w_res = self.wait_engine.wait_for_element_hidden(session_id, raw_selector, timeout_ms=timeout_ms)
        elif condition_type == "clickable":
            w_res = self.wait_engine.wait_for_element_clickable(session_id, raw_selector, timeout_ms=timeout_ms)
        elif condition_type == "present":
            w_res = self.wait_engine.wait_for_element_present(session_id, raw_selector, timeout_ms=timeout_ms)
        else:
            w_res = self.wait_engine.poll_condition(
                condition_fn=lambda: self.adapter.is_enabled(session_id, raw_selector),
                condition_name="enabled",
                target=raw_selector,
                timeout_ms=timeout_ms,
            )

        if not w_res.satisfied:
            raise BrowserActionError(f"Wait until condition '{condition_type}' timed out on selector '{raw_selector}'")

        return StepExecutionResult(status="passed", result_data={"selector": raw_selector, "matched": True, "elapsed_ms": w_res.elapsed_ms})

    def _handle_switch(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        expr = str(scope.interpolate(config.get("expression", "")))
        cases = config.get("cases", [])  # list of branch names
        matched_handle = "default"
        for case in cases:
            if expr == str(case):
                matched_handle = str(case)
                break
        return StepExecutionResult(status="passed", result_data={"expression": expr, "branch": matched_handle}, next_handle=matched_handle)

    def _handle_string_op(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        op = config.get("operation", "upper").lower()
        val = str(scope.interpolate(config.get("input", "")))
        var_name = config.get("output_variable", "string_result")

        if op == "upper":
            result: Any = val.upper()
        elif op == "lower":
            result = val.lower()
        elif op == "trim":
            result = val.strip()
        elif op == "replace":
            find_str = str(scope.interpolate(config.get("find", "")))
            replace_str = str(scope.interpolate(config.get("replace", "")))
            result = val.replace(find_str, replace_str)
        elif op == "split":
            delimiter = config.get("delimiter", ",")
            result = val.split(delimiter)
        elif op == "length":
            result = len(val)
        else:
            result = val

        scope.set(var_name, result)
        return StepExecutionResult(status="passed", result_data={"operation": op, "result": result, "variable_name": var_name})

    def _handle_number_op(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        import math
        op = config.get("operation", "add").lower()
        var_name = config.get("output_variable", "number_result")
        num1 = float(scope.interpolate(str(config.get("a", 0))))
        num2 = float(scope.interpolate(str(config.get("b", 0))))

        if op == "add":
            res_num: Any = num1 + num2
        elif op == "subtract":
            res_num = num1 - num2
        elif op == "multiply":
            res_num = num1 * num2
        elif op == "divide":
            res_num = num1 / num2 if num2 != 0 else 0
        elif op == "round":
            decimals = int(config.get("decimals", 0))
            res_num = round(num1, decimals)
        elif op == "abs":
            res_num = abs(num1)
        elif op == "min":
            res_num = min(num1, num2)
        elif op == "max":
            res_num = max(num1, num2)
        else:
            res_num = num1

        scope.set(var_name, res_num)
        return StepExecutionResult(status="passed", result_data={"operation": op, "result": res_num, "variable_name": var_name})

    def _handle_json_op(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        import json
        op = config.get("operation", "parse").lower()
        var_name = config.get("output_variable", "json_result")
        inp = scope.interpolate(config.get("input", ""))

        if op == "parse":
            try:
                res_json: Any = json.loads(inp) if isinstance(inp, str) else inp
            except Exception:
                res_json = {}
        elif op == "stringify":
            res_json = json.dumps(inp) if not isinstance(inp, str) else inp
        elif op == "get_key":
            key = config.get("key", "")
            data_dict = json.loads(inp) if isinstance(inp, str) else inp
            res_json = data_dict.get(key) if isinstance(data_dict, dict) else None
        else:
            res_json = inp

        scope.set(var_name, res_json)
        return StepExecutionResult(status="passed", result_data={"operation": op, "result": res_json, "variable_name": var_name})

    def _handle_date_op(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        from datetime import datetime, timezone, timedelta
        op = config.get("operation", "now").lower()
        var_name = config.get("output_variable", "date_result")

        now_utc = datetime.now(timezone.utc)
        if op == "now":
            res_date: Any = now_utc.isoformat()
        elif op == "timestamp":
            res_date = int(now_utc.timestamp())
        elif op == "format":
            fmt = config.get("format", "%Y-%m-%d")
            res_date = now_utc.strftime(fmt)
        elif op == "add_days":
            days = int(config.get("days", 1))
            res_date = (now_utc + timedelta(days=days)).isoformat()
        else:
            res_date = now_utc.isoformat()

        scope.set(var_name, res_date)
        return StepExecutionResult(status="passed", result_data={"operation": op, "result": res_date, "variable_name": var_name})

    def _handle_array_op(
        self, session_id: str, config: dict[str, Any], scope: VariableScope, execution_id: UUID | None
    ) -> StepExecutionResult:
        op = config.get("operation", "length").lower()
        var_name = config.get("output_variable", "array_result")
        inp = config.get("array")
        arr = inp if isinstance(inp, list) else []

        if op == "length":
            res_arr: Any = len(arr)
        elif op == "push":
            elem = scope.interpolate(config.get("item"))
            res_arr = list(arr) + [elem]
        elif op == "join":
            sep = config.get("separator", ",")
            res_arr = sep.join(str(x) for x in arr)
        elif op == "slice":
            start_idx = int(config.get("start", 0))
            end_idx = int(config.get("end", len(arr)))
            res_arr = arr[start_idx:end_idx]
        else:
            res_arr = arr

        scope.set(var_name, res_arr)
        return StepExecutionResult(status="passed", result_data={"operation": op, "result": res_arr, "variable_name": var_name})
