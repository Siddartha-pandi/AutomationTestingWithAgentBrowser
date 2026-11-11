"""REST API endpoints for Agent Browser CLI operations (/api/v1/browser)."""

from __future__ import annotations

import base64
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.browser import AgentBrowserAdapter
from backend.app.browser.browser_errors import AgentBrowserError, NavigationSecurityError
from backend.app.browser.session_manager import BrowserSession
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.api.v1.projects import user_has_project_access
from backend.app.engine.selectors import (
    SelectorFallbackResolver,
    parse_selector,
    validate_selector,
)
from backend.app.security.network_policy import is_local_dev_allowed
from backend.app.security.rbac import get_current_user, require_permission
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser", tags=["Browser Engine"])

# Shared adapter instance for interactive browser sessions
_browser_adapter = AgentBrowserAdapter()


def get_verified_session(
    session_id: str,
    current_user: User,
    db: Session | None = None,
) -> BrowserSession:
    """Verifies that the session exists, is active, belongs to the authenticated user, and checks project authorization."""
    session = _browser_adapter.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Browser session '{session_id}' not found",
        )
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Browser session '{session_id}' is no longer active (closed)",
        )

    # Superuser has controlled administrative access
    if current_user.is_superuser:
        return session

    # Ordinary users: reject ownerless sessions
    if session.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Browser session '{session_id}' is ownerless (has no assigned owner)",
        )

    # Verify user ownership
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to browser session '{session_id}'",
        )

    # Recheck project membership if session is associated with a project
    if session.project_id and db is not None:
        try:
            proj_uuid = UUID(str(session.project_id))
            if not user_has_project_access(db, proj_uuid, current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: user is not a member of project '{session.project_id}'",
                )
        except (ValueError, TypeError):
            pass

    # Verify execution ownership if session belongs to an execution
    if session.execution_id and db is not None:
        try:
            exec_uuid = UUID(str(session.execution_id))
            from backend.app.models.execution import Execution

            execution = db.query(Execution).filter(Execution.id == exec_uuid).first()
            if execution:
                if not user_has_project_access(db, execution.project_id, current_user):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied: no access to execution '{session.execution_id}' project",
                    )
        except (ValueError, TypeError):
            pass

    return session


class LaunchSessionPayload(BaseModel):
    session_id: str | None = None
    project_id: str | None = None
    allowed_domains: list[str] | None = None


class NavigatePayload(BaseModel):
    session_id: str
    url: str = Field(..., min_length=5)
    timeout: float = 30.0


class ActionPayload(BaseModel):
    session_id: str
    action: str  # click, dblclick, fill, type, select, check, scroll
    selector: str = ""
    text: str = ""
    value: str = ""
    timeout: float = 15.0


class ScreenshotPayload(BaseModel):
    session_id: str
    custom_name: str | None = None
    full_page: bool = False


class CloseSessionPayload(BaseModel):
    session_id: str


@router.get("/status")
def get_browser_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve verified Agent Browser CLI status and installation details."""
    cli_name = os.getenv("AGENT_BROWSER_CLI", "agent-browser")
    cli_found = bool(
        shutil.which(cli_name) is not None
        or shutil.which(f"{cli_name}.cmd") is not None
        or (Path(cli_name).is_file() and os.access(cli_name, os.X_OK))
    )
    health = _browser_adapter.get_health()

    if not cli_found:
        health_status = "unavailable"
        err_msg = (
            f"Agent Browser CLI '{cli_name}' is not installed or not found in system PATH. "
            "Install it via 'npm install -g agent-browser@0.41.2'."
        )
    elif health.is_healthy:
        health_status = "healthy"
        err_msg = None
    else:
        health_status = "degraded"
        err_msg = health.error_message or f"Agent Browser CLI '{cli_name}' is installed but failed health check."

    return {
        "engine": "agent-browser",
        "cli_version": health.version if health.is_healthy else None,
        "cli_configured": cli_name,
        "is_installed": cli_found,
        "mode": "subprocess_isolated",
        "zero_ai_policy": "Strict Zero-AI Active (100% Deterministic)",
        "default_timeout_seconds": int(os.getenv("AGENT_BROWSER_TIMEOUT", 30)),
        "health": health_status,
        "error_message": err_msg,
    }


@router.post("/test-connection")
def test_browser_connection(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test browser subprocess communication."""
    cli_name = os.getenv("AGENT_BROWSER_CLI", "agent-browser")
    cli_found = bool(
        shutil.which(cli_name) is not None
        or shutil.which(f"{cli_name}.cmd") is not None
        or (Path(cli_name).is_file() and os.access(cli_name, os.X_OK))
    )
    health = _browser_adapter.get_health()

    if not cli_found:
        return {
            "success": False,
            "message": f"Agent Browser CLI '{cli_name}' is not installed or not found in PATH.",
            "version": None,
            "session_state": "unavailable",
        }

    return {
        "success": health.is_healthy,
        "message": (
            "Connected to agent-browser CLI subprocess. Engine responsive."
            if health.is_healthy
            else (health.error_message or "Agent Browser CLI connection failed.")
        ),
        "version": health.version,
        "session_state": "ready" if health.is_healthy else "error",
    }


@router.post("/launch", status_code=status.HTTP_201_CREATED)
def launch_session(
    payload: LaunchSessionPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Launches an isolated Agent Browser subprocess session."""
    if payload.project_id:
        try:
            proj_uuid = UUID(payload.project_id)
            if not user_has_project_access(db, proj_uuid, current_user):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project_id format")

    # Generate a cryptographically secure server-side session ID; do not trust frontend-supplied session IDs
    session_id = f"sess_{uuid.uuid4().hex}"

    # Enforce safe domains: remove unrestricted wildcard unless explicit dev mode
    raw_domains = payload.allowed_domains or list(settings.allowed_domains)
    if not is_local_dev_allowed():
        clean_domains = [d.strip() for d in raw_domains if d.strip() not in ("*", "*.*", "all")]
    else:
        clean_domains = [d.strip() for d in raw_domains]

    if not clean_domains:
        if not is_local_dev_allowed():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty domain allowlist is prohibited in production.",
            )
        clean_domains = list(settings.allowed_domains)

    try:
        session = _browser_adapter.launch(
            session_id=session_id,
            project_id=payload.project_id,
            allowed_domains=clean_domains,
            user_id=str(current_user.id),
        )
        return {
            "session_id": session.session_id,
            "status": "ready",
            "allowed_domains": session.allowed_domains,
            "created_at": session.created_at.isoformat(),
        }
    except Exception as err:
        logger.error("Failed to launch browser session: %s", err)
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/navigate")
def navigate_session(
    payload: NavigatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Navigates active session to specified URL and returns updated viewport."""
    get_verified_session(payload.session_id, current_user, db)
    try:
        res = _browser_adapter.navigate(
            session_id=payload.session_id,
            url=payload.url,
            timeout=payload.timeout,
        )
        data = res.to_dict()

        # Capture viewport frame after navigation
        try:
            shot = _browser_adapter.screenshot(session_id=payload.session_id)
            target_path = Path(shot.file_path)
            if target_path.exists():
                with open(target_path, "rb") as f:
                    data["image_base64"] = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                data["screenshot_path"] = shot.file_path
        except Exception as shot_err:
            logger.warning("Could not capture post-navigation viewport: %s", shot_err)
            data["image_base64"] = None

        return data
    except NavigationSecurityError as sec_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(sec_err))
    except Exception as err:
        logger.error("Navigation error in session %s: %s", payload.session_id, err)
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/action")
def execute_action(
    payload: ActionPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Executes a discrete user interaction in the browser session."""
    get_verified_session(payload.session_id, current_user, db)
    sess = payload.session_id
    act = payload.action.lower()
    sel = payload.selector.strip()

    # Validate selector for selector-dependent actions
    if act in ("click", "dblclick", "double_click", "fill", "type", "select", "check", "uncheck", "radio"):
        if not sel:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Action '{act}' requires a selector")
        is_valid, err_msg = validate_selector(sel)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid selector syntax: {err_msg}",
            )

    try:
        if act == "click":
            res = _browser_adapter.click(sess, sel, timeout=payload.timeout)
        elif act in ("dblclick", "double_click"):
            res = _browser_adapter.dblclick(sess, sel, timeout=payload.timeout)
        elif act == "fill":
            fill_text = payload.text if payload.text != "" else payload.value
            res = _browser_adapter.fill(sess, sel, fill_text, timeout=payload.timeout)
        elif act == "type":
            type_text = payload.text if payload.text != "" else payload.value
            res = _browser_adapter.type_text(sess, sel, type_text, timeout=payload.timeout)
        elif act == "select":
            sel_val = payload.value or payload.text
            if not sel_val:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Action 'select' requires a value or text option to choose.",
                )
            res = _browser_adapter.select(sess, sel, sel_val, timeout=payload.timeout)
        elif act == "check":
            # Native Agent Browser check command
            res = _browser_adapter.check(sess, sel, timeout=payload.timeout)
        elif act == "uncheck":
            # Native Agent Browser uncheck command
            res = _browser_adapter.uncheck(sess, sel, timeout=payload.timeout)
        elif act == "radio":
            # Check radio and verify selection state
            res = _browser_adapter.check(sess, sel, timeout=payload.timeout)
            is_checked = _browser_adapter.is_checked(sess, sel, timeout=payload.timeout)
            if not is_checked:
                raise AgentBrowserError(f"Radio button '{sel}' was not selected after check command")
        elif act == "scroll":
            # Native Agent Browser scroll without synthetic body clicks
            res = _browser_adapter.scroll(sess, direction="down", pixels=400, timeout=payload.timeout)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action '{act}'")

        data = res.to_dict()
        try:
            shot = _browser_adapter.screenshot(session_id=sess)
            target_path = Path(shot.file_path)
            if target_path.exists():
                with open(target_path, "rb") as f:
                    data["image_base64"] = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
        except Exception:
            pass

        return data
    except HTTPException:
        raise
    except Exception as err:
        logger.error("Browser action '%s' failed in session %s: %s", act, sess, err)
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/screenshot")
def capture_screenshot(
    payload: ScreenshotPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Captures screenshot artifact from active browser session."""
    get_verified_session(payload.session_id, current_user, db)
    try:
        shot = _browser_adapter.screenshot(
            session_id=payload.session_id,
            custom_name=payload.custom_name,
            full_page=payload.full_page,
        )
        img_b64 = None
        target_path = Path(shot.file_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        return {
            "success": True,
            "file_path": shot.file_path,
            "file_size": shot.file_size_bytes,
            "sha256": shot.sha256_hash,
            "image_base64": img_b64,
        }
    except Exception as err:
        logger.error("Screenshot error in session %s: %s", payload.session_id, err)
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/viewport/{session_id}")
def get_session_viewport(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns the latest viewport screenshot for an active session as base64."""
    get_verified_session(session_id, current_user, db)
    try:
        shot = _browser_adapter.screenshot(session_id=session_id)
        target_path = Path(shot.file_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
            return {
                "success": True,
                "session_id": session_id,
                "image_base64": img_b64,
                "captured_at": shot.captured_at.isoformat(),
            }
        raise HTTPException(status_code=404, detail="Screenshot file not generated")
    except Exception as err:
        logger.error("Viewport error in session %s: %s", session_id, err)
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/close")
def close_session(
    payload: CloseSessionPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Closes browser session and terminates subprocess."""
    get_verified_session(payload.session_id, current_user, db)
    try:
        _browser_adapter.close(session_id=payload.session_id)
        return {"session_id": payload.session_id, "status": "closed"}
    except Exception as err:
        logger.warning("Error closing session %s: %s", payload.session_id, err)
        return {"session_id": payload.session_id, "status": "closed"}


class ValidateSelectorPayload(BaseModel):
    selector: str = Field(..., min_length=1)


class TestSelectorPayload(BaseModel):
    session_id: str
    selector: str = Field(..., min_length=1)
    fallbacks: list[str] | None = None
    highlight: bool = True
    timeout: float = 10.0


@router.post("/validate-selector")
def validate_selector_syntax(
    payload: ValidateSelectorPayload,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Deterministically validates selector syntax and returns parsed paradigm details."""
    is_valid, error_msg = validate_selector(payload.selector)
    parsed = parse_selector(payload.selector)

    return {
        "raw_selector": payload.selector,
        "is_valid": is_valid,
        "error_message": error_msg,
        "selector_type": parsed.selector_type.value,
        "normalized_selector": parsed.normalized_selector,
        "role_name": parsed.role_name,
        "role_options": parsed.role_options,
        "text_content": parsed.text_content,
        "exact_match": parsed.exact_match,
    }


@router.post("/test-selector")
def test_selector_in_session(
    payload: TestSelectorPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Tests selector against the live browser session and optionally highlights matching element."""
    get_verified_session(payload.session_id, current_user, db)
    sess_id = payload.session_id

    # 1. First validate syntax
    is_valid, error_msg = validate_selector(payload.selector)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid selector syntax: {error_msg}",
        )

    # 2. Resolve via multi-tier fallback
    resolver = SelectorFallbackResolver(_browser_adapter, db=db)
    resolution = resolver.resolve(
        session_id=sess_id,
        primary_selector=payload.selector,
        configured_fallbacks=payload.fallbacks,
    )

    resolved = resolution.resolved_selector
    element_found = resolution.confidence > 0.0 or _browser_adapter.get_count(sess_id, resolved) > 0

    box = None
    text = ""
    is_visible = False
    is_enabled = False
    count = 0
    img_b64 = None

    if element_found:
        count = _browser_adapter.get_count(sess_id, resolved)
        is_visible = _browser_adapter.is_visible(sess_id, resolved)
        is_enabled = _browser_adapter.is_enabled(sess_id, resolved)
        try:
            box = _browser_adapter.get_box(sess_id, resolved)
        except Exception:
            pass
        try:
            text = _browser_adapter.extract_text(sess_id, resolved)
        except Exception:
            pass

        # Highlight element in real browser
        if payload.highlight and is_visible:
            try:
                _browser_adapter.highlight(sess_id, resolved)
            except Exception as hl_err:
                logger.debug("Could not highlight element '%s': %s", resolved, hl_err)

        # Capture viewport frame with highlighted element
        try:
            shot = _browser_adapter.screenshot(session_id=sess_id)
            target_path = Path(shot.file_path)
            if target_path.exists():
                with open(target_path, "rb") as f:
                    img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
        except Exception as scr_err:
            logger.warning("Could not capture test-selector screenshot: %s", scr_err)

    return {
        "found": element_found,
        "count": count,
        "is_visible": is_visible,
        "is_enabled": is_enabled,
        "text": text,
        "box": box,
        "resolved_selector": resolved,
        "tier": resolution.tier,
        "attempted_selectors": resolution.attempted_selectors,
        "healed": resolution.healed,
        "warning": resolution.warning,
        "image_base64": img_b64,
    }
