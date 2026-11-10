"""Deterministic element profile generator and fingerprint manager.

Creates stable, multi-attribute identity representations for web elements
to allow reliable recognition across frontend refactors, class renaming, and DOM mutations.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from backend.app.intelligence.dom_extractor import ExtractedElementNode

logger = logging.getLogger(__name__)


@dataclass
class StructuralFingerprint:
    """Deterministic structural and contextual fingerprint of an element's position."""

    tag: str
    role: str | None = None
    ancestor_path: list[str] = field(default_factory=list)
    sibling_signature: str = ""
    form_id: str | None = None
    nearby_heading: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ElementProfileData:
    """In-memory data transfer object representing a registered element profile."""

    logical_id: str
    description: str
    element_type: str
    page_context: str
    original_text: str = ""
    accessible_name: str | None = None
    role: str | None = None
    stable_attributes: dict[str, str] = field(default_factory=dict)
    aria_properties: dict[str, str] = field(default_factory=dict)
    structural_fingerprint: dict[str, Any] = field(default_factory=dict)
    historical_locators: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ElementProfileBuilder:
    """Constructs stable element profiles and structural fingerprints from extracted DOM nodes."""

    @classmethod
    def compute_fingerprint(cls, node: ExtractedElementNode) -> StructuralFingerprint:
        """Derives a deterministic structural fingerprint from an extracted DOM node."""
        # 1. Ancestor path representation (e.g. ['form#login-form', 'div', 'main'])
        ancestor_path: list[str] = []
        for a in node.ancestors:
            tag = a.get("tag", "div")
            ident = a.get("id")
            test_id = a.get("test_id")
            if test_id:
                ancestor_path.append(f"{tag}[data-testid='{test_id}']")
            elif ident:
                ancestor_path.append(f"{tag}#{ident}")
            else:
                ancestor_path.append(tag)

        # 2. Sibling signature (e.g. 'label + input + span')
        prev_t = node.siblings.get("prev_tag") or "none"
        next_t = node.siblings.get("next_tag") or "none"
        sibling_sig = f"{prev_t} + {node.tag} + {next_t}"

        # 3. Form ID
        form_id = node.form_context.get("form_id") if node.form_context else None

        return StructuralFingerprint(
            tag=node.tag,
            role=node.role,
            ancestor_path=ancestor_path,
            sibling_signature=sibling_sig,
            form_id=form_id,
            nearby_heading=node.nearby_heading,
        )

    @classmethod
    def from_node(
        cls,
        logical_id: str,
        node: ExtractedElementNode,
        page_context: str,
        description: str = "",
    ) -> ElementProfileData:
        """Builds a rich element profile from an extracted DOM node."""
        fingerprint = cls.compute_fingerprint(node)

        # Generate initial candidate locators
        initial_locators: list[dict[str, Any]] = []

        # Candidate 1: Semantic Role + Name (Priority 1)
        if node.role and node.accessible_name:
            initial_locators.append({
                "locator_type": "role_name",
                "locator_value": f"role={node.role}[name='{node.accessible_name}']",
                "success_count": 1,
            })

        # Candidate 2: Stable Attribute (data-testid, id, name)
        if "data-testid" in node.stable_attributes:
            initial_locators.append({
                "locator_type": "stable_attribute",
                "locator_value": f"[data-testid='{node.stable_attributes['data-testid']}']",
                "success_count": 1,
            })
        elif node.element_id:
            initial_locators.append({
                "locator_type": "id",
                "locator_value": f"#{node.element_id}",
                "success_count": 1,
            })
        elif "name" in node.stable_attributes:
            initial_locators.append({
                "locator_type": "name",
                "locator_value": f"{node.tag}[name='{node.stable_attributes['name']}']",
                "success_count": 1,
            })

        # Candidate 3: Associated Form Label
        if node.associated_label:
            initial_locators.append({
                "locator_type": "label",
                "locator_value": f"label='{node.associated_label}'",
                "success_count": 1,
            })

        return ElementProfileData(
            logical_id=logical_id,
            description=description or f"Element on {page_context}",
            element_type=node.role or node.tag,
            page_context=page_context,
            original_text=node.text,
            accessible_name=node.accessible_name,
            role=node.role,
            stable_attributes=node.stable_attributes,
            aria_properties=node.aria_properties,
            structural_fingerprint=fingerprint.to_dict(),
            historical_locators=initial_locators,
        )

