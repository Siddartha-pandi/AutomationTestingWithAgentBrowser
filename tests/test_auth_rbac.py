"""Tests for Phase 3: Authentication, RBAC, Secret Management, Redaction, and Audit Logs."""

from __future__ import annotations

import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.db.session import SessionLocal
from backend.app.models.user import Role, User
from backend.app.models.audit import AuditLog
from backend.app.security.password import hash_password, verify_password
from backend.app.security.jwt import create_access_token, decode_access_token
from backend.app.security.secret_manager import encrypt_secret, decrypt_secret
from backend.app.security.redaction import redact_text, redact_data
from backend.app.security.network_policy import validate_destination_url, is_domain_allowed, is_ip_restricted
from backend.app.security.rbac import get_user_permissions


class TestCryptographicPrimitives:
    """Tests password hashing, JWTs, and AES-256-GCM encryption."""

    def test_password_hashing_and_verification(self) -> None:
        raw_pw = "SuperSecretPassword123!"
        hashed = hash_password(raw_pw)

        assert hashed != raw_pw
        assert verify_password(raw_pw, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False

    def test_jwt_issuance_and_decoding(self) -> None:
        user_id = uuid.uuid4()
        token = create_access_token(
            user_id=user_id,
            email="developer@company.local",
            roles=["developer"],
            permissions=["flows:create_edit", "tests:create_edit"],
        )

        claims = decode_access_token(token)
        assert claims["sub"] == str(user_id)
        assert claims["email"] == "developer@company.local"
        assert "developer" in claims["roles"]
        assert "flows:create_edit" in claims["permissions"]

    def test_aes_gcm_secret_encryption_and_decryption(self) -> None:
        secret = "super-sensitive-api-token-xyz-12345"
        encrypted = encrypt_secret(secret)

        assert encrypted != secret
        assert decrypt_secret(encrypted) == secret

    def test_deterministic_redaction(self) -> None:
        raw_log = "User logged in with password='MySecretPassword123' and Bearer eyJhbGciOiJIUzI1NiJ9.test"
        redacted = redact_text(raw_log, registered_secrets=["MySecretPassword123"])

        assert "MySecretPassword123" not in redacted
        assert "[REDACTED_SECRET]" in redacted
        assert "[REDACTED_TOKEN]" in redacted

    def test_network_policy_and_ssrf_prevention(self) -> None:
        # Loopback blocked
        assert is_ip_restricted("127.0.0.1") is True
        # AWS metadata blocked
        assert is_ip_restricted("169.254.169.254") is True
        # Public IP allowed
        assert is_ip_restricted("93.184.216.34") is False

        # Domain whitelist with wildcards
        assert is_domain_allowed("app.mycompany.com", ["*.mycompany.com"]) is True
        assert is_domain_allowed("evil.attacker.com", ["*.mycompany.com"]) is False

        # Destination URL validator
        valid, msg = validate_destination_url("http://169.254.169.254/latest/meta-data")
        assert valid is False
        assert "SSRF Protection" in msg

        valid_ext, _ = validate_destination_url("https://approved.company.local", allowed_domains=["*.company.local"])
        assert valid_ext is True


class TestRBACPermissions:
    """Tests multi-user role permission resolution."""

    def test_user_permissions_resolution(self) -> None:
        role_dev = Role(name="developer", permissions=["flows:create_edit", "tests:create_edit"])
        role_tester = Role(name="tester", permissions=["executions:trigger", "reports:read"])

        dev_user = User(email="dev@company.local", password_hash="dummy", roles=[role_dev])
        perms = get_user_permissions(dev_user)
        assert "flows:create_edit" in perms
        assert "executions:trigger" not in perms

        multi_role_user = User(email="lead@company.local", password_hash="dummy", roles=[role_dev, role_tester])
        lead_perms = get_user_permissions(multi_role_user)
        assert "flows:create_edit" in lead_perms
        assert "executions:trigger" in lead_perms

        super_user = User(email="admin@company.local", password_hash="dummy", is_superuser=True)
        assert "*" in get_user_permissions(super_user)


@pytest.mark.integration
class TestAuthenticationAPIEndpoints:
    """Integration tests for versioned auth and user management endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app)

    def test_auth_registration_and_login_flow(self, client: TestClient) -> None:
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"test_{unique_suffix}@company.local"
        password = "SecurePassword123!"

        # 1. Register new user
        reg_res = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Test Engineer"},
        )
        assert reg_res.status_code == 201
        data = reg_res.json()
        assert "access_token" in data
        assert data["user"]["email"] == email
        token = data["access_token"]

        # 2. Login with credentials
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()

        # 3. Access protected /me endpoint
        me_res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

    def test_audit_logs_recorded(self, client: TestClient) -> None:
        with SessionLocal() as db:
            logs = db.query(AuditLog).all()
            assert len(logs) > 0
            actions = {l.action for l in logs}
            assert any("user" in a for a in actions)

