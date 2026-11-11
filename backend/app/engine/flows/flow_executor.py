"""Deterministic visual workflow execution engine.

Traverses React Flow DAG graphs, evaluates branching, executes browser actions,
records step logs, and persists execution artifacts into PostgreSQL.
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
from backend.app.engine.flows.action_registry import ActionRegistry, StepExecutionResult
from backend.app.engine.flows.flow_schema import FlowGraphDefinition, FlowNode
from backend.app.engine.flows.variable_scope import VariableScope
from backend.app.engine.events import execution_event_bus, ExecutionEventTypes
from backend.app.models.execution import Execution, ExecutionLog, ExecutionStep
from backend.app.security.redaction import Redactor

logger = logging.getLogger(__name__)


class FlowExecutionError(Exception):
    """Raised when workflow graph execution encounters an unrecoverable error."""


class FlowExecutor:
    """Executes validated visual workflow DAGs with deterministic state tracking and PostgreSQL step logging."""

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

    def execute_flow(
        self,
        execution_id: UUID,
        flow_graph: FlowGraphDefinition,
        initial_variables: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Runs a complete visual workflow graph from start_node_id to termination."""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise FlowExecutionError(f"Execution record {execution_id} not found in database")

        if execution.status == "cancelled":
            logger.info("Execution %s is already cancelled. Aborting.", execution_id)
            return {
                "execution_id": str(execution_id),
                "status": "cancelled",
                "duration_ms": 0.0,
                "summary": execution.summary,
            }

        # Initialize execution metadata
        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        self.db.commit()

        # Build node and edge lookup tables
        node_map: dict[str, FlowNode] = {n.id: n for n in flow_graph.nodes}
        outgoing_edges: dict[str, list[Any]] = {}
        for edge in flow_graph.edges:
            outgoing_edges.setdefault(edge.source, []).append(edge)

        # Initialize variable scope
        merged_vars = dict(flow_graph.variables)
        if initial_variables:
            merged_vars.update(initial_variables)
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

        # Validate graph topology before execution
        if not flow_graph.nodes:
            raise FlowExecutionError("Flow graph contains no nodes")
        if flow_graph.start_node_id not in node_map:
            raise FlowExecutionError(f"Start node ID '{flow_graph.start_node_id}' does not exist in graph")
        for edge in flow_graph.edges:
            if edge.source not in node_map or edge.target not in node_map:
                raise FlowExecutionError(f"Edge '{edge.id}' connects non-existent node: {edge.source} -> {edge.target}")

        start_time_mono = time.monotonic()
        current_node_id: str | None = flow_graph.start_node_id
        step_index: int = 1
        max_step_limit: int = int(flow_graph.variables.get("__max_steps__", 500))
        loop_state: dict[str, int] = {}
        overall_status = "passed"
        steps_summary: list[dict[str, Any]] = []

        logger.info(
            "Starting execution %s for flow '%s' in session %s",
            execution_id,
            flow_graph.name,
            session_id,
        )
        execution_event_bus.publish(
            execution_id,
            ExecutionEventTypes.STATUS_CHANGE,
            {"status": "running", "flow_name": flow_graph.name, "session_id": session_id},
        )

        try:
            # Traversal loop (with safety circuit breaker to prevent infinite cycles)
            while current_node_id and step_index <= max_step_limit:
                # Check for operator cancellation
                self.db.refresh(execution)
                if execution.status == "cancelled":
                    logger.warning("Execution %s cancelled by operator", execution_id)
                    overall_status = "cancelled"
                    break

                node = node_map.get(current_node_id)
                if not node:
                    logger.error("Node ID '%s' not found in graph definition", current_node_id)
                    overall_status = "failed"
                    break

                execution_event_bus.publish(
                    execution_id,
                    ExecutionEventTypes.STEP_START,
                    {
                        "step_index": step_index,
                        "node_id": node.id,
                        "step_type": node.type,
                        "action": node.action.value if node.action else node.type,
                    },
                )

                step_start = time.monotonic()
                step_result: StepExecutionResult

                # Execute action node
                if node.type == "action" and node.action:
                    # Retry loop support
                    attempts = 0
                    max_attempts = 1 + (node.retry_count if node.on_error == "retry" else 0)
                    while attempts < max_attempts:
                        attempts += 1
                        step_result = self.action_registry.execute_action(
                            action=node.action,
                            session_id=session_id,
                            config=node.config,
                            scope=scope,
                            execution_id=execution_id,
                        )
                        if step_result.status == "passed":
                            break
                        if attempts < max_attempts:
                            time.sleep(0.5)

                elif node.type == "condition":
                    step_result = self.action_registry.execute_action(
                        action=node.action or FlowActionType.CONDITION,  # type: ignore
                        session_id=session_id,
                        config=node.config,
                        scope=scope,
                        execution_id=execution_id,
                    )
                elif node.type == "loop":
                    loop_count = loop_state.get(node.id, 0) + 1
                    loop_state[node.id] = loop_count
                    max_iterations = int(node.config.get("iterations", node.config.get("max_iterations", 10)))
                    safety_limit = min(max_iterations, int(node.config.get("safety_limit", 100)))

                    var_name = node.config.get("loop_variable", f"loop_index_{node.id}")
                    scope.set(var_name, loop_count)

                    if loop_count <= safety_limit:
                        step_result = StepExecutionResult(
                            status="passed",
                            result_data={"iteration": loop_count, "max_iterations": safety_limit, "variable": var_name},
                            next_handle="loop_body",
                        )
                    else:
                        step_result = StepExecutionResult(
                            status="passed",
                            result_data={"iterations_completed": loop_count - 1, "max_iterations": safety_limit},
                            next_handle="loop_exit",
                        )
                elif node.type == "branch":
                    step_result = self.action_registry.execute_action(
                        action=FlowActionType.SWITCH,
                        session_id=session_id,
                        config=node.config,
                        scope=scope,
                        execution_id=execution_id,
                    )
                elif node.type == "trigger":
                    step_result = StepExecutionResult(status="passed", result_data={"triggered": True, "config": node.config})
                elif node.type == "stop":
                    step_result = StepExecutionResult(status="passed", result_data={"stopped": True}, next_handle="stop")
                else:
                    step_result = StepExecutionResult(status="failed", error_message=f"Unsupported node type: '{node.type}'")

                duration_ms = (time.monotonic() - step_start) * 1000.0

                # Capture screenshot on failure if not already captured
                screenshot_file = step_result.screenshot_path
                if step_result.status != "passed" and not screenshot_file:
                    try:
                        err_screen = self.adapter.screenshot(session_id)
                        screenshot_file = str(getattr(err_screen, "screenshot_path", err_screen))
                    except Exception as scr_err:
                        logger.warning("Could not capture error screenshot: %s", scr_err)

                # Store output in scope for subsequent steps
                scope.set_step_output(node.id, step_result.result_data)

                # Redact inputs and results before DB persistence
                redacted_input = self.redactor.redact_dict(node.config)
                redacted_result = self.redactor.redact_dict(step_result.result_data)

                # Record ExecutionStep in PostgreSQL
                step_record = ExecutionStep(
                    execution_id=execution_id,
                    step_index=step_index,
                    node_id=node.id,
                    step_type=node.type,
                    action=node.action.value if node.action else node.type,
                    status=step_result.status,
                    input_data=redacted_input,
                    result_data=redacted_result,
                    error_message=step_result.error_message,
                    duration_ms=round(duration_ms, 2),
                    screenshot_path=screenshot_file,
                )
                self.db.add(step_record)
                self.db.flush()

                # Index into artifacts table if screenshot was saved to disk
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
                log_msg = f"Step {step_index} [{node.id}]: {node.action.value if node.action else node.type} -> {step_result.status}"
                if step_result.error_message:
                    log_msg += f" (Error: {step_result.error_message})"
                exec_log = ExecutionLog(
                    execution_id=execution_id,
                    step_id=step_record.id,
                    level="ERROR" if step_result.status == "failed" else "INFO",
                    message=log_msg,
                    is_redacted=True,
                )
                self.db.add(exec_log)
                self.db.commit()

                # Stream live execution events to subscribers
                if screenshot_file:
                    execution_event_bus.publish(
                        execution_id,
                        ExecutionEventTypes.SCREENSHOT_CAPTURED,
                        {"step_index": step_index, "screenshot_path": screenshot_file},
                    )

                if step_result.status == "passed":
                    execution_event_bus.publish(
                        execution_id,
                        ExecutionEventTypes.STEP_COMPLETE,
                        {
                            "step_index": step_index,
                            "node_id": node.id,
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
                            "node_id": node.id,
                            "status": step_result.status,
                            "duration_ms": duration_ms,
                            "error_message": step_result.error_message,
                            "screenshot_path": screenshot_file,
                        },
                    )

                execution_event_bus.publish(
                    execution_id,
                    ExecutionEventTypes.CONSOLE_LOG,
                    {
                        "level": "ERROR" if step_result.status == "failed" else "INFO",
                        "message": log_msg,
                        "step_index": step_index,
                        "node_id": node.id,
                    },
                )

                steps_summary.append({
                    "step_index": step_index,
                    "node_id": node.id,
                    "status": step_result.status,
                    "duration_ms": duration_ms,
                })

                # Handle failure / error policy
                if step_result.status == "failed":
                    if node.on_error == "stop":
                        overall_status = "failed"
                        logger.warning("Step %s failed with on_error='stop'. Halting execution.", node.id)
                        break
                    elif node.on_error == "continue":
                        logger.info("Step %s failed with on_error='continue'. Proceeding to next step.", node.id)

                if step_result.next_handle == "stop":
                    logger.info("Step %s emitted stop signal. Halting execution normally.", node.id)
                    break

                # Resolve next node via graph edges
                edges = outgoing_edges.get(node.id, [])
                if not edges:
                    current_node_id = None
                    break

                if node.type in ("condition", "loop", "branch"):
                    # Match handle ('true', 'false', 'loop_body', 'loop_exit', etc.)
                    matched_edge = next((e for e in edges if e.source_handle == step_result.next_handle), None)
                    if not matched_edge:
                        if step_result.next_handle == "loop_exit":
                            matched_edge = next((e for e in edges if e.source_handle != "loop_body"), None)
                        elif step_result.next_handle in ("true", "false", "default"):
                            matched_edge = next((e for e in edges if e.source_handle in (None, "default")), None)
                    current_node_id = matched_edge.target if matched_edge else None
                else:
                    # Single default edge
                    current_node_id = edges[0].target

                step_index += 1

            if step_index > max_step_limit:
                logger.error("Execution %s exceeded maximum step limit (%d steps)", execution_id, max_step_limit)
                overall_status = "failed"

        except Exception as exc:
            logger.exception("Fatal unhandled exception during flow execution %s: %s", execution_id, exc)
            overall_status = "failed"
            # Log fatal error
            fatal_log = ExecutionLog(
                execution_id=execution_id,
                level="ERROR",
                message=f"Fatal unhandled exception: {exc}",
                is_redacted=True,
            )
            self.db.add(fatal_log)
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
        finally:
            if owns_session and session_id:
                # Terminate and cleanup isolated Agent Browser session
                try:
                    self.session_manager.close_session(session_id)
                except Exception as close_err:
                    logger.warning("Error closing browser session %s: %s", session_id, close_err)

            total_duration_ms = (time.monotonic() - start_time_mono) * 1000.0

            # Update final Execution status in PostgreSQL
            self.db.refresh(execution)
            if execution.status != "cancelled":
                execution.status = overall_status
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = round(total_duration_ms, 2)
            execution.summary = {
                "total_steps": step_index,
                "passed_steps": sum(1 for s in steps_summary if s["status"] == "passed"),
                "failed_steps": sum(1 for s in steps_summary if s["status"] == "failed"),
                "variables": self.redactor.redact_dict(scope.get_all_variables()),
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
            "Completed execution %s in %.2f ms with final status '%s'",
            execution_id,
            total_duration_ms,
            execution.status,
        )

        return {
            "execution_id": str(execution_id),
            "status": execution.status,
            "duration_ms": execution.duration_ms,
            "summary": execution.summary,
        }

