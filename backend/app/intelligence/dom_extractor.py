"""Deterministic DOM extractor for browser automation and element profiling.

Extracts rich structural, semantic, ARIA, and contextual data from live browser pages
using base64-encoded deterministic JavaScript via Agent Browser CLI.
Zero AI models or heuristics.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class AncestorNode:
    """Represents an ancestor element in the DOM tree."""

    tag: str
    id: str | None = None
    role: str | None = None
    test_id: str | None = None
    class_name: str | None = None
    depth: int = 0


@dataclass
class SiblingContext:
    """Immediate sibling element context."""

    prev_tag: str | None = None
    prev_role: str | None = None
    next_tag: str | None = None
    next_role: str | None = None


@dataclass
class FormContext:
    """Enclosing HTML form metadata."""

    form_id: str | None = None
    form_name: str | None = None
    form_action: str | None = None
    form_method: str | None = None


@dataclass
class BoundingBox:
    """Element coordinates and dimensions."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass
class ExtractedElementNode:
    """Rich deterministic snapshot of a single DOM element."""

    tag: str
    role: str | None = None
    accessible_name: str | None = None
    text: str = ""
    element_id: str | None = None
    stable_attributes: dict[str, str] = field(default_factory=dict)
    aria_properties: dict[str, str] = field(default_factory=dict)
    associated_label: str | None = None
    ancestors: list[dict[str, Any]] = field(default_factory=list)
    siblings: dict[str, Any] = field(default_factory=dict)
    nearby_heading: str | None = None
    form_context: dict[str, Any] | None = None
    is_visible: bool = True
    is_enabled: bool = True
    box: dict[str, int] = field(default_factory=dict)
    page_url: str = ""
    route_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FullDOMSnapshot:
    """Complete snapshot of a web page's interactive and semantic elements."""

    page_url: str
    route_path: str
    page_title: str
    timestamp: str
    total_elements: int
    elements: list[ExtractedElementNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_url": self.page_url,
            "route_path": self.route_path,
            "page_title": self.page_title,
            "timestamp": self.timestamp,
            "total_elements": self.total_elements,
            "elements": [e.to_dict() for e in self.elements],
        }


# Deterministic client-side DOM inspection script executed inside Agent Browser
DOM_EXTRACTION_JS = """(() => {
    const elements = [];
    const url = window.location.href;
    const pathname = window.location.pathname;
    const title = document.title || '';

    function computeRole(el) {
        if (el.getAttribute('role')) return el.getAttribute('role').toLowerCase();
        const tag = el.tagName.toLowerCase();
        if (tag === 'button') return 'button';
        if (tag === 'a' && el.hasAttribute('href')) return 'link';
        if (tag === 'input') {
            const type = (el.getAttribute('type') || 'text').toLowerCase();
            if (['button', 'submit', 'reset'].includes(type)) return 'button';
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            return 'textbox';
        }
        if (tag === 'select') return 'combobox';
        if (tag === 'textarea') return 'textbox';
        if (/^h[1-6]$/.test(tag)) return 'heading';
        return null;
    }

    function computeAccessibleName(el) {
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
        if (el.getAttribute('aria-labelledby')) {
            const labelEl = document.getElementById(el.getAttribute('aria-labelledby'));
            if (labelEl) return labelEl.innerText.trim();
        }
        if (el.id) {
            const labelFor = document.querySelector(`label[for="${el.id}"]`);
            if (labelFor) return labelFor.innerText.trim();
        }
        const parentLabel = el.closest('label');
        if (parentLabel) return parentLabel.innerText.trim();
        if (el.getAttribute('placeholder')) return el.getAttribute('placeholder').trim();
        if (el.getAttribute('title')) return el.getAttribute('title').trim();
        if (el.getAttribute('alt')) return el.getAttribute('alt').trim();
        if (el.getAttribute('value') && ['button', 'submit'].includes((el.getAttribute('type') || '').toLowerCase())) {
            return el.getAttribute('value').trim();
        }
        return el.innerText ? el.innerText.trim().slice(0, 150) : '';
    }

    function isVisible(el) {
        if (!el || el.nodeType !== 1) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0;
    }

    function findNearbyHeading(el) {
        let current = el;
        while (current && current !== document.body) {
            const headings = current.querySelectorAll('h1, h2, h3, h4');
            if (headings.length > 0) return headings[0].innerText.trim().slice(0, 100);
            let prev = current.previousElementSibling;
            while (prev) {
                if (/^h[1-6]$/i.test(prev.tagName)) return prev.innerText.trim().slice(0, 100);
                const prevHeadings = prev.querySelectorAll('h1, h2, h3, h4');
                if (prevHeadings.length > 0) return prevHeadings[prevHeadings.length - 1].innerText.trim().slice(0, 100);
                prev = prev.previousElementSibling;
            }
            current = current.parentElement;
        }
        return null;
    }

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
    let node = walker.currentNode;
    let count = 0;

    while (node && count < 800) {
        count++;
        const el = node;
        const tag = el.tagName.toLowerCase();

        if (['script', 'style', 'noscript', 'svg', 'path', 'meta', 'link'].includes(tag)) {
            node = walker.nextNode();
            continue;
        }

        const role = computeRole(el);
        const name = computeAccessibleName(el);
        const rect = el.getBoundingClientRect();
        const visible = isVisible(el);

        // Collect stable attributes
        const stableAttrs = {};
        for (const attr of ['id', 'name', 'data-testid', 'type', 'placeholder', 'title', 'href', 'value', 'data-id', 'data-test']) {
            if (el.hasAttribute(attr)) {
                stableAttrs[attr] = el.getAttribute(attr);
            }
        }

        // Collect ARIA properties
        const ariaProps = {};
        for (let i = 0; i < el.attributes.length; i++) {
            const attr = el.attributes[i];
            if (attr.name.startsWith('aria-')) {
                ariaProps[attr.name] = attr.value;
            }
        }

        // Associated label
        let associatedLabel = null;
        if (el.id) {
            const l = document.querySelector(`label[for="${el.id}"]`);
            if (l) associatedLabel = l.innerText.trim();
        }
        if (!associatedLabel && el.closest('label')) {
            associatedLabel = el.closest('label').innerText.trim();
        }

        // Ancestors
        const ancestors = [];
        let p = el.parentElement;
        let depth = 0;
        while (p && p !== document.body && depth < 5) {
            ancestors.push({
                tag: p.tagName.toLowerCase(),
                id: p.id || null,
                role: p.getAttribute('role') || null,
                test_id: p.getAttribute('data-testid') || null,
                class_name: p.className ? String(p.className).slice(0, 40) : null,
                depth: depth
            });
            p = p.parentElement;
            depth++;
        }

        // Sibling tags
        const siblings = {
            prev_tag: el.previousElementSibling ? el.previousElementSibling.tagName.toLowerCase() : null,
            prev_role: el.previousElementSibling ? computeRole(el.previousElementSibling) : null,
            next_tag: el.nextElementSibling ? el.nextElementSibling.tagName.toLowerCase() : null,
            next_role: el.nextElementSibling ? computeRole(el.nextElementSibling) : null
        };

        // Form Context
        const formEl = el.closest('form');
        const formContext = formEl ? {
            form_id: formEl.id || null,
            form_name: formEl.getAttribute('name') || null,
            form_action: formEl.getAttribute('action') || null,
            form_method: (formEl.getAttribute('method') || 'GET').toUpperCase()
        } : null;

        // Inner Direct Text
        let directText = '';
        for (let c = 0; c < el.childNodes.length; c++) {
            if (el.childNodes[c].nodeType === 3) directText += el.childNodes[c].nodeValue;
        }
        directText = directText.trim().slice(0, 150);

        elements.push({
            tag: tag,
            role: role,
            accessible_name: name || null,
            text: directText || (el.innerText ? el.innerText.trim().slice(0, 150) : ''),
            element_id: el.id || null,
            stable_attributes: stableAttrs,
            aria_properties: ariaProps,
            associated_label: associatedLabel,
            ancestors: ancestors,
            siblings: siblings,
            nearby_heading: findNearbyHeading(el),
            form_context: formContext,
            is_visible: visible,
            is_enabled: !el.disabled,
            box: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            },
            page_url: url,
            route_path: pathname
        });

        node = walker.nextNode();
    }

    return {
        page_url: url,
        route_path: pathname,
        page_title: title,
        total_elements: elements.length,
        elements: elements
    };
})();"""


class DOMExtractor:
    """Extracts, parses, and structures DOM snapshots from live browser sessions."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    def extract_full_dom(self, session_id: str) -> FullDOMSnapshot:
        """Executes the deterministic DOM extractor inside the browser session."""
        from datetime import datetime, timezone

        now_str = datetime.now(timezone.utc).isoformat()
        try:
            raw_data = self.adapter.evaluate(session_id=session_id, js_code=DOM_EXTRACTION_JS)
        except Exception as err:
            logger.error("Failed to execute DOM extraction script: %s", err)
            current_url = self.adapter.get_url(session_id)
            return FullDOMSnapshot(
                page_url=current_url,
                route_path=urlparse(current_url).path,
                page_title="",
                timestamp=now_str,
                total_elements=0,
                elements=[],
            )

        if not isinstance(raw_data, dict):
            logger.warning("Unexpected DOM extraction format: %s", type(raw_data))
            return FullDOMSnapshot(
                page_url="",
                route_path="",
                page_title="",
                timestamp=now_str,
                total_elements=0,
                elements=[],
            )

        elements_list: list[ExtractedElementNode] = []
        for item in raw_data.get("elements", []):
            if isinstance(item, dict):
                node = ExtractedElementNode(
                    tag=item.get("tag", ""),
                    role=item.get("role"),
                    accessible_name=item.get("accessible_name"),
                    text=item.get("text", ""),
                    element_id=item.get("element_id"),
                    stable_attributes=item.get("stable_attributes", {}),
                    aria_properties=item.get("aria_properties", {}),
                    associated_label=item.get("associated_label"),
                    ancestors=item.get("ancestors", []),
                    siblings=item.get("siblings", {}),
                    nearby_heading=item.get("nearby_heading"),
                    form_context=item.get("form_context"),
                    is_visible=item.get("is_visible", True),
                    is_enabled=item.get("is_enabled", True),
                    box=item.get("box", {}),
                    page_url=item.get("page_url", raw_data.get("page_url", "")),
                    route_path=item.get("route_path", raw_data.get("route_path", "")),
                )
                elements_list.append(node)

        return FullDOMSnapshot(
            page_url=raw_data.get("page_url", ""),
            route_path=raw_data.get("route_path", ""),
            page_title=raw_data.get("page_title", ""),
            timestamp=now_str,
            total_elements=len(elements_list),
            elements=elements_list,
        )

