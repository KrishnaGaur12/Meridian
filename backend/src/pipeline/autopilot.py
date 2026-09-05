"""
AI Autopilot Orchestration Layer — Razorpay AI Risk Manager.
Central intelligence layer that:
1. Reassesses disputes on any evidence/state change
2. Computes deterministic merchant_attention_state
3. Computes before/after impact delta
4. Logs AI_ENGINE audit events
5. Persists updated case state
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.database.repository import (
    get_dispute, get_dispute_case_analysis, create_dispute_event,
    get_chargeback_package_by_dispute, calculate_deadline_info
)
from src.database.models import utc_now_iso
from src.utils.logger import get_logger

logger = get_logger("AIAutopilot")


class AIAutopilot:
    """Central AI Autopilot engine for dispute lifecycle intelligence."""

    @staticmethod
    def compute_attention_state(
        analysis: Dict[str, Any],
        dispute_status: str,
        workflow_stage: str,
        deadline_info: Dict[str, Any]
    ) -> tuple:
        """
        Deterministically classifies merchant_attention_state from real analysis results.
        Returns (state, reason) tuple.
        """
        status_upper = (dispute_status or "OPEN").upper()
        stage_upper = (workflow_stage or "DISPUTE_RAISED").upper()

        # WAITING: submitted or terminal states
        if status_upper in ["SUBMITTED", "WON", "LOST", "CLOSED"] or stage_upper in ["SUBMITTED", "RESOLVED"]:
            return "WAITING", "Submitted to local gateway boundary. Awaiting bank resolution."

        # ACTION_REQUIRED: missing evidence, contradictions, high risk, urgent deadline
        missing_evidence = analysis.get("evidence_intelligence", {}).get("missing_evidence", [])
        contradictions = analysis.get("evidence_intelligence", {}).get("contradictions_count", 0)
        risk_level = analysis.get("risk_analysis", {}).get("risk_level", "LOW")
        urgency = deadline_info.get("urgency_level", "SAFE")

        if missing_evidence:
            missing_str = ", ".join(missing_evidence[:3])
            return "ACTION_REQUIRED", f"Missing required evidence: {missing_str}"
        if contradictions > 0:
            return "ACTION_REQUIRED", "Evidence contradiction detected across records."
        if risk_level == "HIGH" and analysis.get("recommendation", {}).get("decision") == "INVESTIGATE":
            return "ACTION_REQUIRED", "High fraud risk transaction requires manual merchant investigation."
        if urgency in ["URGENT", "OVERDUE"]:
            return "ACTION_REQUIRED", f"Representment deadline is {urgency.lower()} — immediate action needed."

        # REVIEW_RECOMMENDED: AI has prepared response, merchant approval needed
        if stage_upper in ["MERCHANT_REVIEW", "AI_RESPONSE_GENERATED", "PACKAGE_GENERATED",
                           "EVIDENCE_BUNDLE_CREATED", "READY_FOR_SUBMISSION"]:
            return "REVIEW_RECOMMENDED", "AI has prepared a response. Merchant review and approval required."

        # AI_HANDLING: everything under control
        evidence_completeness = analysis.get("evidence_intelligence", {}).get("evidence_completeness", 0)
        win_prob = analysis.get("win_probability", {}).get("score", 0)
        if evidence_completeness >= 0.6 and win_prob >= 0.4:
            return "AI_HANDLING", "No action required. AI is actively monitoring evidence and deadlines."

        # Default to ACTION_REQUIRED for safety
        return "ACTION_REQUIRED", "AI analysis in progress. Case requires attention."

    @staticmethod
    def reassess_dispute(db: Session, dispute_id: str, trigger: str = "SYSTEM") -> Dict[str, Any]:
        """
        Executes full case reassessment pipeline:
        1. Captures current state as 'before' snapshot
        2. Runs complete AI case analysis
        3. Computes new merchant_attention_state
        4. Persists updated state to database
        5. Logs AI_ENGINE audit event
        6. Returns reassessment result with impact delta
        """
        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute '{dispute_id}' not found.")

        # Invalidate AI Language Layer cache upon reassessment
        try:
            from src.services.ai.cache import AICacheManager
            AICacheManager().invalidate_dispute(dispute_id)
        except Exception:
            pass

        # Capture BEFORE state
        before_state = {
            "merchant_attention_state": dispute.merchant_attention_state or "ACTION_REQUIRED",
            "workflow_stage": dispute.workflow_stage or "DISPUTE_RAISED",
        }

        # Run authoritative dispute analysis (Fraud V2, Win Model, Evidence Engine, DeepSeek, DisputeAssessment)
        from src.pipeline.analysis_service import analyze_dispute
        analysis = analyze_dispute(dispute_id, db, trigger=trigger, broadcast=True)

        # The analysis function already updates attention state — read it back
        db.refresh(dispute)
        after_state = {
            "merchant_attention_state": dispute.merchant_attention_state,
            "workflow_stage": dispute.workflow_stage,
        }

        # Compute impact delta
        attention_changed = before_state["merchant_attention_state"] != after_state["merchant_attention_state"]

        impact_delta = {
            "before": {
                "merchant_attention_state": before_state["merchant_attention_state"],
                "evidence_completeness": analysis.get("evidence_intelligence", {}).get("evidence_completeness", 0),
                "case_strength": analysis.get("evidence_intelligence", {}).get("evidence_quality", "UNKNOWN"),
            },
            "after": {
                "merchant_attention_state": after_state["merchant_attention_state"],
                "evidence_completeness": analysis.get("evidence_intelligence", {}).get("evidence_completeness", 0),
                "case_strength": analysis.get("evidence_intelligence", {}).get("evidence_quality", "UNKNOWN"),
                "win_probability": analysis.get("win_probability", {}).get("score", 0),
                "risk_level": analysis.get("risk_analysis", {}).get("risk_level", "UNKNOWN"),
                "missing_evidence": analysis.get("evidence_intelligence", {}).get("missing_evidence", []),
                "contradictions_count": analysis.get("evidence_intelligence", {}).get("contradictions_count", 0),
            },
            "attention_state_changed": attention_changed,
            "ai_explanation": analysis.get("attention_reason", "AI reassessment completed."),
        }

        logger.info(
            f"Reassessed dispute {dispute_id}: "
            f"{before_state['merchant_attention_state']} → {after_state['merchant_attention_state']} "
            f"(trigger: {trigger})"
        )

        return {
            "dispute_id": dispute_id,
            "case_analysis": analysis,
            "impact_delta": impact_delta,
            "reassessment_trigger": trigger,
            "reassessed_at": utc_now_iso(),
        }

    @staticmethod
    def compute_evidence_impact_delta(
        before_analysis: Dict[str, Any],
        after_analysis: Dict[str, Any],
        action_description: str = ""
    ) -> Dict[str, Any]:
        """
        Computes honest before/after assessment when evidence changes.
        Only shows win-probability delta when genuinely recalculated from the model.
        """
        before_ev = before_analysis.get("evidence_intelligence", {})
        after_ev = after_analysis.get("evidence_intelligence", {})
        before_win = before_analysis.get("win_probability", {})
        after_win = after_analysis.get("win_probability", {})

        return {
            "action": action_description,
            "before": {
                "evidence_completeness": before_ev.get("evidence_completeness", 0),
                "case_strength": before_ev.get("evidence_quality", "UNKNOWN"),
                "missing_evidence": before_ev.get("missing_evidence", []),
                "contradictions_count": before_ev.get("contradictions_count", 0),
                "win_probability": before_win.get("score", 0),
                "attention_state": before_analysis.get("merchant_attention_state", "UNKNOWN"),
            },
            "after": {
                "evidence_completeness": after_ev.get("evidence_completeness", 0),
                "case_strength": after_ev.get("evidence_quality", "UNKNOWN"),
                "missing_evidence": after_ev.get("missing_evidence", []),
                "contradictions_count": after_ev.get("contradictions_count", 0),
                "win_probability": after_win.get("score", 0),
                "attention_state": after_analysis.get("merchant_attention_state", "UNKNOWN"),
            },
            "ai_explanation": _generate_delta_explanation(before_ev, after_ev, action_description),
        }


def _generate_delta_explanation(before_ev: dict, after_ev: dict, action: str) -> str:
    """Generates a human-readable explanation for what changed."""
    before_comp = before_ev.get("evidence_completeness", 0)
    after_comp = after_ev.get("evidence_completeness", 0)
    before_missing = len(before_ev.get("missing_evidence", []))
    after_missing = len(after_ev.get("missing_evidence", []))

    parts = []
    if after_comp > before_comp:
        parts.append(f"Evidence completeness improved from {int(before_comp*100)}% to {int(after_comp*100)}%.")
    elif after_comp < before_comp:
        parts.append(f"Evidence completeness decreased from {int(before_comp*100)}% to {int(after_comp*100)}%.")

    if after_missing < before_missing:
        parts.append(f"Missing evidence reduced from {before_missing} to {after_missing} items.")
    elif after_missing > before_missing:
        parts.append(f"Missing evidence increased from {before_missing} to {after_missing} items.")

    if action:
        parts.append(f"Action: {action}")

    return " ".join(parts) if parts else "No significant change detected in case metrics."
