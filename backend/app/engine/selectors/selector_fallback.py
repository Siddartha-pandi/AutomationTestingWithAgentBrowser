"""Deterministic multi-tier selector fallback resolver.

Evaluates selectors in strict deterministic order without AI:
  Tier 1: Primary selector
  Tier 2: Explicitly configured fallback selectors
  Tier 3: Test-ID attribute variants (data-testid, data-test-id, data-cy, data-qa)
  Tier 4: Historical profile locators (if profile configured)
  Tier 5: Deterministic DOM tree structural healing (if profile configured and enabled)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.browser import AgentBrowserAdapter
from backend.app.intelligence.self_healing import HealingResult, SelfHealingEngine
from backend.app.models.intelligence import ElementProfile

from .selector_types import ParsedSelector, SelectorType, parse_selector
from .selector_validator import validate_selector

logger = logging.getLogger(__name__)


@dataclass
class ResolvedSelectorResult:
    """Outcome of the multi-tier deterministic selector resolution."""

    resolved_selector: str
    original_selector: str = ""
    tier: str = "primary"  # 'primary', 'configured_fallback', 'variant', 'historical', 'healed'
    attempted_selectors: list[str] = field(default_factory=list)
    healed: bool = False
    confidence: float = 1.0
    healing_result: HealingResult | None = None
    warning: str | None = None
    is_ambiguous: bool = False


class SelectorFallbackResolver:
    """Resolves resilient, deterministic selectors across safety tiers."""

    def __init__(self, adapter: AgentBrowserAdapter, db: Session | None = None) -> None:
        self.adapter = adapter
        self.db = db
        self.healing_engine = SelfHealingEngine(adapter, db=db)

    def _is_present_or_visible(
        self,
        session_id: str,
        selector: str,
        allow_ambiguous: bool = False,
    ) -> tuple[bool, bool]:
        """Determines if selector exists in DOM and is unique.

        Returns:
            (is_usable, is_ambiguous)
        """
        try:
            if self.adapter.is_visible(session_id, selector):
                try:
                    count = self.adapter.get_count(session_id, selector)
                except Exception:
                    count = 1
                if count > 1 and not allow_ambiguous:
                    logger.warning(
                        "Selector '%s' is ambiguous (matches %d elements). Rejecting silent ambiguous selection.",
                        selector,
                        count,
                    )
                    return False, True
                return True, False

            try:
                count = self.adapter.get_count(session_id, selector)
            except Exception:
                count = 0

            if count > 1 and not allow_ambiguous:
                logger.warning(
                    "Selector '%s' matches %d elements (ambiguous). Rejecting silent selection.",
                    selector,
                    count,
                )
                return False, True
            return count > 0, False
        except Exception:
            return False, False

    def resolve(
        self,
        session_id: str,
        primary_selector: str,
        configured_fallbacks: list[str] | None = None,
        logical_id: str | None = None,
        element_profile_id: UUID | str | None = None,
        execution_id: UUID | None = None,
        is_destructive: bool = False,
        enable_fallback: bool = True,
        enable_healing: bool = False,
        allow_ambiguous: bool = False,
    ) -> ResolvedSelectorResult:
        """Executes multi-tier selector resolution without AI."""
        attempted: list[str] = []
        original = primary_selector.strip() if primary_selector else ""

        # -------------------------------------------------------------
        # Tier 1: Primary Selector
        # -------------------------------------------------------------
        if original:
            parsed_primary = parse_selector(original)
            norm_primary = parsed_primary.normalized_selector
            attempted.append(norm_primary)

            is_usable, is_ambig = self._is_present_or_visible(session_id, norm_primary, allow_ambiguous=allow_ambiguous)
            if is_usable:
                return ResolvedSelectorResult(
                    resolved_selector=norm_primary,
                    original_selector=original,
                    tier="primary",
                    attempted_selectors=attempted,
                    is_ambiguous=False,
                )
            if is_ambig:
                return ResolvedSelectorResult(
                    resolved_selector=norm_primary,
                    original_selector=original,
                    tier="primary",
                    attempted_selectors=attempted,
                    confidence=0.0,
                    is_ambiguous=True,
                    warning=f"Primary selector '{norm_primary}' matches multiple elements (ambiguous).",
                )

        # If fallback behavior is not configured/enabled, stop here
        if not enable_fallback and not configured_fallbacks:
            return ResolvedSelectorResult(
                resolved_selector=original,
                original_selector=original,
                tier="primary",
                attempted_selectors=attempted,
                confidence=0.0,
                warning=f"Selector '{original}' not found and fallbacks are disabled.",
            )

        # -------------------------------------------------------------
        # Tier 2: Configured Fallback Selectors
        # -------------------------------------------------------------
        if configured_fallbacks:
            for fb in configured_fallbacks:
                fb_clean = fb.strip()
                if not fb_clean or fb_clean in attempted:
                    continue

                is_valid, _ = validate_selector(fb_clean)
                if not is_valid:
                    continue

                parsed_fb = parse_selector(fb_clean)
                norm_fb = parsed_fb.normalized_selector
                attempted.append(norm_fb)

                is_usable, _ = self._is_present_or_visible(session_id, norm_fb, allow_ambiguous=allow_ambiguous)
                if is_usable:
                    logger.info("Selector resolved via configured fallback: %s", norm_fb)
                    return ResolvedSelectorResult(
                        resolved_selector=norm_fb,
                        original_selector=original,
                        tier="configured_fallback",
                        attempted_selectors=attempted,
                    )

        # If general fallback is disabled, do not proceed to auto variants
        if not enable_fallback:
            return ResolvedSelectorResult(
                resolved_selector=original,
                original_selector=original,
                tier="primary",
                attempted_selectors=attempted,
                confidence=0.0,
                warning="Configured fallbacks failed and automated variant search is disabled.",
            )

        # -------------------------------------------------------------
        # Tier 3: Test-ID and Attribute Variants
        # -------------------------------------------------------------
        if original:
            parsed = parse_selector(original)
            if parsed.selector_type == SelectorType.TEST_ID and parsed.text_content:
                tid = parsed.text_content
                variants = [
                    f'[data-testid="{tid}"]',
                    f'[data-test-id="{tid}"]',
                    f'[data-cy="{tid}"]',
                    f'[data-qa="{tid}"]',
                    f'[data-test="{tid}"]',
                    f'#{tid}',
                ]
                for v in variants:
                    if v not in attempted:
                        attempted.append(v)
                        is_usable, _ = self._is_present_or_visible(session_id, v, allow_ambiguous=allow_ambiguous)
                        if is_usable:
                            logger.info("Selector resolved via test-id variant: %s", v)
                            return ResolvedSelectorResult(
                                resolved_selector=v,
                                original_selector=original,
                                tier="variant",
                                attempted_selectors=attempted,
                            )

        # -------------------------------------------------------------
        # Tier 4: Profile Historical Locators
        # -------------------------------------------------------------
        profile_record: ElementProfile | None = None
        if self.db:
            if element_profile_id:
                try:
                    p_uuid = UUID(str(element_profile_id))
                    profile_record = self.db.query(ElementProfile).filter(ElementProfile.id == p_uuid).first()
                except (ValueError, TypeError):
                    pass
            elif logical_id:
                profile_record = self.db.query(ElementProfile).filter(ElementProfile.logical_id == logical_id).first()

        if profile_record and profile_record.history:
            for hist in profile_record.history:
                val = hist.locator_value
                if val and val not in attempted:
                    attempted.append(val)
                    is_usable, _ = self._is_present_or_visible(session_id, val, allow_ambiguous=allow_ambiguous)
                    if is_usable:
                        logger.info("Selector resolved via historical locator: %s", val)
                        return ResolvedSelectorResult(
                            resolved_selector=val,
                            original_selector=original,
                            tier="historical",
                            attempted_selectors=attempted,
                        )

        # -------------------------------------------------------------
        # Tier 5: Deterministic Self-Healing Engine (if explicitly enabled)
        # -------------------------------------------------------------
        if enable_healing and profile_record:
            logger.info("Primary & fallback locators failed. Running deterministic self-healing...")
            history_list = [
                {"locator_type": h.locator_type, "locator_value": h.locator_value, "success_count": h.success_count}
                for h in profile_record.history
            ]
            healing_res = self.healing_engine.heal_element(
                session_id=session_id,
                profile=profile_record.to_profile_data(),
                failed_locator=original or "unknown",
                locator_history=history_list,
                execution_id=execution_id,
                action_name="action",
                is_destructive=is_destructive,
            )

            if healing_res.success and healing_res.healed_locator:
                return ResolvedSelectorResult(
                    resolved_selector=healing_res.healed_locator,
                    original_selector=original,
                    tier="healed",
                    attempted_selectors=attempted,
                    healed=True,
                    confidence=healing_res.confidence_score,
                    healing_result=healing_res,
                )

        # If nothing succeeded, return original selector with diagnostic warning
        fallback_target = original or (attempted[0] if attempted else "")
        return ResolvedSelectorResult(
            resolved_selector=fallback_target,
            original_selector=original,
            tier="primary",
            attempted_selectors=attempted,
            confidence=0.0,
            warning=f"Selector not found on page after testing {len(attempted)} candidate selectors",
        )
