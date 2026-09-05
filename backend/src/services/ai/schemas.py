"""
Pydantic Schemas for DeepSeek AI Language Layer.
Ensures strictly validated, structured AI outputs before exposing to application layers or frontend.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceGapExplanation(BaseModel):
    """Granular merchant-friendly explanation for an evidence requirement."""
    evidence_type: str = Field(..., description="Evidence type identifier, e.g. delivery_confirmation")
    title: str = Field(..., description="Human-readable title, e.g. Delivery Confirmation")
    status: str = Field(..., description="AVAILABLE, MISSING, UNVERIFIED, or INVALID")
    why_it_matters: str = Field(..., description="Merchant-friendly explanation of why this proof is needed")
    supports_claim: str = Field(..., description="Which dispute claim this evidence supports or refutes")
    is_sufficient: bool = Field(default=False, description="Whether the current evidence is sufficient for this type")
    suggested_action: str = Field(..., description="Clear actionable next step for the merchant")
    urgency: str = Field(default="MEDIUM", description="Urgency: HIGH, MEDIUM, or LOW")


class MerchantDisputeExplanation(BaseModel):
    """Plain-English dispute explanation and recommendation reasoning for merchants."""
    dispute_id: str = Field(..., description="Dispute identifier")
    summary: str = Field(..., description="Concise case summary")
    plain_english_explanation: str = Field(..., description="Merchant-friendly dispute explanation converting technical metrics to simple terms")
    recommendation: str = Field(..., description="Merchant outcome: 'Challenge this dispute', 'Accept this dispute', or 'Review further'")
    recommendation_code: str = Field(..., description="Underlying decision code: CONTEST, ACCEPT, or INVESTIGATE")
    recommendation_reasoning: List[str] = Field(default_factory=list, description="Reasoning points grounded in backend facts")
    merchant_action: str = Field(..., description="Primary action the merchant should take")
    confidence_language: str = Field(..., description="Simple confidence phrasing, e.g., 'High confidence based on complete fulfillment records'")
    missing_evidence_summary: Optional[str] = Field(default=None, description="Summary of any missing evidence items")

    @property
    def plain_language_explanation(self) -> str:
        return self.plain_english_explanation



class EvidenceCitationSchema(BaseModel):
    """Citation linking a factual rebuttal claim to verified backend evidence."""
    claim: str = Field(..., description="Factual claim made in defense response")
    evidence_refs: List[str] = Field(default_factory=list, description="Referenced evidence types supporting this claim")


class StructuredAIResponse(BaseModel):
    """Complete validated AI structured response for dispute rebuttal and defense."""
    title: str = Field(..., description="Response document title")
    summary: str = Field(..., description="Brief executive summary")
    merchant_position: str = Field(..., description="CONTEST, PARTIAL_CONTEST, or INSUFFICIENT_EVIDENCE")
    merchant_recommendation: str = Field(default="Challenge this dispute", description="Guardrail outcome: 'Challenge this dispute', 'Accept this dispute', or 'Review further'")
    response_text: str = Field(..., description="Full merchant defense statement / rebuttal draft")
    response_draft: str = Field(default="", description="Draft rebuttal text ready for merchant review")
    key_facts: List[str] = Field(default_factory=list, description="Bullet points of verified facts")
    reasoning: List[str] = Field(default_factory=list, description="Reasoning bullets explaining the defense strategy")
    supporting_evidence: List[str] = Field(default_factory=list, description="List of available evidence types cited")
    missing_evidence: List[str] = Field(default_factory=list, description="List of missing evidence types")
    evidence_explanations: List[EvidenceGapExplanation] = Field(default_factory=list, description="Granular explanations for evidence items")
    limitations: List[str] = Field(default_factory=list, description="Missing or unverified evidence limitations")
    evidence_citations: List[EvidenceCitationSchema] = Field(default_factory=list, description="Traceable claim to evidence mappings")
    confidence_language: str = Field(default="Moderate confidence", description="Simple confidence statement")
    merchant_action: str = Field(default="Review defense statement and submit package", description="Suggested merchant action")
    generated_at: str
    generator_version: str = Field(default="deepseek_v1")
    is_fallback: bool = Field(default=False, description="True if generated via deterministic fallback")


class AIGenerationMetadata(BaseModel):
    """Metadata recorded in audit trails for AI generation requests."""
    provider: str = Field(default="deepseek")
    model: str = Field(default="deepseek-chat")
    generation_type: str = Field(..., description="case_explanation, evidence_guidance, response_generation, evidence_analysis")
    timestamp: str
    success: bool
    is_fallback: bool
    latency_ms: Optional[float] = None
    cached: bool = False


class EvidenceAnalysisResultSchema(BaseModel):
    """Structured DeepSeek AI Verification and Analysis Result for Evidence."""
    evidence_id: str = Field(..., description="Target evidence item ID")
    dispute_id: str = Field(..., description="Target dispute ID")
    evidence_type: str = Field(..., description="Type of evidence evaluated")
    verification_status: str = Field(..., description="VERIFIED, REJECTED, NEEDS_REVIEW, or FAILED")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    authenticity_assessment: str = Field(default="", description="Evaluation of document legitimacy and format integrity")
    relevance_assessment: str = Field(default="", description="Evaluation of how directly this evidence addresses the dispute reason")
    completeness_assessment: str = Field(default="", description="Evaluation of required elements presence (dates, amounts, signatures, identifiers)")
    key_findings: List[str] = Field(default_factory=list, description="List of key facts extracted from the document")
    matched_dispute_facts: List[str] = Field(default_factory=list, description="Facts in the evidence that corroborate transaction/order details")
    contradictions: List[str] = Field(default_factory=list, description="Discrepancies between evidence and dispute/transaction claims")
    missing_information: List[str] = Field(default_factory=list, description="Missing details needed to make evidence irrefutable")
    risk_flags: List[str] = Field(default_factory=list, description="Identified risk markers or potential issues")
    recommendation: str = Field(default="Review further", description="Merchant action recommendation based on this evidence")
    reasoning_summary: str = Field(default="", description="Clear summary explaining the AI verification outcome")
    analyzed_at: str = Field(default="", description="ISO timestamp of analysis")
    model_used: str = Field(default="deepseek-chat", description="Model identifier used for analysis")
    latency_ms: Optional[float] = Field(default=None, description="Inference latency in milliseconds")
    is_fallback: bool = Field(default=False, description="True if generated via fallback mechanism")
    error: Optional[str] = Field(default=None, description="Error message if analysis failed")

