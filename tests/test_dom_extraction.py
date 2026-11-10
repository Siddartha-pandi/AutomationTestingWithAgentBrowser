"""Tests for Phase 4: Deterministic DOM Extraction and Element Profiles."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.intelligence.dom_extractor import DOMExtractor, ExtractedElementNode
from backend.app.intelligence.element_profile import ElementProfileBuilder
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.security.jwt import create_access_token
from backend.main import app


class TestDOMExtractorUnit:
    """Unit tests for DOM extraction structure and normalization."""

    def test_extracted_element_node_data_structure(self) -> None:
        node = ExtractedElementNode(
            tag="button",
            role="button",
            accessible_name="Submit Application",
            text="Submit Application",
            element_id="btn-submit",
            stable_attributes={"data-testid": "submit-btn", "type": "submit"},
            aria_properties={"aria-disabled": "false"},
            associated_label="Submit Button",
            ancestors=[{"tag": "form", "id": "app-form", "role": None}],
            siblings={"prev_tag": "input", "next_tag": "span"},
            nearby_heading="Personal Information",
            form_context={"form_id": "app-form", "form_method": "POST"},
            is_visible=True,
            is_enabled=True,
            box={"x": 100, "y": 200, "width": 80, "height": 35},
            page_url="https://app.local/form",
            route_path="/form",
        )

        d = node.to_dict()
        assert d["tag"] == "button"
        assert d["role"] == "button"
        assert d["accessible_name"] == "Submit Application"
        assert d["stable_attributes"]["data-testid"] == "submit-btn"
        assert d["form_context"]["form_id"] == "app-form"
        assert d["box"]["width"] == 80


class TestElementProfileBuilder:
    """Tests structural fingerprinting and profile construction."""

    def test_fingerprint_and_profile_construction(self) -> None:
        node = ExtractedElementNode(
            tag="input",
            role="textbox",
            accessible_name="Email Address",
            text="",
            element_id="user-email",
            stable_attributes={"data-testid": "email-input", "name": "email", "type": "email"},
            associated_label="Email Address",
            ancestors=[
                {"tag": "fieldset", "id": None, "test_id": "auth-fields"},
                {"tag": "form", "id": "login-form", "test_id": None},
            ],
            siblings={"prev_tag": "label", "next_tag": "button"},
            nearby_heading="Sign In to Your Account",
            form_context={"form_id": "login-form", "form_method": "POST"},
            is_visible=True,
            is_enabled=True,
        )

        profile = ElementProfileBuilder.from_node(
            logical_id="login_email_input",
            node=node,
            page_context="Login Page",
            description="User login email input",
        )

        assert profile.logical_id == "login_email_input"
        assert profile.page_context == "Login Page"
        assert profile.element_type == "textbox"
        assert profile.accessible_name == "Email Address"

        # Structural fingerprint assertions
        fp = profile.structural_fingerprint
        assert fp["tag"] == "input"
        assert fp["role"] == "textbox"
        assert fp["form_id"] == "login-form"
        assert fp["nearby_heading"] == "Sign In to Your Account"
        assert "label + input + button" in fp["sibling_signature"]
        assert "form#login-form" in fp["ancestor_path"]

        # Locators priority check
        locs = profile.historical_locators
        types = [loc["locator_type"] for loc in locs]
        assert "role_name" in types
        assert "stable_attribute" in types
        assert "label" in types


@pytest.mark.integration
class TestElementProfilesAPI:
    """Integration tests for Element Profiles REST endpoints."""

    @pytest.fixture
    def test_context(self) -> tuple[TestClient, str, uuid.UUID]:
        client = TestClient(app)
        with SessionLocal() as db:
            role = db.query(Role).filter(Role.name == "developer").first()
            user = User(
                email=f"dev_{uuid.uuid4().hex[:6]}@company.local",
                password_hash="dummy",
                full_name="Profile Dev",
                is_active=True,
                roles=[role] if role else [],
            )
            db.add(user)
            db.flush()

            project = Project(name="Profiles Test Project", owner_id=user.id)
            db.add(project)
            db.commit()

            token = create_access_token(
                user_id=user.id,
                email=user.email,
                roles=["developer"],
                permissions=["flows:create_edit"],
            )

            return client, token, project.id

    def test_element_profile_crud_lifecycle(self, test_context: tuple[TestClient, str, uuid.UUID]) -> None:
        client, token, project_id = test_context
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create Element Profile
        create_payload = {
            "project_id": str(project_id),
            "logical_id": "referral_submit_btn",
            "description": "Submit referral form button",
            "element_type": "button",
            "page_context": "Referral Dashboard",
            "original_text": "Submit Referral",
            "stable_attributes": {"data-testid": "submit-referral", "id": "btn-referral"},
            "structural_fingerprint": {"ancestor_path": ["form#referral-form"]},
        }

        res = client.post("/api/v1/elements", json=create_payload, headers=headers)
        assert res.status_code == 201
        created = res.json()
        assert created["logical_id"] == "referral_submit_btn"
        profile_id = created["id"]

        # Verify initial locator history was seeded from data-testid
        assert len(created["history"]) > 0
        assert created["history"][0]["locator_value"] == "[data-testid='submit-referral']"

        # 2. List Profiles
        list_res = client.get(f"/api/v1/elements?project_id={project_id}", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1
        assert any(p["id"] == profile_id for p in items)

        # 3. Get Detail
        detail_res = client.get(f"/api/v1/elements/{profile_id}", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["logical_id"] == "referral_submit_btn"

        # 4. Update Profile
        update_res = client.put(
            f"/api/v1/elements/{profile_id}",
            json={"description": "Updated referral button"},
            headers=headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["description"] == "Updated referral button"

        # 5. Delete Profile
        del_res = client.delete(f"/api/v1/elements/{profile_id}", headers=headers)
        assert del_res.status_code == 204

        # Verify 404 after delete
        not_found = client.get(f"/api/v1/elements/{profile_id}", headers=headers)
        assert not_found.status_code == 404

