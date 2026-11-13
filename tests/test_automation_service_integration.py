"""Integration and unit tests for FastAPI to NestJS Playwright Automation Service integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.app.services.automation_client import AutomationServiceClient
from backend.config import settings


class TestAutomationServiceClient:
    """Tests the authenticated internal communication client."""

    def test_client_headers_contain_service_key_and_correlation_id(self) -> None:
        client = AutomationServiceClient(base_url="http://test-automation:3001", internal_key="secret-key-123")
        headers = client._headers(correlation_id="corr-test-456")

        assert headers["Content-Type"] == "application/json"
        assert headers["X-Internal-Service-Key"] == "secret-key-123"
        assert headers["X-Correlation-ID"] == "corr-test-456"

    @patch("httpx.Client.get")
    def test_check_health_success(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "healthy",
            "service": "automation-service",
            "browsers": {"chromium": True},
        }
        mock_get.return_value = mock_resp

        client = AutomationServiceClient(base_url="http://test-automation:3001")
        res = client.check_health()

        assert res["status"] == "healthy"
        assert res["browsers"]["chromium"] is True
        mock_get.assert_called_once()

    @patch("httpx.Client.post")
    def test_submit_execution_payload_structure(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_resp.json.return_value = {
            "status": "queued",
            "job_id": "bull-123",
            "execution_id": "exec-abc",
        }
        mock_post.return_value = mock_resp

        client = AutomationServiceClient(base_url="http://test-automation:3001")
        res = client.submit_execution(
            execution_id=uuid4(),
            project_id=uuid4(),
            user_id=uuid4(),
            graph_definition={"nodes": [], "edges": []},
            allowed_domains=["app.company.local"],
            variables={"BASE_URL": "https://app.company.local"},
        )

        assert res["status"] == "queued"
        assert res["job_id"] == "bull-123"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "/internal/v1/jobs/execute" in args[0]
        assert "graph_definition" in kwargs["json"]
        assert kwargs["json"]["allowed_domains"] == ["app.company.local"]

    @patch("httpx.Client.post")
    def test_cancel_execution_calls_endpoint(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"cancelled": True}
        mock_post.return_value = mock_resp

        client = AutomationServiceClient(base_url="http://test-automation:3001")
        exec_id = str(uuid4())
        res = client.cancel_execution(exec_id)

        assert res["cancelled"] is True
        mock_post.assert_called_once()
        args, _ = mock_post.call_args
        assert f"/internal/v1/jobs/{exec_id}/cancel" in args[0]

