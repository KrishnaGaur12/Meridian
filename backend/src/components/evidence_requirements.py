"""
Component 2 — Evidence Requirement Engine.
Maps standardized dispute reason codes to mandatory and optional evidence requirements.
"""

from typing import Dict, List, TypedDict
from config.settings import DisputeReason

class EvidenceRequirement(TypedDict):
    required: List[str]
    optional: List[str]

class EvidenceRequirementEngine:
    """Knowledge engine for retrieving required & optional evidence types."""
    
    REQUIREMENT_MAP: Dict[DisputeReason, EvidenceRequirement] = {
        DisputeReason.GOODS_NOT_RECEIVED: {
            "required": ["invoice", "shipping_proof", "proof_of_delivery"],
            "optional": ["customer_communication", "terms_of_service", "tracking_history"]
        },
        DisputeReason.GOODS_NOT_AS_DESCRIBED: {
            "required": ["invoice", "product_description", "customer_communication"],
            "optional": ["return_policy", "quality_inspection_certificate", "refund_policy"]
        },
        DisputeReason.UNAUTHORIZED_TRANSACTION: {
            "required": ["invoice", "ip_address_log", "proof_of_delivery"],
            "optional": ["2fa_verification_log", "customer_communication", "device_fingerprint"]
        },
        DisputeReason.DUPLICATE_TRANSACTION: {
            "required": ["invoice", "transaction_receipt"],
            "optional": ["cancellation_policy", "settlement_batch_log"]
        },
        DisputeReason.REFUND_NOT_RECEIVED: {
            "required": ["refund_receipt", "transaction_receipt", "cancellation_confirmation"],
            "optional": ["customer_communication", "bank_arn_number"]
        },
        DisputeReason.OTHER: {
            "required": ["invoice", "transaction_receipt"],
            "optional": ["customer_communication", "merchant_policy"]
        }
    }
    
    def get_requirements(self, reason: DisputeReason) -> EvidenceRequirement:
        """Returns required and optional evidence lists for the specified reason."""
        return self.REQUIREMENT_MAP.get(
            reason,
            self.REQUIREMENT_MAP[DisputeReason.OTHER]
        )
