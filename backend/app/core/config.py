"""Application configuration settings for AutomationTestingWithAgentBrowser.

Strictly PostgreSQL only. SQLite is prohibited.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Resolve project root .env
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Enterprise application settings."""

    # Database: Strictly PostgreSQL
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/automation_platform_db",
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "change-this-development-secret")
    token_expiry_minutes: int = int(os.getenv("TOKEN_EXPIRY_MINUTES", "480"))
    cors_origins: tuple[str, ...] = tuple(
        value.strip()
        for value in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if value.strip()
    )

    # Browser Execution
    agent_browser_cli: str = os.getenv("AGENT_BROWSER_CLI", "agent-browser.cmd" if os.name == "nt" else "agent-browser")
    agent_browser_timeout: float = float(os.getenv("AGENT_BROWSER_TIMEOUT", "30.0"))
    storage_dir: str = os.getenv("STORAGE_DIR", "./reports")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    allowed_domains: tuple[str, ...] = tuple(
        value.strip()
        for value in os.getenv(
            "ALLOWED_DOMAINS",
            "localhost,127.0.0.1,*.company.internal,*.company.local",
        ).split(",")
        if value.strip()
    )

    # Worker & Redis Execution
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
    celery_task_always_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() in ("true", "1", "yes")
    celery_worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

    # Playwright Automation Service Integration
    automation_engine: str = os.getenv("AUTOMATION_ENGINE", "playwright").lower()
    automation_service_url: str = os.getenv("AUTOMATION_SERVICE_URL", "http://127.0.0.1:3001").rstrip("/")
    internal_service_key: str = os.getenv("INTERNAL_SERVICE_KEY", "enterprise-internal-secret-service-key-32chars")

    def __post_init__(self) -> None:
        if self.database_url.lower().startswith("sqlite"):
            raise ValueError(
                "SQLite is strictly prohibited for this platform. Please configure a valid PostgreSQL DATABASE_URL."
            )


settings = Settings()

