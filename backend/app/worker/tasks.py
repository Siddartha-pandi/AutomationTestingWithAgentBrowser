"""Celery worker tasks for deterministic browser flow execution, tests, and schedules.

Strictly zero AI dependencies. Fully isolated subprocess sessions with guaranteed DB recording.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from croniter import croniter

from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import SessionLocal
from backend.app.engine.flows.flow_executor import FlowExecutor
from backend.app.engine.flows.flow_schema import FlowGraphDefinition
from backend.app.engine.testing.test_runner import TestRunner
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestSuiteDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion, Schedule
from backend.app.models.execution import Execution, ExecutionLog, ExecutionStep
from backend.app.security.redaction import Redactor
from backend.app.security.retention import purge_expired_artifacts
from backend.app.worker.celery_app import celery_app
from backend.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="worker.execute_flow", bind=True)
def execute_flow_task(
    self: Any,
    execution_id_str: str,
    initial_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Celery background worker task for executing a visual flow graph."""
    execution_id = UUID(execution_id_str)
    db = SessionLocal()
    session_manager = SessionManager()
    session_id: str | None = None
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("Execution record %s not found in database", execution_id)
            return {"status": "error", "message": f"Execution {execution_id} not found"}

        version = (
            db.query(DefinitionVersion)
            .filter(DefinitionVersion.id == execution.definition_version_id)
            .first()
        )
        if not version:
            raise ValueError(f"DefinitionVersion {execution.definition_version_id} not found")

        flow_graph = FlowGraphDefinition.model_validate(version.definition_json)

        # Create isolated browser session
        session_id = session_manager.create_session(
            user_id=str(execution.triggered_by or "system_worker")
        )
        adapter = AgentBrowserAdapter(session_id=session_id)

        executor = FlowExecutor(
            adapter=adapter,
            session_manager=session_manager,
            db=db,
            redactor=Redactor(),
        )

        result = executor.execute_flow(
            execution_id=execution_id,
            flow_graph=flow_graph,
            initial_variables=initial_variables,
        )
        return result
    except Exception as err:
        logger.exception("Failed executing flow task for execution %s: %s", execution_id, err)
        try:
            exec_rec = db.query(Execution).filter(Execution.id == execution_id).first()
            if exec_rec and exec_rec.status not in ("completed", "failed"):
                exec_rec.status = "failed"
                exec_rec.completed_at = datetime.now(timezone.utc)
                exec_rec.summary = {"error": str(err), "success": False}
                db.commit()
        except Exception:
            pass
        raise
    finally:
        if session_id:
            try:
                session_manager.close_session(session_id)
            except Exception:
                pass
        db.close()


@celery_app.task(name="worker.execute_test_case", bind=True)
def execute_test_case_task(
    self: Any,
    execution_id_str: str,
    test_data_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Celery background worker task for executing a deterministic test case."""
    execution_id = UUID(execution_id_str)
    db = SessionLocal()
    session_manager = SessionManager()
    session_id: str | None = None
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("Execution record %s not found in database", execution_id)
            return {"status": "error", "message": f"Execution {execution_id} not found"}

        version = (
            db.query(DefinitionVersion)
            .filter(DefinitionVersion.id == execution.definition_version_id)
            .first()
        )
        if not version:
            raise ValueError(f"DefinitionVersion {execution.definition_version_id} not found")

        test_case = TestCaseDefinition.model_validate(version.definition_json)

        session_id = session_manager.create_session(
            user_id=str(execution.triggered_by or "system_worker")
        )
        adapter = AgentBrowserAdapter(session_id=session_id)

        runner = TestRunner(
            adapter=adapter,
            session_manager=session_manager,
            db=db,
            redactor=Redactor(),
        )

        result = runner.execute_test_case(
            execution_id=execution_id,
            test_case=test_case,
            test_data_row=test_data_row,
        )
        return result
    except Exception as err:
        logger.exception("Failed executing test case task for execution %s: %s", execution_id, err)
        try:
            exec_rec = db.query(Execution).filter(Execution.id == execution_id).first()
            if exec_rec and exec_rec.status not in ("completed", "passed", "failed"):
                exec_rec.status = "failed"
                exec_rec.completed_at = datetime.now(timezone.utc)
                exec_rec.summary = {"error": str(err), "success": False}
                db.commit()
        except Exception:
            pass
        raise
    finally:
        if session_id:
            try:
                session_manager.close_session(session_id)
            except Exception:
                pass
        db.close()


@celery_app.task(name="worker.execute_test_suite", bind=True)
def execute_test_suite_task(
    self: Any,
    execution_id_str: str,
) -> dict[str, Any]:
    """Celery background worker task for executing a regression test suite."""
    execution_id = UUID(execution_id_str)
    db = SessionLocal()
    session_manager = SessionManager()
    session_id: str | None = None
    try:
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            logger.error("Execution record %s not found in database", execution_id)
            return {"status": "error", "message": f"Execution {execution_id} not found"}

        version = (
            db.query(DefinitionVersion)
            .filter(DefinitionVersion.id == execution.definition_version_id)
            .first()
        )
        if not version:
            raise ValueError(f"DefinitionVersion {execution.definition_version_id} not found")

        test_suite = TestSuiteDefinition.model_validate(version.definition_json)

        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        db.commit()

        session_id = session_manager.create_session(
            user_id=str(execution.triggered_by or "system_worker")
        )
        adapter = AgentBrowserAdapter(session_id=session_id)

        runner = TestRunner(
            adapter=adapter,
            session_manager=session_manager,
            db=db,
            redactor=Redactor(),
        )

        suite_results = []
        overall_passed = True

        for tc_id in test_suite.test_case_ids:
            tc_def = (
                db.query(AutomationDefinition)
                .filter(AutomationDefinition.id == tc_id)
                .first()
            )
            if not tc_def or not tc_def.current_version_id:
                suite_results.append({
                    "test_case_id": str(tc_id),
                    "status": "failed",
                    "error": "Test case definition or active version not found",
                })
                overall_passed = False
                continue

            tc_version = (
                db.query(DefinitionVersion)
                .filter(DefinitionVersion.id == tc_def.current_version_id)
                .first()
            )
            parsed_tc = TestCaseDefinition.model_validate(tc_version.definition_json)

            tc_res = runner.execute_test_case(
                execution_id=execution.id,
                test_case=parsed_tc,
            )
            suite_results.append({
                "test_case_id": str(tc_id),
                "name": parsed_tc.name,
                "status": tc_res.get("status"),
                "passed": tc_res.get("passed"),
            })
            if not tc_res.get("passed"):
                overall_passed = False

        execution.status = "completed" if overall_passed else "failed"
        execution.completed_at = datetime.now(timezone.utc)
        execution.summary = {
            "suite_name": test_suite.name,
            "total_cases": len(test_suite.test_case_ids),
            "passed": overall_passed,
            "case_results": suite_results,
        }
        db.commit()
        return execution.summary
    except Exception as err:
        logger.exception("Failed executing test suite task for execution %s: %s", execution_id, err)
        try:
            exec_rec = db.query(Execution).filter(Execution.id == execution_id).first()
            if exec_rec and exec_rec.status not in ("completed", "failed"):
                exec_rec.status = "failed"
                exec_rec.completed_at = datetime.now(timezone.utc)
                exec_rec.summary = {"error": str(err), "passed": False}
                db.commit()
        except Exception:
            pass
        raise
    finally:
        if session_id:
            try:
                session_manager.close_session(session_id)
            except Exception:
                pass
        db.close()


@celery_app.task(name="worker.schedule_checker")
def schedule_checker_task() -> dict[str, Any]:
    """Celery Beat periodic task evaluating automation schedules and dispatching runs."""
    db = SessionLocal()
    triggered: list[str] = []
    try:
        now = datetime.now(timezone.utc)
        active_schedules = db.query(Schedule).filter(Schedule.is_enabled == True).all()

        for sched in active_schedules:
            try:
                tz_name = sched.timezone or settings.default_timezone
                try:
                    tz = ZoneInfo(tz_name)
                except Exception:
                    tz = timezone.utc

                local_now = now.astimezone(tz)
                base_time = (
                    sched.last_run_at.astimezone(tz)
                    if sched.last_run_at
                    else (local_now - timedelta(minutes=1))
                )

                cron = croniter(sched.cron_expression, base_time)
                next_fire = cron.get_next(datetime)
                if next_fire.tzinfo is None:
                    next_fire = next_fire.replace(tzinfo=tz)

                if next_fire <= local_now:
                    definition = (
                        db.query(AutomationDefinition)
                        .filter(AutomationDefinition.id == sched.definition_id)
                        .first()
                    )
                    if not definition or not definition.current_version_id:
                        continue

                    # Create Execution record
                    new_exec = Execution(
                        project_id=definition.project_id,
                        definition_id=definition.id,
                        definition_version_id=definition.current_version_id,
                        environment_id=sched.environment_id,
                        trigger_type="scheduled",
                        status="queued",
                        summary={
                            "schedule_id": str(sched.id),
                            "cron_expression": sched.cron_expression,
                        },
                    )
                    db.add(new_exec)
                    db.flush()

                    # Dispatch to Celery background workers
                    if definition.type == "flow":
                        execute_flow_task.delay(str(new_exec.id))
                    else:
                        execute_test_case_task.delay(str(new_exec.id))

                    sched.last_run_at = now
                    sched.next_run_at = croniter(sched.cron_expression, local_now).get_next(datetime)
                    triggered.append(str(new_exec.id))
            except Exception as sched_err:
                logger.error("Error evaluating schedule %s: %s", sched.id, sched_err)

        db.commit()
        return {
            "evaluated_count": len(active_schedules),
            "triggered_count": len(triggered),
            "executions": triggered,
        }
    finally:
        db.close()


@celery_app.task(name="worker.cleanup_retention")
def cleanup_retention_task(retention_days: int = 30) -> dict[str, int]:
    """Periodic retention task to purge stale artifacts and screenshots."""
    db = SessionLocal()
    try:
        counts = purge_expired_artifacts(db, screenshot_days=retention_days)
        return counts
    finally:
        db.close()
