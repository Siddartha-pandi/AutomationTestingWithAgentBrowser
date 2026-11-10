"""Unit and integration tests for Reports & Binary Artifact Management (Phase 10).

Validates:
- SHA-256 cryptographic hashing and PostgreSQL metadata indexing.
- Path traversal rejection and storage isolation.
- File integrity audit and tamper detection.
- Consolidated JSON report and standalone executive HTML report generation.
- REST endpoints for artifact download, inline inspection, and report exports.
Strictly Zero-AI compliance verified.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.execution import Artifact, DOMSnapshot, Execution, ExecutionLog, ExecutionStep
from backend.app.models.intelligence import ElementProfile, HealingEvent
from backend.app.models.project import Environment, Project
from backend.app.models.user import Role, User
from backend.app.reports.artifact_manager import ArtifactManager, ArtifactSecurityError
from backend.app.reports.report_generator import ReportGenerator
from backend.app.security.jwt import create_access_token
from backend.config import settings
from backend.main import app

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def artifact_fixture(db_session, tmp_path):
    """Sets up a test project, execution, user token, and temporary test storage."""
    proj = Project(
        name=f"Artifact Project {uuid.uuid4().hex[:6]}",
        description="Artifact management workspace",
    )
    db_session.add(proj)

    env = Environment(
        project=proj,
        name="Artifact Staging",
        base_url="https://artifacts.staging.local",
        allowed_domains=["artifacts.staging.local"],
    )
    db_session.add(env)

    user = User(
        email=f"artifact.auditor.{uuid.uuid4().hex[:6]}@company.internal",
        password_hash="mock_hash",
        full_name="Compliance Auditor",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    owner_role = db_session.query(Role).filter(Role.name == "owner").first()
    if owner_role:
        user.roles.append(owner_role)

    flow = AutomationDefinition(
        project_id=proj.id,
        type="flow",
        name="Artifacts Test Flow",
        status="published",
        created_by=user.id,
    )
    db_session.add(flow)
    db_session.flush()

    version = DefinitionVersion(
        definition_id=flow.id,
        version_num=1,
        definition_json={"nodes": [], "edges": []},
        checksum_sha256="abc123artifactshash",
        is_published=True,
    )
    db_session.add(version)
    db_session.flush()
    flow.current_version_id = version.id

    execution = Execution(
        project_id=proj.id,
        definition_id=flow.id,
        definition_version_id=version.id,
        environment_id=env.id,
        trigger_type="manual",
        triggered_by=user.id,
        status="completed",
        duration_ms=1250.0,
        summary={"status": "passed"},
    )
    db_session.add(execution)
    db_session.flush()

    # Add steps
    step1 = ExecutionStep(
        execution_id=execution.id,
        step_index=1,
        node_id="n1",
        step_type="action",
        action="navigate",
        status="passed",
        input_data={"url": "https://company.internal/login"},
        result_data={"loaded": True},
        duration_ms=450.0,
    )
    db_session.add(step1)

    step2 = ExecutionStep(
        execution_id=execution.id,
        step_index=2,
        node_id="n2",
        step_type="action",
        action="click",
        status="passed",
        input_data={"selector": "#btn-submit"},
        result_data={"clicked": True},
        duration_ms=150.0,
    )
    db_session.add(step2)

    # Add log
    log1 = ExecutionLog(
        execution_id=execution.id,
        step_id=step1.id,
        level="INFO",
        message="Navigated to https://company.internal/login successfully",
        is_redacted=True,
    )
    db_session.add(log1)

    # Add element profile & healing event
    elem_profile = ElementProfile(
        project_id=proj.id,
        logical_id=f"btn_submit_{uuid.uuid4().hex[:6]}",
        description="Loan submission button",
        element_type="button",
        page_context="Loan Application",
        original_text="Submit",
        stable_attributes={"data-testid": "submit-loan"},
        structural_fingerprint={"tag": "button", "role": "button"},
    )
    db_session.add(elem_profile)
    db_session.flush()

    heal = HealingEvent(
        execution_id=execution.id,
        element_profile_id=elem_profile.id,
        original_locator="#btn-old",
        healed_locator="button[name='submit']",
        confidence_score=0.96,
        scoring_breakdown={"semantic": 0.98, "attributes": 0.95},
        decision="auto_healed",
        is_approved=True,
    )
    db_session.add(heal)

    db_session.commit()
    db_session.refresh(proj)
    db_session.refresh(execution)
    db_session.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email, roles=["owner"])

    return {
        "project": proj,
        "execution": execution,
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "storage_dir": Path(settings.storage_dir).resolve(),
    }


class TestArtifactManagerUnit:
    """Verifies file saving, hashing, DOM snapshotting, and tamper detection."""

    def test_save_file_artifact_and_sha256(self, db_session, artifact_fixture):
        manager = ArtifactManager()
        exec_id = artifact_fixture["execution"].id
        sample_bytes = b"Hello Enterprise Artifact Storage - No AI"
        expected_hash = hashlib.sha256(sample_bytes).hexdigest()

        artifact = manager.save_file_artifact(
            db=db_session,
            execution_id=exec_id,
            artifact_type="pdf",
            content_bytes=sample_bytes,
            filename="audit_report.pdf",
            mime_type="application/pdf",
        )

        assert artifact.id is not None
        assert artifact.file_size_bytes == len(sample_bytes)
        assert artifact.sha256_hash == expected_hash
        assert artifact.mime_type == "application/pdf"
        assert Path(artifact.file_path).exists()
        assert manager.verify_artifact_integrity(artifact) is True

    def test_save_dom_snapshot_redacted(self, db_session, artifact_fixture):
        manager = ArtifactManager()
        exec_id = artifact_fixture["execution"].id
        raw_dom = {
            "page_title": "Login Portal",
            "total_elements": 42,
            "secret_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret123",
            "body": "<button>Submit</button>",
        }

        dom_record, art_record = manager.save_dom_snapshot_artifact(
            db=db_session,
            execution_id=exec_id,
            page_url="https://company.internal/login",
            dom_data=raw_dom,
        )

        assert dom_record.id is not None
        assert dom_record.element_count == 42
        assert art_record.artifact_type == "dom"
        assert Path(art_record.file_path).exists()

        # Verify that secret token was redacted before writing to disk
        content = Path(art_record.file_path).read_text(encoding="utf-8")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret123" not in content
        assert "[REDACTED_SECRET]" in content or "[REDACTED]" in content

    def test_artifact_tamper_detection(self, db_session, artifact_fixture):
        manager = ArtifactManager()
        exec_id = artifact_fixture["execution"].id

        artifact = manager.save_file_artifact(
            db=db_session,
            execution_id=exec_id,
            artifact_type="trace",
            content_bytes=b"unmodified trace data",
            filename="browser_trace.har",
        )
        assert manager.verify_artifact_integrity(artifact) is True

        # Tamper with file on disk
        with open(artifact.file_path, "wb") as f:
            f.write(b"tampered and modified data")

        # Integrity check must detect alteration
        assert manager.verify_artifact_integrity(artifact) is False

    def test_path_traversal_attack_rejected(self, db_session, artifact_fixture):
        manager = ArtifactManager()
        exec_id = artifact_fixture["execution"].id

        # Fabricate an artifact attempting to point outside approved storage directory
        malicious_artifact = Artifact(
            execution_id=exec_id,
            artifact_type="screenshot",
            file_path="C:/Windows/System32/drivers/etc/hosts",
            file_size_bytes=100,
            mime_type="text/plain",
            sha256_hash="fakehash123",
        )

        with pytest.raises(ArtifactSecurityError) as exc_info:
            manager.get_safe_artifact_path(malicious_artifact)

        assert "Path traversal detected" in str(exc_info.value)


class TestReportGenerator:
    """Verifies consolidated report compilation and HTML rendering."""

    def test_generate_consolidated_report_json(self, db_session, artifact_fixture):
        exec_id = artifact_fixture["execution"].id

        report = ReportGenerator.generate_consolidated_report(db_session, exec_id)

        assert report["execution_id"] == str(exec_id)
        assert report["status"] == "completed"
        assert report["metrics"]["total_steps"] == 2
        assert report["metrics"]["passed_steps"] == 2
        assert report["metrics"]["pass_rate_percent"] == 100.0
        assert report["metrics"]["self_healing_count"] == 1
        assert len(report["steps"]) == 2
        assert len(report["logs"]) == 1
        assert len(report["healing_events"]) == 1
        assert report["data_protection_compliance"]["ai_processing"] is False
        assert report["data_protection_compliance"]["policy_status"] == "VERIFIED_COMPLIANT"

    def test_export_html_report_rendering(self, db_session, artifact_fixture):
        exec_id = artifact_fixture["execution"].id
        report = ReportGenerator.generate_consolidated_report(db_session, exec_id)

        html_out = ReportGenerator.export_html_report(report)

        assert "<!DOCTYPE html>" in html_out
        assert "AutomationTestingWithAgentBrowser" in html_out
        assert "Step Execution Timeline" in html_out
        assert "Company Data Protection Policy Certified" in html_out
        assert "100% Deterministic" in html_out or "deterministic" in html_out


class TestArtifactsAndReportsAPI:
    """Verifies REST endpoints for downloading artifacts, inspecting reports, and security gates."""

    def test_artifact_download_and_verify_endpoints(self, db_session, artifact_fixture):
        headers = artifact_fixture["headers"]
        exec_id = artifact_fixture["execution"].id

        manager = ArtifactManager()
        artifact = manager.save_file_artifact(
            db=db_session,
            execution_id=exec_id,
            artifact_type="screenshot",
            content_bytes=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRmock_png_binary",
            filename="dashboard_view.png",
            mime_type="image/png",
        )

        # 1. Get metadata
        meta_res = client.get(f"/api/v1/artifacts/{artifact.id}", headers=headers)
        assert meta_res.status_code == 200
        assert meta_res.json()["sha256_hash"] == artifact.sha256_hash

        # 2. Verify endpoint
        verify_res = client.get(f"/api/v1/artifacts/{artifact.id}/verify", headers=headers)
        assert verify_res.status_code == 200
        assert verify_res.json()["is_intact"] is True

        # 3. View endpoint (inline)
        view_res = client.get(f"/api/v1/artifacts/{artifact.id}/view", headers=headers)
        assert view_res.status_code == 200
        assert "image/png" in view_res.headers["content-type"]
        assert view_res.headers.get("x-sha256-checksum") == artifact.sha256_hash

        # 4. Download endpoint (attachment)
        down_res = client.get(f"/api/v1/artifacts/{artifact.id}/download", headers=headers)
        assert down_res.status_code == 200
        assert "attachment" in down_res.headers.get("content-disposition", "")
        assert down_res.content == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRmock_png_binary"

    def test_execution_report_api_endpoints(self, artifact_fixture):
        headers = artifact_fixture["headers"]
        exec_id = artifact_fixture["execution"].id

        # 1. JSON Report
        rep_res = client.get(f"/api/v1/executions/{exec_id}/report", headers=headers)
        assert rep_res.status_code == 200
        data = rep_res.json()
        assert data["execution_id"] == str(exec_id)
        assert data["metrics"]["total_steps"] == 2

        # 2. HTML Report
        html_res = client.get(f"/api/v1/executions/{exec_id}/report/html", headers=headers)
        assert html_res.status_code == 200
        assert "text/html" in html_res.headers["content-type"]
        assert "<!DOCTYPE html>" in html_res.text

        # 3. List Execution Artifacts
        arts_res = client.get(f"/api/v1/executions/{exec_id}/artifacts", headers=headers)
        assert arts_res.status_code == 200
        assert isinstance(arts_res.json(), list)

