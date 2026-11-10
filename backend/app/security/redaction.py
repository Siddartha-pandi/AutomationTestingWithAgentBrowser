"""Deterministic redaction engine for execution logs, step results, and error messages.

Scrubs passwords, tokens, API keys, bearer headers, and registered credential secrets
before data is saved to PostgreSQL, broadcast over WebSockets, or served to clients.
Zero AI processing.
"""

from __future__ import annotations

import re
from typing import Any

# Compiled regex patterns for sensitive tokens and headers
SENSITIVE_PATTERNS = [
    # Bearer tokens: Bearer <token>
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=.]+", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    # Generic password / secret parameters in JSON or URL query strings
    (
        re.compile(r"""(?i)(["']?(?:password|passwd|secret|token|api[_-]?key|auth|access_token|client_secret)["']?\s*[:=]\s*["']?)([^"'&\s,]+)"""),
        r"\1[REDACTED_SECRET]",
    ),
    # Credit Card Numbers (13-16 digits)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
    # Basic auth in URLs: http://user:pass@host
    (re.compile(r"(https?://)([^:]+):([^@]+)@"), r"\1\2:[REDACTED]@"),
]


def redact_text(text: str, registered_secrets: list[str] | None = None) -> str:
    """Scrubs registered secrets and matches against deterministic sensitive regex patterns."""
    if not text:
        return ""

    redacted = text

    # Step 1: Exact replacement of registered project secrets
    if registered_secrets:
        for secret in registered_secrets:
            if secret and len(secret) >= 4:  # Avoid redacting trivial substrings
                redacted = redacted.replace(secret, "[REDACTED_SECRET]")

    # Step 2: Apply pattern scrubbers
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)

    return redacted


def redact_data(data: Any, registered_secrets: list[str] | None = None) -> Any:
    """Recursively walks nested dictionaries/lists to redact string values and ensure JSON safety."""
    if isinstance(data, str):
        return redact_text(data, registered_secrets)
    if isinstance(data, (int, float, bool)) or data is None:
        return data
    if isinstance(data, dict):
        return {
            str(k): ("[REDACTED_SECRET]" if any(kw in str(k).lower() for kw in ("password", "secret", "token", "key")) and isinstance(v, str)
                else redact_data(v, registered_secrets))
            for k, v in data.items()
        }
    if isinstance(data, (list, tuple, set)):
        return [redact_data(item, registered_secrets) for item in data]
    # Fallback to string for arbitrary non-JSON types (e.g. Mocks)
    return str(data)


class Redactor:
    """Class wrapper for deterministic redaction."""

    def __init__(self, registered_secrets: list[str] | None = None) -> None:
        self.registered_secrets = registered_secrets or []

    def redact_text(self, text: str) -> str:
        return redact_text(text, self.registered_secrets)

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return redact_data(data, self.registered_secrets)

    def redact_data(self, data: Any) -> Any:
        return redact_data(data, self.registered_secrets)


