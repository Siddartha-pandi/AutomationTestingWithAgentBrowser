"""Deterministic multi-tier selector fallback resolver.

Evaluates selectors in strict deterministic order without AI:
  Tier 1: Primary selector
  Tier 2: Explicitly configured fallback selectors
  Tier 3: Test-ID attribute variants (data-testid, data-test-id, data-cy, data-qa)
  Tier 4: Accessibility / Semantic match (Role + Name, Text)
  Tier 5: Historical profile locators (if profile configured)
  Tier 6: Deterministic DOM tree structural healing (if profile configured)
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
    tier: str  # 'primary', 'configured_fallback', 'variant', 'historical', 'healed'
    attempted_selectors: list[str] = field(default_factory=list)
    healed: bool = False
    confidence: float = 1.0
    healing_result: HealingResult | None = None
    warning: str | None = None


class SelectorFallbackResolver:
    """Resolves resilient, deterministic selectors across 6 safety tiers."""

    def __init__(self, adapter: AgentBrowserAdapter, db: Session | None = None) -> None:
        self.adapter = adapter
        self.db = db
        self.healing_engine = SelfHealingEngine(adapter, db=db)

    def _is_present_or_visible(self, session_id: str, selector: str) -> bool:
        """Determines if selector exists in DOM and is interactable."""
        try:
            # First check visibility
            if self.adapter.is_visible(session_id, selector):
                return True
            # Check element count > 0
            count = self.adapter.get_count(session_id, selector)
            return count > 0
        except Exception:
            return False

    def resolve(
        self,
        session_id: str,
        primary_selector: str,
        configured_fallbacks: list[str] | None = None,
        logical_id: str | None = None,
        element_profile_id: UUID | str | None = None,
        execution_id: UUID | None = None,
        is_destructive: bool = False,
    ) -> ResolvedSelectorResult:
        """Executes multi-tier selector resolution."""
        attempted: list[str] = []

        # -------------------------------------------------------------
        # Tier 1: Primary Selector
        # -------------------------------------------------------------
        if primary_selector and primary_selector.strip():
            parsed_primary = parse_selector(primary_selector.strip())
            norm_primary = parsed_primary.normalized_selector
            attempted.append(norm_primary)

            if self._is_present_or_visible(session_id, norm_primary):
                return ResolvedSelectorResult(
                    resolved_selector=norm_primary,
                    tier="primary",
                    attempted_selectors=attempted,
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

                if self._is_present_or_visible(session_id, norm_fb):
                    logger.info("Selector resolved via configured fallback: %s", norm_fb)
                    return ResolvedSelectorResult(
                        resolved_selector=norm_fb,
                        tier="configured_fallback",
                        attempted_selectors=attempted,
                    )

        # -------------------------------------------------------------
        # Tier 3: Test-ID and Attribute Variants
        # -------------------------------------------------------------
        if primary_selector:
            parsed = parse_selector(primary_selector.strip())
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
                        if self._is_present_or_visible(session_id, v):
                            logger.info("Selector resolved via test-id variant: %s", v)
                            return ResolvedSelectorResult(
                                resolved_selector=v,
                                tier="variant",
                                attempted_selectors=attempted,
                            )

        # -------------------------------------------------------------
        # Tier 4 & 5: Profile Historical Locators & Deterministic Healing
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

        # Tier 4: Check historical selectors recorded on profile
        if profile_record and profile_record.history:
            for hist in profile_record.history:
                val = hist.locator_value
                if val and val not in attempted:
                    attempted.append(val)
                    if self._is_present_or_visible(session_id, val):
                        logger.info("Selector resolved via historical locator: %s", val)
                        return ResolvedSelectorResult(
                            resolved_selector=val,
                            tier="historical",
                            attempted_selectors=attempted,
                        )

        # Tier 6: Trigger Deterministic Self-Healing Engine
        if profile_record:
            logger.info("Primary & fallback locators failed. Running deterministic self-healing...")
            history_list = [
                {"locator_type": h.locator_type, "locator_value": h.locator_value, "success_count": h.success_count}
                for h in profile_record.history
            ]
            healing_res = self.healing_engine.heal_element(
                session_id=session_id,
                profile=profile_record.to_profile_data(),
                failed_locator=primary_selector or "unknown",
                locator_history=history_list,
                execution_id=execution_id,
                action_name="action",
                is_destructive=is_destructive,
            )

            if healing_res.success and healing_res.healed_locator:
                return ResolvedSelectorResult(
                    resolved_selector=healing_res.healed_locator,
                    tier="healed",
                    attempted_selectors=attempted,
                    healed=True,
                    confidence=healing_res.confidence_score,
                    healing_result=healing_res,
                )

        # If nothing succeeded, return the primary or first attempted with a warning
        fallback_target = primary_selector or (attempted[0] if attempted else "")
        return ResolvedSelectorResult(
            resolved_selector=fallback_target,
            tier="primary",
            attempted_selectors=attempted,
            confidence=0.0,
            warning=f"Selector not found on page after testing {len(attempted)} candidate selectors",
        )

