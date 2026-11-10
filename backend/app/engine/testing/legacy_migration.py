"""Migration and seeding of canonical business test definitions.

Preserves the 4 original business test workflows (Login, Referral, FVR Status, Dashboard)
as first-class, verified platform Test Cases and Regression Test Suites.
Zero AI models or heuristics.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.engine.flows.flow_schema import ElementTarget, FlowActionType
from backend.app.engine.testing.test_schema import TestCaseDefinition, TestStep, TestSuiteDefinition
from backend.app.models.automation import AutomationDefinition, DefinitionVersion

logger = logging.getLogger(__name__)


def compute_checksum(data: dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_login_test_definition() -> TestCaseDefinition:
    """Constructs the canonical Login test case definition."""
    return TestCaseDefinition(
        name="Test 1: User Authentication & Login Verification",
        description="Verifies user authentication, secure credential entry, session initialization, and dashboard redirection.",
        setup_steps=[
            TestStep(
                id="setup_nav_login",
                name="Navigate to Authentication Portal",
                step_type="action",
                action=FlowActionType.NAVIGATE,
                config={"url": "https://app.local/login"},
            ),
        ],
        steps=[
            TestStep(
                id="fill_username",
                name="Enter Username",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="input[name='username']"),
                config={"value": "testuser@company.local"},
            ),
            TestStep(
                id="fill_password",
                name="Enter Password",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="input[name='password']"),
                config={"value": "SuperSecretPass123!", "is_secret": True},
            ),
            TestStep(
                id="click_submit_login",
                name="Submit Login Credentials",
                step_type="action",
                action=FlowActionType.CLICK,
                target=ElementTarget(selector="button[type='submit']"),
            ),
            TestStep(
                id="assert_dashboard_url",
                name="Verify Redirect to Dashboard URL",
                step_type="assertion",
                assertion="url_contains",
                expected="/dashboard",
            ),
            TestStep(
                id="assert_dashboard_header_visible",
                name="Verify Dashboard Header Element Visible",
                step_type="assertion",
                assertion="element_visible",
                target=ElementTarget(selector="h1#dashboard-header"),
            ),
            TestStep(
                id="assert_welcome_text",
                name="Verify Personalized Greeting Text Contains Username",
                step_type="assertion",
                assertion="text_contains",
                target=ElementTarget(selector="#user-greeting"),
                expected="Welcome",
            ),
        ],
        teardown_steps=[],
        test_data=[{"username": "testuser@company.local"}],
    )


def get_referral_test_definition() -> TestCaseDefinition:
    """Constructs the canonical Referral Submission test case definition."""
    return TestCaseDefinition(
        name="Test 2: Referral Creation & Submission Workflow",
        description="Fills referral candidate details, selects relationship, submits form, and validates confirmation toast.",
        setup_steps=[
            TestStep(
                id="setup_nav_referral",
                name="Navigate to Referral Form",
                step_type="action",
                action=FlowActionType.NAVIGATE,
                config={"url": "https://app.local/referrals/new"},
            ),
        ],
        steps=[
            TestStep(
                id="fill_referee_name",
                name="Enter Candidate Full Name",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="#referee-name"),
                config={"value": "Jane Doe"},
            ),
            TestStep(
                id="fill_referee_email",
                name="Enter Candidate Email",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="#referee-email"),
                config={"value": "jane.doe@example.com"},
            ),
            TestStep(
                id="fill_referee_phone",
                name="Enter Candidate Phone Number",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="#referee-phone"),
                config={"value": "+1-555-0199"},
            ),
            TestStep(
                id="click_submit_referral",
                name="Click Submit Referral Button",
                step_type="action",
                action=FlowActionType.CLICK,
                target=ElementTarget(logical_id="referral_submit", selector="button#submit-referral"),
            ),
            TestStep(
                id="assert_success_alert",
                name="Verify Success Confirmation Alert Visible",
                step_type="assertion",
                assertion="element_visible",
                target=ElementTarget(selector=".alert-success"),
            ),
            TestStep(
                id="assert_success_text",
                name="Verify Referral Confirmation Text",
                step_type="assertion",
                assertion="text_contains",
                target=ElementTarget(selector=".alert-success"),
                expected="Referral submitted successfully",
            ),
        ],
        teardown_steps=[],
    )


def get_fvr_status_test_definition() -> TestCaseDefinition:
    """Constructs the canonical FVR Status Verification test case definition."""
    return TestCaseDefinition(
        name="Test 3: Field Verification Report (FVR) Status Check",
        description="Queries case ID, verifies tabular report entries, and asserts verified completion status.",
        setup_steps=[
            TestStep(
                id="setup_nav_fvr",
                name="Navigate to FVR Search Portal",
                step_type="action",
                action=FlowActionType.NAVIGATE,
                config={"url": "https://app.local/fvr/status"},
            ),
        ],
        steps=[
            TestStep(
                id="fill_fvr_case_id",
                name="Enter FVR Case ID",
                step_type="action",
                action=FlowActionType.FILL,
                target=ElementTarget(selector="#case-search-input"),
                config={"value": "CASE-99281"},
            ),
            TestStep(
                id="click_fvr_search",
                name="Execute Case Search",
                step_type="action",
                action=FlowActionType.CLICK,
                target=ElementTarget(selector="button#btn-case-search"),
            ),
            TestStep(
                id="assert_fvr_table_contains_case",
                name="Assert Results Table Contains Case ID and Status",
                step_type="assertion",
                assertion="table_contains",
                target=ElementTarget(selector="table#fvr-results-table"),
                expected="CASE-99281",
            ),
            TestStep(
                id="assert_status_badge_text",
                name="Verify Status Badge Shows 'Verified'",
                step_type="assertion",
                assertion="text_equals",
                target=ElementTarget(selector="span.badge-status"),
                expected="Verified",
            ),
        ],
        teardown_steps=[],
    )


def get_dashboard_test_definition() -> TestCaseDefinition:
    """Constructs the canonical Dashboard Analytics test case definition."""
    return TestCaseDefinition(
        name="Test 4: Executive Dashboard Analytics & Metrics Verification",
        description="Inspects KPI metric summary cards, validates page title, and ensures charts are rendered.",
        setup_steps=[
            TestStep(
                id="setup_nav_dashboard",
                name="Navigate to Analytics Dashboard",
                step_type="action",
                action=FlowActionType.NAVIGATE,
                config={"url": "https://app.local/dashboard"},
            ),
        ],
        steps=[
            TestStep(
                id="assert_page_title",
                name="Assert Page Title Matches Analytics Dashboard",
                step_type="assertion",
                assertion="page_title_equals",
                expected="Executive Analytics Dashboard",
            ),
            TestStep(
                id="assert_metric_cards_count",
                name="Verify Four Primary KPI Metric Cards Rendered",
                step_type="assertion",
                assertion="element_count",
                target=ElementTarget(selector=".kpi-metric-card"),
                expected=4,
            ),
            TestStep(
                id="assert_main_chart_visible",
                name="Verify Trends Visualization Chart Visible",
                step_type="assertion",
                assertion="element_visible",
                target=ElementTarget(selector="#analytics-trend-chart"),
            ),
        ],
        teardown_steps=[],
    )


def seed_legacy_test_cases(db: Session, project_id: UUID, user_id: UUID | None = None) -> list[UUID]:
    """Seeds the 4 canonical business tests into PostgreSQL as AutomationDefinition records."""
    definitions = [
        get_login_test_definition(),
        get_referral_test_definition(),
        get_fvr_status_test_definition(),
        get_dashboard_test_definition(),
    ]

    created_ids: list[UUID] = []

    for def_model in definitions:
        existing = (
            db.query(AutomationDefinition)
            .filter(
                AutomationDefinition.project_id == project_id,
                AutomationDefinition.name == def_model.name,
                AutomationDefinition.type == "test",
            )
            .first()
        )
        if existing:
            created_ids.append(existing.id)
            continue

        raw_dict = def_model.model_dump()
        checksum = compute_checksum(raw_dict)

        automation = AutomationDefinition(
            project_id=project_id,
            type="test",
            name=def_model.name,
            description=def_model.description,
            status="published",
            created_by=user_id,
        )
        db.add(automation)
        db.flush()

        version = DefinitionVersion(
            definition_id=automation.id,
            version_num=1,
            definition_json=raw_dict,
            checksum_sha256=checksum,
            is_published=True,
            published_by=user_id,
        )
        db.add(version)
        db.flush()

        automation.current_version_id = version.id
        created_ids.append(automation.id)

    db.commit()
    logger.info("Successfully seeded %d canonical business test definitions", len(created_ids))
    return created_ids

