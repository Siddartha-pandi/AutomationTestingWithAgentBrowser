"""Tests for Phase 5: Deterministic Element Resolution and Self-Healing Engine.

Verifies recovery from UI refactors, CSS class changes, dynamic ID replacements,
hierarchy wrapping, ambiguity safety protection, and human approval gates.
Zero AI models or heuristics.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.browser import AgentBrowserAdapter
from backend.app.db.session import SessionLocal
from backend.app.intelligence.attribute_matcher import AttributeMatcher
from backend.app.intelligence.confidence_engine import ConfidenceEngine
from backend.app.intelligence.dom_extractor import ExtractedElementNode, FullDOMSnapshot
from backend.app.intelligence.element_profile import ElementProfileData
from backend.app.intelligence.self_healing import SelfHealingEngine
from backend.app.intelligence.semantic_matcher import SemanticMatcher
from backend.app.intelligence.structural_matcher import StructuralMatcher
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Execution
from backend.app.models.intelligence import Approval, ElementProfile, HealingEvent, LocatorHistory
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.security.jwt import create_access_token
from backend.main import app


class TestDeterministicMatchers:
    """Unit tests for individual deterministic matching components."""

    def test_semantic_matcher_tag_and_role_compatibility(self) -> None:
        matcher = SemanticMatcher()

        # Exact match
        assert matcher.match_role("button", "button", "button") == 1.0

        # Compatible roles
        assert matcher.match_role("button", "link", "a") > 0.80
        assert matcher.match_role("textbox", "textbox", "input") == 1.0

        # Incompatible roles
        assert matcher.match_role("heading", "button", "button") == 0.0

    def test_semantic_matcher_accessible_name_similarity(self) -> None:
        matcher = SemanticMatcher()

        # Identical
        assert matcher.match_accessible_name("Submit Referral", "Submit Referral", "Submit Referral") == 1.0

        # Minor punctuation or casing
        assert matcher.match_accessible_name("Submit Referral", "submit referral!", "submit referral!") > 0.90

        # Substring containment
        assert matcher.match_accessible_name("Submit Referral Form", "Submit Referral", "Submit Referral") >= 0.80

        # Completely unrelated
        assert matcher.match_accessible_name("Submit Referral", "Cancel Subscription", "Cancel Subscription") < 0.30

    def test_attribute_matcher_dynamic_id_stripping(self) -> None:
        matcher = AttributeMatcher()

        # Static IDs - preserved
        assert matcher.clean_dynamic_id("login-button") == "login-button"
        assert matcher.clean_dynamic_id("referral_submit") == "referral_submit"

        # Auto-generated trailing digits or hashes stripped to base prefix
        assert matcher.clean_dynamic_id("btn-1293819") == "btn"
        assert matcher.clean_dynamic_id("submit-btn-49182") == "submit-btn"
        assert matcher.clean_dynamic_id("btn_84712918") == "btn"

    def test_attribute_matcher_stable_attributes(self) -> None:
        matcher = AttributeMatcher()

        saved = {
            "data-testid": "submit-btn",
            "name": "referral_action",
            "type": "submit",
        }

        candidate_node = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Submit",
            text="Submit",
            element_id=None,
            stable_attributes={
                "data-testid": "submit-btn",
                "name": "referral_action",
                "type": "submit",
                "class": "btn-primary large new-theme",  # CSS classes intentionally ignored
            },
            aria_properties={},
            associated_label=None,
            ancestors=[],
            siblings={},
            nearby_heading=None,
            form_context={},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        assert matcher.match_attributes(saved, candidate_node) == 1.0

    def test_structural_matcher_ancestor_jaccard_and_wrapping(self) -> None:
        matcher = StructuralMatcher()

        saved_ancestors = ["form#referral-form", "div.modal-content", "div.modal-dialog"]
        # Frontend refactor: wrapped in an extra container 'div.card-body'
        candidate_ancestors = [
            {"tag": "div", "id": "card-body"},
            {"tag": "form", "id": "referral-form"},
            {"tag": "div", "id": "modal-content"},
            {"tag": "div", "id": "modal-dialog"},
        ]

        overlap = matcher.match_ancestors(saved_ancestors, candidate_ancestors)
        # 1 intersection ("form#referral-form") or tag matching
        assert overlap > 0.0

    def test_confidence_engine_scoring_weights(self) -> None:
        profile = ElementProfileData(
            logical_id="test_btn",
            description="Test button",
            element_type="button",
            page_context="Dashboard",
            original_text="Submit",
            role="button",
            accessible_name="Submit",
            stable_attributes={"data-testid": "btn-submit", "associated_label": "Submit"},
            structural_fingerprint={
                "ancestor_path": ["form#app-form"],
                "role": "button",
                "accessible_name": "Submit",
                "form_id": "app-form",
            },
            historical_locators=[{"locator_type": "stable_attribute", "locator_value": "[data-testid='btn-submit']"}],
        )

        node = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Submit",
            text="Submit",
            element_id=None,
            stable_attributes={"data-testid": "btn-submit"},
            aria_properties={},
            associated_label="Submit",
            ancestors=[{"tag": "form", "id": "app-form", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={"form_id": "app-form"},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        breakdown = ConfidenceEngine.evaluate(profile, node)
        assert breakdown.total_score >= 0.90
        assert breakdown.role_name_score == 1.0
        assert breakdown.stable_attr_score >= 0.70
        assert breakdown.text_score == 1.0


class TestSelfHealingScenarios:
    """End-to-end deterministic self-healing scenarios simulating frontend UI refactors."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        return MagicMock(spec=AgentBrowserAdapter)

    def test_scenario_a_button_text_changed_heals_automatically(self, mock_adapter: MagicMock) -> None:
        """Text changed ('Submit Referral' -> 'Send Referral') while role, name, attributes stay intact."""
        engine = SelfHealingEngine(mock_adapter)

        profile = ElementProfileData(
            logical_id="submit_referral",
            description="Submit referral form",
            element_type="button",
            page_context="Referrals",
            original_text="Submit Referral",
            role="button",
            accessible_name="Submit Referral",
            stable_attributes={"data-testid": "submit-referral-btn", "type": "submit"},
            structural_fingerprint={"ancestor_path": ["form#referral-form"], "role": "button", "form_id": "referral-form"},
            historical_locators=[{"locator_type": "stable_attribute", "locator_value": "[data-testid='submit-referral-btn']"}],
        )

        candidate = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Submit Referral",  # Accessible name preserved
            text="Send Referral",               # Text modified by marketing
            element_id=None,
            stable_attributes={"data-testid": "submit-referral-btn", "type": "submit"},
            aria_properties={},
            associated_label="Submit Referral",
            ancestors=[{"tag": "form", "id": "referral-form", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={"form_id": "referral-form"},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        engine.extractor.extract_full_dom = MagicMock(return_value=FullDOMSnapshot(
            page_url="https://app.local",
            route_path="/referrals",
            page_title="Referrals",
            timestamp="2026-11-10T12:00:00Z",
            total_elements=1,
            elements=[candidate],
        ))

        result = engine.resolve_element("session-1", profile, original_locator="button:has-text('Submit Referral')")
        assert result.success is True
        assert result.decision == "auto_healed"
        assert result.healed_locator == "[data-testid='submit-referral-btn']"
        assert result.confidence_score >= 0.95

    def test_scenario_b_dynamic_id_mutation_heals_via_attributes(self, mock_adapter: MagicMock) -> None:
        """Dynamic ID mutated (#btn-491 -> #btn-928) and CSS classes changed."""
        engine = SelfHealingEngine(mock_adapter)

        profile = ElementProfileData(
            logical_id="action_btn",
            description="Action button",
            element_type="button",
            page_context="Dashboard",
            original_text="Approve",
            role="button",
            accessible_name="Approve",
            stable_attributes={"name": "approve_action", "data-testid": "approve-btn"},
            structural_fingerprint={"ancestor_path": ["form#approval-form"], "role": "button", "form_id": "approval-form"},
            historical_locators=[{"locator_type": "stable_attribute", "locator_value": "[data-testid='approve-btn']"}],
        )

        candidate = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Approve",
            text="Approve",
            element_id="btn-928471",  # Mutated dynamic ID
            stable_attributes={"name": "approve_action", "data-testid": "approve-btn"},
            aria_properties={},
            associated_label="Approve",
            ancestors=[{"tag": "form", "id": "approval-form", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={"form_id": "approval-form"},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        engine.extractor.extract_full_dom = MagicMock(return_value=FullDOMSnapshot(
            page_url="https://app.local",
            route_path="/dashboard",
            page_title="Dashboard",
            timestamp="2026-11-10T12:00:00Z",
            total_elements=1,
            elements=[candidate],
        ))

        result = engine.resolve_element("session-1", profile, original_locator="#btn-491")
        assert result.success is True
        assert result.decision == "auto_healed"
        assert result.healed_locator == "[data-testid='approve-btn']"
        assert result.confidence_score >= 0.95

    def test_scenario_c_ambiguity_protection_rejects_guessing(self, mock_adapter: MagicMock) -> None:
        """Two identical buttons score within AMBIGUITY_DELTA (5%). Engine must reject guessing!"""
        engine = SelfHealingEngine(mock_adapter)

        profile = ElementProfileData(
            logical_id="delete_item",
            description="Delete item button",
            element_type="button",
            page_context="Items",
            original_text="Delete",
            role="button",
            accessible_name="Delete",
            stable_attributes={},
            structural_fingerprint={"role": "button"},
            historical_locators=[],
        )

        # 2 duplicate Delete buttons on same page
        btn1 = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Delete",
            text="Delete",
            element_id=None,
            stable_attributes={},
            aria_properties={},
            associated_label="Delete",
            ancestors=[{"tag": "tr", "id": "row-1", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )
        btn2 = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Delete",
            text="Delete",
            element_id=None,
            stable_attributes={},
            aria_properties={},
            associated_label="Delete",
            ancestors=[{"tag": "tr", "id": "row-2", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        engine.extractor.extract_full_dom = MagicMock(return_value=FullDOMSnapshot(
            page_url="https://app.local",
            route_path="/items",
            page_title="Items",
            timestamp="2026-11-10T12:00:00Z",
            total_elements=2,
            elements=[btn1, btn2],
        ))

        result = engine.resolve_element("session-1", profile, original_locator=".delete-btn")
        assert result.success is False
        assert result.decision == "rejected"
        assert "Ambiguous element" in (result.error_message or "")

    def test_scenario_d_destructive_action_safety_gate(self, mock_adapter: MagicMock) -> None:
        """Destructive action candidate scores 0.96 (normally auto-healed at 0.95). Requires approval at 0.98 threshold."""
        engine = SelfHealingEngine(mock_adapter)

        profile = ElementProfileData(
            logical_id="wipe_database",
            description="Wipe test database button",
            element_type="button",
            page_context="Settings",
            original_text="Purge Data",
            role="button",
            accessible_name="Purge Data",
            stable_attributes={"data-testid": "purge-btn"},
            structural_fingerprint={"ancestor_path": ["form#settings-form"], "role": "button", "form_id": "settings-form"},
            historical_locators=[{"locator_type": "stable_attribute", "locator_value": "[data-testid='purge-btn']"}],
        )

        # Candidate with minor text mutation bringing score to ~0.97
        candidate = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Purge Data",
            text="Purge Data Now (Permanent)",
            element_id=None,
            stable_attributes={"data-testid": "purge-btn"},
            aria_properties={},
            associated_label="Purge Data",
            ancestors=[{"tag": "form", "id": "settings-form", "test_id": None}],
            siblings={},
            nearby_heading=None,
            form_context={"form_id": "settings-form"},
            is_visible=True,
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        engine.extractor.extract_full_dom = MagicMock(return_value=FullDOMSnapshot(
            page_url="https://app.local",
            route_path="/settings",
            page_title="Settings",
            timestamp="2026-11-10T12:00:00Z",
            total_elements=1,
            elements=[candidate],
        ))

        # With is_destructive=True, auto-heal requires 0.98
        result = engine.resolve_element("session-1", profile, original_locator="#purge-btn", is_destructive=True)
        assert result.success is False
        assert result.decision == "requires_approval"

    def test_scenario_e_hidden_element_rejected(self, mock_adapter: MagicMock) -> None:
        """Resolved candidate is hidden in DOM. Must reject recovery."""
        engine = SelfHealingEngine(mock_adapter)

        profile = ElementProfileData(
            logical_id="modal_save",
            description="Save modal",
            element_type="button",
            page_context="Modal",
            original_text="Save",
            role="button",
            accessible_name="Save",
            stable_attributes={"data-testid": "save-btn"},
            structural_fingerprint={"role": "button"},
            historical_locators=[],
        )

        candidate = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Save",
            text="Save",
            element_id=None,
            stable_attributes={"data-testid": "save-btn"},
            aria_properties={},
            associated_label=None,
            ancestors=[],
            siblings={},
            nearby_heading=None,
            form_context={},
            is_visible=False,  # Hidden!
            is_enabled=True,
            box={},
            page_url="",
            route_path="",
        )

        engine.extractor.extract_full_dom = MagicMock(return_value=FullDOMSnapshot(
            page_url="https://app.local",
            route_path="/modal",
            page_title="Modal",
            timestamp="2026-11-10T12:00:00Z",
            total_elements=1,
            elements=[candidate],
        ))

        result = engine.resolve_element("session-1", profile, original_locator="#save-btn")
        assert result.success is False
        assert result.decision == "rejected"
        assert "hidden or not visible" in (result.error_message or "")


class TestHealingAPI:
    """Tests for /api/v1/healing endpoints and approval response lifecycle."""

    @pytest.fixture
    def test_context(self) -> tuple[TestClient, str, uuid.UUID, uuid.UUID]:
        client = TestClient(app)
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"heal_dev_{uuid.uuid4().hex[:8]}@company.local",
                password_hash="dummy_hash",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="Healing Test Project", owner_id=user.id)
            db.add(project)
            db.flush()

            automation = AutomationDefinition(
                project_id=project.id,
                type="flow",
                name="Healing Test Flow",
                status="published",
                created_by=user.id,
            )
            db.add(automation)
            db.flush()

            version = DefinitionVersion(
                definition_id=automation.id,
                version_num=1,
                definition_json={"nodes": [], "edges": []},
                checksum_sha256="dummy_sha256",
                is_published=True,
            )
            db.add(version)
            db.flush()

            execution = Execution(
                project_id=project.id,
                definition_id=automation.id,
                definition_version_id=version.id,
                trigger_type="manual",
                status="running",
                summary={},
            )
            db.add(execution)
            db.flush()

            profile = ElementProfile(
                project_id=project.id,
                logical_id="api_heal_btn",
                element_type="button",
                page_context="Dashboard",
                original_text="Save Changes",
                stable_attributes={"data-testid": "save-btn"},
                structural_fingerprint={"role": "button"},
            )
            db.add(profile)
            db.commit()

            token = create_access_token(
                user_id=user.id,
                email=user.email,
                roles=["developer"],
                permissions=["healing:approve", "reports:read", "flows:execute"],
            )

            return client, token, project.id, profile.id, execution.id

    def test_approval_lifecycle_and_locator_history_recording(
        self,
        test_context: tuple[TestClient, str, uuid.UUID, uuid.UUID, uuid.UUID],
    ) -> None:
        client, token, project_id, profile_id, execution_id = test_context
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a simulated HealingEvent requiring approval directly in DB
        with SessionLocal() as db:
            event = HealingEvent(
                execution_id=execution_id,
                element_profile_id=profile_id,
                original_locator="#old-save-id",
                healed_locator="[data-testid='save-btn']",
                confidence_score=0.88,
                scoring_breakdown={"role_name": 0.9, "attributes": 0.85},
                decision="requires_approval",
                is_approved=False,
            )
            db.add(event)
            db.flush()

            approval = Approval(
                healing_event_id=event.id,
                status="pending",
                comment="Score: 88.0%. Awaiting operator confirmation.",
            )
            db.add(approval)
            db.commit()
            approval_id = approval.id

        # 2. List pending approvals via API
        list_res = client.get("/api/v1/healing/approvals?status=pending", headers=headers)
        assert list_res.status_code == 200
        approvals = list_res.json()
        assert any(a["id"] == str(approval_id) for a in approvals)

        # 3. Respond with 'approved'
        respond_res = client.post(
            f"/api/v1/healing/approvals/{approval_id}/respond",
            json={"decision": "approved", "comment": "Operator verified correct button on UI."},
            headers=headers,
        )
        assert respond_res.status_code == 200
        resolved = respond_res.json()
        assert resolved["status"] == "approved"
        assert resolved["comment"] is not None

        # 4. Verify in DB: HealingEvent is now approved and LocatorHistory was saved
        with SessionLocal() as db:
            refreshed_event = db.query(HealingEvent).filter(HealingEvent.id == event.id).first()
            assert refreshed_event is not None
            assert refreshed_event.is_approved is True

            history = (
                db.query(LocatorHistory)
                .filter(
                    LocatorHistory.element_profile_id == profile_id,
                    LocatorHistory.locator_value == "[data-testid='save-btn']",
                )
                .first()
            )
            assert history is not None
            assert history.success_count >= 1

        # 5. List healing events via API
        events_res = client.get(f"/api/v1/healing/events?element_profile_id={profile_id}", headers=headers)
        assert events_res.status_code == 200
        events = events_res.json()
        assert len(events) >= 1
        assert events[0]["healed_locator"] == "[data-testid='save-btn']"
