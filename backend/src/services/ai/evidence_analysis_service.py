"""
Evidence Analysis Service for Razorpay AI Risk Manager.
Dedicated AI pipeline that extracts evidence content, formats rich dispute context,
invokes DeepSeek for deep verification analysis, validates with strict schemas,
persists results, and avoids duplicate LLM calls.
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from src.database.models import Evidence, Dispute, DisputeEvent, Transaction, Order, Fulfillment, utc_now_iso
from src.database.repository import get_dispute, create_dispute_event
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.schemas import EvidenceAnalysisResultSchema
from src.utils.logger import get_logger

logger = get_logger("EvidenceAnalysisService")


class EvidenceAnalysisService:
    """
    Dedicated AI Evidence Verification Pipeline.
    Evaluates evidence authenticity, relevance, completeness, and contradictions via DeepSeek LLM.
    """

    def __init__(self, client: Optional[DeepSeekClient] = None):
        self.client = client or DeepSeekClient()

    @staticmethod
    def compute_content_hash(text: str, facts: Optional[Dict[str, Any]] = None) -> str:
        """Computes deterministic SHA-256 hash of evidence content and facts."""
        payload = f"{text}\n{json.dumps(facts or {}, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _build_dispute_context(self, db: Session, dispute_id: str) -> Dict[str, Any]:
        """Assembles rich context from dispute, transaction, order, and fulfillment tables."""
        dispute = get_dispute(db, dispute_id)
        if not dispute:
            raise ValueError(f"Dispute with ID '{dispute_id}' not found.")

        tx: Optional[Transaction] = dispute.transaction
        cust = tx.customer if tx else None
        order: Optional[Order] = tx.order if tx else None
        fulfillment: Optional[Fulfillment] = order.fulfillment if order else None
        payments = tx.payments if tx else []
        payment = payments[0] if payments else None

        return {
            "dispute_id": dispute.dispute_id,
            "reason_code": dispute.reason_code,
            "reason_description": dispute.reason_description or "",
            "status": dispute.status,
            "phase": dispute.phase or "chargeback",
            "workflow_stage": dispute.workflow_stage or "DISPUTE_RAISED",
            "merchant_attention_state": dispute.merchant_attention_state or "ACTION_REQUIRED",
            "transaction_id": tx.transaction_id if tx else "N/A",
            "amount": tx.amount if tx else 0.0,
            "currency": tx.currency if tx else "USD",
            "timestamp": tx.timestamp if tx else None,
            "payment_method": tx.payment_method if tx else "credit_card",
            "customer_id": dispute.customer_id,
            "customer": {
                "customer_id": cust.customer_id if cust else dispute.customer_id,
                "account_age_days": cust.account_age_days if cust else 180,
                "verification_status": cust.verification_status if cust else "VERIFIED",
                "country": cust.country if cust else "US"
            },
            "order": {
                "order_id": order.order_id if order else None,
                "product_description": order.product_description if order else None,
                "order_amount": order.order_amount if order else None,
                "order_status": order.order_status if order else None
            } if order else {},
            "fulfillment": {
                "fulfillment_id": fulfillment.fulfillment_id if fulfillment else None,
                "shipping_status": fulfillment.shipping_status if fulfillment else None,
                "tracking_number": fulfillment.tracking_number if fulfillment else None,
                "shipped_at": fulfillment.shipped_at if fulfillment else None,
                "delivered_at": fulfillment.delivered_at if fulfillment else None,
                "delivery_status": fulfillment.delivery_status if fulfillment else None
            } if fulfillment else {},
            "payment": {
                "payment_id": payment.payment_id if payment else None,
                "card_network": payment.card_network if payment else None,
                "last4": payment.last4 if payment else None,
                "auth_code": payment.auth_code if payment else None,
                "avs_match": payment.avs_match if payment else None,
                "cvv_match": payment.cvv_match if payment else None
            } if payment else {}
        }

    def analyze_evidence(
        self,
        db: Session,
        evidence_id: str,
        force_reanalyze: bool = False
    ) -> EvidenceAnalysisResultSchema:
        """
        Executes complete AI Evidence Verification pipeline:
        1. Retrieve evidence record from DB.
        2. Extract & normalize content.
        3. Check content hash to prevent duplicate AI calls.
        4. Build evidence-aware DeepSeek prompt.
        5. Invoke DeepSeek LLM.
        6. Parse and strictly validate response.
        7. Persist result and update verification status in DB.
        8. Record audit trail event.
        """
        evidence: Optional[Evidence] = db.query(Evidence).filter(
            Evidence.evidence_id == evidence_id,
            Evidence.is_deleted == 0
        ).first()

        if not evidence:
            raise ValueError(f"Evidence with ID '{evidence_id}' not found.")

        dispute_id = evidence.dispute_id
        logger.info(f"Evidence received: {evidence_id} (type: {evidence.evidence_type}, dispute: {dispute_id})")

        # Normalize extracted text and structured facts
        extracted_text = (evidence.extracted_text or evidence.raw_content or "").strip()
        facts = evidence.key_entities or evidence.evidence_data or {}
        
        # If no explicit text was stored, synthesize readable summary from facts or metadata
        if not extracted_text and facts:
            extracted_text = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in facts.items() if v])
            evidence.extracted_text = extracted_text

        content_hash = self.compute_content_hash(extracted_text, facts)
        logger.info(f"Evidence extracted: {len(extracted_text)} chars from {evidence.source_reference_id or evidence.title}")

        # Check if already analyzed and content has not changed
        if (
            not force_reanalyze
            and evidence.ai_analysis_status in ["VERIFIED", "REJECTED", "NEEDS_REVIEW"]
            and evidence.content_hash == content_hash
            and evidence.ai_analysis
        ):
            logger.info(f"Serving persisted AI evidence analysis for {evidence_id} (hash match: {content_hash[:8]}).")
            try:
                return EvidenceAnalysisResultSchema.model_validate(evidence.ai_analysis)
            except Exception as e:
                logger.warning(f"Failed to validate persisted analysis: {e}. Re-analyzing.")

        # If evidence has zero content and no facts, mark as unreadable/invalid
        if not extracted_text and not facts:
            now = utc_now_iso()
            error_result = EvidenceAnalysisResultSchema(
                evidence_id=evidence_id,
                dispute_id=dispute_id,
                evidence_type=evidence.evidence_type,
                verification_status="UNREADABLE",
                confidence_score=0.0,
                authenticity_assessment="Document contains no extractable text or readable data.",
                relevance_assessment="Cannot evaluate relevance due to missing document content.",
                completeness_assessment="Empty document — missing all essential transaction/fulfillment facts.",
                key_findings=[],
                matched_dispute_facts=[],
                contradictions=["Document is empty or unreadable."],
                missing_information=["Readable text, transaction receipt, or courier delivery confirmation."],
                risk_flags=["EMPTY_OR_CORRUPT_DOCUMENT"],
                recommendation="Replace this evidence item with a readable document.",
                reasoning_summary="Evidence verification failed because no usable content could be extracted from the file.",
                analyzed_at=now,
                model_used=self.client.model if self.client.is_available() else "system_validator",
                is_fallback=False,
                error="Document contains no readable content."
            )

            evidence.ai_analysis = error_result.model_dump()
            evidence.ai_analysis_status = "FAILED"
            evidence.verification_status = "UNREADABLE"
            evidence.verification_confidence = 0.0
            evidence.ai_analyzed_at = now
            evidence.content_hash = content_hash
            evidence.ai_error = "Document contains no readable content."
            db.commit()
            return error_result

        # Build full dispute context
        dispute_context = self._build_dispute_context(db, dispute_id)

        evidence_dict = {
            "evidence_id": evidence.evidence_id,
            "evidence_type": evidence.evidence_type,
            "title": evidence.title,
            "description": evidence.description,
            "source": evidence.source,
            "source_reference_id": evidence.source_reference_id,
            "mime_type": evidence.mime_type,
            "file_size": evidence.file_size,
            "extracted_text": extracted_text,
            "facts": facts
        }

        # Check DeepSeek client availability
        if not self.client.is_available():
            logger.warning(f"DeepSeek API is not configured. Marking evidence analysis as unavailable for {evidence_id}.")
            now = utc_now_iso()
            unavail_result = EvidenceAnalysisResultSchema(
                evidence_id=evidence_id,
                dispute_id=dispute_id,
                evidence_type=evidence.evidence_type,
                verification_status="FAILED",
                confidence_score=0.0,
                authenticity_assessment="AI verification unavailable: DeepSeek API key is not configured.",
                relevance_assessment="AI verification unavailable: DeepSeek API key is not configured.",
                completeness_assessment="AI verification unavailable: DeepSeek API key is not configured.",
                key_findings=[f"Document '{evidence.title}' extracted successfully ({len(extracted_text)} chars)."],
                matched_dispute_facts=[],
                contradictions=[],
                missing_information=[],
                risk_flags=["AI_VERIFICATION_UNAVAILABLE"],
                recommendation="Configure DEEPSEEK_API_KEY in backend environment to enable AI evidence analysis.",
                reasoning_summary="AI verification unavailable: DeepSeek API key is not configured.",
                analyzed_at=now,
                model_used="unavailable",
                is_fallback=False,
                error="DeepSeek API key is not configured. Set DEEPSEEK_API_KEY in .env."
            )

            evidence.ai_analysis = unavail_result.model_dump()
            evidence.ai_analysis_status = "FAILED"
            evidence.verification_status = "UNVERIFIED"
            evidence.verification_confidence = 0.0
            evidence.ai_analyzed_at = now
            evidence.content_hash = content_hash
            evidence.ai_error = "AI verification unavailable: DeepSeek API key is not configured."
            db.commit()
            return unavail_result

        # Update status to ANALYZING
        evidence.ai_analysis_status = "ANALYZING"
        db.commit()

        # Build prompt & call DeepSeek
        messages = PromptBuilder.build_evidence_analysis_prompt(evidence_dict, dispute_context)
        logger.info(f"DeepSeek analysis started: {evidence_id} (prompt messages: {len(messages)})")

        start_time = time.perf_counter()
        raw_res = self.client.chat_completion(messages, json_mode=True, temperature=0.1, max_tokens=1500)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"DeepSeek request completed: {latency_ms}ms")

        now = utc_now_iso()

        if not raw_res or not raw_res.get("content"):
            logger.warning(f"DeepSeek response was empty or failed for {evidence_id}.")
            failed_result = EvidenceAnalysisResultSchema(
                evidence_id=evidence_id,
                dispute_id=dispute_id,
                evidence_type=evidence.evidence_type,
                verification_status="FAILED",
                confidence_score=0.0,
                authenticity_assessment="DeepSeek API request failed or timed out.",
                relevance_assessment="Could not be determined due to API failure.",
                completeness_assessment="Could not be determined due to API failure.",
                key_findings=[f"Document '{evidence.title}' is present in case."],
                matched_dispute_facts=[],
                contradictions=[],
                missing_information=[],
                risk_flags=["AI_API_TIMEOUT_OR_FAILURE"],
                recommendation="Retry AI verification when network or service is restored.",
                reasoning_summary="Evidence analysis failed due to upstream AI API communication error.",
                analyzed_at=now,
                model_used=self.client.model,
                latency_ms=latency_ms,
                is_fallback=False,
                error="DeepSeek API request failed or timed out."
            )

            evidence.ai_analysis = failed_result.model_dump()
            evidence.ai_analysis_status = "FAILED"
            evidence.ai_analyzed_at = now
            evidence.content_hash = content_hash
            evidence.ai_error = "DeepSeek API request failed or timed out."
            db.commit()
            return failed_result

        # Parse & Validate Response
        parsed_dict = ResponseParser.parse_to_dict(raw_res["content"])
        if not parsed_dict:
            logger.warning(f"Failed to parse DeepSeek response as JSON for {evidence_id}: {raw_res['content'][:200]}")
            malformed_result = EvidenceAnalysisResultSchema(
                evidence_id=evidence_id,
                dispute_id=dispute_id,
                evidence_type=evidence.evidence_type,
                verification_status="FAILED",
                confidence_score=0.0,
                authenticity_assessment="AI response could not be parsed as valid JSON.",
                relevance_assessment="Unparseable AI response.",
                completeness_assessment="Unparseable AI response.",
                key_findings=[],
                matched_dispute_facts=[],
                contradictions=[],
                missing_information=[],
                risk_flags=["MALFORMED_AI_RESPONSE"],
                recommendation="Retry AI verification.",
                reasoning_summary="AI verification failed because the model output was malformed.",
                analyzed_at=now,
                model_used=self.client.model,
                latency_ms=latency_ms,
                is_fallback=False,
                error="Malformed JSON response from AI model."
            )
            evidence.ai_analysis = malformed_result.model_dump()
            evidence.ai_analysis_status = "FAILED"
            evidence.ai_analyzed_at = now
            evidence.content_hash = content_hash
            evidence.ai_error = "Malformed JSON response from AI model."
            db.commit()
            return malformed_result

        # Populate mandatory identifiers
        parsed_dict["evidence_id"] = evidence_id
        parsed_dict["dispute_id"] = dispute_id
        parsed_dict["evidence_type"] = evidence.evidence_type
        parsed_dict["analyzed_at"] = now
        parsed_dict["model_used"] = self.client.model
        parsed_dict["latency_ms"] = latency_ms
        parsed_dict["is_fallback"] = False
        parsed_dict["error"] = None

        # Normalize verification_status
        raw_status = (parsed_dict.get("verification_status") or "NEEDS_REVIEW").upper().strip()
        if raw_status not in ["VERIFIED", "REJECTED", "NEEDS_REVIEW", "FAILED"]:
            if "VERIF" in raw_status:
                raw_status = "VERIFIED"
            elif "REJECT" in raw_status or "INVALID" in raw_status:
                raw_status = "REJECTED"
            elif "REVIEW" in raw_status:
                raw_status = "NEEDS_REVIEW"
            else:
                raw_status = "NEEDS_REVIEW"
        parsed_dict["verification_status"] = raw_status

        # Validate through strict Pydantic model
        try:
            validated_result = EvidenceAnalysisResultSchema.model_validate(parsed_dict)
        except Exception as ve:
            logger.warning(f"Schema validation error on DeepSeek response: {ve}. Normalizing fields.")
            parsed_dict["confidence_score"] = float(parsed_dict.get("confidence_score") or 0.5)
            parsed_dict["key_findings"] = list(parsed_dict.get("key_findings") or [])
            parsed_dict["matched_dispute_facts"] = list(parsed_dict.get("matched_dispute_facts") or [])
            parsed_dict["contradictions"] = list(parsed_dict.get("contradictions") or [])
            parsed_dict["missing_information"] = list(parsed_dict.get("missing_information") or [])
            parsed_dict["risk_flags"] = list(parsed_dict.get("risk_flags") or [])
            validated_result = EvidenceAnalysisResultSchema.model_validate(parsed_dict)

        logger.info(
            f"AI response parsed: status={validated_result.verification_status}, "
            f"confidence={validated_result.confidence_score}, "
            f"findings={len(validated_result.key_findings)}"
        )

        # Persist results in DB
        evidence.ai_analysis = validated_result.model_dump()
        evidence.ai_analysis_status = validated_result.verification_status
        evidence.verification_status = validated_result.verification_status
        evidence.verification_confidence = validated_result.confidence_score
        evidence.ai_analyzed_at = now
        evidence.content_hash = content_hash
        evidence.ai_error = None
        evidence.updated_at = now

        # Record timeline audit event
        try:
            create_dispute_event(
                db, dispute_id,
                event_type="AI_EVIDENCE_VERIFIED",
                title=f"AI Verified Evidence: {evidence.title}",
                description=(
                    f"DeepSeek evaluated {evidence.evidence_type}. Status: {validated_result.verification_status} "
                    f"(Confidence: {int(validated_result.confidence_score * 100)}%). "
                    f"{validated_result.reasoning_summary}"
                ),
                actor_type="AI_ENGINE",
                previous_stage=dispute_context.get("workflow_stage"),
                new_stage=dispute_context.get("workflow_stage"),
                metadata={
                    "evidence_id": evidence_id,
                    "evidence_type": evidence.evidence_type,
                    "verification_status": validated_result.verification_status,
                    "confidence_score": validated_result.confidence_score,
                    "model": self.client.model,
                    "latency_ms": latency_ms,
                    "key_findings": validated_result.key_findings[:3]
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit event for AI evidence verification: {audit_err}")

        db.commit()
        db.refresh(evidence)
        logger.info(f"Evidence analysis persisted: {evidence_id}")

        return validated_result
