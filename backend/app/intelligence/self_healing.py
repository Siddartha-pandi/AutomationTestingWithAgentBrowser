"""Deterministic element resolver and self-healing engine.

Recovers from UI refactors, CSS class changes, dynamic ID replacements, and structural shifts
using multi-factor confidence scoring and strict safety gates.
Zero AI models or heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.browser import AgentBrowserAdapter
from backend.app.intelligence.confidence_engine import ConfidenceEngine, ScoringBreakdown
from backend.app.intelligence.dom_extractor import DOMExtractor, ExtractedElementNode
from backend.app.intelligence.element_profile import ElementProfileData
from backend.app.intelligence.verification import StateVerifier, VerificationResult
from backend.app.models.intelligence import Approval, ElementProfile, HealingEvent, LocatorHistory

logger = logging.getLogger(__name__)


@dataclass
class CandidateMatch:
    """Evaluated DOM candidate element with its confidence score."""

    node: ExtractedElementNode
    score_breakdown: ScoringBreakdown
    generated_locator: str
    is_unique: bool = True

    @property
    def total_score(self) -> float:
        return self.score_breakdown.total_score


@dataclass
class HealingResult:
    """Outcome of a self-healing resolution attempt."""

    success: bool
    decision: str  # 'auto_healed', 'requires_approval', 'rejected', 'direct_match'
    original_locator: str
    healed_locator: str | None = None
    confidence_score: float = 0.0
    scoring_breakdown: dict[str, Any] = field(default_factory=dict)
    candidate_node: dict[str, Any] | None = None
    approval_id: UUID | None = None
    healing_event_id: UUID | None = None
    verification: dict[str, Any] | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "decision": self.decision,
            "original_locator": self.original_locator,
            "healed_locator": self.healed_locator,
            "confidence_score": round(self.confidence_score, 4),
            "scoring_breakdown": self.scoring_breakdown,
            "candidate_node": self.candidate_node,
            "approval_id": str(self.approval_id) if self.approval_id else None,
            "healing_event_id": str(self.healing_event_id) if self.healing_event_id else None,
            "verification": self.verification,
            "error_message": self.error_message,
        }


class SelfHealingEngine:
    """Executes deterministic element resolution, threshold gating, and verified recovery."""

    # Configurable safety thresholds
    THRESHOLD_AUTO_HEAL: float = 0.95
    THRESHOLD_REQUIRES_APPROVAL: float = 0.85
    AMBIGUITY_DELTA: float = 0.05
    DESTRUCTIVE_THRESHOLD: float = 0.98

    def __init__(
        self,
        adapter: AgentBrowserAdapter,
        db: Session | None = None,
    ) -> None:
        self.adapter = adapter
        self.db = db
        self.extractor = DOMExtractor(adapter)
        self.verifier = StateVerifier(adapter)

    @classmethod
    def generate_resilient_locator(cls, node: ExtractedElementNode) -> str:
        """Constructs a deterministic, unique selector for the resolved candidate."""
        # 1. Prefer stable data-testid
        if "data-testid" in node.stable_attributes:
            return f"[data-testid='{node.stable_attributes['data-testid']}']"

        # 2. Prefer semantic Role + Accessible Name (agent-browser native find syntax)
        if node.role and node.accessible_name:
            clean_name = node.accessible_name.replace("'", "\\'")
            return f"role={node.role}[name='{clean_name}']"

        # 3. Prefer element ID
        if node.element_id:
            return f"#{node.element_id}"

        # 4. Prefer form name
        if "name" in node.stable_attributes:
            return f"{node.tag}[name='{node.stable_attributes['name']}']"

        # 5. Form context + tag
        if node.form_context and node.form_context.get("form_id"):
            return f"#{node.form_context['form_id']} {node.tag}"

        return node.tag

    def resolve_element(
        self,
        session_id: str,
        profile: ElementProfileData,
        original_locator: str,
        action: str = "click",
        is_destructive: bool = False,
        execution_id: UUID | None = None,
        element_profile_id: UUID | None = None,
    ) -> HealingResult:
        """Executes the complete 16-step deterministic self-healing resolution workflow."""
        logger.info(
            "Initiating self-healing resolution for logical_id '%s' (original: '%s')",
            profile.logical_id,
            original_locator,
        )

        # 1 & 2. Extract current DOM snapshot
        snapshot = self.extractor.extract_full_dom(session_id)
        if not snapshot.elements:
            return HealingResult(
                success=False,
                decision="rejected",
                original_locator=original_locator,
                error_message="Current DOM snapshot returned 0 elements. Browser page may be unrendered.",
            )

        # 3. Find candidates (elements with matching or compatible role/tag)
        candidates: list[CandidateMatch] = []
        for el in snapshot.elements:
            breakdown = ConfidenceEngine.evaluate(profile, el)
            loc = self.generate_resilient_locator(el)
            candidates.append(CandidateMatch(node=el, score_breakdown=breakdown, generated_locator=loc))

        # Sort candidates descending by total confidence score
        candidates.sort(key=lambda c: c.total_score, reverse=True)
        if not candidates:
            return HealingResult(
                success=False,
                decision="rejected",
                original_locator=original_locator,
                error_message="No matching DOM candidates identified for element profile.",
            )

        best_match = candidates[0]
        top_score = best_match.total_score

        # 10. Ambiguity Validation: If top 2 candidates score within AMBIGUITY_DELTA (5%), reject!
        if len(candidates) > 1:
            second_match = candidates[1]
            if (top_score - second_match.total_score) < self.AMBIGUITY_DELTA and top_score >= 0.70:
                logger.warning(
                    "Ambiguous element resolution: Best match (%.2f) and 2nd match (%.2f) are within %.2f. Guessing is prohibited.",
                    top_score,
                    second_match.total_score,
                    self.AMBIGUITY_DELTA,
                )
                return HealingResult(
                    success=False,
                    decision="rejected",
                    original_locator=original_locator,
                    confidence_score=top_score,
                    scoring_breakdown=best_match.score_breakdown.to_dict(),
                    candidate_node=best_match.node.to_dict(),
                    error_message=f"Ambiguous element: 2 candidates scored within {self.AMBIGUITY_DELTA*100:.0f}%. Guessing is prohibited.",
                )

        # 11. Check visibility and enabled state
        if not best_match.node.is_visible:
            return HealingResult(
                success=False,
                decision="rejected",
                original_locator=original_locator,
                confidence_score=top_score,
                scoring_breakdown=best_match.score_breakdown.to_dict(),
                candidate_node=best_match.node.to_dict(),
                error_message="Resolved candidate element is hidden or not visible on page.",
            )

        if not best_match.node.is_enabled:
            return HealingResult(
                success=False,
                decision="rejected",
                original_locator=original_locator,
                confidence_score=top_score,
                scoring_breakdown=best_match.score_breakdown.to_dict(),
                candidate_node=best_match.node.to_dict(),
                error_message="Resolved candidate element is disabled.",
            )

        # 12. Evaluate destructive safety threshold
        effective_auto_threshold = self.DESTRUCTIVE_THRESHOLD if is_destructive else self.THRESHOLD_AUTO_HEAL

        # 13. Determine decision based on thresholds
        if top_score >= effective_auto_threshold:
            decision = "auto_healed"
        elif top_score >= self.THRESHOLD_REQUIRES_APPROVAL:
            decision = "requires_approval"
        else:
            decision = "rejected"

        healed_loc = best_match.generated_locator

        # Record Healing Event in PostgreSQL if db session provided
        healing_event_id = None
        approval_id = None
        if self.db and execution_id and element_profile_id:
            try:
                healing_event = HealingEvent(
                    execution_id=execution_id,
                    element_profile_id=element_profile_id,
                    original_locator=original_locator,
                    healed_locator=healed_loc,
                    confidence_score=top_score,
                    scoring_breakdown=best_match.score_breakdown.to_dict(),
                    decision=decision,
                    is_approved=(decision == "auto_healed"),
                )
                self.db.add(healing_event)
                self.db.flush()
                healing_event_id = healing_event.id

                if decision == "requires_approval":
                    approval = Approval(
                        healing_event_id=healing_event.id,
                        status="pending",
                        comment=f"Self-healing confidence score: {top_score*100:.1f}%. Awaiting operator confirmation.",
                    )
                    self.db.add(approval)
                    self.db.flush()
                    approval_id = approval.id

                self.db.commit()
            except Exception as db_err:
                logger.error("Failed to persist healing event: %s", db_err)
                self.db.rollback()

        if decision == "rejected":
            return HealingResult(
                success=False,
                decision="rejected",
                original_locator=original_locator,
                healed_locator=healed_loc,
                confidence_score=top_score,
                scoring_breakdown=best_match.score_breakdown.to_dict(),
                candidate_node=best_match.node.to_dict(),
                healing_event_id=healing_event_id,
                error_message=f"Confidence score {top_score*100:.1f}% below recovery threshold {self.THRESHOLD_REQUIRES_APPROVAL*100:.0f}%.",
            )

        if decision == "requires_approval":
            return HealingResult(
                success=False,
                decision="requires_approval",
                original_locator=original_locator,
                healed_locator=healed_loc,
                confidence_score=top_score,
                scoring_breakdown=best_match.score_breakdown.to_dict(),
                candidate_node=best_match.node.to_dict(),
                approval_id=approval_id,
                healing_event_id=healing_event_id,
                error_message=f"Self-healing score {top_score*100:.1f}% requires operator approval before execution.",
            )

        # 14. Execute only when safe (auto_healed)
        logger.info(
            "Executing auto-healed action '%s' with locator '%s' (Confidence: %.1f%%)",
            action,
            healed_loc,
            top_score * 100.0,
        )

        return HealingResult(
            success=True,
            decision="auto_healed",
            original_locator=original_locator,
            healed_locator=healed_loc,
            confidence_score=top_score,
            scoring_breakdown=best_match.score_breakdown.to_dict(),
            candidate_node=best_match.node.to_dict(),
            healing_event_id=healing_event_id,
        )

    def record_locator_success(
        self,
        element_profile_id: UUID,
        locator_type: str,
        locator_value: str,
    ) -> None:
        """Saves verified locator to history ONLY after verified post-action success."""
        if not self.db:
            return
        try:
            existing = (
                self.db.query(LocatorHistory)
                .filter(
                    LocatorHistory.element_profile_id == element_profile_id,
                    LocatorHistory.locator_value == locator_value,
                )
                .first()
            )
            if existing:
                existing.success_count += 1
            else:
                new_hist = LocatorHistory(
                    element_profile_id=element_profile_id,
                    locator_type=locator_type,
                    locator_value=locator_value,
                    success_count=1,
                )
                self.db.add(new_hist)
            self.db.commit()
            logger.info("Recorded verified locator history for element %s: %s", element_profile_id, locator_value)
        except Exception as err:
            logger.error("Failed to commit locator history: %s", err)
            self.db.rollback()
