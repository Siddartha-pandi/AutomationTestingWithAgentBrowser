"""REST API endpoints for managing automation schedules and Celery Beat cron jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.automation import AutomationDefinition, Schedule
from backend.app.models.execution import Execution
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import require_permission
from backend.app.worker.tasks import execute_flow_task, execute_test_case_task, schedule_checker_task
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


class ScheduleCreateRequest(BaseModel):
    definition_id: UUID
    environment_id: UUID
    cron_expression: str = Field(min_length=5, max_length=64)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)
    is_enabled: bool = True


class ScheduleUpdateRequest(BaseModel):
    cron_expression: str | None = None
    timezone: str | None = None
    is_enabled: bool | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    definition_id: UUID
    environment_id: UUID
    cron_expression: str
    timezone: str
    is_enabled: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreateRequest,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit", "tests:create_edit")),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Creates a new cron-based automation schedule pinned to an environment and definition."""
    # Validate cron expression
    if not croniter.is_valid(payload.cron_expression):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: '{payload.cron_expression}'",
        )

    definition = (
        db.query(AutomationDefinition)
        .filter(AutomationDefinition.id == payload.definition_id)
        .first()
    )
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation definition not found",
        )

    now = datetime.now(timezone.utc)
    iter_cron = croniter(payload.cron_expression, now)
    next_run = iter_cron.get_next(datetime)

    schedule = Schedule(
        definition_id=payload.definition_id,
        environment_id=payload.environment_id,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        is_enabled=payload.is_enabled,
        next_run_at=next_run,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="schedule:create",
        resource_type="schedule",
        resource_id=str(schedule.id),
        client_ip=request.client.host if request.client else None,
        details={"cron": payload.cron_expression, "definition_id": str(payload.definition_id)},
    )

    return ScheduleResponse.model_validate(schedule)


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(
    definition_id: UUID | None = None,
    current_user=Depends(require_permission("flows:read", "tests:read")),
    db: Session = Depends(get_db),
) -> list[ScheduleResponse]:
    """Lists automation schedules."""
    query = db.query(Schedule)
    if definition_id:
        query = query.filter(Schedule.definition_id == definition_id)
    schedules = query.order_by(Schedule.created_at.desc()).all()
    return [ScheduleResponse.model_validate(s) for s in schedules]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: UUID,
    current_user=Depends(require_permission("flows:read", "tests:read")),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Retrieves a single schedule by ID."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return ScheduleResponse.model_validate(schedule)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: UUID,
    payload: ScheduleUpdateRequest,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit", "tests:create_edit")),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    """Updates cron expression, timezone, or enabled state."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    if payload.cron_expression is not None:
        if not croniter.is_valid(payload.cron_expression):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: '{payload.cron_expression}'",
            )
        schedule.cron_expression = payload.cron_expression
        schedule.next_run_at = croniter(schedule.cron_expression, datetime.now(timezone.utc)).get_next(datetime)

    if payload.timezone is not None:
        schedule.timezone = payload.timezone

    if payload.is_enabled is not None:
        schedule.is_enabled = payload.is_enabled

    db.commit()
    db.refresh(schedule)

    log_audit_event(
        db,
        user_id=current_user.id,
        action="schedule:update",
        resource_type="schedule",
        resource_id=str(schedule.id),
        client_ip=request.client.host if request.client else None,
        details={"is_enabled": schedule.is_enabled, "cron": schedule.cron_expression},
    )

    return ScheduleResponse.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    request: Request,
    current_user=Depends(require_permission("flows:create_edit", "tests:create_edit")),
    db: Session = Depends(get_db),
) -> None:
    """Deletes an automation schedule."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    db.delete(schedule)
    db.commit()

    log_audit_event(
        db,
        user_id=current_user.id,
        action="schedule:delete",
        resource_type="schedule",
        resource_id=str(schedule_id),
        client_ip=request.client.host if request.client else None,
        details={},
    )


@router.post("/evaluate", response_model=dict[str, Any])
def evaluate_schedules_now(
    current_user=Depends(require_permission("executions:trigger")),
) -> dict[str, Any]:
    """Manually invokes the schedule evaluator task right now."""
    result = schedule_checker_task()
    return result

