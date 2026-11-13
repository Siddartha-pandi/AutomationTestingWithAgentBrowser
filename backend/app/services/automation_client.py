"""Client service for communicating with the Node.js NestJS Playwright Automation Service."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class AutomationServiceClient:
    """Authenticated HTTP client dispatching execution jobs to the NestJS Automation Service."""

    def __init__(
        self,
        base_url: str | None = None,
        internal_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or settings.automation_service_url).rstrip("/")
        self.internal_key = internal_key or settings.internal_service_key
        self.timeout = timeout

    def _headers(self, correlation_id: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Internal-Service-Key": self.internal_key,
        }
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        return headers

    def check_health(self) -> dict[str, Any]:
        """Queries the automation service health and browser readiness."""
        url = f"{self.base_url}/internal/v1/health"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "unhealthy", "status_code": resp.status_code, "body": resp.text}
        except Exception as exc:
            logger.warning("Failed to reach automation service at %s: %s", url, exc)
            return {"status": "unreachable", "error": str(exc)}

    def submit_execution(
        self,
        execution_id: str | UUID,
        project_id: str | UUID,
        user_id: str | UUID,
        graph_definition: dict[str, Any],
        environment_id: str | UUID | None = None,
        flow_id: str | UUID | None = None,
        test_case_id: str | UUID | None = None,
        browser_config: dict[str, Any] | None = None,
        allowed_domains: list[str] | None = None,
        variables: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Dispatches an authorized execution job to the NestJS BullMQ queue."""
        url = f"{self.base_url}/internal/v1/jobs/execute"
        payload = {
            "execution_id": str(execution_id),
            "project_id": str(project_id),
            "environment_id": str(environment_id) if environment_id else None,
            "user_id": str(user_id),
            "flow_id": str(flow_id) if flow_id else None,
            "test_case_id": str(test_case_id) if test_case_id else None,
            "browser_config": browser_config or {
                "browser_type": "chromium",
                "headless": True,
                "viewport": {"width": 1280, "height": 800},
                "record_video": False,
                "record_trace": True,
                "timeout_ms": 30000,
            },
            "allowed_domains": allowed_domains or ["*"],
            "variables": variables or {},
            "graph_definition": graph_definition,
            "correlation_id": correlation_id or f"corr-{execution_id}",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=self._headers(correlation_id=correlation_id))
            if resp.status_code not in (200, 201, 202):
                logger.error(
                    "Automation service returned error %d: %s",
                    resp.status_code,
                    resp.text,
                )
                raise RuntimeError(
                    f"Automation service job submission failed ({resp.status_code}): {resp.text}"
                )
            return resp.json()

    def cancel_execution(self, execution_id: str | UUID) -> dict[str, Any]:
        """Sends cancellation request for an active or queued execution."""
        url = f"{self.base_url}/internal/v1/jobs/{execution_id}/cancel"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._headers())
            return resp.json()


automation_client = AutomationServiceClient()

