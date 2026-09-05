"""
Pydantic Schemas for Chargeback Package Generator.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.evidence.schemas import EvidenceItemSchema
from src.response.schemas import AIResponseSchema, EvidenceCitationSchema

class ChargebackPackageSchema(BaseModel):
    package_id: str = Field(..., description="Unique package ID e.g. PKG_DSP123")
    package_status: str = Field(..., description="READY_FOR_REVIEW, INCOMPLETE, or INSUFFICIENT_EVIDENCE")
    dispute: Dict[str, Any] = Field(..., description="Case and dispute information")
    transaction: Dict[str, Any] = Field(..., description="Transaction information")
    risk_assessment: Dict[str, Any] = Field(..., description="Risk assessment prediction results")
    evidence_summary: Dict[str, Any] = Field(..., description="Summary of evidence status counts")
    evidence: List[EvidenceItemSchema] = Field(default_factory=list, description="Verified evidence records")
    ai_response: AIResponseSchema = Field(..., description="Generated AI defense response")
    evidence_citations: List[EvidenceCitationSchema] = Field(default_factory=list, description="Claim to evidence mappings")
    generated_at: str
    package_version: str = Field(default="1.0")
