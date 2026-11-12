"""DOM extraction and inspection API endpoints."""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.v1.browser import _browser_adapter
from backend.app.browser import AgentBrowserAdapter
from backend.app.intelligence.dom_extractor import DOMExtractor
from backend.app.schemas.intelligence import DOMExtractRequest, DOMExtractResponse, DOMExploreRequest
from backend.app.security.rbac import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dom", tags=["DOM Intelligence"])


def get_browser_adapter() -> AgentBrowserAdapter:
    return _browser_adapter


@router.post("/extract", response_model=DOMExtractResponse)
def extract_dom(
    payload: DOMExtractRequest,
    current_user=Depends(get_current_user),
    adapter: AgentBrowserAdapter = Depends(get_browser_adapter),
) -> DOMExtractResponse:
    """Executes deterministic dynamic DOM extraction on an active browser session."""
    extractor = DOMExtractor(adapter)
    try:
        snapshot = extractor.extract_full_dom(payload.session_id)
        return DOMExtractResponse(
            page_url=snapshot.page_url,
            route_path=snapshot.route_path,
            page_title=snapshot.page_title,
            timestamp=snapshot.timestamp,
            total_elements=snapshot.total_elements,
            elements=[e.to_dict() for e in snapshot.elements],
        )
    except Exception as err:
        logger.error("DOM extraction failed for session '%s': %s", payload.session_id, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DOM extraction failed: {err}",
        )


@router.post("/explore")
def explore_dom(
    payload: DOMExploreRequest,
    current_user=Depends(get_current_user),
    adapter: AgentBrowserAdapter = Depends(get_browser_adapter),
) -> dict[str, Any]:
    """Navigates to the specified URL in an isolated Agent Browser session,
    captures a live viewport screenshot, and deterministically extracts DOM elements and attributes."""
    if adapter is None or not hasattr(adapter, "launch"):
        adapter = _browser_adapter
    url = payload.url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid target URL: {err}")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target URL: missing hostname.")

    allowed_domains = [hostname]
    parts = hostname.split(".")
    if len(parts) >= 2:
        allowed_domains.append(f"*.{'.'.join(parts[-2:])}")

    session_id = payload.session_id
    existing_session = adapter.session_manager.get_session(session_id) if session_id else None

    if not existing_session or not existing_session.is_active:
        session_id = f"dom_{uuid.uuid4().hex[:12]}"
        try:
            adapter.launch(
                session_id=session_id,
                project_id=payload.project_id,
                user_id=str(current_user.id),
                allowed_domains=allowed_domains,
            )
        except Exception as launch_err:
            logger.error("Failed to launch DOM explorer browser session: %s", launch_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to launch browser session: {launch_err}",
            )

    try:
        # Navigate to target page with 45s launch allowance
        adapter.navigate(session_id=session_id, url=url, timeout=45.0)

        # Capture live screenshot
        shot = adapter.screenshot(session_id=session_id, custom_name="dom_explorer")
        img_b64 = None
        target_path = Path(shot.file_path)
        if target_path.exists():
            with open(target_path, "rb") as f:
                img_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        # Extract deterministic DOM elements
        extractor = DOMExtractor(adapter)
        snapshot = extractor.extract_full_dom(session_id)

        return {
            "session_id": session_id,
            "page_url": snapshot.page_url or url,
            "page_title": snapshot.page_title,
            "screenshot": img_b64,
            "total_elements": snapshot.total_elements,
            "elements": [e.to_dict() for e in snapshot.elements],
        }
    except Exception as err:
        logger.error("DOM exploration failed for '%s': %s", url, err)
        if hasattr(adapter.executor, "_kill_session_daemon"):
            try:
                adapter.executor._kill_session_daemon(session_id)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DOM exploration failed: {err}",
        )

