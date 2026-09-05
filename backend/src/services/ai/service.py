"""
Central AI Service Layer for Razorpay AI Risk Manager.
Coordinates DeepSeek language generation, caching, fallback guarantees,
Pydantic validation, and audit trail logging.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import time

from src.database.models import Evidence
from src.database.repository import (
    get_dispute, get_latest_risk_assessment, create_dispute_event
)
from src.evidence.engine import EvidenceEngine
from src.services.ai.schemas import (
    MerchantDisputeExplanation,
    EvidenceGapExplanation,
    StructuredAIResponse,
    AIGenerationMetadata,
    EvidenceAnalysisResultSchema
)
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.fallback import FallbackGenerator
from src.services.ai.cache import AICacheManager
from src.services.ai.evidence_reasoner import EvidenceReasoner
from src.services.ai.evidence_analysis_service import EvidenceAnalysisService
from src.services.ai.response_generator import AIResponseGenerator
from src.utils.logger import get_logger

logger = get_logger("AIService")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIService:
    """
    Central AI Language Layer Service.
    Wraps DeepSeek LLM with deterministic fallbacks, in-memory caching,
    strict schema validation, and audit event recording.
    """

    def __init__(self):
        self.client = DeepSeekClient()
        self.cache = AICacheManager()
        self.evidence_engine = EvidenceEngine()
        self.evidence_reasoner = EvidenceReasoner(self.client)
        self.evidence_analyzer = EvidenceAnalysisService(self.client)
        self.response_generator = AIResponseGenerator(self.client)

    def analyze_evidence(
        self,
        db: Session,
        evidence_id: str,
        force_reanalyze: bool = False
    ) -> EvidenceAnalysisResultSchema:
        """Invokes DeepSeek evidence verification pipeline for a specific evidence record."""
        return self.evidence_analyzer.analyze_evidence(db, evidence_id, force_reanalyze=force_reanalyze)

    def _extract_dispute_context(self, db: Session, dispute_id: str, context_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Assembles verified backend facts for a dispute into an AI-ready context dictionary."""
        if context_override:
            return context_override

        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute with ID '{dispute_id}' not found.")

        tx = dispute.transaction
        cust = tx.customer if tx else None
        order = tx.order if tx else None
        fulfillment = order.fulfillment if order else None
        payments = tx.payments if tx else []
        payment = payments[0] if payments else None

        # Evidence package evaluation
        ev_pkg = self.evidence_engine.evaluate_dispute_evidence(db, dispute_id)
        ev_dict = ev_pkg.model_dump()
        ev_items = ev_dict.get("evidence", [])

        available_ev = [i.get("evidence_type") for i in ev_items if i.get("status") in ["AVAILABLE", "VERIFIED"]]
        missing_ev = [i.get("evidence_type") for i in ev_items if i.get("status") == "MISSING"]
        unverified_ev = [i.get("evidence_type") for i in ev_items if i.get("status") == "UNVERIFIED"]
        completeness_score = float(ev_dict.get("completeness_score", 0.0))
        has_delivery = "delivery_confirmation" in available_ev or "proof_of_delivery" in available_ev or (fulfillment and (fulfillment.delivery_status or "").upper() == "DELIVERED")

        if dispute.reason_code in ["product_not_received", "goods_not_received"] and not has_delivery:
            win_prob = 0.30
            backend_code = "INSUFFICIENT_EVIDENCE"
        elif not missing_ev and not unverified_ev:
            win_prob = 0.85
            backend_code = "CONTEST"
        elif missing_ev or unverified_ev:
            if completeness_score >= 0.70 and has_delivery:
                win_prob = 0.65
                backend_code = "CONTEST"
            elif completeness_score < 0.40:
                win_prob = 0.30
                backend_code = "INSUFFICIENT_EVIDENCE"
            else:
                win_prob = 0.50
                backend_code = "PARTIAL_CONTEST"
        elif completeness_score >= 0.50:
            win_prob = 0.75
            backend_code = "CONTEST"
        else:
            win_prob = 0.50
            backend_code = "INVESTIGATE"
        backend_recommendation = FallbackGenerator.get_merchant_recommendation_label(backend_code)

        # Load active structured DB evidence items
        active_ev_rows = db.query(Evidence).filter(
            Evidence.dispute_id == dispute_id,
            Evidence.is_deleted == 0
        ).all()
        structured_evidence_list = [
            {
                "evidence_id": e.evidence_id,
                "evidence_type": e.evidence_type,
                "title": e.title,
                "extracted_text": e.extracted_text or e.raw_content or "",
                "key_entities": e.key_entities,
                "verification_status": e.verification_status,
                "approval_status": e.approval_status,
                "source": e.source
            } for e in active_ev_rows
        ]

        return {
            "dispute_id": dispute.dispute_id,
            "transaction_id": tx.transaction_id if tx else "N/A",
            "customer_id": dispute.customer_id,
            "amount": tx.amount if tx else 0.0,
            "currency": tx.currency if tx else "USD",
            "reason_code": dispute.reason_code,
            "reason_description": dispute.reason_description or "",
            "status": dispute.status,
            "phase": dispute.phase or "chargeback",
            "workflow_stage": dispute.workflow_stage or "DISPUTE_RAISED",
            "merchant_attention_state": dispute.merchant_attention_state or "ACTION_REQUIRED",
            "risk_score": 0.15,
            "risk_level": "LOW",
            "evidence_completeness": completeness_score,
            "win_probability": win_prob,
            "backend_decision_code": backend_code,
            "merchant_position": backend_code,
            "backend_recommendation": backend_recommendation,
            "available_evidence": available_ev,
            "missing_evidence": missing_ev,
            "unverified_evidence": unverified_ev,
            "verified_evidence": ev_items,
            "structured_evidence": structured_evidence_list,
            "case_summary": {
                "product_description": order.product_description if order else "N/A",
                "shipping_status": fulfillment.shipping_status if fulfillment else "N/A",
                "delivery_status": fulfillment.delivery_status if fulfillment else "N/A",
                "tracking_number": fulfillment.tracking_number if fulfillment else None,
                "auth_code": payment.auth_code if payment else None,
                "account_age_days": cust.account_age_days if cust else 180
            }
        }

    def get_case_explanation(self, db: Session, dispute_id: str, context_override: Optional[Dict[str, Any]] = None) -> MerchantDisputeExplanation:
        """
        Retrieves or generates merchant-friendly dispute explanation and recommendation reasoning.
        Uses cached result when available. Falls back deterministically on any LLM issue.
        """
        context = self._extract_dispute_context(db, dispute_id, context_override=context_override)
        cache_key = self.cache.build_key(dispute_id, "explanation", context)

        cached_val = self.cache.get(cache_key)
        if cached_val:
            logger.info(f"Serving cached merchant explanation for dispute '{dispute_id}'.")
            return MerchantDisputeExplanation.model_validate(cached_val)

        start_time = time.perf_counter()
        is_fallback = True
        explanation: Optional[MerchantDisputeExplanation] = None

        if self.client.is_available():
            try:
                messages = PromptBuilder.build_case_explanation_prompt(context)
                res = self.client.chat_completion(messages, json_mode=True)
                if res and res.get("content"):
                    data = ResponseParser.parse_to_dict(res["content"])
                    if data:
                        # Enforce backend recommendation guardrail
                        data["dispute_id"] = dispute_id
                        data["recommendation"] = context["backend_recommendation"]
                        data["recommendation_code"] = context["backend_decision_code"]
                        explanation = MerchantDisputeExplanation.model_validate(data)
                        is_fallback = False
            except Exception as e:
                logger.warning(f"DeepSeek case explanation failed: {e}. Using deterministic fallback.")

        if not explanation:
            explanation = FallbackGenerator.generate_merchant_explanation(context)

        object.__setattr__(explanation, "_is_fallback", is_fallback)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Cache result
        self.cache.set(cache_key, explanation.model_dump(), dispute_id)

        # Log AI generation audit event
        try:
            create_dispute_event(
                db, dispute_id,
                event_type="AI_EXPLANATION_GENERATED",
                title="AI Dispute Explanation Generated",
                description=f"Generated plain-English explanation for merchant. Recommendation: {explanation.recommendation}",
                actor_type="AI_ENGINE",
                previous_stage=context.get("workflow_stage"),
                new_stage=context.get("workflow_stage"),
                metadata={
                    "provider": "deepseek" if not is_fallback else "deterministic_fallback",
                    "model": self.client.model if not is_fallback else "fallback",
                    "is_fallback": is_fallback,
                    "latency_ms": latency_ms,
                    "recommendation": explanation.recommendation
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit event for AI generation: {audit_err}")

        return explanation

    def get_evidence_guidance(self, db: Session, dispute_id: str) -> List[EvidenceGapExplanation]:
        """
        Returns granular evidence requirement explanations and actionable merchant suggestions.
        Cached by dispute state.
        """
        context = self._extract_dispute_context(db, dispute_id)
        cache_key = self.cache.build_key(dispute_id, "evidence_guidance", context)

        cached_val = self.cache.get(cache_key)
        if cached_val:
            logger.info(f"Serving cached evidence guidance for dispute '{dispute_id}'.")
            return [EvidenceGapExplanation.model_validate(i) for i in cached_val]

        explanations = self.evidence_reasoner.analyze_evidence_gaps(context)

        # Cache result
        self.cache.set(cache_key, [e.model_dump() for e in explanations], dispute_id)
        return explanations

    def generate_structured_response(self, db: Session, dispute_id: str) -> StructuredAIResponse:
        """
        Generates validated, structured chargeback defense statement / rebuttal draft.
        Enforces post-LLM claim validation and records audit event.
        """
        context = self._extract_dispute_context(db, dispute_id)
        cache_key = self.cache.build_key(dispute_id, "structured_response", context)

        cached_val = self.cache.get(cache_key)
        if cached_val:
            logger.info(f"Serving cached structured response for dispute '{dispute_id}'.")
            return StructuredAIResponse.model_validate(cached_val)

        start_time = time.perf_counter()
        response = self.response_generator.generate_defense_response(context)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Cache result
        self.cache.set(cache_key, response.model_dump(), dispute_id)

        # Log AI generation audit event
        try:
            create_dispute_event(
                db, dispute_id,
                event_type="AI_RESPONSE_GENERATED",
                title="AI Defense Statement Generated",
                description=f"Generated structured rebuttal statement. Position: {response.merchant_position}",
                actor_type="AI_ENGINE",
                previous_stage=context.get("workflow_stage"),
                new_stage=context.get("workflow_stage"),
                metadata={
                    "provider": "deepseek" if not response.is_fallback else "deterministic_fallback",
                    "model": response.generator_version,
                    "is_fallback": response.is_fallback,
                    "latency_ms": latency_ms,
                    "merchant_position": response.merchant_position
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit event for AI response: {audit_err}")

        return response

    def invalidate_cache(self, dispute_id: str) -> int:
        """Invalidates all cached AI generations for the specified dispute."""
        return self.cache.invalidate_dispute(dispute_id)
