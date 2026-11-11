"""Deterministic selector types, parsing, and normalization for Agent Browser.

Supports CSS, XPath, Text, ARIA Role, Test ID, and Accessibility Snapshot references (@e<id>).
Strictly zero AI models or heuristics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SelectorType(str, Enum):
    """Supported selector paradigms in Agent Browser."""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"
    TEST_ID = "testid"
    REF = "ref"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    ALT = "alt"
    TITLE = "title"


@dataclass
class ParsedSelector:
    """Structured representation of a parsed and normalized selector."""

    raw_selector: str
    selector_type: SelectorType
    normalized_selector: str
    role_name: str | None = None
    role_options: dict[str, Any] = field(default_factory=dict)
    text_content: str | None = None
    exact_match: bool = False

    def to_cli_format(self) -> str:
        """Converts into standard Agent Browser CLI selector string."""
        if self.selector_type == SelectorType.REF:
            return self.normalized_selector
        if self.selector_type == SelectorType.TEST_ID:
            return self.normalized_selector
        if self.selector_type == SelectorType.XPATH:
            return self.normalized_selector
        if self.selector_type == SelectorType.ROLE:
            return self.normalized_selector
        if self.selector_type == SelectorType.TEXT:
            return self.normalized_selector
        return self.normalized_selector


REF_PATTERN = re.compile(r"^@e\d+$|^@\w+$")
XPATH_PREFIX_PATTERN = re.compile(r"^(?:xpath=|\/{1,2}|\(\/{1,2})", re.IGNORECASE)
ROLE_PREFIX_PATTERN = re.compile(r"^role=([a-zA-Z_-]+)(?:\[(.*)\])?$", re.IGNORECASE)
TEXT_PREFIX_PATTERN = re.compile(r"^text=(.*)$", re.IGNORECASE)
TESTID_PREFIX_PATTERN = re.compile(r"^(?:testid|data-testid)=(.*)$", re.IGNORECASE)
LABEL_PREFIX_PATTERN = re.compile(r"^label=(.*)$", re.IGNORECASE)
PLACEHOLDER_PREFIX_PATTERN = re.compile(r"^placeholder=(.*)$", re.IGNORECASE)
ALT_PREFIX_PATTERN = re.compile(r"^alt=(.*)$", re.IGNORECASE)
TITLE_PREFIX_PATTERN = re.compile(r"^title=(.*)$", re.IGNORECASE)


def parse_selector(selector: str) -> ParsedSelector:
    """Deterministically identifies the selector paradigm and normalizes it.

    Examples:
        - "@e12" -> REF
        - "text=Submit" or "text='Submit'" -> TEXT
        - "role=button[name='Save']" -> ROLE
        - "testid=submit-btn" -> TEST_ID "[data-testid='submit-btn']"
        - "//button[@type='submit']" -> XPATH "xpath=//button[@type='submit']"
        - "#submit-btn", "button.primary" -> CSS
    """
    clean = selector.strip()

    # 1. Snapshot Reference (@e1, @e42)
    if REF_PATTERN.match(clean):
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.REF,
            normalized_selector=clean,
        )

    # 2. Text Selector
    text_match = TEXT_PREFIX_PATTERN.match(clean)
    if text_match:
        val = text_match.group(1).strip()
        exact = False
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
            exact = True
        normalized = f'text="{val}"' if exact else f"text={val}"
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.TEXT,
            normalized_selector=normalized,
            text_content=val,
            exact_match=exact,
        )

    # 3. Test ID
    testid_match = TESTID_PREFIX_PATTERN.match(clean)
    if testid_match:
        val = testid_match.group(1).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        normalized = f'[data-testid="{val}"]'
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.TEST_ID,
            normalized_selector=normalized,
            text_content=val,
        )

    if clean.startswith("[data-testid=") or clean.startswith("[data-test-id=") or clean.startswith("[data-cy="):
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.TEST_ID,
            normalized_selector=clean,
        )

    # 4. ARIA Role
    role_match = ROLE_PREFIX_PATTERN.match(clean)
    if role_match:
        role_name = role_match.group(1).lower()
        options_raw = role_match.group(2)
        opts: dict[str, Any] = {}
        if options_raw:
            # Parse key="value" or key='value' pairs
            for pair in re.finditer(r'([a-zA-Z_-]+)=(?:["\']([^"\']*)["\']|(\S+))', options_raw):
                k = pair.group(1).lower()
                v = pair.group(2) if pair.group(2) is not None else pair.group(3)
                opts[k] = v

        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.ROLE,
            normalized_selector=clean,
            role_name=role_name,
            role_options=opts,
        )

    # 5. Label
    label_match = LABEL_PREFIX_PATTERN.match(clean)
    if label_match:
        val = label_match.group(1).strip().strip("\"'")
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.LABEL,
            normalized_selector=f'label="{val}"',
            text_content=val,
        )

    # 6. Placeholder
    ph_match = PLACEHOLDER_PREFIX_PATTERN.match(clean)
    if ph_match:
        val = ph_match.group(1).strip().strip("\"'")
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.PLACEHOLDER,
            normalized_selector=f'placeholder="{val}"',
            text_content=val,
        )

    # 7. Alt
    alt_match = ALT_PREFIX_PATTERN.match(clean)
    if alt_match:
        val = alt_match.group(1).strip().strip("\"'")
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.ALT,
            normalized_selector=f'alt="{val}"',
            text_content=val,
        )

    # 8. Title
    title_match = TITLE_PREFIX_PATTERN.match(clean)
    if title_match:
        val = title_match.group(1).strip().strip("\"'")
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.TITLE,
            normalized_selector=f'title="{val}"',
            text_content=val,
        )

    # 9. XPath
    if clean.startswith("xpath="):
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.XPATH,
            normalized_selector=clean,
        )
    if clean.startswith("//") or clean.startswith("(//"):
        return ParsedSelector(
            raw_selector=selector,
            selector_type=SelectorType.XPATH,
            normalized_selector=f"xpath={clean}",
        )

    # 10. Default CSS
    return ParsedSelector(
        raw_selector=selector,
        selector_type=SelectorType.CSS,
        normalized_selector=clean,
    )

