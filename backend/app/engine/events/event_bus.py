"""Real-time execution event bus and multi-process distribution hub.

Strictly zero AI dependencies. Supports:
- Cross-process Celery worker to FastAPI WebSocket event streaming via Redis Streams & Pub/Sub
- Thread-safe in-memory event buffering and local broadcast fallback
- Replay of chronological event history for reconnecting clients
- Monotonic sequence numbering and deduplication
- Graceful error handling and offline fallback when Redis is unreachable
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections.abc import AsyncGenerator
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
    """Multi-process and thread-safe event distributor for live execution monitoring."""

    def __init__(self, max_buffer_per_execution: int = 200) -> None:
        self._max_buffer = max_buffer_per_execution
        self._lock = threading.Lock()
        # execution_id (str) -> set of connected local WebSocket clients
        self._connections: dict[str, set[WebSocket]] = {}
        # execution_id (str) -> list of recent event dicts
        self._history: dict[str, list[dict[str, Any]]] = {}
        # Monotonic event sequence counter per execution
        self._sequences: dict[str, int] = {}

        self._redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
        self._sync_redis_client: Any = None
        self._redis_available: bool | None = None

    def _get_sync_redis(self) -> Any:
        """Lazily initializes and returns synchronous Redis connection."""
        if self._sync_redis_client is not None:
            return self._sync_redis_client
        try:
            import redis

            self._sync_redis_client = redis.Redis.from_url(
                self._redis_url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=True,
            )
            return self._sync_redis_client
        except Exception as exc:
            logger.debug("Could not initialize Redis client: %s", exc)
            return None

    def _next_seq(self, execution_id: str) -> int:
        with self._lock:
            current = self._sequences.get(execution_id, 0) + 1
            self._sequences[execution_id] = current
            return current

    async def connect(self, websocket: WebSocket, execution_id: str) -> None:
        """Registers a connected WebSocket client to receive live execution events."""
        with self._lock:
            if execution_id not in self._connections:
                self._connections[execution_id] = set()
            self._connections[execution_id].add(websocket)
        logger.debug(
            "WebSocket client connected to execution %s (local active: %d)",
            execution_id,
            len(self._connections[execution_id]),
        )

    async def disconnect(self, websocket: WebSocket, execution_id: str) -> None:
        """Unregisters a WebSocket client when closed or disconnected."""
        with self._lock:
            if execution_id in self._connections:
                self._connections[execution_id].discard(websocket)
                if not self._connections[execution_id]:
                    del self._connections[execution_id]
        logger.debug("WebSocket client disconnected from execution %s", execution_id)

    def get_history(self, execution_id: str | UUID) -> list[dict[str, Any]]:
        """Returns the chronological buffered event stream for immediate replay upon connection.

        First attempts to read from Redis Stream; falls back to in-memory history.
        """
        key = str(execution_id)
        redis_client = self._get_sync_redis()
        if redis_client:
            try:
                stream_key = f"execution:stream:{key}"
                entries = redis_client.xrange(stream_key, min="-", max="+", count=self._max_buffer)
                if entries:
                    history = []
                    for _entry_id, data_dict in entries:
                        if "payload" in data_dict:
                            try:
                                history.append(json.loads(data_dict["payload"]))
                            except Exception:
                                pass
                    if history:
                        return history
            except Exception as exc:
                logger.debug("Redis stream history lookup failed (%s); using local history fallback", exc)

        with self._lock:
            return list(self._history.get(key, []))

    def clear_history(self, execution_id: str | UUID) -> None:
        """Purges buffered execution events."""
        key = str(execution_id)
        with self._lock:
            self._history.pop(key, None)
            self._sequences.pop(key, None)

        redis_client = self._get_sync_redis()
        if redis_client:
            try:
                redis_client.delete(f"execution:stream:{key}")
                redis_client.delete(f"execution:events:{key}")
            except Exception:
                pass

    def publish(
        self,
        execution_id: str | UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Publishes an event to Redis Stream/PubSub and local memory buffer.

        Can be called synchronously from any process (e.g. Celery workers or sync executors).
        """
        key = str(execution_id)
        seq = self._next_seq(key)
        event_id = f"evt_{key}_{seq}_{int(time.time() * 1000)}"

        event_payload = {
            "id": event_id,
            "execution_id": key,
            "seq": seq,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        # 1. Update in-memory fallback buffer
        with self._lock:
            if key not in self._history:
                self._history[key] = []
            self._history[key].append(event_payload)
            if len(self._history[key]) > self._max_buffer:
                self._history[key].pop(0)

            active_sockets = list(self._connections.get(key, set()))

        # 2. Publish to Redis (Cross-process distribution to FastAPI workers)
        redis_client = self._get_sync_redis()
        if redis_client:
            try:
                json_payload = json.dumps(event_payload)
                stream_key = f"execution:stream:{key}"
                channel_key = f"execution:channel:{key}"

                # Append to Redis Stream for ordered replay and persistence
                redis_client.xadd(
                    stream_key,
                    {"id": event_id, "payload": json_payload},
                    maxlen=self._max_buffer,
                    approximate=True,
                )
                # Set TTL on stream (24 hours)
                redis_client.expire(stream_key, 86400)

                # Broadcast to PubSub channel for instant sub-millisecond push
                redis_client.publish(channel_key, json_payload)
            except Exception as exc:
                logger.debug("Redis publish failed (%s); event retained in local memory", exc)

        # 3. Schedule broadcast to connected same-process WebSockets
        if active_sockets:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._broadcast_async(active_sockets, key, event_payload))
            except RuntimeError:
                pass

        return event_payload

    async def _broadcast_async(
        self,
        sockets: list[WebSocket],
        execution_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Sends event payload to all active local WebSockets."""
        dead_sockets: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.append(ws)

        if dead_sockets:
            with self._lock:
                if execution_id in self._connections:
                    for ds in dead_sockets:
                        self._connections[execution_id].discard(ds)

    async def subscribe_redis_events(
        self,
        execution_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Asynchronously subscribes to Redis PubSub for cross-process live updates.

        Yields deserialized event payloads as they are received from Redis.
        Gracefully handles disconnections and reconnect attempts.
        """
        key = str(execution_id)
        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.debug("redis.asyncio not available; skipping Redis subscription")
            return

        client = None
        pubsub = None
        try:
            client = aioredis.from_url(
                self._redis_url,
                socket_timeout=5.0,
                socket_connect_timeout=3.0,
                decode_responses=True,
            )
            pubsub = client.pubsub()
            channel_key = f"execution:channel:{key}"
            await pubsub.subscribe(channel_key)
            logger.debug("Subscribed to Redis channel: %s", channel_key)

            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        raw_data = message.get("data")
                        if raw_data:
                            try:
                                yield json.loads(raw_data)
                            except Exception:
                                pass
                    await asyncio.sleep(0.05)
                except asyncio.CancelledError:
                    break
                except Exception as loop_err:
                    logger.debug("Redis pubsub loop exception: %s", loop_err)
                    await asyncio.sleep(1.0)
        except Exception as conn_err:
            logger.debug("Redis async connection failed (%s); WebSocket falling back to local bus", conn_err)
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe()
                    await pubsub.close()
                except Exception:
                    pass
            if client:
                try:
                    await client.close()
                except Exception:
                    pass


# Singleton event bus instance shared across the application
execution_event_bus = ExecutionEventBus()
