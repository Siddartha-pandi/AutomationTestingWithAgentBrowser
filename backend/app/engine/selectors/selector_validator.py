"""Pure deterministic validator for Agent Browser selectors.

Validates syntax, balanced quotes, brackets, and ARIA roles.
Zero AI models or heuristics.
"""

from __future__ import annotations

import re
from .selector_types import ParsedSelector, SelectorType, parse_selector

# Standard WAI-ARIA 1.2 roles
VALID_ARIA_ROLES = frozenset({
    "alert", "alertdialog", "application", "article", "banner", "button",
    "cell", "checkbox", "columnheader", "combobox", "complementary", "contentinfo",
    "definition", "dialog", "directory", "document", "feed", "figure", "form",
    "grid", "gridcell", "group", "heading", "img", "link", "list", "listbox",
    "listitem", "log", "main", "marquee", "math", "menu", "menubar", "menuitem",
    "menuitemcheckbox", "menuitemradio", "navigation", "none", "note", "option",
    "presentation", "progressbar", "radio", "radiogroup", "region", "row",
    "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator",
    "slider", "spinbutton", "status", "switch", "tab", "table", "tablist",
    "tabpanel", "term", "textbox", "timer", "toolbar", "tooltip", "tree",
    "treegrid", "treeitem"
})


def validate_brackets_and_quotes(text: str) -> tuple[bool, str | None]:
    """Ensures quotes and brackets are properly balanced and escaped."""
    stack: list[str] = []
    pairs = {"[": "]", "(": ")"}
    in_single_quote = False
    in_double_quote = False
    escaped = False

    for idx, ch in enumerate(text):
        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue

        if in_single_quote or in_double_quote:
            continue

        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in ("]", ")"):
            if not stack or stack.pop() != ch:
                return False, f"Unbalanced bracket '{ch}' at position {idx}"

    if in_single_quote:
        return False, "Unclosed single quote"
    if in_double_quote:
        return False, "Unclosed double quote"
    if stack:
        return False, f"Unclosed bracket, expected '{stack[-1]}'"

    return True, None


def validate_selector(selector: str | None) -> tuple[bool, str | None]:
    """Deterministically validates a selector string.

    Returns:
        (is_valid, error_message_or_None)
    """
    if not selector or not selector.strip():
        return False, "Selector cannot be empty or whitespace only"

    clean = selector.strip()
    if len(clean) > 2000:
        return False, "Selector length exceeds maximum limit of 2000 characters"

    # Check balanced quotes and brackets
    balanced, err = validate_brackets_and_quotes(clean)
    if not balanced:
        return False, err

    parsed = parse_selector(clean)

    # Validate based on type
    if parsed.selector_type == SelectorType.REF:
        if not re.match(r"^@e\d+$|^@\w+$", parsed.normalized_selector):
            return False, f"Invalid reference format '{parsed.normalized_selector}'. Must be @e<id> (e.g. @e1)"
        return True, None

    if parsed.selector_type == SelectorType.ROLE:
        if not parsed.role_name or parsed.role_name not in VALID_ARIA_ROLES:
            return False, f"Invalid ARIA role '{parsed.role_name}'. Must be a recognized WAI-ARIA role."
        return True, None

    if parsed.selector_type == SelectorType.TEXT:
        if not parsed.text_content:
            return False, "Text selector cannot be empty"
        return True, None

    if parsed.selector_type == SelectorType.TEST_ID:
        if not clean.strip("[]"):
            return False, "Test-ID selector cannot be empty"
        return True, None

    if parsed.selector_type == SelectorType.XPATH:
        xpath_body = clean[6:] if clean.startswith("xpath=") else clean
        if not xpath_body.strip():
            return False, "XPath selector cannot be empty"
        if xpath_body.endswith("/") and not xpath_body.endswith("//"):
            return False, "XPath selector cannot end with a trailing slash without a node test"
        return True, None

    # CSS Selector checks
    if clean.startswith(">") or clean.startswith("+") or clean.startswith("~"):
        return False, "CSS selector cannot start with a combinator (>, +, ~)"

    return True, None

