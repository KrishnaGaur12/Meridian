"""
Pydantic Schemas for AI Response Generator.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EvidenceCitationSchema(BaseModel):
    claim: str = Field(..., description="Factual claim made in response")
    evidence_refs: List[str] = Field(default_factory=list, description="Referenced evidence types supporting this claim")

class AIResponseSchema(BaseModel):
    title: str = Field(..., description="Response document title")
    summary: str = Field(..., description="Brief executive summary")
    merchant_position: str = Field(..., description="CONTEST, PARTIAL_CONTEST, or INSUFFICIENT_EVIDENCE")
    response_text: str = Field(..., description="Full merchant defense statement")
    key_facts: List[str] = Field(default_factory=list, description="Bullet points of verified facts")
    supporting_evidence: List[str] = Field(default_factory=list, description="List of available evidence types cited")
    limitations: List[str] = Field(default_factory=list, description="Missing or unverified evidence limitations")
    evidence_citations: List[EvidenceCitationSchema] = Field(default_factory=list, description="Traceable claim to evidence mappings")
    generated_at: str
    generator_version: str = Field(default="response_v1")
