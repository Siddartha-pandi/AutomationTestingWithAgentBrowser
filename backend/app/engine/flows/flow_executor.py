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
        session_manager: SessionManager,
        db: Session,
        redactor: Redactor | None = None,
    ) -> None:
        self.adapter = adapter
        self.session_manager = session_manager
        self.db = db
        self.redactor = redactor or Redactor()
        self.action_registry = ActionRegistry(adapter, db=db)

    def execute_flow(
        self,
        execution_id: UUID,
        flow_graph: FlowGraphDefinition,
        initial_variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Runs a complete visual workflow graph from start_node_id to termination."""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise FlowExecutionError(f"Execution record {execution_id} not found in database")

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

        # Allocate dedicated Agent Browser session
        session_context = self.session_manager.create_session()
        session_id = getattr(session_context, "session_id", str(session_context))
        execution.session_id = session_id
        self.db.commit()

        start_time_mono = time.monotonic()
        current_node_id: str | None = flow_graph.start_node_id
        step_index: int = 1
        overall_status = "passed"
        steps_summary: list[dict[str, Any]] = []

        logger.info(
            "Starting execution %s for flow '%s' in session %s",
            execution_id,
            flow_graph.name,
            session_id,
        )

        try:
            # Traversal loop (with safety circuit breaker at 500 steps to prevent infinite cycles)
            while current_node_id and step_index <= 500:
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
                        action=node.action or "condition",  # type: ignore
                        session_id=session_id,
                        config=node.config,
                        scope=scope,
                        execution_id=execution_id,
                    )
                elif node.type == "stop":
                    step_result = StepExecutionResult(status="passed", result_data={"stopped": True}, next_handle="stop")
                else:
                    step_result = StepExecutionResult(status="passed", result_data={"type": node.type})

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

                if node.type == "condition":
                    # Branch based on 'true' or 'false' handle
                    matched_edge = next((e for e in edges if e.source_handle == step_result.next_handle), None)
                    current_node_id = matched_edge.target if matched_edge else None
                else:
                    # Single default edge
                    current_node_id = edges[0].target

                step_index += 1

            if step_index > 500:
                logger.error("Execution %s exceeded maximum safe loop limit (500 steps)", execution_id)
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
        finally:
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

