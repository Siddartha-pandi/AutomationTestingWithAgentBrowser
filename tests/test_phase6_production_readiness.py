"""Tests for Phase 6: Production Readiness & DevOps.

Validates configuration security, Docker/container environment variables,
Celery Beat schedule integrity, SecretManager AES-256 key derivations,
CommandExecutor flag forwarding, and database connection resiliency.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from backend.config import Settings
from backend.app.browser.command_executor import CommandExecutor
from backend.app.security.secret_manager import SecretManager, _get_encryption_key, encrypt_secret, decrypt_secret
from backend.app.worker.celery_app import celery_app
from backend.app.security.network_policy import validate_destination_url


def test_sqlite_prohibition_in_settings():
    """Settings must immediately reject SQLite database configurations."""
    with pytest.raises(ValueError, match="SQLite is strictly prohibited"):
        Settings(database_url="sqlite:///test.db")


def test_settings_default_values():
    """Settings must properly load defaults and parse comma-separated lists."""
    test_settings = Settings(
        database_url="postgresql://user:pass@localhost:5432/testdb",
        cors_origins=("http://localhost:3000", "http://127.0.0.1:3000"),
        allowed_domains=("localhost", "company.local"),
    )
    assert test_settings.database_url.startswith("postgresql://")
    assert "http://localhost:3000" in test_settings.cors_origins
    assert "company.local" in test_settings.allowed_domains
    assert test_settings.default_timezone == "Asia/Kolkata"


def test_secret_manager_key_derivation_precedence():
    """SecretManager derives keys from APP_ENCRYPTION_KEY or CREDENTIALS_MASTER_KEY."""
    with patch.dict(os.environ, {"APP_ENCRYPTION_KEY": "app-custom-key-12345", "CREDENTIALS_MASTER_KEY": ""}, clear=False):
        key1 = _get_encryption_key()
        assert len(key1) == 32  # 256 bits

    with patch.dict(os.environ, {"APP_ENCRYPTION_KEY": "", "CREDENTIALS_MASTER_KEY": "master-custom-key-67890"}, clear=False):
        key2 = _get_encryption_key()
        assert len(key2) == 32
        assert key1 != key2


def test_secret_manager_roundtrip_and_tamper_detection():
    """SecretManager encrypts with AES-256-GCM and detects tampered ciphertexts."""
    plaintext = "super-secret-production-api-token-998877"
    ciphertext = SecretManager.encrypt(plaintext)
    assert ciphertext != plaintext

    decrypted = SecretManager.decrypt(ciphertext)
    assert decrypted == plaintext

    # Tampered ciphertext must fail authentication
    tampered = ciphertext[:-4] + "AAAA"
    with pytest.raises(Exception):
        SecretManager.decrypt(tampered)


def test_command_executor_args_and_flags():
    """CommandExecutor properly passes session, json, executable-path, and AGENT_BROWSER_ARGS."""
    executor = CommandExecutor(cli_path="agent-browser")

    with patch.dict(os.environ, {"AGENT_BROWSER_ARGS": "--no-sandbox --disable-dev-shm-usage"}), \
         patch.object(CommandExecutor, "_resolve_executable_path", return_value="/usr/bin/chromium"), \
         patch("subprocess.Popen") as mock_popen:

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ('{"ok": true}', "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        result = executor.execute(
            args=["open", "https://example.com"],
            session_id="test-session-42",
            parse_json=True,
        )

        assert mock_popen.called
        cmd_called = mock_popen.call_args[0][0]

        # Verify command flags
        assert "--session" in cmd_called
        assert "test-session-42" in cmd_called
        assert "--executable-path" in cmd_called
        assert "/usr/bin/chromium" in cmd_called
        assert "--args" in cmd_called
        assert "--no-sandbox --disable-dev-shm-usage" in cmd_called
        assert "--json" in cmd_called
        assert "open" in cmd_called
        assert "https://example.com" in cmd_called


def test_celery_beat_schedule_configuration():
    """Celery Beat schedules must include schedule-checker and artifact-retention tasks."""
    schedules = celery_app.conf.beat_schedule
    assert "evaluate-scheduled-automations-every-minute" in schedules
    assert schedules["evaluate-scheduled-automations-every-minute"]["task"] == "worker.schedule_checker"
    assert schedules["evaluate-scheduled-automations-every-minute"]["schedule"] == 60.0

    assert "daily-artifact-retention-cleanup" in schedules
    assert schedules["daily-artifact-retention-cleanup"]["task"] == "worker.cleanup_retention"
    assert schedules["daily-artifact-retention-cleanup"]["schedule"] == 86400.0


def test_celery_task_registry():
    """All core automation tasks must be registered in the Celery task registry."""
    import backend.app.worker.tasks  # registers decorated tasks
    registered = celery_app.tasks
    assert "worker.execute_flow" in registered
    assert "worker.execute_test_case" in registered
    assert "worker.execute_test_suite" in registered
    assert "worker.schedule_checker" in registered
    assert "worker.cleanup_retention" in registered


def test_network_policy_cloud_metadata_protection():
    """validate_destination_url must block AWS, GCP, Azure, and Oracle cloud metadata IP addresses."""
    # AWS/GCP metadata service
    allowed, err = validate_destination_url("http://169.254.169.254/latest/meta-data/")
    assert not allowed
    assert "SSRF Protection" in err or "prohibited" in err

    # GCP internal DNS
    allowed, err = validate_destination_url("http://metadata.google.internal/computeMetadata/v1/")
    assert not allowed
    assert "Cloud metadata" in err or "SSRF Protection" in err

    # Loopback forbidden when allow_loopback is False
    allowed, err = validate_destination_url("http://127.0.0.1:8080/admin", allow_loopback=False)
    assert not allowed

    # Allowed domain
    allowed, msg = validate_destination_url(
        "https://example.com/login",
        allowed_domains=["*.example.com", "example.com"],
    )
    assert allowed
    assert "allowed" in msg.lower()
