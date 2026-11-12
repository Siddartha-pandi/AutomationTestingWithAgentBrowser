"""REST API endpoints for Agent Browser recording sessions (/api/v1/recorder)."""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.v1.browser import _browser_adapter, get_verified_session
from backend.app.api.v1.projects import resolve_project_id
from backend.app.db.session import get_db
from backend.app.models.automation import AutomationDefinition, DefinitionVersion
from backend.app.models.user import User
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recorder", tags=["Browser Recorder"])

# Active in-memory recorder sessions: { session_id: { "project_id": str, "user_id": str, "url": str, "actions": list } }
_ACTIVE_RECORDINGS: dict[str, dict[str, Any]] = {}


class StartRecorderPayload(BaseModel):
    project_id: str
    target_url: str = Field(..., min_length=5)


class RecordActionPayload(BaseModel):
    session_id: str
    action: str  # navigate, click, fill, type, select, check, radio, scroll, hover, dblclick, reload, back, forward
    selector: str = ""
    value: str | None = None


class StopRecorderPayload(BaseModel):
    session_id: str


class SaveRecordingPayload(BaseModel):
    session_id: str
    project_id: str
    name: str = Field(..., min_length=1, max_length=200)
    target_type: str = Field("test", pattern="^(test|flow)$")
    description: str | None = None


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_recorder(
    payload: StartRecorderPayload,
    current_user: User = Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Starts a browser recording session using isolated Agent Browser subprocess."""
    proj = resolve_project_id(
        db,
        payload.project_id,
        current_user.id,
        is_superuser=getattr(current_user, "is_superuser", False),
    )
    if not proj and getattr(current_user, "is_superuser", False):
        from backend.app.models.project import Project
        proj = db.query(Project).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target project workspace not found.")

    try:
        parsed = urlparse(payload.target_url)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target URL: {err}")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target URL: missing hostname.")

    allowed_domains = [hostname]
    parts = hostname.split(".")
    if len(parts) >= 2:
        allowed_domains.append(f"*.{'.'.join(parts[-2:])}")

    session_id = f"rec_{uuid.uuid4().hex[:12]}"
    try:
        session = _browser_adapter.launch(
            session_id=session_id,
            project_id=str(proj.id),
            user_id=str(current_user.id),
            allowed_domains=allowed_domains,
        )
        # Navigate to initial URL
        _browser_adapter.navigate(session_id=session_id, url=payload.target_url)

        _ACTIVE_RECORDINGS[session_id] = {
            "project_id": str(proj.id),
            "user_id": str(current_user.id),
            "url": payload.target_url,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "actions": [
                {
                  "id": f"act_{uuid.uuid4().hex[:8]}",
                  "action": "navigate",
                  "selector": payload.target_url,
                  "value": None,
                  "timestamp": datetime.now(timezone.utc).isoformat(),
                  "status": "verified",
                }
            ],
        }

        # Take initial snapshot
        shot = _browser_adapter.screenshot(session_id=session_id, custom_name="recorder_init")
        img_b64 = None
        target_path = Path(shot.file_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        return {
            "session_id": session_id,
            "status": "recording",
            "target_url": payload.target_url,
            "initial_screenshot": img_b64,
            "screenshot": img_b64,
            "image_base64": img_b64,
            "screenshot_path": shot.file_path,
            "action_count": 1,
        }
    except Exception as err:
        try:
            _browser_adapter.close(session_id)
        except Exception:
            pass
        logger.error("Failed to start recorder session: %s", err)
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/status")
def get_recorder_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves the active recorded action list and session status."""
    get_verified_session(session_id, current_user, db)
    rec = _ACTIVE_RECORDINGS.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recorder session not found or expired.")

    return {
        "session_id": session_id,
        "status": "recording",
        "url": rec["url"],
        "action_count": len(rec["actions"]),
        "actions": rec["actions"],
    }


@router.post("/action")
def record_action(
    payload: RecordActionPayload,
    current_user: User = Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Executes and logs a recorded action in the active recording session."""
    sess = payload.session_id
    get_verified_session(sess, current_user, db)
    rec = _ACTIVE_RECORDINGS.get(sess)
    if not rec:
        raise HTTPException(status_code=404, detail="Recorder session not active.")

    act = payload.action.lower()
    sel = payload.selector
    try:
        # Dispatch action through Agent Browser using native commands
        if act == "click":
            res = _browser_adapter.click(sess, sel)
        elif act in ("dblclick", "double_click"):
            res = _browser_adapter.dblclick(sess, sel)
        elif act in ("right_click", "contextmenu"):
            res = _browser_adapter.right_click(sess, sel)
        elif act == "fill":
            res = _browser_adapter.fill(sess, sel, payload.value or "")
        elif act == "type":
            res = _browser_adapter.type_text(sess, sel, payload.value or "")
        elif act == "select":
            res = _browser_adapter.select(sess, sel, payload.value or "")
        elif act == "hover":
            res = _browser_adapter.hover(sess, sel)
        elif act == "check":
            res = _browser_adapter.check(sess, sel)
        elif act == "uncheck":
            res = _browser_adapter.uncheck(sess, sel)
        elif act == "radio":
            res = _browser_adapter.radio(sess, sel)
        elif act == "scroll":
            res = _browser_adapter.scroll(sess, 0, 400)
        elif act == "reload":
            res = _browser_adapter.reload(sess)
        elif act == "back":
            res = _browser_adapter.back(sess)
        elif act == "forward":
            res = _browser_adapter.forward(sess)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action '{act}'")

        action_entry = {
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "action": act,
            "selector": sel,
            "value": payload.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "verified",
            "duration_ms": res.duration_ms,
        }
        rec["actions"].append(action_entry)

        # Update screenshot
        shot = _browser_adapter.screenshot(session_id=sess, custom_name="recorder_latest")
        img_b64 = None
        target_path = Path(shot.file_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        return {
            "success": True,
            "action": action_entry,
            "total_actions": len(rec["actions"]),
            "screenshot": img_b64,
            "image_base64": img_b64,
            "screenshot_path": shot.file_path,
        }
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Failed executing recorded action: %s", err)
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/stop")
def stop_recorder(
    payload: StopRecorderPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Stops the recorder and closes the browser subprocess."""
    sess = payload.session_id
    rec = _ACTIVE_RECORDINGS.get(sess)
    try:
        get_verified_session(sess, current_user, db)
    except Exception:
        pass
    try:
        _browser_adapter.close(session_id=sess)
    except Exception:
        pass

    actions = rec["actions"] if rec else []
    return {
        "session_id": sess,
        "status": "stopped",
        "action_count": len(actions),
        "actions": actions,
    }


@router.get("/inspect/{session_id}")
def inspect_recorder_page(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Inspects interactive elements on current page for the recorder."""
    get_verified_session(session_id, current_user, db)
    try:
        elements = _browser_adapter.extract_dom(session_id=session_id, max_depth=6)
        interactive = []
        for el in elements:
            if not el.get("is_visible"):
                continue
            tag = el.get("tag", "")
            role = el.get("role")
            if tag in ("button", "input", "select", "a", "textarea") or role in ("button", "link", "checkbox", "radio", "tab"):
                stable = el.get("stable_attributes") or {}
                selector = stable.get("selector")
                if not selector and stable.get("id"):
                    selector = f"#{stable['id']}"
                elif not selector and stable.get("name"):
                    selector = f"[name='{stable['name']}']"
                elif not selector and el.get("text"):
                    clean_text = el['text'][:30].replace("'", "\\'")
                    selector = f"{tag}:has-text('{clean_text}')"
                elif not selector:
                    selector = tag

                interactive.append({
                    "tag": tag,
                    "role": role,
                    "text": el.get("text") or el.get("associated_label") or "",
                    "selector": selector,
                    "box": el.get("box"),
                })

        return {
            "session_id": session_id,
            "elements_count": len(interactive),
            "elements": interactive[:40],
        }
    except Exception as err:
        logger.warning("Could not extract interactive elements: %s", err)
        return {"session_id": session_id, "elements_count": 0, "elements": []}


@router.post("/save", status_code=status.HTTP_201_CREATED)
def save_recording(
    payload: SaveRecordingPayload,
    current_user: User = Depends(require_permission("tests:create_edit")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Saves recorded action list directly as an Automation Flow or Test Case."""
    import hashlib
    import json

    rec = _ACTIVE_RECORDINGS.get(payload.session_id)
    actions = rec["actions"] if rec else []
    if not actions:
        raise HTTPException(status_code=400, detail="Cannot save empty recording session.")

    proj = resolve_project_id(
        db,
        payload.project_id,
        current_user.id,
        is_superuser=getattr(current_user, "is_superuser", False),
    )
    if not proj and getattr(current_user, "is_superuser", False):
        from backend.app.models.project import Project
        proj = db.query(Project).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Target project workspace not found.")
    project_uuid = proj.id

    if payload.target_type == "flow":
        nodes = []
        edges = []
        for idx, act in enumerate(actions):
            nid = f"node_{idx + 1}"
            nodes.append({
                "id": nid,
                "type": "action",
                "action": act["action"],
                "config": {
                    "url": act["selector"] if act["action"] == "navigate" else None,
                    "target": {"selector": act["selector"]} if act["action"] != "navigate" else None,
                    "selector": act["selector"] if act["action"] != "navigate" else None,
                    "value": act.get("value"),
                    "value_template": act.get("value"),
                },
                "position": {"x": 100 + idx * 240, "y": 150},
            })
            if idx > 0:
                edges.append({"id": f"e_{idx}", "source": f"node_{idx}", "target": nid})

        stop_id = f"node_{len(nodes) + 1}"
        nodes.append({
            "id": stop_id,
            "type": "stop",
            "action": "stop",
            "config": {"reason": "Completed"},
            "position": {"x": 100 + len(nodes) * 240, "y": 150},
        })
        if len(nodes) > 1:
            edges.append({"id": f"e_{len(nodes)-1}", "source": f"node_{len(nodes)-1}", "target": stop_id})

        flow_graph = {
            "name": payload.name,
            "description": payload.description or f"Recorded flow from {rec.get('url', 'browser')}",
            "start_node_id": "node_1",
            "nodes": nodes,
            "edges": edges,
        }

        checksum = hashlib.sha256(json.dumps(flow_graph, sort_keys=True).encode("utf-8")).hexdigest()

        automation = AutomationDefinition(
            project_id=project_uuid,
            type="flow",
            name=payload.name,
            description=payload.description or "Imported from Browser Recorder",
            status="draft",
            created_by=current_user.id,
        )
        db.add(automation)
        db.flush()

        version = DefinitionVersion(
            definition_id=automation.id,
            version_num=1,
            definition_json=flow_graph,
            checksum_sha256=checksum,
            is_published=False,
        )
        db.add(version)
        db.flush()
        automation.current_version_id = version.id
        db.commit()

        log_audit_event(
            db,
            action="recorder.save_flow",
            resource_type="automation_definition",
            resource_id=str(automation.id),
            user_id=current_user.id,
        )

        return {"id": str(automation.id), "type": "flow", "name": payload.name, "step_count": len(actions)}

    else:
        # Save as test case
        steps = []
        for idx, act in enumerate(actions):
            steps.append({
                "id": f"step_{idx + 1}",
                "name": f"{act['action'].upper()} {act['selector']}",
                "step_type": "action",
                "action": act["action"],
                "target": {"selector": act["selector"]} if act["action"] != "navigate" else None,
                "config": {"url": act["selector"]} if act["action"] == "navigate" else {"value": act.get("value")},
            })

        test_def = {
            "name": payload.name,
            "description": payload.description or f"Recorded test case from {rec.get('url', 'browser')}",
            "setup_steps": [],
            "steps": steps,
            "teardown_steps": [],
        }

        checksum = hashlib.sha256(json.dumps(test_def, sort_keys=True).encode("utf-8")).hexdigest()

        automation = AutomationDefinition(
            project_id=project_uuid,
            type="test",
            name=payload.name,
            description=payload.description or "Imported from Browser Recorder",
            status="draft",
            created_by=current_user.id,
        )
        db.add(automation)
        db.flush()

        version = DefinitionVersion(
            definition_id=automation.id,
            version_num=1,
            definition_json=test_def,
            checksum_sha256=checksum,
            is_published=False,
        )
        db.add(version)
        db.flush()
        automation.current_version_id = version.id
        db.commit()

        log_audit_event(
            db,
            action="recorder.save_test",
            resource_type="automation_definition",
            resource_id=str(automation.id),
            user_id=current_user.id,
        )

        return {"id": str(automation.id), "type": "test", "name": payload.name, "step_count": len(actions)}

