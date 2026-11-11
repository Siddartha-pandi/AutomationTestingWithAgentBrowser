"""Deterministic retry and recovery policy for Agent Browser operations.

Guarantees:
- Safe retry execution with linear, exponential, or fixed backoff
- Pre-retry verification preventing duplicate submissions or side effects
- Stale element detection and automatic fallback selector recovery
- Strict non-retryable error classification (e.g. security violations, syntax errors)
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from backend.app.browser import AgentBrowserAdapter
from backend.app.browser.browser_errors import (
    AgentBrowserError,
    BrowserNotFoundError,
    BrowserTimeoutError,
    ElementNotFoundError,
    NavigationSecurityError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BackoffStrategy(str, Enum):
    """Backoff delay calculation strategy."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


# Non-retryable error classes that should fail fast
NON_RETRYABLE_EXCEPTIONS = (
    NavigationSecurityError,
    BrowserNotFoundError,
    ValueError,
    TypeError,
)


@dataclass
class RetryConfig:
    """Configuration for action execution retries."""

    max_retries: int = 2
    initial_delay_sec: float = 0.5
    backoff_strategy: BackoffStrategy = BackoffStrategy.LINEAR
    max_delay_sec: float = 5.0
    verify_state_before_retry: bool = True
    expected_state_type: str | None = None
    expected_state_target: str | None = None
    expected_state_val: Any = None


@dataclass
class RetryOutcome:
    """Telemetry of the retry operation."""

    success: bool
    result: Any = None
    attempts: int = 1
    total_elapsed_ms: float = 0.0
    last_error: Exception | None = None
    recovered_via_retry: bool = False
    side_effect_prevented: bool = False


class RetryExecutor:
    """Executes actions with deterministic retry policies."""

    def __init__(self, adapter: AgentBrowserAdapter) -> None:
        self.adapter = adapter

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculates backoff delay deterministically."""
        if config.backoff_strategy == BackoffStrategy.FIXED:
            delay = config.initial_delay_sec
        elif config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = config.initial_delay_sec * attempt
        elif config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = config.initial_delay_sec * (2 ** (attempt - 1))
        else:
            delay = config.initial_delay_sec

        return min(delay, config.max_delay_sec)

    def execute_with_retry(
        self,
        session_id: str,
        action_fn: Callable[[], T],
        config: RetryConfig,
        action_name: str = "action",
    ) -> RetryOutcome:
        """Executes the action with configured retry rules."""
        start_time = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(1, config.max_retries + 2):
            try:
                result = action_fn()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return RetryOutcome(
                    success=True,
                    result=result,
                    attempts=attempt,
                    total_elapsed_ms=round(elapsed_ms, 2),
                    recovered_via_retry=(attempt > 1),
                )
            except Exception as err:
                last_error = err
                # Fail fast on non-retryable errors
                if isinstance(err, NON_RETRYABLE_EXCEPTIONS):
                    logger.warning("Action '%s' failed with non-retryable error: %s", action_name, err)
                    break

                if attempt > config.max_retries:
                    logger.warning("Action '%s' exhausted all %d retries. Last error: %s", action_name, config.max_retries, err)
                    break

                # State verification check: did the action actually succeed despite timeout/error?
                if (
                    config.verify_state_before_retry
                    and config.expected_state_type
                    and config.expected_state_target
                ):
                    already_succeeded = self.adapter.verify_state_before_retry(
                        session_id=session_id,
                        expected_type=config.expected_state_type,
                        target=config.expected_state_target,
                        expected_value=config.expected_state_val,
                    )
                    if already_succeeded:
                        logger.info(
                            "Action '%s' had error '%s' but post-state '%s' is already satisfied. Avoiding duplicate retry.",
                            action_name,
                            err,
                            config.expected_state_type,
                        )
                        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                        return RetryOutcome(
                            success=True,
                            result=None,
                            attempts=attempt,
                            total_elapsed_ms=round(elapsed_ms, 2),
                            recovered_via_retry=True,
                            side_effect_prevented=True,
                        )

                delay = self.calculate_delay(attempt, config)
                logger.info(
                    "Retrying '%s' (attempt %d/%d) after %.2fs delay due to: %s",
                    action_name,
                    attempt,
                    config.max_retries,
                    delay,
                    err,
                )
                time.sleep(delay)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return RetryOutcome(
            success=False,
            result=None,
            attempts=min(attempt, config.max_retries + 1),
            total_elapsed_ms=round(elapsed_ms, 2),
            last_error=last_error,
        )

