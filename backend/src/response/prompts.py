"""
Prompt templates and input structure builders for AI Response Generator.
Enforces strict anti-hallucination constraints and evidence citation format.
"""

from typing import Dict, Any, List

def build_structured_ai_input(
    dispute_payload: Dict[str, Any],
    tx_payload: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    evidence_package: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Constructs a clean, controlled structured input for the AI generator.
    Filters out untrusted raw payloads and passes only verified facts.
    """
    verified_items = []
    for item in evidence_package.get("evidence", []):
        verified_items.append({
            "evidence_type": item.get("evidence_type"),
            "status": item.get("status"),
            "title": item.get("title"),
            "source": item.get("source"),
            "data": item.get("data")
        })

    return {
        "dispute": {
            "dispute_id": dispute_payload.get("dispute_id"),
            "reason_code": dispute_payload.get("reason_code"),
            "reason_description": dispute_payload.get("reason_description", "")
        },
        "transaction": {
            "transaction_id": tx_payload.get("transaction_id"),
            "amount": tx_payload.get("amount"),
            "currency": tx_payload.get("currency", "USD"),
            "merchant_category": tx_payload.get("merchant_category"),
            "timestamp": tx_payload.get("timestamp")
        },
        "risk_assessment": {
            "risk_score": risk_assessment.get("risk_score"),
            "risk_level": risk_assessment.get("risk_level"),
            "decision": risk_assessment.get("decision")
        },
        "evidence_summary": {
            "available_count": evidence_package.get("available_count", 0),
            "missing_count": evidence_package.get("missing_count", 0),
            "unverified_count": evidence_package.get("unverified_count", 0),
            "invalid_count": evidence_package.get("invalid_count", 0)
        },
        "verified_evidence": verified_items
    }

SYSTEM_PROMPT = """You are Razorpay AI Chargeback Response Generator.
Your task is to write a highly professional, objective, fact-based merchant chargeback defense statement for a payment dispute.

CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
1. Base your statement STRICTLY on the verified evidence items supplied.
2. DO NOT invent delivery dates, tracking numbers, customer names, authentication results, or payment details.
3. If an evidence type has status 'MISSING' or 'UNVERIFIED', you MUST NOT claim that fact was verified. State missing items as limitations.
4. Facts in your response MUST map directly to verified evidence references.
5. Merchant position must be CONTEST (if strong available evidence), PARTIAL_CONTEST (if partial evidence), or INSUFFICIENT_EVIDENCE (if critical evidence is missing).
"""
