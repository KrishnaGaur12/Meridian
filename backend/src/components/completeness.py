"""
Component 5 — Evidence Completeness Evaluator.
Deterministic component comparing required vs available evidence items to compute a completeness score.
"""

from typing import List, Dict, Any, TypedDict

EVIDENCE_TYPE_ALIASES = {
    "proof_of_delivery": ["proof_of_delivery", "delivery_confirmation", "delivery_proof", "carrier_tracking", "delivery_receipt"],
    "delivery_confirmation": ["delivery_confirmation", "proof_of_delivery", "delivery_proof", "carrier_tracking", "delivery_receipt"],
    "shipping_proof": ["shipping_proof", "shipping_confirmation", "carrier_manifest", "dispatch_proof", "tracking_info"],
    "shipping_confirmation": ["shipping_confirmation", "shipping_proof", "carrier_manifest", "dispatch_proof", "tracking_info"],
    "invoice": ["invoice", "payment_confirmation", "order_invoice", "receipt", "payment_receipt", "transaction_receipt"],
    "payment_confirmation": ["payment_confirmation", "invoice", "order_invoice", "receipt", "payment_receipt", "transaction_receipt"],
    "customer_communication": ["customer_communication", "customer_history", "chat_log", "support_ticket", "email_transcript"],
    "customer_history": ["customer_history", "customer_communication", "chat_log", "support_ticket", "customer_profile"],
    "terms_of_service": ["terms_of_service", "terms_and_conditions", "cancellation_policy", "refund_policy", "merchant_policy"],
    "refund_policy": ["refund_policy", "terms_of_service", "cancellation_policy", "return_policy", "policy_acknowledgement"],
    "refund_receipt": ["refund_receipt", "credit_receipt", "refund_confirmation", "arn_receipt"],
}

class CompletenessResult(TypedDict):
    completeness_score: float
    provided_evidence_types: List[str]
    missing_required: List[str]
    missing_optional: List[str]

class EvidenceCompletenessEvaluator:
    """Evaluates how completely available evidence satisfies required checklist."""
    
    def evaluate(
        self,
        required_evidence: List[str],
        optional_evidence: List[str],
        available_evidence: List[Dict[str, Any]]
    ) -> CompletenessResult:
        # Extract normalized types of provided documents
        provided_types = set()
        for doc in available_evidence:
            doc_type = str(doc.get("document_type", doc.get("evidence_type", ""))).strip().lower()
            if doc_type:
                provided_types.add(doc_type)
                # Expand with known aliases
                aliases = EVIDENCE_TYPE_ALIASES.get(doc_type, [])
                for a in aliases:
                    provided_types.add(a)

        # Check required missing
        missing_req = []
        satisfied_req_count = 0
        for req in required_evidence:
            norm_req = req.strip().lower()
            req_aliases = EVIDENCE_TYPE_ALIASES.get(norm_req, [norm_req])
            if any(a in provided_types for a in req_aliases):
                satisfied_req_count += 1
            else:
                missing_req.append(norm_req)

        # Check optional missing
        missing_opt = []
        for opt in optional_evidence:
            norm_opt = opt.strip().lower()
            opt_aliases = EVIDENCE_TYPE_ALIASES.get(norm_opt, [norm_opt])
            if not any(a in provided_types for a in opt_aliases):
                missing_opt.append(norm_opt)

        # Calculate deterministic score
        total_req = len(required_evidence)
        if total_req == 0:
            score = 1.0
        else:
            score = round(satisfied_req_count / float(total_req), 4)

        return CompletenessResult(
            completeness_score=score,
            provided_evidence_types=list(provided_types),
            missing_required=missing_req,
            missing_optional=missing_opt
        )
