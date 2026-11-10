"""Enterprise security package for AutomationTestingWithAgentBrowser."""

from backend.app.security.audit import log_audit_event
from backend.app.security.jwt import create_access_token, decode_access_token
from backend.app.security.network_policy import validate_destination_url
from backend.app.security.password import hash_password, verify_password
from backend.app.security.rbac import (
    get_current_superuser,
    get_current_user,
    get_user_permissions,
    require_permission,
    require_role,
)
from backend.app.security.redaction import redact_data, redact_text
from backend.app.security.retention import purge_expired_artifacts
from backend.app.security.secret_manager import decrypt_secret, encrypt_secret

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_current_superuser",
    "require_permission",
    "require_role",
    "get_user_permissions",
    "log_audit_event",
    "encrypt_secret",
    "decrypt_secret",
    "redact_text",
    "redact_data",
    "validate_destination_url",
    "purge_expired_artifacts",
]

