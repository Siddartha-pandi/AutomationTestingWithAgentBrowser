"""Post-action application state verifier.

Asserts that a browser action actually changed application state before
recording healing events or committing updated locator history.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.app.browser import AgentBrowserAdapter

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Outcome of a post-action verification check."""

    is_verified: bool
    check_type: str
    target: str
    observed_value: Any
    expected_value: Any
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_verified": self.is_verified,
            "check_type": self.check_type,
            "target": self.target,
            "observed_value": self.observed_value,
            "expected_value": self.expected_value,
            "duration_ms": round(self.duration_ms, 2),
        }


class StateVerifier:
    """Verifies that an automated action produced the expected application side-effect."""

    def __init__(self, adapter: AgentBrowserAdapter) -> None:
        self.adapter = adapter

    def verify_action_effect(
        self,
        session_id: str,
        expected_check: str,
        target: str,
        expected_value: Any = None,
        timeout_ms: int = 5000,
    ) -> VerificationResult:
        """Verifies application state after an action."""
        import time

        start = time.perf_counter()
        is_verified = False
        observed: Any = None

        try:
            if expected_check == "url_contains":
                observed = self.adapter.get_url(session_id)
                is_verified = str(expected_value).lower() in str(observed).lower()
            elif expected_check == "element_visible":
                observed = self.adapter.is_visible(session_id, target)
                is_verified = observed is True
            elif expected_check == "element_hidden":
                observed = self.adapter.is_visible(session_id, target)
                is_verified = observed is False
            elif expected_check == "text_contains":
                observed = self.adapter.extract_text(session_id, target)
                is_verified = str(expected_value).lower() in str(observed).lower()
            elif expected_check == "value_equals":
                observed = self.adapter.get_value(session_id, target)
                is_verified = str(observed) == str(expected_value)
            else:
                # Default check: browser remains responsive
                observed = self.adapter.get_url(session_id)
                is_verified = bool(observed)
        except Exception as err:
            logger.warning("Verification check failed: %s", err)
            observed = str(err)
            is_verified = False

        duration_ms = (time.perf_counter() - start) * 1000.0
        return VerificationResult(
            is_verified=is_verified,
            check_type=expected_check,
            target=target,
            observed_value=observed,
            expected_value=expected_value,
            duration_ms=duration_ms,
        )

