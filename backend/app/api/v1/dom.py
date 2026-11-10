"""DOM extraction and inspection API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.browser import AgentBrowserAdapter
from backend.app.intelligence.dom_extractor import DOMExtractor
from backend.app.schemas.intelligence import DOMExtractRequest, DOMExtractResponse
from backend.app.security.rbac import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dom", tags=["DOM Intelligence"])

# Shared adapter instance for API extraction requests
_adapter: AgentBrowserAdapter | None = None


def get_browser_adapter() -> AgentBrowserAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AgentBrowserAdapter()
    return _adapter


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

