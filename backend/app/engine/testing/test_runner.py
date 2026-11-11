"""Deterministic Test Case and Test Suite runner.

Orchestrates parameterized test execution, setup/teardown lifecycle,
13 deterministic assertions, step metrics, and PostgreSQL reporting.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.engine.events import execution_event_bus, ExecutionEventTypes
from backend.app.engine.flows.action_registry import ActionRegistry, StepExecutionResult
from backend.app.engine.flows.variable_scope import VariableScope
from backend.app.engine.testing.assertion_engine import AssertionEngine, AssertionResult
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep
from backend.app.models.execution import Execution, ExecutionLog, ExecutionStep
from backend.app.security.redaction import Redactor

logger = logging.getLogger(__name__)


class TestRunnerError(Exception):
    """Raised on unrecoverable test execution failure."""


class TestRunner:
    """Executes deterministic test cases and suites with setup/teardown and assertion evaluations."""

    __test__ = False

    def __init__(
        self,
        adapter: AgentBrowserAdapter,
        session_manager: SessionManager | None = None,
        db: Session | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        self.adapter = adapter
        self.session_manager = session_manager or getattr(adapter, "session_manager", None) or SessionManager()
        self.db = db
        self.redactor = redactor or Redactor()
        self.action_registry = ActionRegistry(adapter, db=db)
        self.assertion_engine = AssertionEngine(adapter)

    def execute_test_case(
        self,
        execution_id: UUID,
        test_case: TestCaseDefinition,
        test_data_row: dict[str, Any] | None = None,
        session_id: str | None = None,
        manage_session: bool = True,
    ) -> dict[str, Any]:
        """Executes a single test case through setup, action/assertion steps, and teardown."""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise TestRunnerError(f"Execution record {execution_id} not found in database")

        if execution.status == "cancelled":
            logger.info("Execution %s is already cancelled. Aborting.", execution_id)
            return {
                "execution_id": str(execution_id),
                "status": "cancelled",
                "duration_ms": 0.0,
                "summary": execution.summary,
            }

        if manage_session:
            execution.status = "running"
            execution.started_at = datetime.now(timezone.utc)
            self.db.commit()

        # Initialize variable scope with test data
        merged_vars = dict(test_data_row or {})
        scope = VariableScope(initial_vars=merged_vars)

        # Allocate dedicated Agent Browser session if not already provided
        owns_session = False
        if not session_id:
            if execution.session_id:
                session_id = execution.session_id
            else:
                session_context = self.session_manager.create_session(
                    execution_id=str(execution_id),
                    project_id=str(execution.project_id) if execution.project_id else None,
                    user_id=str(execution.triggered_by) if execution.triggered_by else None,
                )
                session_id = getattr(session_context, "session_id", str(session_context))
                execution.session_id = session_id
                self.db.commit()
                owns_session = True
        else:
            if execution.session_id != session_id:
                execution.session_id = session_id
                self.db.commit()

        start_time_mono = time.monotonic()
        step_index: int = 1
        overall_status = "passed"
        assertions_total = 0
        assertions_passed = 0
        assertions_failed = 0
        step_metrics: list[dict[str, Any]] = []

        logger.info(
            "Starting test case execution %s: '%s' in session %s",
            execution_id,
            test_case.name,
            session_id,
        )
        execution_event_bus.publish(
            execution_id,
            ExecutionEventTypes.STATUS_CHANGE,
            {"status": "running", "test_name": test_case.name, "session_id": session_id},
        )

        try:
            # 1. SETUP PHASE
            for step in test_case.setup_steps:
                res = self._execute_step(step, session_id, scope, execution_id, step_index, phase="setup")
                step_metrics.append(res)
                step_index += 1
                if res["status"] == "failed":
                    overall_status = "blocked"
                    raise TestRunnerError(f"Setup step '{step.name}' failed: {res.get('error_message')}")

            # 2. MAIN TEST STEPS & ASSERTIONS PHASE
            for step in test_case.steps:
                # Check for cancellation
                self.db.refresh(execution)
                if execution.status == "cancelled":
                    overall_status = "cancelled"
                    break

                res = self._execute_step(step, session_id, scope, execution_id, step_index, phase="test")
                step_metrics.append(res)
                step_index += 1

                if step.step_type == "assertion":
                    assertions_total += 1
                    if res["status"] == "passed":
                        assertions_passed += 1
                    else:
                        assertions_failed += 1

                if res["status"] == "failed":
                    overall_status = "failed"
                    if step.on_failure == "stop":
                        logger.warning("Step '%s' failed with on_failure='stop'. Halting test execution.", step.name)
                        break

        except Exception as exc:
            logger.exception("Error executing test case %s: %s", execution_id, exc)
            if overall_status != "blocked":
                overall_status = "failed"
        finally:
            # 3. TEARDOWN PHASE (Always executed!)
            for step in test_case.teardown_steps:
                try:
                    res = self._execute_step(step, session_id, scope, execution_id, step_index, phase="teardown")
                    step_metrics.append(res)
                    step_index += 1
                except Exception as td_err:
                    logger.warning("Teardown step '%s' encountered error: %s", step.name, td_err)

            # Cleanup browser session if managed locally
            if manage_session and owns_session and session_id:
                try:
                    self.session_manager.close_session(session_id)
                except Exception as close_err:
                    logger.warning("Error closing test session %s: %s", session_id, close_err)

            total_duration_ms = (time.monotonic() - start_time_mono) * 1000.0

            # Commit final execution report to PostgreSQL if running standalone test case
            if manage_session:
                self.db.refresh(execution)
                if execution.status != "cancelled":
                    execution.status = overall_status
                execution.completed_at = datetime.now(timezone.utc)
                execution.duration_ms = round(total_duration_ms, 2)
                execution.summary = {
                    "outcome": execution.status,
                    "total_steps": len(step_metrics),
                    "passed_steps": sum(1 for s in step_metrics if s["status"] == "passed"),
                    "failed_steps": sum(1 for s in step_metrics if s["status"] == "failed"),
                    "assertions_total": assertions_total,
                    "assertions_passed": assertions_passed,
                    "assertions_failed": assertions_failed,
                }
                self.db.commit()
                execution_event_bus.publish(
                    execution_id,
                    ExecutionEventTypes.STATUS_CHANGE,
                    {
                        "status": execution.status,
                        "duration_ms": execution.duration_ms,
                        "summary": execution.summary,
                    },
                )

        logger.info(
            "Test case %s completed in %.2f ms with outcome '%s' (Assertions: %d/%d passed)",
            execution_id,
            total_duration_ms,
            execution.status,
            assertions_passed,
            assertions_total,
        )

        return {
            "execution_id": str(execution_id),
            "status": execution.status,
            "duration_ms": execution.duration_ms,
            "summary": execution.summary,
        }

    def _execute_step(
        self,
        step: TestStep,
        session_id: str,
        scope: VariableScope,
        execution_id: UUID,
        step_index: int,
        phase: str = "test",
    ) -> dict[str, Any]:
        """Executes a single test step (action or assertion) and writes step results to PostgreSQL."""
        step_start = time.monotonic()
        status_code = "passed"
        error_msg: str | None = None
        screenshot_file: str | None = None
        result_data: dict[str, Any] = {}

        # Resolve target selector if step targets an element
        target_selector: str | None = None
        healed_loc: str | None = None
        if step.target:
            target_dict = step.target.model_dump()
            target_selector, healed_loc = self.action_registry.resolve_target_selector(
                session_id=session_id,
                target_config=target_dict,
                action_name=step.action.value if step.action else "inspect",
                execution_id=execution_id,
            )

        if step.step_type == "action" and step.action:
            action_cfg = dict(step.config)
            if target_selector:
                action_cfg["target"] = {"selector": target_selector}
            if getattr(step, "retries", 0) > 0 and "retries" not in action_cfg:
                action_cfg["retries"] = step.retries
            step_res = self.action_registry.execute_action(
                action=step.action,
                session_id=session_id,
                config=action_cfg,
                scope=scope,
                execution_id=execution_id,
            )
            status_code = step_res.status
            error_msg = step_res.error_message
            result_data = step_res.result_data
            screenshot_file = step_res.screenshot_path

        elif step.step_type == "assertion" and step.assertion:
            interpolated_expected = scope.interpolate(step.expected)
            assert_res: AssertionResult = self.assertion_engine.evaluate_assertion(
                session_id=session_id,
                assertion_type=step.assertion,
                selector=target_selector,
                expected=interpolated_expected,
                attribute_name=step.attribute_name,
            )
            status_code = "passed" if assert_res.passed else "failed"
            error_msg = None if assert_res.passed else assert_res.message
            result_data = {
                "assertion": step.assertion,
                "expected": assert_res.expected,
                "actual": assert_res.actual,
                "message": assert_res.message,
            }

        duration_ms = (time.monotonic() - step_start) * 1000.0

        # Automatic error screenshot capture on failed assertions or actions
        if status_code != "passed" and not screenshot_file:
            try:
                scr = self.adapter.screenshot(session_id)
                screenshot_file = str(getattr(scr, "screenshot_path", scr))
            except Exception as scr_err:
                logger.warning("Could not capture failure screenshot: %s", scr_err)

        # Redact before saving to database
        redacted_config = self.redactor.redact_dict(step.config)
        redacted_result = self.redactor.redact_dict(result_data)

        # Record ExecutionStep in PostgreSQL
        step_record = ExecutionStep(
            execution_id=execution_id,
            step_index=step_index,
            node_id=step.id,
            step_type=f"{phase}:{step.step_type}",
            action=step.action.value if step.action else (step.assertion or "assert"),
            status=status_code,
            input_data=redacted_config,
            result_data=redacted_result,
            error_message=error_msg,
            duration_ms=round(duration_ms, 2),
            screenshot_path=screenshot_file,
        )
        self.db.add(step_record)
        self.db.flush()

        # Index into artifacts table if screenshot file exists on disk
        if screenshot_file and Path(screenshot_file).is_file():
            try:
                from backend.app.reports.artifact_manager import ArtifactManager
                ArtifactManager().save_screenshot_artifact(
                    db=self.db,
                    execution_id=execution_id,
                    screenshot_path=screenshot_file,
                )
            except Exception as art_err:
                logger.warning("Could not index screenshot artifact: %s", art_err)

        # Record ExecutionLog
        log_text = f"[{phase.upper()}] Step {step_index} '{step.name}': {step_record.action} -> {status_code}"
        if error_msg:
            log_text += f" (Failure: {error_msg})"
        exec_log = ExecutionLog(
            execution_id=execution_id,
            step_id=step_record.id,
            level="ERROR" if status_code == "failed" else "INFO",
            message=log_text,
            is_redacted=True,
        )
        self.db.add(exec_log)
        self.db.commit()

        # Stream live execution events
        if screenshot_file:
            execution_event_bus.publish(
                execution_id,
                ExecutionEventTypes.SCREENSHOT_CAPTURED,
                {"step_index": step_index, "screenshot_path": screenshot_file},
            )

        if status_code == "passed":
            execution_event_bus.publish(
                execution_id,
                ExecutionEventTypes.STEP_COMPLETE,
                {
                    "step_index": step_index,
                    "node_id": step.id,
                    "status": "passed",
                    "duration_ms": duration_ms,
                    "result_data": redacted_result,
                },
            )
        else:
            execution_event_bus.publish(
                execution_id,
                ExecutionEventTypes.STEP_FAILED,
                {
                    "step_index": step_index,
                    "node_id": step.id,
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "error_message": error_msg,
                    "screenshot_path": screenshot_file,
                },
            )

        execution_event_bus.publish(
            execution_id,
            ExecutionEventTypes.CONSOLE_LOG,
            {
                "level": "ERROR" if status_code == "failed" else "INFO",
                "message": log_text,
                "step_index": step_index,
                "node_id": step.id,
            },
        )

        return {
            "step_id": step.id,
            "name": step.name,
            "status": status_code,
            "duration_ms": duration_ms,
            "error_message": error_msg,
        }

