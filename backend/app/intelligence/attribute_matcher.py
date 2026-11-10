"""Stable attribute and ARIA property matcher.

Scores attribute stability, test IDs, and form attributes with dynamic ID tolerance.
Zero AI models or heuristics.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.intelligence.dom_extractor import ExtractedElementNode


class AttributeMatcher:
    """Evaluates attribute similarity between saved element profiles and candidate DOM nodes."""

    @classmethod
    def clean_dynamic_id(cls, raw_id: str | None) -> str:
        """Strips auto-generated trailing digits or hashes (e.g. 'btn-submit-12847' -> 'btn-submit')."""
        if not raw_id:
            return ""
        # Remove trailing uuid-like or numeric suffixes
        cleaned = re.sub(r"[-_](?:[0-9a-f]{8,}|[0-9]{3,})$", "", raw_id.strip().lower())
        return cleaned

    @classmethod
    def match_attributes(
        cls,
        expected_attrs: dict[str, Any],
        candidate: ExtractedElementNode,
    ) -> float:
        """Scores overall attribute similarity [0.0 - 1.0]."""
        if not expected_attrs:
            return 0.5

        scores: list[float] = []
        cand_attrs = candidate.stable_attributes

        # 1. data-testid (High Confidence)
        if "data-testid" in expected_attrs:
            exp_tid = str(expected_attrs["data-testid"]).strip().lower()
            cand_tid = str(cand_attrs.get("data-testid", "")).strip().lower()
            scores.append(1.0 if exp_tid == cand_tid and exp_tid else 0.0)

        # 2. name attribute
        if "name" in expected_attrs:
            exp_name = str(expected_attrs["name"]).strip().lower()
            cand_name = str(cand_attrs.get("name", "")).strip().lower()
            scores.append(1.0 if exp_name == cand_name and exp_name else 0.0)

        # 3. id attribute (with dynamic ID tolerance)
        if "id" in expected_attrs or candidate.element_id:
            exp_id = cls.clean_dynamic_id(str(expected_attrs.get("id", "")))
            cand_id = cls.clean_dynamic_id(candidate.element_id or str(cand_attrs.get("id", "")))
            if exp_id and cand_id:
                if exp_id == cand_id:
                    scores.append(1.0)
                elif exp_id in cand_id or cand_id in exp_id:
                    scores.append(0.75)
                else:
                    scores.append(0.0)

        # 4. type attribute
        if "type" in expected_attrs:
            exp_type = str(expected_attrs["type"]).strip().lower()
            cand_type = str(cand_attrs.get("type", "")).strip().lower()
            scores.append(1.0 if exp_type == cand_type and exp_type else 0.2)

        # 5. placeholder attribute
        if "placeholder" in expected_attrs:
            exp_ph = str(expected_attrs["placeholder"]).strip().lower()
            cand_ph = str(cand_attrs.get("placeholder", "")).strip().lower()
            scores.append(1.0 if exp_ph == cand_ph and exp_ph else 0.0)

        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    @classmethod
    def match_aria_properties(
        cls,
        expected_aria: dict[str, Any],
        candidate: ExtractedElementNode,
    ) -> float:
        """Scores ARIA property overlap [0.0 - 1.0]."""
        if not expected_aria:
            return 1.0  # Neutral / full match when profile defines no ARIA constraints
        cand_aria = candidate.aria_properties
        if not cand_aria:
            return 0.3

        matches = 0
        total = len(expected_aria)
        for key, exp_val in expected_aria.items():
            if key in cand_aria and str(cand_aria[key]).strip().lower() == str(exp_val).strip().lower():
                matches += 1

        return matches / total if total > 0 else 1.0

