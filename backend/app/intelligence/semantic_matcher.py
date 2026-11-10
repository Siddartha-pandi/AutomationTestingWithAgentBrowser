"""Semantic role, accessible name, and label matcher.

Compares semantic ARIA roles, computed accessible names, and associated form labels.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from typing import Any

from rapidfuzz import fuzz

from backend.app.intelligence.dom_extractor import ExtractedElementNode

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """Evaluates semantic similarity between saved element profiles and candidate DOM nodes."""

    @classmethod
    def match_role(cls, expected_role: str | None, candidate_role: str | None, candidate_tag: str) -> float:
        """Scores role compatibility [0.0 - 1.0]."""
        if not expected_role:
            return 0.5  # Neutral if profile had no specific role

        exp = expected_role.strip().lower()
        cand = (candidate_role or "").strip().lower()

        if exp == cand and exp:
            return 1.0

        # Compatible role equivalence mappings
        if exp == "button" and (cand == "button" or candidate_tag in ("button", "a")):
            return 0.85
        if exp == "textbox" and (cand == "textbox" or candidate_tag in ("input", "textarea")):
            return 0.85
        if exp == "link" and (cand == "link" or candidate_tag == "a"):
            return 0.85
        if exp == "combobox" and (cand == "combobox" or candidate_tag == "select"):
            return 0.85

        return 0.0

    @classmethod
    def match_accessible_name(cls, expected_name: str | None, candidate_name: str | None, candidate_text: str) -> float:
        """Scores accessible name similarity [0.0 - 1.0]."""
        if not expected_name:
            return 0.5

        exp = expected_name.strip().lower()
        cand_name = (candidate_name or "").strip().lower()
        cand_text = (candidate_text or "").strip().lower()

        # Exact match
        if exp == cand_name or exp == cand_text:
            return 1.0

        # Exact match ignoring punctuation
        import re
        exp_clean = re.sub(r"[^\w\s]", "", exp)
        cand_name_clean = re.sub(r"[^\w\s]", "", cand_name)
        cand_text_clean = re.sub(r"[^\w\s]", "", cand_text)
        if exp_clean and (exp_clean == cand_name_clean or exp_clean == cand_text_clean):
            return 0.95

        # Substring containment
        if exp in cand_name or cand_name in exp or exp in cand_text or cand_text in exp:
            return 0.85

        # Normalized Levenshtein ratio via RapidFuzz as supporting evidence
        ratio1 = fuzz.ratio(exp, cand_name) / 100.0 if cand_name else 0.0
        ratio2 = fuzz.ratio(exp, cand_text) / 100.0 if cand_text else 0.0
        return max(ratio1, ratio2) * 0.70

    @classmethod
    def match_label(cls, expected_label: str | None, candidate_label: str | None) -> float:
        """Scores associated form label match [0.0 - 1.0]."""
        if not expected_label and not candidate_label:
            return 1.0
        if not expected_label or not candidate_label:
            return 0.5

        exp = expected_label.strip().lower()
        cand = candidate_label.strip().lower()

        if exp == cand:
            return 1.0
        if exp in cand or cand in exp:
            return 0.85

        return (fuzz.ratio(exp, cand) / 100.0) * 0.60
