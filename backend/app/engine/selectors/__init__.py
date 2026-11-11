"""Native deterministic selector module for Agent Browser."""

from .selector_fallback import ResolvedSelectorResult, SelectorFallbackResolver
from .selector_types import ParsedSelector, SelectorType, parse_selector
from .selector_validator import validate_selector

__all__ = [
    "SelectorType",
    "ParsedSelector",
    "parse_selector",
    "validate_selector",
    "ResolvedSelectorResult",
    "SelectorFallbackResolver",
]

