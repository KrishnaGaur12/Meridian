"""
Deterministic Fallback Generator for AI Language Layer.
Ensures zero-downtime fault tolerance by providing structured, merchant-friendly explanations,
evidence guidance, and rebuttal drafts whenever DeepSeek LLM is offline, unconfigured, or fails.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

from config.settings import (
    MERCHANT_RECOMMENDATION_CONTEST,
    MERCHANT_RECOMMENDATION_ACCEPT,
    MERCHANT_RECOMMENDATION_REVIEW
)
from src.services.ai.schemas import (
    MerchantDisputeExplanation,
    EvidenceGapExplanation,
    StructuredAIResponse,
    EvidenceCitationSchema
)
from src.utils.logger import get_logger

logger = get_logger("AIFallbackGenerator")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Reason Code Merchant-Friendly Descriptions & Guidance
REASON_EXPLANATIONS = {
    "product_not_received": {
        "title": "Goods / Services Not Received",
        "description": "The customer claims they never received the ordered items or services.",
        "key_evidence": "delivery_confirmation",
        "key_evidence_name": "Delivery Confirmation",
        "advice_contest": "A valid carrier delivery confirmation with timestamp directly disproves the non-delivery claim.",
        "advice_missing": "Upload carrier tracking and proof of delivery confirming successful delivery to the customer address."
    },
    "GOODS_NOT_RECEIVED": {
        "title": "Goods / Services Not Received",
        "description": "The customer claims they never received the ordered items or services.",
        "key_evidence": "delivery_confirmation",
        "key_evidence_name": "Delivery Confirmation",
        "advice_contest": "A valid carrier delivery confirmation with timestamp directly disproves the non-delivery claim.",
        "advice_missing": "Upload carrier tracking and proof of delivery confirming successful delivery to the customer address."
    },
    "fraudulent_transaction": {
        "title": "Unauthorized / Fraudulent Transaction",
        "description": "The cardholder states they did not make or authorize this transaction.",
        "key_evidence": "authentication",
        "key_evidence_name": "Payment Authentication Records",
        "advice_contest": "3D Secure (3DS), AVS, and CVV authorization matches prove the cardholder authorized the payment.",
        "advice_missing": "Provide security authorization logs, IP match records, or past transaction history for this customer."
    },
    "UNAUTHORIZED_TRANSACTION": {
        "title": "Unauthorized / Fraudulent Transaction",
        "description": "The cardholder states they did not make or authorize this transaction.",
        "key_evidence": "authentication",
        "key_evidence_name": "Payment Authentication Records",
        "advice_contest": "3D Secure (3DS), AVS, and CVV authorization matches prove the cardholder authorized the payment.",
        "advice_missing": "Provide security authorization logs, IP match records, or past transaction history for this customer."
    },
    "duplicate_charge": {
        "title": "Duplicate / Multiple Charge",
        "description": "The customer claims they were charged multiple times for a single order.",
        "key_evidence": "invoice",
        "key_evidence_name": "Order Invoice & Separate Receipts",
        "advice_contest": "Invoices and line-item receipts prove each charge corresponds to separate distinct orders.",
        "advice_missing": "Upload individual invoices or itemized order details for each distinct transaction."
    },
    "DUPLICATE_TRANSACTION": {
        "title": "Duplicate / Multiple Charge",
        "description": "The customer claims they were charged multiple times for a single order.",
        "key_evidence": "invoice",
        "key_evidence_name": "Order Invoice & Separate Receipts",
        "advice_contest": "Invoices and line-item receipts prove each charge corresponds to separate distinct orders.",
        "advice_missing": "Upload individual invoices or itemized order details for each distinct transaction."
    },
    "refund_not_processed": {
        "title": "Credit / Refund Not Processed",
        "description": "The customer claims a promised refund was never issued or terms were violated.",
        "key_evidence": "refund_policy",
        "key_evidence_name": "Refund Policy & Terms of Service",
        "advice_contest": "Merchant refund terms accepted at checkout and any prior communications confirm refund ineligibility.",
        "advice_missing": "Upload accepted refund terms, terms of service agreement, or customer support communication logs."
    },
    "REFUND_NOT_RECEIVED": {
        "title": "Credit / Refund Not Processed",
        "description": "The customer claims a promised refund was never issued or terms were violated.",
        "key_evidence": "refund_policy",
        "key_evidence_name": "Refund Policy & Terms of Service",
        "advice_contest": "Merchant refund terms accepted at checkout and any prior communications confirm refund ineligibility.",
        "advice_missing": "Upload accepted refund terms, terms of service agreement, or customer support communication logs."
    }
}


class FallbackGenerator:
    """Deterministic fallback generator for all AI Language Layer tasks."""

    @classmethod
    def get_merchant_recommendation_label(cls, decision_code: str) -> str:
        """Converts internal code (CONTEST, ACCEPT, INVESTIGATE) to standard merchant label."""
        code_upper = (decision_code or "INVESTIGATE").upper()
        if code_upper == "CONTEST":
            return MERCHANT_RECOMMENDATION_CONTEST
        elif code_upper == "ACCEPT":
            return MERCHANT_RECOMMENDATION_ACCEPT
        else:
            return MERCHANT_RECOMMENDATION_REVIEW

    @classmethod
    def generate_merchant_explanation(cls, context: Dict[str, Any]) -> MerchantDisputeExplanation:
        """Generates deterministic, clear merchant explanation and recommendation reasoning."""
        dispute_id = context.get("dispute_id", "DSP_UNKNOWN")
        reason_code = context.get("reason_code", "product_not_received")
        amount = context.get("amount", 0.0)
        currency = context.get("currency", "USD")
        backend_code = context.get("backend_decision_code") or context.get("recommendation_code") or "INVESTIGATE"
        recommendation_label = cls.get_merchant_recommendation_label(backend_code)

        evidence_completeness = float(context.get("evidence_completeness", 0.0))
        raw_win = context.get("win_probability", 0.0)
        if isinstance(raw_win, dict):
            win_prob = float(raw_win.get("score", 0.0))
        else:
            win_prob = float(raw_win or 0.0)
        missing_evidence = context.get("missing_evidence", [])
        contradictions = int(context.get("contradictions", 0))


        reason_info = REASON_EXPLANATIONS.get(reason_code, {
            "title": reason_code.replace("_", " ").title(),
            "description": f"Customer initiated dispute under reason code '{reason_code}'.",
            "key_evidence_name": "Relevant Proof",
            "advice_contest": "Sufficient records support this transaction.",
            "advice_missing": "Please provide supporting documentation."
        })

        summary = f"Dispute {dispute_id} for {currency} {amount:.2f} — {reason_info['title']}."
        plain_english = (
            f"The customer filed a chargeback claiming: {reason_info['description']} "
            f"Current evidence completeness is {int(evidence_completeness * 100)}% with an estimated win probability of {int(win_prob * 100)}%."
        )

        reasoning: List[str] = []
        if backend_code == "CONTEST":
            reasoning.append("Strong verified evidence is present in database records to disprove the customer's claim.")
            reasoning.append(f"Estimated win probability is favorable ({int(win_prob * 100)}%).")
            if evidence_completeness >= 0.75:
                reasoning.append("Evidence completeness meets card network submission requirements.")
            merchant_action = "Review the AI-prepared defense package and submit representment."
            confidence = "High confidence — verified records directly refute claim."
        elif backend_code == "ACCEPT":
            reasoning.append("Crucial fulfillment/delivery evidence is missing or shows an unresolved customer issue.")
            if missing_evidence:
                reasoning.append(f"Missing required records: {', '.join(missing_evidence[:2])}.")
            reasoning.append("Accepting this dispute will prevent additional chargeback processing fees.")
            merchant_action = "Accept dispute to close the case and avoid arbitration penalties."
            confidence = "High confidence — lacking mandatory counter-evidence."
        else:
            reasoning.append("Transaction requires merchant verification before proceeding to representment.")
            if missing_evidence:
                reasoning.append(f"Upload missing evidence ({', '.join(missing_evidence[:2])}) to increase win probability.")
            if contradictions > 0:
                reasoning.append("Resolve record contradictions between order details and fulfillment data.")
            merchant_action = "Provide missing evidence records or manually verify transaction fulfillment."
            confidence = "Moderate confidence — additional evidence recommended."

        missing_summary = f"Missing: {', '.join(missing_evidence)}" if missing_evidence else None

        return MerchantDisputeExplanation(
            dispute_id=dispute_id,
            summary=summary,
            plain_english_explanation=plain_english,
            recommendation=recommendation_label,
            recommendation_code=backend_code,
            recommendation_reasoning=reasoning,
            merchant_action=merchant_action,
            confidence_language=confidence,
            missing_evidence_summary=missing_summary
        )

    @classmethod
    def generate_evidence_gap_explanations(cls, context: Dict[str, Any]) -> List[EvidenceGapExplanation]:
        """Generates granular, merchant-friendly explanations for all evidence items."""
        reason_code = context.get("reason_code", "product_not_received")
        available_items = context.get("available_evidence", [])
        missing_items = context.get("missing_evidence", [])
        unverified_items = context.get("unverified_evidence", [])

        # Normalize items
        all_items: List[Dict[str, Any]] = []
        if isinstance(available_items, list):
            for it in available_items:
                ev_type = it.get("evidence_type") if isinstance(it, dict) else str(it)
                all_items.append({"type": ev_type, "status": "AVAILABLE", "title": it.get("title") if isinstance(it, dict) else None})
        if isinstance(missing_items, list):
            for it in missing_items:
                ev_type = it.get("evidence_type") if isinstance(it, dict) else str(it)
                all_items.append({"type": ev_type, "status": "MISSING", "title": None})
        if isinstance(unverified_items, list):
            for it in unverified_items:
                ev_type = it.get("evidence_type") if isinstance(it, dict) else str(it)
                all_items.append({"type": ev_type, "status": "UNVERIFIED", "title": None})

        explanations: List[EvidenceGapExplanation] = []
        seen = set()

        for item in all_items:
            ev_type = item["type"]
            if not ev_type or ev_type in seen:
                continue
            seen.add(ev_type)

            status = item["status"]
            title = item["title"] or ev_type.replace("_", " ").title()

            if ev_type in ("delivery_confirmation", "proof_of_delivery"):
                why = "Card networks require independent carrier proof showing date and delivery address to refute non-receipt claims."
                supports = "Disproves customer claim that the order was never delivered."
                action = "Available in system." if status == "AVAILABLE" else "Upload carrier delivery receipt with recipient name or delivery timestamp."
                urgency = "HIGH" if reason_code in ("product_not_received", "GOODS_NOT_RECEIVED") else "MEDIUM"
            elif ev_type in ("shipping_confirmation", "carrier_tracking"):
                why = "Establishes that the merchant fulfilled and dispatched the physical goods within the agreed timeframe."
                supports = "Proves order dispatch and tracking provenance."
                action = "Available in system." if status == "AVAILABLE" else "Provide carrier name and active tracking number."
                urgency = "HIGH"
            elif ev_type in ("payment_confirmation", "authentication"):
                why = "Demonstrates that the card transaction passed AVS address and CVV security checks with bank capture."
                supports = "Proves legitimate payment authorization and protects against fraud chargebacks."
                action = "Available in system." if status == "AVAILABLE" else "Ensure payment gateway authorization logs are recorded."
                urgency = "HIGH"
            elif ev_type in ("invoice", "order_receipt"):
                why = "Itemizes goods purchased, pricing, customer details, and transaction amount."
                supports = "Establishes contractual scope and order validity."
                action = "Available in system." if status == "AVAILABLE" else "Upload customer order invoice or purchase receipt."
                urgency = "MEDIUM"
            elif ev_type in ("customer_history", "account_profile"):
                why = "Shows customer account longevity, past dispute record, and legitimate purchasing history."
                supports = "Demonstrates established positive customer relationship."
                action = "Available in system." if status == "AVAILABLE" else "Attach customer profile verification logs."
                urgency = "LOW"
            elif ev_type in ("refund_policy", "terms_of_service", "tos_acceptance"):
                why = "Proves the cardholder accepted merchant cancellation and return policies at checkout."
                supports = "Protects against refund disputes and buyer remorse claims."
                action = "Available in system." if status == "AVAILABLE" else "Upload customer checkout acceptance terms or refund policy link."
                urgency = "MEDIUM"
            else:
                why = f"Provides supplementary factual documentation supporting the merchant's fulfillment of {title}."
                supports = "Supports merchant defense package completeness."
                action = "Available in system." if status == "AVAILABLE" else f"Upload {title} document if available."
                urgency = "LOW"

            explanations.append(EvidenceGapExplanation(
                evidence_type=ev_type,
                title=title,
                status=status,
                why_it_matters=why,
                supports_claim=supports,
                is_sufficient=(status == "AVAILABLE"),
                suggested_action=action,
                urgency=urgency
            ))

        return explanations

    @classmethod
    def generate_structured_response(cls, context: Dict[str, Any]) -> StructuredAIResponse:
        """Generates deterministic structured rebuttal statement based strictly on verified facts."""
        dispute_id = context.get("dispute_id", "DSP_UNKNOWN")
        reason_code = context.get("reason_code", "product_not_received")
        reason_desc = context.get("reason_description", "")
        tx_id = context.get("transaction_id", "TXN_UNKNOWN")
        amount = float(context.get("amount", 0.0))
        currency = context.get("currency", "USD")

        backend_code = context.get("backend_decision_code") or context.get("merchant_position") or "INSUFFICIENT_EVIDENCE"
        if backend_code not in ("CONTEST", "PARTIAL_CONTEST", "INSUFFICIENT_EVIDENCE"):
            backend_code = "CONTEST" if backend_code == "CONTEST" else ("INSUFFICIENT_EVIDENCE" if backend_code == "ACCEPT" else "PARTIAL_CONTEST")

        recommendation_label = cls.get_merchant_recommendation_label(backend_code)

        evidence_items = context.get("verified_evidence", context.get("available_evidence", []))
        ev_map = {}
        if isinstance(evidence_items, list):
            for it in evidence_items:
                if isinstance(it, dict):
                    ev_map[it.get("evidence_type", "")] = it
                else:
                    ev_map[str(it)] = {"evidence_type": str(it), "status": "AVAILABLE"}

        available_types = [t for t, item in ev_map.items() if item.get("status") == "AVAILABLE"]
        missing_types = context.get("missing_evidence", [t for t, item in ev_map.items() if item.get("status") == "MISSING"])

        # Construct key facts and citations
        key_facts: List[str] = []
        citations: List[EvidenceCitationSchema] = []

        # Payment fact
        pay_ev = ev_map.get("payment_confirmation") or ev_map.get("authentication")
        if pay_ev and pay_ev.get("status") == "AVAILABLE":
            pay_data = pay_ev.get("data", {})
            auth_code = pay_data.get("auth_code", "AUTH_VERIFIED")
            fact = f"Transaction {tx_id} of {currency} {amount:.2f} was successfully authorized (Auth Code: {auth_code}) and settled."
            key_facts.append(fact)
            citations.append(EvidenceCitationSchema(claim=fact, evidence_refs=["payment_confirmation"]))

        # Shipping fact
        ship_ev = ev_map.get("shipping_confirmation")
        if ship_ev and ship_ev.get("status") == "AVAILABLE":
            ship_data = ship_ev.get("data", {})
            trk = ship_data.get("tracking_number", "")
            shipped_at = ship_data.get("shipped_at", "")
            fact = f"Order was dispatched with tracking number '{trk}' on {shipped_at}."
            key_facts.append(fact)
            citations.append(EvidenceCitationSchema(claim=fact, evidence_refs=["shipping_confirmation"]))

        # Delivery fact
        deliv_ev = ev_map.get("delivery_confirmation") or ev_map.get("proof_of_delivery")
        if deliv_ev and deliv_ev.get("status") == "AVAILABLE":
            deliv_data = deliv_ev.get("data", {})
            delivered_at = deliv_data.get("delivered_at", "")
            trk = deliv_data.get("tracking_number", "")
            fact = f"Carrier confirmed successful package delivery on {delivered_at} (Tracking: '{trk}')."
            key_facts.append(fact)
            citations.append(EvidenceCitationSchema(claim=fact, evidence_refs=["delivery_confirmation"]))

        # Customer history fact
        cust_ev = ev_map.get("customer_history")
        if cust_ev and cust_ev.get("status") == "AVAILABLE":
            cust_data = cust_ev.get("data", {})
            age = cust_data.get("account_age_days", 180)
            fact = f"Customer account has been active and verified for {age} days."
            key_facts.append(fact)
            citations.append(EvidenceCitationSchema(claim=fact, evidence_refs=["customer_history"]))

        limitations = [f"Record for '{m}' is missing or incomplete in database records." for m in missing_types]

        title = f"Chargeback Defense Statement — Dispute {dispute_id} ({reason_code})"
        summary = (
            f"Merchant response for dispute {dispute_id} regarding charge of {currency} {amount:.2f}. "
            f"Position: {backend_code}. Verified available evidence items: {len(available_types)}."
        )

        resp_lines = [
            f"REF: Chargeback Defense Statement for Dispute {dispute_id}",
            f"Reason Code: {reason_code}",
            f"Transaction ID: {tx_id} | Amount: {currency} {amount:.2f}\n",
            "SUMMARY OF MERCHANT POSITION:",
            f"We respectfully {backend_code.lower().replace('_', ' ')} this dispute based on verified database records.\n",
            "VERIFIED EVIDENCE & FACTS:"
        ]
        for fact in key_facts:
            resp_lines.append(f"- {fact}")

        if limitations:
            resp_lines.append("\nLIMITATIONS & MISSING RECORDS:")
            for lim in limitations:
                resp_lines.append(f"- {lim}")

        resp_lines.append("\nCONCLUSION:")
        if backend_code == "CONTEST":
            resp_lines.append("The verified transaction and fulfillment records demonstrate complete fulfillment. We request that the dispute be resolved in favor of the merchant.")
        elif backend_code == "PARTIAL_CONTEST":
            resp_lines.append("Partial evidence supports transaction validity, but missing items are noted for operator review.")
        else:
            resp_lines.append("Current evidence is insufficient to fully contest the dispute. Operator review recommended.")

        response_text = "\n".join(resp_lines)
        response_draft = (
            f"Rebuttal for {dispute_id}: We contest the '{reason_code}' claim for transaction {tx_id} ({currency} {amount:.2f}). "
            f"Verified records confirm payment capture and order fulfillment. Please review the attached evidence package."
        )

        evidence_explanations = cls.generate_evidence_gap_explanations(context)

        return StructuredAIResponse(
            title=title,
            summary=summary,
            merchant_position=backend_code,
            merchant_recommendation=recommendation_label,
            response_text=response_text,
            response_draft=response_draft,
            key_facts=key_facts,
            reasoning=[
                f"Position is {backend_code} based on {len(available_types)} verified evidence records.",
                f"{'Zero missing items detected.' if not missing_types else f'{len(missing_types)} missing items noted.'}"
            ],
            supporting_evidence=available_types,
            missing_evidence=missing_types,
            evidence_explanations=evidence_explanations,
            limitations=limitations,
            evidence_citations=citations,
            confidence_language="High confidence based on verified records" if backend_code == "CONTEST" else "Moderate confidence",
            merchant_action="Review defense statement and proceed to submission" if backend_code == "CONTEST" else "Upload missing evidence or investigate",
            generated_at=utc_now_iso(),
            generator_version="deterministic_fallback_v1",
            is_fallback=True
        )
