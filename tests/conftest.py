"""Pytest shared configuration, markers, and database connectivity fixtures."""

from __future__ import annotations

import logging
import pytest
from sqlalchemy import text
from backend.app.db.session import engine

logger = logging.getLogger(__name__)

_DB_CONNECTED: bool | None = None


def is_database_connected() -> bool:
    """Checks if the configured PostgreSQL database is reachable."""
    global _DB_CONNECTED
    if _DB_CONNECTED is not None:
        return _DB_CONNECTED

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            _DB_CONNECTED = True
    except Exception as err:
        logger.warning("Database connectivity check failed (offline or unreachable): %s", err)
        _DB_CONNECTED = False

    return _DB_CONNECTED


@pytest.fixture(autouse=True)
def skip_if_no_db(request: pytest.FixtureRequest) -> None:
    """Automatically skips tests requiring a live database when running offline."""
    needs_db = False
    name = request.node.name.lower()
    cls_name = getattr(request.cls, "__name__", "").lower()
    module_name = getattr(request.module, "__name__", "").lower()

    if any(token in request.fixturenames for token in ("db", "test_context", "test_execution_context", "test_flow_context")):
        needs_db = True
    elif request.node.get_closest_marker("integration") or request.node.get_closest_marker("requires_db"):
        needs_db = True
    elif (
        cls_name.endswith("api")
        or "postgres" in name
        or "db" in name
        or "seed" in name
        or "artifacts_reports" in module_name
        or "worker_tasks" in module_name
    ):
        needs_db = True

    if needs_db and not is_database_connected():
        pytest.skip("PostgreSQL database is offline or unreachable in current execution sandbox.")
