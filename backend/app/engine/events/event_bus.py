"""Real-time execution event bus and WebSocket distribution hub.

Strictly zero AI dependencies. Deterministic in-memory event buffering
and thread-safe broadcast for live execution monitoring, viewport streaming,
and diagnostic log tracing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ExecutionEventTypes:
    """Standardized event types for live execution streaming."""

    STATUS_CHANGE = "execution:status_change"
    STEP_START = "step:start"
    STEP_COMPLETE = "step:complete"
    STEP_FAILED = "step:failed"
    SCREENSHOT_CAPTURED = "screenshot:captured"
    CONSOLE_LOG = "console:log"
    VIEWPORT_FRAME = "viewport:frame"


class ExecutionEventBus:
    """Thread-safe event distributor and buffer for real-time execution monitoring."""

    def __init__(self, max_buffer_per_execution: int = 150) -> None:
        self._max_buffer = max_buffer_per_execution
        self._lock = threading.Lock()
        # execution_id (str) -> set of connected WebSocket clients
        self._connections: dict[str, set[WebSocket]] = {}
        # execution_id (str) -> list of recent event dicts
        self._history: dict[str, list[dict[str, Any]]] = {}

    async def connect(self, websocket: WebSocket, execution_id: str) -> None:
        """Registers a connected WebSocket client to receive live execution events."""
        with self._lock:
            if execution_id not in self._connections:
                self._connections[execution_id] = set()
            self._connections[execution_id].add(websocket)
        logger.debug("WebSocket client connected to execution %s (total: %d)", execution_id, len(self._connections[execution_id]))

    async def disconnect(self, websocket: WebSocket, execution_id: str) -> None:
        """Unregisters a WebSocket client when closed or disconnected."""
        with self._lock:
            if execution_id in self._connections:
                self._connections[execution_id].discard(websocket)
                if not self._connections[execution_id]:
                    del self._connections[execution_id]
        logger.debug("WebSocket client disconnected from execution %s", execution_id)

    def get_history(self, execution_id: str | UUID) -> list[dict[str, Any]]:
        """Returns the chronological buffered event stream for immediate replay upon connection."""
        key = str(execution_id)
        with self._lock:
            return list(self._history.get(key, []))

    def clear_history(self, execution_id: str | UUID) -> None:
        """Purges buffered execution events."""
        key = str(execution_id)
        with self._lock:
            self._history.pop(key, None)

    def publish(self, execution_id: str | UUID, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Publishes an event to memory buffer and schedules asynchronous broadcast to active WebSockets.

        Can be called synchronously from any thread (e.g. Celery workers or sync executors).
        """
        key = str(execution_id)
        event_payload = {
            "execution_id": key,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        # 1. Store in replay history buffer
        with self._lock:
            if key not in self._history:
                self._history[key] = []
            self._history[key].append(event_payload)
            if len(self._history[key]) > self._max_buffer:
                self._history[key].pop(0)

            active_sockets = list(self._connections.get(key, set()))

        # 2. Schedule broadcast to connected websockets
        if active_sockets:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcast_async(active_sockets, key, event_payload))
            except RuntimeError:
                # No running event loop in current thread; try global event loop if available
                pass

        return event_payload

    async def _broadcast_async(
        self,
        sockets: list[WebSocket],
        execution_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Sends event payload to all active WebSockets, silently pruning dead connections."""
        dead_sockets: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.append(ws)

        if dead_sockets:
            with self._lock:
                if execution_id in self._connections:
                    for dead in dead_sockets:
                        self._connections[execution_id].discard(dead)


# Global singleton event bus
execution_event_bus = ExecutionEventBus()

