"""Application configuration re-export for AutomationTestingWithAgentBrowser.

Strictly PostgreSQL only. SQLite is prohibited.
Core settings are maintained in backend.app.core.config.
"""

from __future__ import annotations

from backend.app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
