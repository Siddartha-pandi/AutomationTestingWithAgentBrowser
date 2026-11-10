"""Self-healing and human approval endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from backend.app.browser import AgentBrowserAdapter
from backend.app.db.session import get_db
from backend.app.intelligence.element_profile import ElementProfileData
from backend.app.intelligence.self_healing import SelfHealingEngine
from backend.app.models.intelligence import Approval, ElementProfile, HealingEvent
from backend.app.schemas.intelligence import (
    ApprovalActionRequest,
    ApprovalResponse,
    HealingEventResponse,
    ResolveElementRequest,
    ResolveElementResponse,
)
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healing", tags=["Self Healing & Approvals"])


@router.get("/events", response_model=list[HealingEventResponse])
def list_healing_events(
    execution_id: UUID | None = None,
    element_profile_id: UUID | None = None,
    decision: str | None = Query(default=None, pattern="^(auto_healed|requires_approval|rejected)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> list[HealingEventResponse]:
    """Lists deterministic self-healing events with score breakdowns and outcomes."""
    query = db.query(HealingEvent)

    if execution_id:
        query = query.filter(HealingEvent.execution_id == execution_id)
    if element_profile_id:
        query = query.filter(HealingEvent.element_profile_id == element_profile_id)
    if decision:
        query = query.filter(HealingEvent.decision == decision)

    events = query.order_by(HealingEvent.timestamp.desc()).offset(offset).limit(limit).all()
    return [HealingEventResponse.model_validate(e) for e in events]


@router.get("/approvals", response_model=list[ApprovalResponse])
def list_pending_approvals(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(pending|approved|rejected)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_permission("reports:read")),
    db: Session = Depends(get_db),
) -> list[ApprovalResponse]:
    """Lists self-healing human approval requests requiring operator intervention."""
    query = db.query(Approval).options(joinedload(Approval.healing_event))

    if status_filter:
        query = query.filter(Approval.status == status_filter)

    approvals = query.order_by(Approval.created_at.desc()).offset(offset).limit(limit).all()
    return [ApprovalResponse.model_validate(a) for a in approvals]


@router.post("/approvals/{approval_id}/respond", response_model=ApprovalResponse)
def respond_to_approval(
    approval_id: UUID,
    payload: ApprovalActionRequest,
    request: Request,
    current_user=Depends(require_permission("healing:approve")),
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    """Approves or rejects a pending self-healing recovery decision."""
    approval = (
        db.query(Approval)
        .options(joinedload(Approval.healing_event))
        .filter(Approval.id == approval_id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if approval.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request is already resolved with status '{approval.status}'",
        )

    now = datetime.now(timezone.utc)
    approval.status = payload.decision
    approval.approved_by = current_user.id
    approval.responded_at = now
    if payload.comment:
        approval.comment = f"{approval.comment or ''}\n[Decision: {payload.decision}] {payload.comment}".strip()

    if approval.healing_event:
        approval.healing_event.is_approved = (payload.decision == "approved")
        if payload.decision == "approved":
            # Save verified locator to history upon approval
            engine = SelfHealingEngine(AgentBrowserAdapter(), db=db)
            engine.record_locator_success(
                element_profile_id=approval.healing_event.element_profile_id,
                locator_type="self_healed_approved",
                locator_value=approval.healing_event.healed_locator,
            )

    log_audit_event(
        db,
        user_id=current_user.id,
        action=f"healing:approval:{payload.decision}",
        resource_type="approval",
        resource_id=str(approval.id),
        client_ip=request.client.host if request.client else None,
        details={
            "healing_event_id": str(approval.healing_event_id),
            "decision": payload.decision,
            "comment": payload.comment,
        },
    )

    db.commit()
    db.refresh(approval)
    return ApprovalResponse.model_validate(approval)


@router.post("/resolve", response_model=ResolveElementResponse)
def resolve_element_endpoint(
    payload: ResolveElementRequest,
    current_user=Depends(require_permission("flows:execute")),
    db: Session = Depends(get_db),
) -> ResolveElementResponse:
    """Executes deterministic element resolution and self-healing against an active session."""
    profile = db.query(ElementProfile).filter(ElementProfile.id == payload.element_profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element profile not found")

    # Load locator history
    history = [
        {
            "locator_type": h.locator_type,
            "locator_value": h.locator_value,
            "success_count": h.success_count,
        }
        for h in profile.history
    ]

    profile_data = ElementProfileData(
        logical_id=profile.logical_id,
        description=profile.description or "",
        element_type=profile.element_type,
        page_context=profile.page_context,
        original_text=profile.original_text,
        stable_attributes=profile.stable_attributes or {},
        structural_fingerprint=profile.structural_fingerprint or {},
        historical_locators=history,
    )

    adapter = AgentBrowserAdapter()
    engine = SelfHealingEngine(adapter, db=db)

    result = engine.resolve_element(
        session_id=payload.session_id,
        profile=profile_data,
        original_locator=payload.original_locator,
        action=payload.action,
        is_destructive=payload.is_destructive,
        execution_id=payload.execution_id,
        element_profile_id=profile.id,
    )

    return ResolveElementResponse(
        success=result.success,
        decision=result.decision,
        original_locator=result.original_locator,
        healed_locator=result.healed_locator,
        confidence_score=result.confidence_score,
        scoring_breakdown=result.scoring_breakdown,
        candidate_node=result.candidate_node,
        approval_id=result.approval_id,
        healing_event_id=result.healing_event_id,
        error_message=result.error_message,
    )

