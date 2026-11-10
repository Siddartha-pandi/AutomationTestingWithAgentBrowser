"""Automated Security & Company Data Protection Policy Verification (Phase 11).

Validates:
1. Zero AI SDKs installed or imported (OpenAI, Anthropic, Gemini, Ollama, LangChain).
2. Zero external AI API endpoints in configuration or source code.
3. Zero AI creator or AI settings pages in frontend.
4. Automatic credential and token redaction from logs and DOM snapshots.
5. Strict SSRF network policy blocking private IP ranges and unauthorized hosts.
6. Path traversal rejection for artifact file storage.
"""

from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.reports.artifact_manager import ArtifactManager, ArtifactSecurityError
from backend.app.security.network_policy import is_ip_restricted, validate_destination_url
from backend.app.security.redaction import Redactor
from backend.main import app

client = TestClient(app)

PROHIBITED_PACKAGES = {
    "openai",
    "anthropic",
    "google-generativeai",
    "google-ai-generativelanguage",
    "langchain",
    "langchain-core",
    "langchain-community",
    "llama-index",
    "litellm",
    "ollama",
    "cohere",
    "mistralai",
}

PROHIBITED_ENDPOINTS = [
    r"api\.openai\.com",
    r"api\.anthropic\.com",
    r"generativelanguage\.googleapis\.com",
    r"api\.cohere\.ai",
    r"localhost:11434",
    r"127\.0\.0\.1:11434",
    r"ollama:11434",
]


class TestZeroAIPolicyEnforcement:
    """Verifies that no AI dependencies, SDKs, or routes exist anywhere in the platform."""

    def test_no_prohibited_ai_packages_installed(self):
        installed = {dist.metadata["Name"].lower() for dist in importlib.metadata.distributions()}
        for pkg in PROHIBITED_PACKAGES:
            assert pkg not in installed, f"Prohibited AI package '{pkg}' must not be installed!"

    def test_no_prohibited_ai_endpoints_in_codebase(self):
        root_dir = Path(__file__).resolve().parent.parent
        scan_dirs = ["backend", "frontend/src"]
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in PROHIBITED_ENDPOINTS]

        for s_dir in scan_dirs:
            folder = root_dir / s_dir
            if not folder.exists():
                continue
            for file_path in folder.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix not in (".py", ".ts", ".tsx", ".json", ".env"):
                    continue
                if any(part in file_path.parts for part in ("node_modules", ".next", "__pycache__")):
                    continue

                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat in compiled_patterns:
                    assert not pat.search(content), (
                        f"Prohibited AI endpoint '{pat.pattern}' found in {file_path.relative_to(root_dir)}"
                    )

    def test_no_ai_routes_registered_in_fastapi(self):
        for route in app.routes:
            path = getattr(route, "path", "").lower()
            assert "openai" not in path
            assert "gemini" not in path
            assert "claude" not in path
            assert "ollama" not in path
            assert "ai-creator" not in path
            assert "llm" not in path

    def test_frontend_has_no_ai_creator_or_ai_settings_pages(self):
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "src"
        if not frontend_dir.exists():
            return

        for page_file in frontend_dir.rglob("*.tsx"):
            file_name = page_file.name.lower()
            assert "aicreator" not in file_name
            assert "aisettings" not in file_name
            assert "aiprovider" not in file_name


class TestCompanyDataProtectionEnforcement:
    """Verifies secret redaction, SSRF prevention, and safe artifact isolation."""

    def test_secrets_redaction_in_data_payloads(self):
        redactor = Redactor()
        sensitive_data = {
            "username": "admin_user",
            "password": "SuperSecretPassword123!",
            "api_key": "sk-proj-91289182918291829182",
            "access_token": "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy",
            "regular_field": "public_information",
        }

        redacted = redactor.redact_dict(sensitive_data)

        assert redacted["username"] == "admin_user"
        assert redacted["password"] in ("[REDACTED_SECRET]", "[REDACTED_PASSWORD]")
        assert redacted["api_key"] == "[REDACTED_SECRET]"
        assert "[REDACTED" in redacted["access_token"]
        assert redacted["regular_field"] == "public_information"

    def test_network_policy_blocks_ssrf_and_private_ip_ranges(self):
        allowed = ["app.company.net"]

        # Allowed host
        ok, msg = validate_destination_url("https://app.company.net/dashboard", allowed_domains=allowed)
        assert ok is True

        # Blocked unauthorized external domain
        ok, msg = validate_destination_url("https://malicious-site.com", allowed_domains=allowed)
        assert ok is False
        assert "not in the approved allowed domains" in msg

        # Blocked illegal schemes (SSRF & Arbitrary File Access)
        ok, msg = validate_destination_url("file:///etc/passwd", allowed_domains=allowed)
        assert ok is False
        assert "Prohibited URL scheme" in msg

        # Blocked private and loopback IPs (SSRF prevention)
        assert is_ip_restricted("127.0.0.1") is True
        assert is_ip_restricted("169.254.169.254") is True
        assert is_ip_restricted("10.0.0.1") is True
        assert is_ip_restricted("192.168.1.1") is True
        assert is_ip_restricted("93.184.216.34") is False

    def test_artifact_manager_rejects_directory_traversal(self):
        manager = ArtifactManager()
        from backend.app.models.execution import Artifact
        import uuid

        # Construct an artifact pointing to an escape path
        escape_artifact = Artifact(
            id=uuid.uuid4(),
            execution_id=uuid.uuid4(),
            artifact_type="screenshot",
            file_path="C:/Windows/System32/config/SAM",
            file_size_bytes=1024,
            mime_type="application/octet-stream",
            sha256_hash="fakehash",
        )

        with pytest.raises(ArtifactSecurityError):
            manager.get_safe_artifact_path(escape_artifact)
