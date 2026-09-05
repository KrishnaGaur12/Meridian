"""
Evidence Rules Engine — Defines deterministic required evidence items for dispute reason codes.
"""

from typing import List, Dict
from src.evidence.requirements import EvidenceRequirementService

EVIDENCE_RULES: Dict[str, List[str]] = {
    k: v["required"] for k, v in EvidenceRequirementService.REQUIREMENTS.items()
}

REASON_ALIASES: Dict[str, str] = EvidenceRequirementService.REASON_ALIASES

def get_required_evidence_types(reason_code: str) -> List[str]:
    """Returns required evidence types for a given dispute reason code."""
    return EvidenceRequirementService.get_required_types(reason_code)

def get_optional_evidence_types(reason_code: str) -> List[str]:
    """Returns optional evidence types for a given dispute reason code."""
    return EvidenceRequirementService.get_optional_types(reason_code)
