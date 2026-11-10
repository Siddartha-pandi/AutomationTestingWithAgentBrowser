"""Test automation endpoints for creating, managing, seeding, and executing test cases."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.api.v1.flows import compute_definition_checksum
from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import get_db
from backend.app.engine.testing.legacy_migration import seed_legacy_test_cases
from backend.app.engine.testing.test_runner import TestRunner
from backend.app.engine.testing.test_schema import TestCaseDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.project import Project
from backend.app.api.v1.projects import resolve_project_id
from backend.app.schemas.flows import ExecutionDetailResponse, PublishVersionResponse
from backend.app.schemas.testing import (
    ExecuteTestRequest,
    SeedLegacyTestsRequest,
    TestCaseCreateRequest,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tests", tags=["Testing Automation"])


@router.post("", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreateRequest,
    request: Request,
    current_user=Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Creates a new deterministic test case definition draft."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    def_dict = payload.test_case.model_dump()
    checksum = compute_definition_checksum(def_dict)

    # 1. Create AutomationDefinition record of type 'test'
    automation = AutomationDefinition(
        project_id=project.id,
        type="test",
        name=payload.name,
        description=payload.description,
        status="draft",
        created_by=current_user.id,
    )
    db.add(automation)
    db.flush()

    # 2. Create initial draft version
    version = DefinitionVersion(
        definition_id=automation.id,
        version_num=1,
        definition_json=def_dict,
        checksum_sha256=checksum,
        is_published=False,
    )
    db.add(version)
    db.flush()

    automation.current_version_id = version.id

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test:create",
        resource_type="automation_definition",
        resource_id=str(automation.id),
        client_ip=request.client.host if request.client else None,
        details={"name": automation.name, "project_id": str(payload.project_id)},
    )

    db.commit()
    db.refresh(automation)

    return TestCaseResponse(
        id=automation.id,
        project_id=automation.project_id,
        type=automation.type,
        name=automation.name,
        description=automation.description,
        status=automation.status,
        current_version_id=automation.current_version_id,
        created_by=automation.created_by,
        created_at=automation.created_at,
        updated_at=automation.updated_at,
        definition=def_dict,
        version_count=1,
    )


@router.get("", response_model=list[TestCaseResponse])
def list_test_cases(
    project_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("tests:read", "tests:create_edit", "reports:read")),
    db: Session = Depends(get_db),
) -> list[TestCaseResponse]:
    """Lists test case definitions with optional project filter."""
    query = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.type == "test")
        .options(joinedload(AutomationDefinition.versions))
    )
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(AutomationDefinition.project_id == proj.id)

    tests = query.order_by(AutomationDefinition.updated_at.desc()).offset(offset).limit(limit).all()
    results = []
    for t in tests:
        latest_ver = t.versions[0] if t.versions else None
        results.append(
            TestCaseResponse(
                id=t.id,
                project_id=t.project_id,
                type=t.type,
                name=t.name,
                description=t.description,
                status=t.status,
                current_version_id=t.current_version_id,
                created_by=t.created_by,
                created_at=t.created_at,
                updated_at=t.updated_at,
                definition=latest_ver.definition_json if latest_ver else None,
                version_count=len(t.versions),
            )
        )
    return results


@router.get("/{test_id}", response_model=TestCaseResponse)
def get_test_case(
    test_id: UUID,
    current_user=Depends(require_permission("tests:read", "tests:create_edit", "reports:read")),
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Retrieves full test case details with active step definition JSON."""
    test = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == test_id, AutomationDefinition.type == "test")
        .first()
    )
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")

    latest_ver = test.versions[0] if test.versions else None
    return TestCaseResponse(
        id=test.id,
        project_id=test.project_id,
        type=test.type,
        name=test.name,
        description=test.description,
        status=test.status,
        current_version_id=test.current_version_id,
        created_by=test.created_by,
        created_at=test.created_at,
        updated_at=test.updated_at,
        definition=latest_ver.definition_json if latest_ver else None,
        version_count=len(test.versions),
    )


@router.put("/{test_id}", response_model=TestCaseResponse)
def update_test_case(
    test_id: UUID,
    payload: TestCaseUpdateRequest,
    request: Request,
    current_user=Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> TestCaseResponse:
    """Updates test case draft metadata and steps."""
    test = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == test_id, AutomationDefinition.type == "test")
        .first()
    )
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")

    if payload.name:
        test.name = payload.name
    if payload.description is not None:
        test.description = payload.description

    def_dict = None
    if payload.test_case:
        def_dict = payload.test_case.model_dump()
        checksum = compute_definition_checksum(def_dict)

        latest_ver = test.versions[0] if test.versions else None
        if latest_ver and latest_ver.is_published:
            new_version = DefinitionVersion(
                definition_id=test.id,
                version_num=latest_ver.version_num + 1,
                definition_json=def_dict,
                checksum_sha256=checksum,
                is_published=False,
            )
            db.add(new_version)
            db.flush()
            test.current_version_id = new_version.id
        elif latest_ver:
            latest_ver.definition_json = def_dict
            latest_ver.checksum_sha256 = checksum
        else:
            new_version = DefinitionVersion(
                definition_id=test.id,
                version_num=1,
                definition_json=def_dict,
                checksum_sha256=checksum,
                is_published=False,
            )
            db.add(new_version)
            db.flush()
            test.current_version_id = new_version.id

    test.updated_at = datetime.now(timezone.utc)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test:update",
        resource_type="automation_definition",
        resource_id=str(test.id),
        client_ip=request.client.host if request.client else None,
        details={"name": test.name},
    )

    db.commit()
    db.refresh(test)

    latest_ver = test.versions[0] if test.versions else None
    return TestCaseResponse(
        id=test.id,
        project_id=test.project_id,
        type=test.type,
        name=test.name,
        description=test.description,
        status=test.status,
        current_version_id=test.current_version_id,
        created_by=test.created_by,
        created_at=test.created_at,
        updated_at=test.updated_at,
        definition=latest_ver.definition_json if latest_ver else None,
        version_count=len(test.versions),
    )


@router.post("/{test_id}/publish", response_model=PublishVersionResponse)
def publish_test_case(
    test_id: UUID,
    request: Request,
    current_user=Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> PublishVersionResponse:
    """Publishes current test case draft as an immutable version."""
    test = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == test_id, AutomationDefinition.type == "test")
        .first()
    )
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")

    if not test.versions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test case has no definition to publish")

    latest_ver = test.versions[0]
    now = datetime.now(timezone.utc)
    latest_ver.is_published = True
    latest_ver.published_by = current_user.id
    latest_ver.published_at = now

    test.status = "published"
    test.current_version_id = latest_ver.id
    test.updated_at = now

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test:publish",
        resource_type="definition_version",
        resource_id=str(latest_ver.id),
        client_ip=request.client.host if request.client else None,
        details={"version_num": latest_ver.version_num, "checksum": latest_ver.checksum_sha256},
    )

    db.commit()
    db.refresh(latest_ver)

    return PublishVersionResponse.model_validate(latest_ver)


@router.post("/{test_id}/execute", response_model=ExecutionDetailResponse)
def execute_test_case_endpoint(
    test_id: UUID,
    payload: ExecuteTestRequest,
    request: Request,
    current_user=Depends(require_permission("tests:execute", "executions:trigger")),
    db: Session = Depends(get_db),
) -> ExecutionDetailResponse:
    """Executes a deterministic test case with setup/teardown and 13 assertion evaluations."""
    test = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == test_id, AutomationDefinition.type == "test")
        .first()
    )
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")

    target_version: DefinitionVersion | None = None
    if payload.version_id:
        target_version = next((v for v in test.versions if v.id == payload.version_id), None)
    elif test.current_version_id:
        target_version = next((v for v in test.versions if v.id == test.current_version_id), None)
    elif test.versions:
        target_version = test.versions[0]

    if not target_version:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No executable version found for test case")

    test_case_def = TestCaseDefinition.model_validate(target_version.definition_json)

    # 1. Create Execution record pinned to this immutable version
    execution = Execution(
        project_id=test.project_id,
        definition_id=test.id,
        definition_version_id=target_version.id,
        environment_id=payload.environment_id,
        trigger_type="manual",
        triggered_by=current_user.id,
        status="queued",
        summary={},
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test:execute:start",
        resource_type="execution",
        resource_id=str(execution.id),
        client_ip=request.client.host if request.client else None,
        details={"test_id": str(test.id), "version_num": target_version.version_num, "async": payload.async_exec},
    )

    if payload.async_exec:
        from backend.app.worker.tasks import execute_test_case_task
        execute_test_case_task.delay(str(execution.id), payload.test_data_row)
        return ExecutionDetailResponse.model_validate(execution)

    # 2. Run Test Case via TestRunner synchronously
    adapter = AgentBrowserAdapter()
    session_mgr = SessionManager()
    runner = TestRunner(adapter=adapter, session_manager=session_mgr, db=db)

    runner.execute_test_case(
        execution_id=execution.id,
        test_case=test_case_def,
        test_data_row=payload.test_data_row,
    )

    db.refresh(execution)

    # Eagerly load steps and logs for full execution report response
    execution_detail = (
        db.query(Execution)
        .options(joinedload(Execution.steps), joinedload(Execution.logs))
        .filter(Execution.id == execution.id)
        .first()
    )

    return ExecutionDetailResponse.model_validate(execution_detail)


@router.post("/seed-legacy", response_model=list[TestCaseResponse])
def seed_legacy_tests_endpoint(
    payload: SeedLegacyTestsRequest,
    request: Request,
    current_user=Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> list[TestCaseResponse]:
    """Migrates the 4 canonical business tests (Login, Referral, FVR Status, Dashboard) into PostgreSQL."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    created_ids = seed_legacy_test_cases(db=db, project_id=project.id, user_id=current_user.id)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="test:seed_legacy",
        resource_type="project",
        resource_id=str(project.id),
        client_ip=request.client.host if request.client else None,
        details={"seeded_count": len(created_ids)},
    )

    seeded_records = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id.in_(created_ids))
        .all()
    )

    results = []
    for t in seeded_records:
        latest_ver = t.versions[0] if t.versions else None
        results.append(
            TestCaseResponse(
                id=t.id,
                project_id=t.project_id,
                type=t.type,
                name=t.name,
                description=t.description,
                status=t.status,
                current_version_id=t.current_version_id,
                created_by=t.created_by,
                created_at=t.created_at,
                updated_at=t.updated_at,
                definition=latest_ver.definition_json if latest_ver else None,
                version_count=len(t.versions),
            )
        )
    return results

