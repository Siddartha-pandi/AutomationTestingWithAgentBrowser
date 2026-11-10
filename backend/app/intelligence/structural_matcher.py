"""Structural DOM tree and contextual relationship matcher.

Scores ancestor hierarchies, sibling contexts, form enclosures, and section headings.
Zero AI models or heuristics.
"""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from backend.app.intelligence.dom_extractor import ExtractedElementNode


class StructuralMatcher:
    """Evaluates hierarchical and spatial similarity in the DOM tree."""

    @classmethod
    def match_ancestors(
        cls,
        expected_path: list[str],
        candidate_ancestors: list[dict[str, Any]],
    ) -> float:
        """Calculates Jaccard overlap between expected ancestor path and candidate ancestors [0.0 - 1.0]."""
        if not expected_path and not candidate_ancestors:
            return 1.0
        if not expected_path:
            return 1.0
        if not candidate_ancestors:
            return 0.2

        cand_tags: set[str] = set()
        for a in candidate_ancestors:
            tag = a.get("tag", "").lower()
            ident = a.get("id")
            if ident:
                cand_tags.add(f"{tag}#{ident.lower()}")
            elif tag:
                cand_tags.add(tag)

        exp_tags: set[str] = {p.lower() for p in expected_path}
        intersection = exp_tags.intersection(cand_tags)
        union = exp_tags.union(cand_tags)

        return len(intersection) / len(union) if union else 1.0

    @classmethod
    def match_siblings(
        cls,
        expected_sig: str,
        candidate_siblings: dict[str, Any],
        candidate_tag: str,
    ) -> float:
        """Scores immediate sibling sequence similarity [0.0 - 1.0]."""
        if not expected_sig:
            return 1.0

        prev_t = candidate_siblings.get("prev_tag") or "none"
        next_t = candidate_siblings.get("next_tag") or "none"
        cand_sig = f"{prev_t} + {candidate_tag} + {next_t}".lower()

        if expected_sig.lower() == cand_sig:
            return 1.0
        if candidate_tag in expected_sig.lower():
            return 0.70
        return 0.20

    @classmethod
    def match_form_context(
        cls,
        expected_form_id: str | None,
        candidate_form: dict[str, Any] | None,
    ) -> float:
        """Scores enclosing form match [0.0 - 1.0]."""
        if not expected_form_id and not candidate_form:
            return 1.0
        if not expected_form_id or not candidate_form:
            return 0.5

        cand_id = candidate_form.get("form_id")
        if cand_id and cand_id.lower() == expected_form_id.lower():
            return 1.0
        return 0.3

    @classmethod
    def match_nearby_heading(
        cls,
        expected_heading: str | None,
        candidate_heading: str | None,
    ) -> float:
        """Scores nearby section heading similarity [0.0 - 1.0]."""
        if not expected_heading and not candidate_heading:
            return 1.0
        if not expected_heading or not candidate_heading:
            return 0.5

        exp = expected_heading.strip().lower()
        cand = candidate_heading.strip().lower()

        if exp == cand:
            return 1.0
        if exp in cand or cand in exp:
            return 0.80

        return (fuzz.ratio(exp, cand) / 100.0) * 0.70
