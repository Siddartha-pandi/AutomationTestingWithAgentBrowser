"""Deterministic variable scope and safe template interpolator.

Manages execution state, variable resolution, and condition evaluation without eval() or exec().
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.security.redaction import Redactor

logger = logging.getLogger(__name__)


class VariableScope:
    """Deterministic variable store and template interpolation context."""

    def __init__(self, initial_vars: dict[str, Any] | None = None) -> None:
        self._vars: dict[str, Any] = dict(initial_vars or {})
        self._secrets: set[str] = set()
        self._step_outputs: dict[str, Any] = {}
        self.loop_index: int = 0

    def set(self, key: str, value: Any, is_secret: bool = False) -> None:
        """Sets a variable in scope, optionally marking it for redaction."""
        self._vars[key] = value
        if is_secret and isinstance(value, str) and value:
            self._secrets.add(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a variable value from scope."""
        return self._vars.get(key, default)

    def set_step_output(self, node_id: str, output: Any) -> None:
        """Records output of an executed workflow node."""
        self._step_outputs[node_id] = output

    def get_step_output(self, node_id: str) -> Any:
        """Retrieves output produced by a specific node."""
        return self._step_outputs.get(node_id)

    def get_all_variables(self) -> dict[str, Any]:
        """Returns shallow copy of all current variables."""
        return dict(self._vars)

    def get_registered_secrets(self) -> set[str]:
        """Returns set of secret strings that must be scrubbed from logs and DB."""
        return set(self._secrets)

    def interpolate(self, text_or_value: Any) -> Any:
        """Deterministically replaces {{var_name}} patterns with scope values."""
        if not isinstance(text_or_value, str):
            return text_or_value

        template = text_or_value

        # Regex to match {{ variable_expression }}
        pattern = re.compile(r"\{\{\s*([\w\.\$]+)\s*\}\}")

        def replace_match(match: re.Match) -> str:
            expr = match.group(1).strip()

            # 1. Built-in system expressions
            if expr == "$timestamp":
                return datetime.now(timezone.utc).isoformat()
            if expr == "$uuid":
                return str(uuid.uuid4())
            if expr == "$index":
                return str(self.loop_index)

            # 2. Step outputs: {{node_id.output}} or {{node_id.extracted_text}}
            if "." in expr:
                prefix, field = expr.split(".", 1)
                if prefix in self._step_outputs:
                    step_out = self._step_outputs[prefix]
                    if isinstance(step_out, dict):
                        return str(step_out.get(field, ""))
                    return str(step_out)

            # 3. Direct variable lookup
            if expr in self._vars:
                val = self._vars[expr]
                return str(val) if val is not None else ""

            # Return empty string if unresolved
            return ""

        # If string is entirely "{{var}}", preserve original type if non-string
        single_match = pattern.fullmatch(template.strip())
        if single_match:
            expr = single_match.group(1).strip()
            if expr in self._vars:
                return self._vars[expr]
            if "." in expr:
                prefix, field = expr.split(".", 1)
                if prefix in self._step_outputs:
                    step_out = self._step_outputs[prefix]
                    if isinstance(step_out, dict):
                        return step_out.get(field)
                    return step_out

        return pattern.sub(replace_match, template)

    @classmethod
    def evaluate_condition(cls, left: Any, operator: str, right: Any) -> bool:
        """Deterministically compares operands according to strict operator rules."""
        op = operator.strip().lower()

        # Handle None
        if left is None:
            left_str = ""
        else:
            left_str = str(left)

        if right is None:
            right_str = ""
        else:
            right_str = str(right)

        if op in ("==", "equals", "eq"):
            return left_str == right_str

        if op in ("!=", "not_equals", "neq"):
            return left_str != right_str

        if op in ("contains", "has"):
            return right_str in left_str

        if op in ("not_contains", "!contains"):
            return right_str not in left_str

        if op in ("starts_with", "startswith"):
            return left_str.startswith(right_str)

        if op in ("ends_with", "endswith"):
            return left_str.endswith(right_str)

        if op in ("empty", "is_empty"):
            return left_str == "" or left is None or left == [] or left == {}

        if op in ("not_empty", "is_not_empty"):
            return not (left_str == "" or left is None or left == [] or left == {})

        # Numerical comparisons
        try:
            num_left = float(left)
            num_right = float(right)

            if op in (">", "gt"):
                return num_left > num_right
            if op in (">=", "gte"):
                return num_left >= num_right
            if op in ("<", "lt"):
                return num_left < num_right
            if op in ("<=", "lte"):
                return num_left <= num_right
        except (ValueError, TypeError):
            logger.warning("Numerical comparison failed for '%s' %s '%s'; falling back to False", left, op, right)
            return False

        logger.warning("Unrecognized condition operator '%s'; evaluating to False", operator)
        return False

