"""
Pydantic Schemas for Evidence Engine Output.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class EvidenceItemSchema(BaseModel):
    evidence_id: Optional[str] = None
    evidence_type: str = Field(..., description="Type of evidence e.g. payment_confirmation, delivery_confirmation")
    status: str = Field(..., description="AVAILABLE, VERIFIED, MISSING, UNVERIFIED, or INVALID")
    verification_status: Optional[str] = Field(default="UNVERIFIED", description="UNVERIFIED, VERIFIED, INVALID, UNREADABLE, REJECTED, NEEDS_REVIEW, FAILED")
    approval_status: Optional[str] = Field(default="PENDING_APPROVAL", description="PENDING_APPROVAL, APPROVED, REJECTED")
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = Field(default="DATABASE", description="Database source entity/table provenance")
    source_reference_id: Optional[str] = None
    verification_details: Optional[str] = None
    data: Optional[Dict[str, Any]] = Field(default=None, description="Actual supporting data retrieved from DB")
    ai_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Persisted DeepSeek AI verification result")
    ai_analysis_status: Optional[str] = Field(default="PENDING", description="PENDING, ANALYZING, VERIFIED, REJECTED, NEEDS_REVIEW, FAILED")
    ai_analyzed_at: Optional[str] = None
    ai_error: Optional[str] = None
    created_at: Optional[str] = None

class EvidencePackageSchema(BaseModel):
    dispute_id: str
    transaction_id: str
    reason: str
    evidence_count: int
    available_count: int
    missing_count: int
    unverified_count: int
    invalid_count: int
    evidence: List[EvidenceItemSchema]

class EvidenceDetailSchema(BaseModel):
    evidence_id: str
    dispute_id: str
    transaction_id: str
    evidence_type: str
    title: str
    description: str
    verification_status: str
    approval_status: str
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    source: str
    source_reference_id: Optional[str] = None
    extracted_text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    ai_analysis_status: Optional[str] = None
    ai_analyzed_at: Optional[str] = None
    ai_error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class EvidenceApprovalResponseSchema(BaseModel):
    success: bool = True
    message: str
    evidence: EvidenceDetailSchema
    dispute: Dict[str, Any]
    ml_assessment: Dict[str, Any]
    ai_analysis: Dict[str, Any]
    impact_delta: Optional[Dict[str, Any]] = None
