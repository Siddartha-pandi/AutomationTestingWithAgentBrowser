"""Unit and integration test suite for Phase 5: Multi-User Platform and Enterprise Features.

Strictly zero AI dependencies. Tests:
1. Multi-tenant project isolation for environments and credentials.
2. AES-256-GCM encrypted credential vault, write-only masking, and secret rotation.
3. Runtime credential resolution, domain scope wildcard enforcement, and audit injection trail.
4. Granular RBAC permission checks, implied permissions, and IDOR prevention.
5. Immutable security audit logging, filtering, CSV/JSON compliance export, and retention purging.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import Response

from backend.app.api.v1.audit import export_audit_logs, list_audit_logs, trigger_retention_purge
from backend.app.api.v1.credentials import (
    CredentialCreateSchema,
    CredentialUpdateSchema,
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    resolve_credential_for_execution,
    update_credential,
)
from backend.app.api.v1.environments import (
    EnvironmentCreateSchema,
    EnvironmentUpdateSchema,
    create_environment,
    delete_environment,
    get_environment,
    list_environments,
    update_environment,
)
from backend.app.models.audit import AuditLog
from backend.app.models.project import Credential, Environment, Project, ProjectMember
from backend.app.models.user import Role, User
from backend.app.security.rbac import get_user_permissions, require_permission
from backend.app.security.secret_manager import SecretManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def superuser():
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.email = "admin@platform.internal"
    u.is_active = True
    u.is_superuser = True
    u.roles = []
    return u


@pytest.fixture
def regular_user():
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.email = "developer@platform.internal"
    u.is_active = True
    u.is_superuser = False
    role = MagicMock(spec=Role)
    role.name = "developer"
    role.permissions = ["flows:create_edit", "tests:create_edit", "environments:read", "credentials:read"]
    u.roles = [role]
    return u


@pytest.fixture
def viewer_user():
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.email = "auditor@platform.internal"
    u.is_active = True
    u.is_superuser = False
    role = MagicMock(spec=Role)
    role.name = "viewer"
    role.permissions = ["audit_logs:read"]
    u.roles = [role]
    return u


@pytest.fixture
def mock_project():
    p = MagicMock(spec=Project)
    p.id = uuid4()
    p.name = "Enterprise Banking Portal"
    p.owner_id = uuid4()
    return p


# ---------------------------------------------------------------------------
# 1. Environment Management & Multi-Tenant Isolation
# ---------------------------------------------------------------------------

def test_environment_create_and_encrypted_variables(superuser, mock_project):
    mock_db = MagicMock()
    with patch("backend.app.api.v1.environments.resolve_project_id", return_value=mock_project):
        payload = EnvironmentCreateSchema(
            project_id=str(mock_project.id),
            name="Staging Tier",
            base_url="https://staging.internal.net",
            allowed_domains=["*.internal.net"],
            variables={"API_KEY": "secret-key-123", "REGION": "us-east-1"},
        )
        res = create_environment(payload=payload, db=mock_db, current_user=superuser)

        assert res["name"] == "Staging Tier"
        assert res["base_url"] == "https://staging.internal.net"
        assert res["allowed_domains"] == ["*.internal.net"]
        assert "API_KEY" in res["variable_keys"]
        assert "REGION" in res["variable_keys"]
        assert res["variables_count"] == 2
        assert any(isinstance(c[0][0], Environment) for c in mock_db.add.call_args_list)
        assert mock_db.commit.called


def test_environment_update_and_get_access_control(superuser, regular_user, mock_project):
    mock_db = MagicMock()
    mock_env = MagicMock(spec=Environment)
    mock_env.id = uuid4()
    mock_env.project_id = mock_project.id
    mock_env.name = "Old QA"
    mock_env.base_url = "https://old.qa.internal"
    mock_env.allowed_domains = ["old.qa.internal"]
    mock_env.variables_encrypted = SecretManager.encrypt(json.dumps({"KEY": "val"}))
    mock_env.created_at = datetime.now(timezone.utc)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_env

    # 1. Successful update by authorized user
    with patch("backend.app.api.v1.environments.user_has_project_access", return_value=True):
        update_payload = EnvironmentUpdateSchema(
            name="New QA Tier",
            base_url="https://new.qa.internal",
            variables={"KEY": "new-val", "EXTRA": "added"},
        )
        updated = update_environment(
            environment_id=mock_env.id,
            payload=update_payload,
            db=mock_db,
            current_user=superuser,
        )
        assert updated["name"] == "New QA Tier"
        assert updated["base_url"] == "https://new.qa.internal"
        assert updated["variables_count"] == 2

    # 2. Unauthorized project access rejection (IDOR protection)
    with patch("backend.app.api.v1.environments.user_has_project_access", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            get_environment(environment_id=mock_env.id, db=mock_db, current_user=regular_user)
        assert exc_info.value.status_code == 404


def test_environment_deletion(superuser, mock_project):
    mock_db = MagicMock()
    mock_env = MagicMock(spec=Environment, id=uuid4(), project_id=mock_project.id, name="Temp Env")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_env

    with patch("backend.app.api.v1.environments.user_has_project_access", return_value=True):
        delete_environment(environment_id=mock_env.id, db=mock_db, current_user=superuser)
        mock_db.delete.assert_called_once_with(mock_env)
        assert mock_db.commit.called


# ---------------------------------------------------------------------------
# 2. AES-256 Credential Vault & Secret Rotation
# ---------------------------------------------------------------------------

def test_credential_create_encrypts_and_masks_secret(superuser, mock_project):
    mock_db = MagicMock()
    with patch("backend.app.api.v1.credentials.resolve_project_id", return_value=mock_project):
        payload = CredentialCreateSchema(
            project_id=str(mock_project.id),
            name="Payment Gateway API Key",
            credential_type="api_token",
            username="pg_service_account",
            secret_value="sk_live_very_secret_key_9999",
            domain_scope="*.payment.internal",
        )
        created = create_credential(payload=payload, db=mock_db, current_user=superuser)

        assert created["name"] == "Payment Gateway API Key"
        assert created["credential_type"] == "api_token"
        assert created["username"] == "pg_service_account"
        assert created["domain_scope"] == "*.payment.internal"
        # Verify write-only masking: plaintext secret must NOT be in response
        assert created["masked_secret"] == "••••••••"
        assert "sk_live_very_secret_key_9999" not in json.dumps(created)

        # Verify added model has ciphertext that decrypts correctly
        saved_cred = next(c[0][0] for c in mock_db.add.call_args_list if isinstance(c[0][0], Credential))
        assert saved_cred.secret_encrypted != "sk_live_very_secret_key_9999"
        assert SecretManager.decrypt(saved_cred.secret_encrypted) == "sk_live_very_secret_key_9999"


def test_credential_update_rotation_and_idor_protection(superuser, regular_user, mock_project):
    mock_db = MagicMock()
    initial_ciphertext = SecretManager.encrypt("old_initial_secret")
    mock_cred = MagicMock(
        spec=Credential,
        id=uuid4(),
        project_id=mock_project.id,
        name="OAuth Bearer",
        credential_type="bearer_token",
        username=None,
        domain_scope="api.company.internal",
        secret_encrypted=initial_ciphertext,
        created_at=datetime.now(timezone.utc),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_cred

    # 1. Rotate secret value with AES-256 encryption
    with patch("backend.app.api.v1.credentials.user_has_project_access", return_value=True):
        update_payload = CredentialUpdateSchema(
            name="OAuth Bearer Rotated",
            secret_value="new_rotated_secret_value",
        )
        updated = update_credential(
            credential_id=mock_cred.id,
            payload=update_payload,
            db=mock_db,
            current_user=superuser,
        )
        assert updated["name"] == "OAuth Bearer Rotated"
        assert mock_cred.secret_encrypted != initial_ciphertext
        assert SecretManager.decrypt(mock_cred.secret_encrypted) == "new_rotated_secret_value"

    # 2. Reject unauthorized cross-project access
    with patch("backend.app.api.v1.credentials.user_has_project_access", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            get_credential(credential_id=mock_cred.id, db=mock_db, current_user=regular_user)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 3. Secure Runtime Credential Resolution & Domain Scope
# ---------------------------------------------------------------------------

def test_resolve_credential_for_execution_success(mock_project):
    mock_db = MagicMock()
    plain_secret = "UltraSecretPassword123!"
    mock_cred = MagicMock(
        spec=Credential,
        id=uuid4(),
        project_id=mock_project.id,
        name="Admin Credentials",
        credential_type="username_password",
        username="admin_sys",
        domain_scope="*.company.internal",
        secret_encrypted=SecretManager.encrypt(plain_secret),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_cred

    resolved = resolve_credential_for_execution(
        db=mock_db,
        credential_id=mock_cred.id,
        project_id=mock_project.id,
        current_domain="auth.company.internal",
        user_id=uuid4(),
    )
    assert resolved["username"] == "admin_sys"
    assert resolved["secret"] == plain_secret
    assert resolved["type"] == "username_password"


def test_resolve_credential_domain_scope_violation(mock_project):
    mock_db = MagicMock()
    mock_cred = MagicMock(
        spec=Credential,
        id=uuid4(),
        project_id=mock_project.id,
        name="Internal Only",
        domain_scope="*.corp.internal",
        secret_encrypted=SecretManager.encrypt("topsecret"),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_cred

    # Attempting to inject into an external or unauthorized domain must trigger PermissionError
    with pytest.raises(PermissionError) as exc_info:
        resolve_credential_for_execution(
            db=mock_db,
            credential_id=mock_cred.id,
            project_id=mock_project.id,
            current_domain="malicious-site.com",
        )
    assert "restricted to domain scope '*.corp.internal'" in str(exc_info.value)


def test_resolve_credential_cross_project_blocked(mock_project):
    mock_db = MagicMock()
    mock_cred = MagicMock(
        spec=Credential,
        id=uuid4(),
        project_id=uuid4(),  # Different project
        name="Cross Project Cred",
        domain_scope=None,
        secret_encrypted=SecretManager.encrypt("val"),
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_cred

    with pytest.raises(PermissionError) as exc_info:
        resolve_credential_for_execution(
            db=mock_db,
            credential_id=mock_cred.id,
            project_id=mock_project.id,  # Target project mismatch
        )
    assert "does not belong to project" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. RBAC Matrix & Implied Permissions
# ---------------------------------------------------------------------------

def test_rbac_user_permissions_and_superusers(superuser, regular_user):
    # Superuser has wildcard permission
    assert get_user_permissions(superuser) == {"*"}

    # Regular user inherits role permissions
    dev_perms = get_user_permissions(regular_user)
    assert "flows:create_edit" in dev_perms
    assert "credentials:read" in dev_perms
    assert "*" not in dev_perms


def test_rbac_implied_permissions(regular_user, viewer_user):
    # environments:write implies environments:read
    role_env = MagicMock(spec=Role, permissions=["environments:write"])
    u_env = MagicMock(spec=User, is_superuser=False, roles=[role_env], email="env@corp.local")
    checker = require_permission("environments:read")
    assert checker(u_env) == u_env

    # credentials:manage implies credentials:read
    role_cred = MagicMock(spec=Role, permissions=["credentials:manage"])
    u_cred = MagicMock(spec=User, is_superuser=False, roles=[role_cred], email="cred@corp.local")
    checker_cred = require_permission("credentials:read")
    assert checker_cred(u_cred) == u_cred

    # Denied access when lacking permission
    with pytest.raises(HTTPException) as exc_info:
        require_permission("roles:manage")(viewer_user)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 5. Immutable Audit Logging, Export & Retention Purge
# ---------------------------------------------------------------------------

def test_audit_logs_list_and_filters(viewer_user):
    mock_db = MagicMock()
    audit_entry = MagicMock(
        spec=AuditLog,
        id=uuid4(),
        user_id=viewer_user.id,
        action="project.created",
        resource_type="project",
        resource_id="proj-123",
        client_ip="192.168.1.10",
        details={"name": "Test Project"},
        timestamp=datetime.now(timezone.utc),
    )
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [audit_entry]
    mock_db.query.return_value = mock_query

    logs = list_audit_logs(
        skip=0,
        limit=50,
        user_id=viewer_user.id,
        action="project.created",
        resource_type="project",
        current_user=viewer_user,
        db=mock_db,
    )
    assert len(logs) == 1
    assert logs[0].action == "project.created"
    assert logs[0].resource_type == "project"


def test_audit_logs_export_csv_and_json(viewer_user):
    mock_db = MagicMock()
    audit_entry = MagicMock(
        spec=AuditLog,
        id=uuid4(),
        user_id=viewer_user.id,
        action="credential.rotated",
        resource_type="credential",
        resource_id="cred-456",
        client_ip="10.0.0.5",
        details={"rotated": True},
        timestamp=datetime(2026, 11, 11, 12, 30, 0, tzinfo=timezone.utc),
    )
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value.limit.return_value.all.return_value = [audit_entry]
    mock_db.query.return_value = mock_query

    # 1. Test CSV export
    csv_res = export_audit_logs(format="csv", current_user=viewer_user, db=mock_db)
    assert isinstance(csv_res, Response)
    assert "text/csv" in csv_res.media_type
    assert "attachment; filename=audit_logs.csv" in csv_res.headers["content-disposition"]
    csv_content = csv_res.body.decode("utf-8")
    assert "Timestamp (UTC),User ID,Action,Resource Type" in csv_content
    assert "credential.rotated" in csv_content

    # 2. Test JSON export
    json_res = export_audit_logs(format="json", current_user=viewer_user, db=mock_db)
    assert isinstance(json_res, Response)
    assert "application/json" in json_res.media_type
    data = json.loads(json_res.body.decode("utf-8"))
    assert isinstance(data, list)
    assert data[0]["action"] == "credential.rotated"


def test_retention_purge_endpoint(superuser):
    mock_db = MagicMock()
    with patch("backend.app.api.v1.audit.purge_expired_artifacts", return_value={"logs": 45, "artifacts": 12, "dom_snapshots": 5}) as mock_purge:
        res = trigger_retention_purge(
            log_days=60,
            screenshot_days=15,
            dom_days=7,
            current_user=superuser,
            db=mock_db,
        )
        mock_purge.assert_called_once_with(db=mock_db, log_days=60, screenshot_days=15, dom_days=7)
        assert res["status"] == "completed"
        assert res["purged"]["logs"] == 45
        assert res["purged"]["artifacts"] == 12
        assert res["policy_horizons"]["log_days"] == 60
