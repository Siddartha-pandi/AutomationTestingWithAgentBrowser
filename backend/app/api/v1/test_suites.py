"""Test Suite management and regression execution endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.v1.flows import compute_definition_checksum
from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import get_db
from backend.app.engine.testing.test_runner import TestRunner
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestSuiteDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.project import Project, ProjectMember
from backend.app.api.v1.projects import resolve_project_id
from backend.app.schemas.flows import ExecutionDetailResponse
from backend.app.schemas.testing import ExecuteTestRequest, TestSuiteCreateRequest, TestSuiteResponse
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-suites", tags=["Test Suites & Regression"])


@router.post("", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
def create_test_suite(
    payload: TestSuiteCreateRequest,
    request: Request,
    current_user=Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> TestSuiteResponse:
    """Creates a new test suite aggregating multiple test cases for regression."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Serialize with string UUIDs
    suite_dict = payload.test_suite.model_dump(mode="json")
    checksum = compute_definition_checksum(suite_dict)

    automation = AutomationDefinition(
        project_id=project.id,
        type="test_suite",
        name=payload.name,
        description=payload.description,
        status="published",
        created_by=current_user.id,
    )
    db.add(automation)
    db.flush()

    version = DefinitionVersion(
        definition_id=automation.id,
        version_num=1,
        definition_json=suite_dict,
        checksum_sha256=checksum,
        is_published=True,
        published_by=current_user.id,
    )
    db.add(version)
    db.flush()

    automation.current_version_id = version.id

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test_suite:create",
        resource_type="automation_definition",
        resource_id=str(automation.id),
        client_ip=request.client.host if request.client else None,
        details={"name": automation.name, "test_cases_count": len(payload.test_suite.test_case_ids)},
    )

    db.commit()
    db.refresh(automation)

    return TestSuiteResponse(
        id=automation.id,
        project_id=automation.project_id,
        name=automation.name,
        description=automation.description,
        status=automation.status,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
        definition=suite_dict,
    )


@router.get("", response_model=list[TestSuiteResponse])
def list_test_suites(
    project_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("tests:read", "tests:create_edit", "reports:read")),
    db: Session = Depends(get_db),
) -> list[TestSuiteResponse]:
    """Lists all configured regression test suites."""
    query = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.type == "test_suite")
        .options(joinedload(AutomationDefinition.versions))
    )
    if project_id:
        proj = resolve_project_id(db, project_id, current_user.id)
        if proj:
            query = query.filter(AutomationDefinition.project_id == proj.id)
        else:
            return []
    elif not getattr(current_user, "is_superuser", False):
        user_projects = (
            db.query(Project.id)
            .filter(
                (Project.owner_id == current_user.id)
                | (Project.members.any(ProjectMember.user_id == current_user.id))
            )
            .subquery()
        )
        query = query.filter(AutomationDefinition.project_id.in_(user_projects))

    suites = query.order_by(AutomationDefinition.updated_at.desc()).offset(offset).limit(limit).all()
    results = []
    for s in suites:
        latest_ver = s.versions[0] if s.versions else None
        results.append(
            TestSuiteResponse(
                id=s.id,
                project_id=s.project_id,
                name=s.name,
                description=s.description,
                status=s.status,
                created_at=s.created_at,
                updated_at=s.updated_at,
                definition=latest_ver.definition_json if latest_ver else None,
            )
        )
    return results


@router.get("/{suite_id}", response_model=TestSuiteResponse)
def get_test_suite(
    suite_id: UUID,
    current_user=Depends(require_permission("tests:read", "tests:create_edit", "reports:read")),
    db: Session = Depends(get_db),
) -> TestSuiteResponse:
    """Retrieves full test suite details and member test case definitions."""
    suite = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == suite_id, AutomationDefinition.type == "test_suite")
        .first()
    )
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    latest_ver = suite.versions[0] if suite.versions else None
    return TestSuiteResponse(
        id=suite.id,
        project_id=suite.project_id,
        name=suite.name,
        description=suite.description,
        status=suite.status,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
        definition=latest_ver.definition_json if latest_ver else None,
    )


@router.post("/{suite_id}/execute", response_model=ExecutionDetailResponse)
def execute_test_suite_endpoint(
    suite_id: UUID,
    payload: ExecuteTestRequest,
    request: Request,
    current_user=Depends(require_permission("tests:execute", "executions:trigger")),
    db: Session = Depends(get_db),
) -> ExecutionDetailResponse:
    """Executes a full regression test suite running all member test cases in isolated sessions."""
    suite = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == suite_id, AutomationDefinition.type == "test_suite")
        .first()
    )
    if not suite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    if not suite.versions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test suite has no valid definition")

    target_version = suite.versions[0]
    suite_def = TestSuiteDefinition.model_validate(target_version.definition_json)

    # 1. Create top-level Suite Execution record
    suite_execution = Execution(
        project_id=suite.project_id,
        definition_id=suite.id,
        definition_version_id=target_version.id,
        environment_id=payload.environment_id,
        trigger_type="manual",
        triggered_by=current_user.id,
        status="running",
        summary={},
    )
    db.add(suite_execution)
    db.commit()
    db.refresh(suite_execution)

    adapter = AgentBrowserAdapter()
    session_mgr = SessionManager()
    runner = TestRunner(adapter=adapter, session_manager=session_mgr, db=db)

    # 2. Iterate through each member test case
    cases_passed = 0
    cases_failed = 0
    test_case_results = []

    for tc_uuid in suite_def.test_case_ids:
        tc_record = (
            db.query(AutomationDefinition)
            .options(joinedload(AutomationDefinition.versions))
            .filter(AutomationDefinition.id == tc_uuid)
            .first()
        )
        if not tc_record or not tc_record.versions:
            continue

        tc_ver = tc_record.versions[0]
        tc_def = TestCaseDefinition.model_validate(tc_ver.definition_json)

        # Run member test case
        case_run = runner.execute_test_case(
            execution_id=suite_execution.id,
            test_case=tc_def,
            test_data_row=payload.test_data_row,
        )
        test_case_results.append(case_run)

        if case_run["status"] == "passed":
            cases_passed += 1
        else:
            cases_failed += 1
            if suite_def.stop_on_failure:
                break

    # 3. Finalize Suite Execution summary
    suite_execution.status = "passed" if cases_failed == 0 else "failed"
    suite_execution.completed_at = datetime.now(timezone.utc)
    suite_execution.summary = {
        "cases_total": len(suite_def.test_case_ids),
        "cases_executed": len(test_case_results),
        "cases_passed": cases_passed,
        "cases_failed": cases_failed,
    }
    db.commit()
    db.refresh(suite_execution)

    execution_detail = (
        db.query(Execution)
        .options(joinedload(Execution.steps), joinedload(Execution.logs))
        .filter(Execution.id == suite_execution.id)
        .first()
    )

    return ExecutionDetailResponse.model_validate(execution_detail)

