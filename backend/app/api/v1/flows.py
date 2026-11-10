"""Flow automation endpoints for creating, editing, publishing, and executing workflows."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.browser import AgentBrowserAdapter, SessionManager
from backend.app.db.session import get_db
from backend.app.engine.flows.flow_executor import FlowExecutor
from backend.app.engine.flows.flow_schema import FlowGraphDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.project import Project
from backend.app.api.v1.projects import resolve_project_id
from backend.app.schemas.flows import (
    ExecuteFlowRequest,
    ExecutionDetailResponse,
    FlowCreateRequest,
    FlowResponse,
    FlowUpdateRequest,
    PublishVersionResponse,
)
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["Flow Automation"])


def compute_definition_checksum(definition_dict: dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of a normalized JSON workflow definition."""
    canonical_json = json.dumps(definition_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@router.post("", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(
    payload: FlowCreateRequest,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> FlowResponse:
    """Creates a new visual flow workflow definition draft."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    def_dict = payload.definition.model_dump()
    checksum = compute_definition_checksum(def_dict)

    # 1. Create container
    automation = AutomationDefinition(
        project_id=project.id,
        type="flow",
        name=payload.name,
        description=payload.description,
        status="draft",
        created_by=current_user.id,
    )
    db.add(automation)
    db.flush()

    # 2. Create initial draft version (version 1)
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
        action="flow:create",
        resource_type="automation_definition",
        resource_id=str(automation.id),
        client_ip=request.client.host if request.client else None,
        details={"name": automation.name, "project_id": str(payload.project_id)},
    )

    db.commit()
    db.refresh(automation)

    return FlowResponse(
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


@router.get("", response_model=list[FlowResponse])
def list_flows(
    project_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("flows:read")),
    db: Session = Depends(get_db),
) -> list[FlowResponse]:
    """Lists flow workflows with optional project filter."""
    query = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.type == "flow")
        .options(joinedload(AutomationDefinition.versions))
    )
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(AutomationDefinition.project_id == proj.id)

    flows = query.order_by(AutomationDefinition.updated_at.desc()).offset(offset).limit(limit).all()
    results = []
    for f in flows:
        latest_ver = f.versions[0] if f.versions else None
        results.append(
            FlowResponse(
                id=f.id,
                project_id=f.project_id,
                type=f.type,
                name=f.name,
                description=f.description,
                status=f.status,
                current_version_id=f.current_version_id,
                created_by=f.created_by,
                created_at=f.created_at,
                updated_at=f.updated_at,
                definition=latest_ver.definition_json if latest_ver else None,
                version_count=len(f.versions),
            )
        )
    return results


@router.get("/{flow_id}", response_model=FlowResponse)
def get_flow(
    flow_id: UUID,
    current_user=Depends(require_permission("flows:read")),
    db: Session = Depends(get_db),
) -> FlowResponse:
    """Retrieves full flow details with active graph definition."""
    flow = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == flow_id, AutomationDefinition.type == "flow")
        .first()
    )
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    latest_ver = flow.versions[0] if flow.versions else None
    return FlowResponse(
        id=flow.id,
        project_id=flow.project_id,
        type=flow.type,
        name=flow.name,
        description=flow.description,
        status=flow.status,
        current_version_id=flow.current_version_id,
        created_by=flow.created_by,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        definition=latest_ver.definition_json if latest_ver else None,
        version_count=len(flow.versions),
    )


@router.put("/{flow_id}", response_model=FlowResponse)
def update_flow(
    flow_id: UUID,
    payload: FlowUpdateRequest,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> FlowResponse:
    """Updates flow draft metadata and graph definition."""
    flow = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == flow_id, AutomationDefinition.type == "flow")
        .first()
    )
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    if payload.name:
        flow.name = payload.name
    if payload.description is not None:
        flow.description = payload.description

    def_dict = None
    if payload.definition:
        def_dict = payload.definition.model_dump()
        checksum = compute_definition_checksum(def_dict)

        # If current version is already published, start a new draft version
        latest_ver = flow.versions[0] if flow.versions else None
        if latest_ver and latest_ver.is_published:
            new_version = DefinitionVersion(
                definition_id=flow.id,
                version_num=latest_ver.version_num + 1,
                definition_json=def_dict,
                checksum_sha256=checksum,
                is_published=False,
            )
            db.add(new_version)
            db.flush()
            flow.current_version_id = new_version.id
        elif latest_ver:
            # Overwrite active unpublished draft
            latest_ver.definition_json = def_dict
            latest_ver.checksum_sha256 = checksum
        else:
            new_version = DefinitionVersion(
                definition_id=flow.id,
                version_num=1,
                definition_json=def_dict,
                checksum_sha256=checksum,
                is_published=False,
            )
            db.add(new_version)
            db.flush()
            flow.current_version_id = new_version.id

    flow.updated_at = datetime.now(timezone.utc)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="flow:update",
        resource_type="automation_definition",
        resource_id=str(flow.id),
        client_ip=request.client.host if request.client else None,
        details={"name": flow.name},
    )

    db.commit()
    db.refresh(flow)

    latest_ver = flow.versions[0] if flow.versions else None
    return FlowResponse(
        id=flow.id,
        project_id=flow.project_id,
        type=flow.type,
        name=flow.name,
        description=flow.description,
        status=flow.status,
        current_version_id=flow.current_version_id,
        created_by=flow.created_by,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        definition=latest_ver.definition_json if latest_ver else None,
        version_count=len(flow.versions),
    )


@router.post("/{flow_id}/publish", response_model=PublishVersionResponse)
def publish_flow(
    flow_id: UUID,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit")),
    db: Session = Depends(get_db),
) -> PublishVersionResponse:
    """Publishes current draft as an immutable version pinned by SHA-256 checksum."""
    flow = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == flow_id, AutomationDefinition.type == "flow")
        .first()
    )
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    if not flow.versions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Flow has no definition to publish")

    latest_ver = flow.versions[0]
    now = datetime.now(timezone.utc)
    latest_ver.is_published = True
    latest_ver.published_by = current_user.id
    latest_ver.published_at = now

    flow.status = "published"
    flow.current_version_id = latest_ver.id
    flow.updated_at = now

    log_audit_event(
        db,
        user_id=current_user.id,
        action="flow:publish",
        resource_type="definition_version",
        resource_id=str(latest_ver.id),
        client_ip=request.client.host if request.client else None,
        details={"version_num": latest_ver.version_num, "checksum": latest_ver.checksum_sha256},
    )

    db.commit()
    db.refresh(latest_ver)

    return PublishVersionResponse.model_validate(latest_ver)


@router.post("/{flow_id}/execute", response_model=ExecutionDetailResponse)
def execute_flow_endpoint(
    flow_id: UUID,
    payload: ExecuteFlowRequest,
    request: Request,
    current_user=Depends(require_permission("flows:execute")),
    db: Session = Depends(get_db),
) -> ExecutionDetailResponse:
    """Executes a visual flow workflow pinned to an immutable published version."""
    flow = (
        db.query(AutomationDefinition)
        .options(joinedload(AutomationDefinition.versions))
        .filter(AutomationDefinition.id == flow_id, AutomationDefinition.type == "flow")
        .first()
    )
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    # Select version to execute
    target_version: DefinitionVersion | None = None
    if payload.version_id:
        target_version = next((v for v in flow.versions if v.id == payload.version_id), None)
    elif flow.current_version_id:
        target_version = next((v for v in flow.versions if v.id == flow.current_version_id), None)
    elif flow.versions:
        target_version = flow.versions[0]

    if not target_version:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No executable version found for flow")

    # Parse and validate stored JSON graph definition
    graph_def = FlowGraphDefinition.model_validate(target_version.definition_json)

    # 1. Create Execution record pinned to this immutable version
    execution = Execution(
        project_id=flow.project_id,
        definition_id=flow.id,
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
        action="flow:execute:start",
        resource_type="execution",
        resource_id=str(execution.id),
        client_ip=request.client.host if request.client else None,
        details={"flow_id": str(flow.id), "version_num": target_version.version_num, "async": payload.async_exec},
    )

    if payload.async_exec:
        from backend.app.worker.tasks import execute_flow_task
        execute_flow_task.delay(str(execution.id), payload.initial_variables)
        return ExecutionDetailResponse.model_validate(execution)

    # 2. Run Flow via FlowExecutor synchronously
    adapter = AgentBrowserAdapter()
    session_mgr = SessionManager()
    executor = FlowExecutor(adapter=adapter, session_manager=session_mgr, db=db)

    executor.execute_flow(
        execution_id=execution.id,
        flow_graph=graph_def,
        initial_variables=payload.initial_variables,
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

