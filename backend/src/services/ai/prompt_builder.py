"""
Prompt Builder for DeepSeek AI Language Layer.
Constructs strict, contextualized prompts for dispute explanations, evidence reasoning, and defense drafting.
Enforces anti-hallucination guardrails and grounds all generations exclusively in verified backend facts.
"""

import json
from typing import Dict, Any, List


SYSTEM_PROMPT_EXPLAINABILITY = """You are Razorpay's AI Dispute & Chargeback Assistant.
Your mission is to translate complex technical fraud models and dispute evidence into clean, simple, merchant-friendly explanations.

CRITICAL OPERATIONAL RULES:
1. NEVER override or contradict the backend recommendation decision provided to you. Your role is solely to EXPLAIN the recommendation and guide the merchant.
2. NEVER fabricate, hallucinate, or assume any facts not explicitly present in the provided context (e.g. do not invent tracking numbers, delivery dates, carrier names, or customer communications).
3. Always keep merchant-facing language clear, professional, and accessible. Avoid exposing technical model terms like 'XGBoost', 'RandomForest', 'feature vectors', or 'SHAP values'.
4. Merchant recommendations must strictly follow the 3 standard guardrail outcomes:
   - "Challenge this dispute" (for CONTEST)
   - "Accept this dispute" (for ACCEPT)
   - "Review further" (for INVESTIGATE)
5. Output ONLY valid JSON matching the requested structure. No markdown formatting outside of JSON.
"""

SYSTEM_PROMPT_RESPONSE_DRAFTER = """You are a senior payment dispute specialist drafting formal chargeback defense statements for bank representment.

CRITICAL REBUTTAL RULES:
1. Ground every claim strictly in verified available evidence provided in the context.
2. If evidence for a fact (e.g. delivery confirmation) is missing or unverified, acknowledge the limitation clearly. NEVER state or imply an order was delivered if delivery_confirmation is not AVAILABLE.
3. Keep the tone formal, respectful, concise, and structured.
4. Directly refute the customer's specific dispute reason using verified transaction, fulfillment, or policy records.
5. Provide traceable citations linking claims to evidence types.
6. Output ONLY valid JSON matching the required schema.
"""


class PromptBuilder:
    """Builds structured message lists for DeepSeek LLM prompts."""

    @staticmethod
    def sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """Strips out sensitive internal fields and database-specific identifiers."""
        safe_keys = {
            "dispute_id", "transaction_id", "amount", "currency", "reason_code",
            "reason_description", "status", "phase", "workflow_stage", "urgency_level",
            "remaining_time_human", "case_summary", "risk_level", "fraud_probability",
            "evidence_completeness", "evidence_quality", "available_evidence",
            "missing_evidence", "unverified_evidence", "contradictions",
            "backend_recommendation", "backend_decision_code", "key_facts"
        }
        sanitized = {}
        for k, v in context.items():
            if k in safe_keys:
                sanitized[k] = v
        return sanitized

    @classmethod
    def build_case_explanation_prompt(cls, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Constructs prompt for merchant case summary and recommendation reasoning."""
        clean_ctx = cls.sanitize_context(context)
        backend_rec = context.get("backend_recommendation", "Review further")
        backend_code = context.get("backend_decision_code", "INVESTIGATE")

        user_content = f"""Please analyze this chargeback dispute case and produce a merchant-friendly explanation.

BACKEND CONTEXT:
{json.dumps(clean_ctx, indent=2)}

MANDATED BACKEND RECOMMENDATION: {backend_rec} ({backend_code})

Generate a JSON object matching this schema:
{{
  "summary": "1-2 sentence concise executive summary of the dispute",
  "plain_english_explanation": "Simple explanation of what happened, why the customer filed a dispute, and current standing",
  "recommendation_reasoning": [
    "Bullet point 1 explaining why {backend_rec} is recommended based on facts",
    "Bullet point 2 noting evidence standing or risk level"
  ],
  "merchant_action": "Direct next step for the merchant (e.g. Upload tracking receipt, Submit package, or Concede dispute)",
  "confidence_language": "Clear confidence summary (e.g. 'High confidence based on verified delivery confirmation')",
  "missing_evidence_summary": "Brief note on missing records if any, or null"
}}
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT_EXPLAINABILITY},
            {"role": "user", "content": user_content}
        ]

    @classmethod
    def build_evidence_guidance_prompt(cls, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Constructs prompt for granular evidence gap explanations and suggestions."""
        clean_ctx = cls.sanitize_context(context)

        user_content = f"""Analyze the evidence status for this dispute and explain each evidence requirement in simple merchant terms.

DISPUTE & EVIDENCE DATA:
{json.dumps(clean_ctx, indent=2)}

Generate a JSON object with this structure:
{{
  "evidence_explanations": [
    {{
      "evidence_type": "string matching requirement",
      "title": "Clean document title",
      "status": "AVAILABLE | MISSING | UNVERIFIED | INVALID",
      "why_it_matters": "Plain-English explanation of why the card network requires this document for this dispute reason",
      "supports_claim": "The specific claim this proof verifies or refutes",
      "is_sufficient": true | false,
      "suggested_action": "Clear instruction on what the merchant should upload or check next",
      "urgency": "HIGH | MEDIUM | LOW"
    }}
  ],
  "overall_guidance": "1 sentence summarizing whether current evidence is sufficient to win the dispute",
  "next_suggested_upload": "Top priority document to upload next, or 'None required'"
}}
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT_EXPLAINABILITY},
            {"role": "user", "content": user_content}
        ]

    @classmethod
    def build_response_draft_prompt(cls, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Constructs prompt for formal chargeback defense statement / rebuttal drafting."""
        clean_ctx = cls.sanitize_context(context)
        backend_pos = context.get("merchant_position", "INSUFFICIENT_EVIDENCE")

        user_content = f"""Draft a professional, evidence-backed chargeback rebuttal defense statement based strictly on the verified facts provided below.

CASE DATA & VERIFIED EVIDENCE:
{json.dumps(clean_ctx, indent=2)}

MERCHANT POSITION: {backend_pos}

Generate a JSON object matching this schema:
{{
  "title": "Defense statement title including dispute ID and reason code",
  "summary": "1-2 sentence executive summary of merchant position",
  "response_text": "Full multi-paragraph formal defense statement structured with REF, SUMMARY, EVIDENCE & FACTS, LIMITATIONS (if any), and CONCLUSION",
  "response_draft": "Concise 1-paragraph rebuttal statement ready for fast merchant copy/paste",
  "key_facts": ["Bullet point 1 of verified fact", "Bullet point 2"],
  "reasoning": ["Bullet point explaining defense rationale 1", "Bullet point 2"],
  "supporting_evidence": ["list of available evidence types cited"],
  "limitations": ["list of missing evidence limitations noted"],
  "evidence_citations": [
    {{"claim": "exact factual sentence in statement", "evidence_refs": ["referenced_evidence_type"]}}
  ],
  "confidence_language": "Confidence assessment language",
  "merchant_action": "Recommended merchant action"
}}
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT_RESPONSE_DRAFTER},
            {"role": "user", "content": user_content}
        ]

    @classmethod
    def build_evidence_analysis_prompt(
        cls,
        evidence_dict: Dict[str, Any],
        dispute_context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Constructs evidence-aware prompt for DeepSeek to analyze the actual extracted document content
        against the dispute reason, transaction details, and order facts.
        """
        system_prompt = """You are Razorpay's Senior AI Evidence Verification Engine.
Your role is to rigorously inspect uploaded chargeback evidence documents, extract verifiable facts, and determine whether the evidence genuinely substantiates the merchant's defense against the dispute.

CRITICAL OPERATIONAL RULES:
1. Base your evaluation strictly on the PROVIDED EXTRACTED EVIDENCE CONTENT and DISPUTE CONTEXT. Do not invent facts.
2. The AI must NOT automatically approve evidence merely because a file was uploaded. Evaluate authenticity, relevance, and completeness carefully.
3. Verification status MUST be one of:
   - "VERIFIED": The document is authentic, readable, and directly refutes the dispute reason with matching facts (e.g. proof of delivery matching order amount/date).
   - "REJECTED": The document is invalid, for the wrong customer/transaction, fraudulent, or directly contradicts the case facts.
   - "NEEDS_REVIEW": The document is partially relevant or missing critical corroborating data (e.g. tracking number without delivery timestamp).
   - "FAILED": The document text is unreadable or corrupted.
4. Output ONLY a valid JSON object matching the requested schema. Do not enclose in markdown ticks if json_mode is active."""

        extracted_text = evidence_dict.get("extracted_text") or evidence_dict.get("raw_content") or ""
        # Truncate text if excessively long to prevent context overflow while keeping relevant facts
        if len(extracted_text) > 8000:
            extracted_text = extracted_text[:8000] + "\n...[Content truncated for analysis]..."

        payload = {
            "dispute_context": {
                "dispute_id": dispute_context.get("dispute_id"),
                "reason_code": dispute_context.get("reason_code"),
                "reason_description": dispute_context.get("reason_description", ""),
                "phase": dispute_context.get("phase", "chargeback"),
                "workflow_stage": dispute_context.get("workflow_stage", "DISPUTE_RAISED"),
                "merchant_attention_state": dispute_context.get("merchant_attention_state", "ACTION_REQUIRED"),
                "transaction": {
                    "transaction_id": dispute_context.get("transaction_id"),
                    "amount": dispute_context.get("amount"),
                    "currency": dispute_context.get("currency", "USD"),
                    "timestamp": dispute_context.get("timestamp"),
                    "payment_method": dispute_context.get("payment_method"),
                    "customer_id": dispute_context.get("customer_id")
                },
                "order": dispute_context.get("order", {}),
                "fulfillment": dispute_context.get("fulfillment", {})
            },
            "evidence_item": {
                "evidence_id": evidence_dict.get("evidence_id"),
                "evidence_type": evidence_dict.get("evidence_type"),
                "title": evidence_dict.get("title"),
                "description": evidence_dict.get("description"),
                "source": evidence_dict.get("source"),
                "source_reference_id": evidence_dict.get("source_reference_id"),
                "mime_type": evidence_dict.get("mime_type"),
                "file_size_bytes": evidence_dict.get("file_size"),
                "structured_facts": evidence_dict.get("facts", {})
            },
            "extracted_evidence_content": extracted_text
        }

        user_content = f"""Please analyze this evidence document for dispute resolution and produce a rigorous verification assessment.

DATA FOR ANALYSIS:
{json.dumps(payload, indent=2)}

Generate a JSON object matching this schema:
{{
  "verification_status": "VERIFIED | REJECTED | NEEDS_REVIEW | FAILED",
  "confidence_score": 0.85,
  "authenticity_assessment": "1-2 sentences on document legitimacy, consistency of headers/stamps/formats",
  "relevance_assessment": "1-2 sentences on how directly this evidence refutes the customer's dispute claim",
  "completeness_assessment": "1-2 sentences on presence of mandatory identifiers (dates, amounts, customer name, courier tracking)",
  "key_findings": [
    "Key fact 1 extracted from document",
    "Key fact 2 extracted from document"
  ],
  "matched_dispute_facts": [
    "Fact matching transaction/order (e.g. Tracking number matches fulfillment BD12345678)"
  ],
  "contradictions": [
    "Any discrepancy detected between document and transaction/dispute (e.g. amount mismatch, wrong date), or empty list"
  ],
  "missing_information": [
    "Any missing proof elements needed for complete representment defense, or empty list"
  ],
  "risk_flags": [
    "Any risk signals (e.g. missing signature, altered date, mismatching name), or empty list"
  ],
  "recommendation": "Clear actionable recommendation for the merchant regarding this evidence",
  "reasoning_summary": "1-2 sentence executive summary of the verification outcome"
}}
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

