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


class ActionRegistry:
    """Central registry of deterministic browser and control flow action handlers."""

    def __init__(self, adapter: AgentBrowserAdapter, db: Session | None = None) -> None:
        self.adapter = adapter
        self.db = db
        self.healing_engine = SelfHealingEngine(adapter, db=db)

    def resolve_target_selector(
        self,
        session_id: str,
        target_config: dict[str, Any],
        action_name: str = "click",
        execution_id: UUID | None = None,
        is_destructive: bool = False,
    ) -> tuple[str, str | None]:
        """Resolves resilient locator using element profiles and deterministic self-healing if needed.

        Returns (resolved_selector, healed_locator_or_None).
        """
        logical_id = target_config.get("logical_id")
        element_profile_id = target_config.get("element_profile_id")
        raw_selector = target_config.get("selector") or ""

        # 1. Direct selector test if no profile configured
        if not logical_id and not element_profile_id:
            if not raw_selector:
                raise ElementNotFoundError("No target selector or logical ID specified in action config")
            return raw_selector, None

        # 2. Look up element profile from database if available
        profile_record: ElementProfile | None = None
        if self.db:
            if element_profile_id:
                try:
                    profile_uuid = UUID(str(element_profile_id))
                    profile_record = self.db.query(ElementProfile).filter(ElementProfile.id == profile_uuid).first()
                except ValueError:
                    pass
            elif logical_id:
                profile_record = self.db.query(ElementProfile).filter(ElementProfile.logical_id == logical_id).first()

        # If profile found, attempt preferred / historical locators first
        active_selector = raw_selector
        if profile_record and profile_record.history:
            # Try top verified selector
            top_historical = profile_record.history[0].locator_value
            if self.adapter.is_visible(session_id, top_historical):
                return top_historical, None

        if active_selector and self.adapter.is_visible(session_id, active_selector):
            return active_selector, None

        # 3. If selector is not visible or changed, trigger Deterministic Self-Healing!
        if profile_record:
            logger.info("Target selector '%s' not visible. Initiating deterministic self-healing...", active_selector)
            history_list = [
                {"locator_type": h.locator_type, "locator_value": h.locator_value, "success_count": h.success_count}
                for h in profile_record.history
            ]
            profile_data = ElementProfileData(
                logical_id=profile_record.logical_id,
                description=profile_record.description or "",
                element_type=profile_record.element_type,
                page_context=profile_record.page_context,
                original_text=profile_record.original_text,
                role=profile_record.structural_fingerprint.get("role") if profile_record.structural_fingerprint else None,
                accessible_name=profile_record.structural_fingerprint.get("accessible_name") if profile_record.structural_fingerprint else None,
                stable_attributes=profile_record.stable_attributes or {},
                structural_fingerprint=profile_record.structural_fingerprint or {},
                historical_locators=history_list,
            )

            heal_result = self.healing_engine.resolve_element(
                session_id=session_id,
                profile=profile_data,
                original_locator=active_selector or profile_record.logical_id,
                action=action_name,
                is_destructive=is_destructive,
                execution_id=execution_id,
                element_profile_id=profile_record.id,
            )

            if heal_result.success and heal_result.healed_locator:
                logger.info(
                    "Deterministic self-healing recovered element with locator '%s' (Confidence: %.1f%%)",
                    heal_result.healed_locator,
                    heal_result.confidence_score * 100.0,
                )
                return heal_result.healed_locator, heal_result.healed_locator
            elif heal_result.decision == "requires_approval":
                raise BrowserActionError(
                    f"Self-healing confidence score ({heal_result.confidence_score*100:.1f}%) requires human approval before executing action."
                )
            else:
                raise ElementNotFoundError(
                    f"Deterministic element recognition failed: {heal_result.error_message}"
                )

        if not active_selector:
            raise ElementNotFoundError(f"Element '{logical_id}' could not be resolved on current page")

        return active_selector, None

    def execute_action(
        self,
        action: FlowActionType,
        session_id: str,
        config: dict[str, Any],
        scope: VariableScope,
        execution_id: UUID | None = None,
    ) -> StepExecutionResult:
        """Dispatches action execution deterministically."""
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
            FlowActionType.EXTRACT_TEXT: self._handle_extract_text,
            FlowActionType.EXTRACT_ATTRIBUTE: self._handle_extract_attribute,
            FlowActionType.EXTRACT_TABLE: self._handle_extract_table,
            FlowActionType.WAIT: self._handle_wait,
            FlowActionType.WAIT_UNTIL: self._handle_wait_until,
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

        try:
            return handler(session_id, config, scope, execution_id)
        except Exception as err:
            logger.error("Error executing action '%s': %s", action.value, err)
            return StepExecutionResult(status="failed", error_message=str(err))

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
        # Double click via double dispatch
        self.adapter.click(session_id, selector=selector)
        time.sleep(0.1)
        self.adapter.click(session_id, selector=selector)
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

        start = time.time()
        deadline = start + (timeout_ms / 1000.0)
        matched = False
        while time.time() < deadline:
            if condition_type == "visible" and self.adapter.is_visible(session_id, raw_selector):
                matched = True
                break
            elif condition_type == "hidden" and not self.adapter.is_visible(session_id, raw_selector):
                matched = True
                break
            elif condition_type == "enabled" and self.adapter.is_enabled(session_id, raw_selector):
                matched = True
                break
            time.sleep(0.5)

        if not matched:
            raise BrowserActionError(f"Wait until condition '{condition_type}' timed out on selector '{raw_selector}'")

        return StepExecutionResult(status="passed", result_data={"selector": raw_selector, "matched": True})

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
