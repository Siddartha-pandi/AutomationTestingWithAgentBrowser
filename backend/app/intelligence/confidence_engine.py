"""Deterministic confidence scoring engine for element recognition.

Implements multi-factor weighted scoring across 6 independent evidence categories.
Never selects elements on text similarity alone.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from rapidfuzz import fuzz

from backend.app.intelligence.attribute_matcher import AttributeMatcher
from backend.app.intelligence.dom_extractor import ExtractedElementNode
from backend.app.intelligence.element_profile import ElementProfileData
from backend.app.intelligence.semantic_matcher import SemanticMatcher
from backend.app.intelligence.structural_matcher import StructuralMatcher

logger = logging.getLogger(__name__)


@dataclass
class ScoringBreakdown:
    """Detailed score components contributing to the final confidence rating."""

    role_name_score: float
    stable_attr_score: float
    label_score: float
    structural_score: float
    historical_score: float
    text_score: float
    total_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_name_score": round(self.role_name_score, 4),
            "stable_attr_score": round(self.stable_attr_score, 4),
            "label_score": round(self.label_score, 4),
            "structural_score": round(self.structural_score, 4),
            "historical_score": round(self.historical_score, 4),
            "text_score": round(self.text_score, 4),
            "total_score": round(self.total_score, 4),
        }


class ConfidenceEngine:
    """Calculates weighted multi-factor deterministic confidence ratings."""

    # Configurable weights summing to 1.0
    WEIGHT_ROLE_NAME: float = 0.30
    WEIGHT_STABLE_ATTR: float = 0.25
    WEIGHT_LABEL: float = 0.15
    WEIGHT_STRUCTURAL: float = 0.15
    WEIGHT_HISTORICAL: float = 0.10
    WEIGHT_TEXT: float = 0.05  # Minor supporting evidence only

    @classmethod
    def match_historical(
        cls,
        history: list[dict[str, Any]],
        candidate: ExtractedElementNode,
    ) -> float:
        """Scores candidate against previously verified successful locators."""
        if not history:
            return 0.5  # Neutral for new profiles

        max_score = 0.0
        for item in history:
            loc_type = item.get("locator_type")
            loc_val = item.get("locator_value", "")
            if not loc_val:
                continue

            if loc_type == "id" and candidate.element_id and f"#{candidate.element_id}" == loc_val:
                max_score = max(max_score, 1.0)
            elif loc_type == "stable_attribute" and loc_val.startswith("[data-testid="):
                test_id = loc_val.split("'")[1] if "'" in loc_val else ""
                if candidate.stable_attributes.get("data-testid") == test_id:
                    max_score = max(max_score, 1.0)
            elif loc_type == "name" and candidate.stable_attributes.get("name") in loc_val:
                max_score = max(max_score, 0.9)
            elif loc_type == "role_name" and candidate.role and candidate.accessible_name:
                if f"role={candidate.role}" in loc_val and candidate.accessible_name in loc_val:
                    max_score = max(max_score, 1.0)

        return max_score

    @classmethod
    def evaluate(
        cls,
        profile: ElementProfileData,
        candidate: ExtractedElementNode,
    ) -> ScoringBreakdown:
        """Evaluates overall deterministic similarity between profile and candidate element."""
        # 1. Semantic Role & Accessible Name (30%)
        role_score = SemanticMatcher.match_role(profile.role, candidate.role, candidate.tag)
        name_score = SemanticMatcher.match_accessible_name(
            profile.accessible_name, candidate.accessible_name, candidate.text
        )
        role_name_score = (role_score * 0.5) + (name_score * 0.5)

        # 2. Stable Attributes & ARIA (25%)
        attr_score = AttributeMatcher.match_attributes(profile.stable_attributes, candidate)
        aria_score = AttributeMatcher.match_aria_properties(profile.aria_properties, candidate)
        stable_attr_score = (attr_score * 0.7) + (aria_score * 0.3)

        # 3. Associated Label (15%)
        exp_label = profile.stable_attributes.get("associated_label") or profile.accessible_name
        cand_label = candidate.associated_label or candidate.accessible_name
        label_score = SemanticMatcher.match_label(exp_label, cand_label)

        # 4. Structural Fingerprint (15%)
        fp = profile.structural_fingerprint
        anc_score = StructuralMatcher.match_ancestors(fp.get("ancestor_path", []), candidate.ancestors)
        sib_score = StructuralMatcher.match_siblings(fp.get("sibling_signature", ""), candidate.siblings, candidate.tag)
        form_score = StructuralMatcher.match_form_context(fp.get("form_id"), candidate.form_context)
        head_score = StructuralMatcher.match_nearby_heading(fp.get("nearby_heading"), candidate.nearby_heading)
        structural_score = (anc_score * 0.35) + (sib_score * 0.25) + (form_score * 0.20) + (head_score * 0.20)

        # 5. Historical Locators (10%)
        historical_score = cls.match_historical(profile.historical_locators, candidate)

        # 6. Text Similarity (5% Supporting Evidence Only)
        if profile.original_text and candidate.text:
            text_score = fuzz.ratio(profile.original_text.lower(), candidate.text.lower()) / 100.0
        else:
            text_score = 0.5

        # Weighted Total
        total_score = (
            (cls.WEIGHT_ROLE_NAME * role_name_score)
            + (cls.WEIGHT_STABLE_ATTR * stable_attr_score)
            + (cls.WEIGHT_LABEL * label_score)
            + (cls.WEIGHT_STRUCTURAL * structural_score)
            + (cls.WEIGHT_HISTORICAL * historical_score)
            + (cls.WEIGHT_TEXT * text_score)
        )

        return ScoringBreakdown(
            role_name_score=role_name_score,
            stable_attr_score=stable_attr_score,
            label_score=label_score,
            structural_score=structural_score,
            historical_score=historical_score,
            text_score=text_score,
            total_score=total_score,
        )
