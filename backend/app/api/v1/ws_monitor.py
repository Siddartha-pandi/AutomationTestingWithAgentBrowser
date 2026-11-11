"""WebSocket endpoint for live browser execution monitoring, log streaming, and viewport updates.

Strictly zero AI dependencies. Authenticates via standard JWT (query token or bearer header),
subscribes across processes via Redis PubSub/Streams with local fallback, and streams
deterministic execution step transitions, logs, and screenshots.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from backend.app.api.v1.projects import user_has_project_access
from backend.app.browser import AgentBrowserAdapter
from backend.app.db.session import get_db
from backend.app.engine.events.event_bus import execution_event_bus
from backend.app.models.execution import Execution, ExecutionStep
from backend.app.models.user import User
from backend.app.security.jwt import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Live Monitoring"])


def _authenticate_ws_token(token_str: str | None, db: Session) -> User | None:
    """Validates JWT access token and retrieves corresponding active user."""
    if not token_str:
        return None
    try:
        payload = decode_access_token(token_str)
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            return None
        user_id = UUID(str(user_id_raw))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
        return user
    except Exception as exc:
        logger.debug("WebSocket authentication failed: %s", exc)
        return None


@router.websocket("/ws/executions/{execution_id}")
async def execution_live_monitor_ws(
    websocket: WebSocket,
    execution_id: str,
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Real-time bidirectional WebSocket stream for execution monitoring.

    Authenticates via JWT `token` query param or `access_token` cookie.
    Replays recent step history upon connection, then streams live step, log, and screenshot events.
    Subscribes across processes via Redis Pub/Sub with local in-memory fallback.
    """
    forwarder_task: asyncio.Task[None] | None = None
    delivered_event_ids: set[str] = set()

    try:
        # 1. Resolve token from query param, cookies, or auth headers
        resolved_token = token
        if not resolved_token:
            resolved_token = websocket.cookies.get("access_token")
        if not resolved_token:
            auth_hdr = websocket.headers.get("authorization", "")
            if auth_hdr.lower().startswith("bearer "):
                resolved_token = auth_hdr[7:].strip()

        # 2. Authenticate user
        user = _authenticate_ws_token(resolved_token, db)
        if not user:
            logger.warning("Rejected unauthenticated WebSocket attempt for execution %s", execution_id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 3. Verify execution exists and user has project authorization
        try:
            exec_uuid = UUID(execution_id)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        execution = db.query(Execution).filter(Execution.id == exec_uuid).first()
        if not execution or not user_has_project_access(db, execution.project_id, user):
            logger.warning("Rejected unauthorized WebSocket access to execution %s by user %s", execution_id, user.id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 4. Accept connection and register with local event distributor
        await websocket.accept()
        await execution_event_bus.connect(websocket, execution_id)

        # 5. Send initial connection payload & replay buffered events
        await websocket.send_json({
            "type": "connected",
            "execution_id": execution_id,
            "status": execution.status,
            "session_id": execution.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Replay event stream from Redis stream or memory buffer
        for history_evt in execution_event_bus.get_history(execution_id):
            evt_id = history_evt.get("id")
            if evt_id:
                delivered_event_ids.add(evt_id)
            await websocket.send_json(history_evt)

        # 6. Start cross-process Redis subscriber task if running in an event loop
        async def _redis_forwarder() -> None:
            try:
                async for evt in execution_event_bus.subscribe_redis_events(execution_id):
                    evt_id = evt.get("id")
                    if evt_id and evt_id in delivered_event_ids:
                        continue
                    if evt_id:
                        delivered_event_ids.add(evt_id)
                    await websocket.send_json(evt)
            except asyncio.CancelledError:
                pass
            except Exception as fwd_err:
                logger.debug("Redis event forwarder stopped: %s", fwd_err)

        try:
            loop = asyncio.get_running_loop()
            forwarder_task = loop.create_task(_redis_forwarder())
        except RuntimeError:
            forwarder_task = None

        # 7. Listen for incoming client heartbeats or control messages
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg)
            except Exception:
                msg = {"type": "text", "content": raw_msg}

            msg_type = msg.get("type", "")
            action = msg.get("action", "")

            if msg_type == "ping" or action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif action == "get_status":
                db.refresh(execution)
                await websocket.send_json({
                    "type": "execution:status_change",
                    "execution_id": execution_id,
                    "data": {
                        "status": execution.status,
                        "duration_ms": execution.duration_ms,
                        "session_id": execution.session_id,
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif action == "capture_viewport":
                # Safe viewport capture: avoids creating orphan sessions and returns artifact reference
                adapter = AgentBrowserAdapter()
                active_session = None
                if execution.session_id:
                    active_session = adapter.session_manager.get_session(execution.session_id)

                if active_session and active_session.is_active:
                    try:
                        res = adapter.screenshot(execution.session_id)
                        path = getattr(res, "screenshot_path", str(res))
                        await websocket.send_json({
                            "type": "viewport:frame",
                            "execution_id": execution_id,
                            "data": {
                                "artifact_path": path,
                                "viewport_url": f"/api/v1/executions/{execution_id}/viewport",
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception as err:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Could not capture live viewport from active session: {err}",
                        })
                else:
                    # Session expired or closed: retrieve latest recorded step screenshot artifact
                    latest_step = (
                        db.query(ExecutionStep)
                        .filter(ExecutionStep.execution_id == exec_uuid, ExecutionStep.screenshot_file != None)  # noqa: E711
                        .order_by(ExecutionStep.step_number.desc())
                        .first()
                    )
                    if latest_step and latest_step.screenshot_file:
                        await websocket.send_json({
                            "type": "viewport:frame",
                            "execution_id": execution_id,
                            "data": {
                                "artifact_path": latest_step.screenshot_file,
                                "viewport_url": f"/api/v1/executions/{execution_id}/viewport",
                                "step_number": latest_step.step_number,
                                "is_final": (execution.status in ("completed", "passed", "failed", "cancelled")),
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": (
                                "Browser session is no longer active and no prior step screenshot was recorded."
                                if execution.status in ("completed", "passed", "failed", "cancelled")
                                else "Browser session active in background worker; awaiting next step screenshot event."
                            ),
                        })

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected normally: %s", execution_id)
    except Exception as exc:
        logger.warning("Unhandled error in WebSocket execution monitor %s: %s", execution_id, exc)
    finally:
        if forwarder_task and not forwarder_task.done():
            forwarder_task.cancel()
        await execution_event_bus.disconnect(websocket, execution_id)
