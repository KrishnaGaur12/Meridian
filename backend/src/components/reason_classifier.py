"""
Component 1 — Dispute Reason Classifier.
Determines and standardizes the dispute reason category using deterministic rules.
"""

from typing import Union, Dict, Any
from config.settings import DisputeReason

class ReasonClassifier:
    """Classifies dispute reason inputs into standard dispute codes."""
    
    # Mapping table of keywords to standardized dispute reason
    KEYWORD_MAPPINGS = {
        DisputeReason.GOODS_NOT_RECEIVED: [
            "goods_not_received", "not_received", "item_not_received", "never_arrived",
            "non_delivery", "delivery_failed", "undelivered", "missing_order"
        ],
        DisputeReason.GOODS_NOT_AS_DESCRIBED: [
            "goods_not_as_described", "not_as_described", "defective", "damaged",
            "wrong_item", "counterfeit", "poor_quality", "broken", "incorrect_product"
        ],
        DisputeReason.UNAUTHORIZED_TRANSACTION: [
            "unauthorized_transaction", "unauthorized", "fraud", "stolen_card",
            "fraudulent", "never_authorized", "unknown_charge", "account_takeover"
        ],
        DisputeReason.DUPLICATE_TRANSACTION: [
            "duplicate_transaction", "duplicate", "charged_twice", "double_charge",
            "multiple_billing", "repeated_charge"
        ],
        DisputeReason.REFUND_NOT_RECEIVED: [
            "refund_not_received", "refund_missing", "credit_not_processed",
            "promised_refund", "return_not_credited"
        ]
    }
    
    def classify(self, reason_input: Union[str, Dict[str, Any]]) -> DisputeReason:
        """
        Classifies input reason text or dictionary into a standardized DisputeReason enum.
        """
        if isinstance(reason_input, dict):
            raw_reason = str(reason_input.get("dispute_reason", reason_input.get("reason", "")))
        else:
            raw_reason = str(reason_input)
            
        clean_text = raw_reason.strip().lower().replace(" ", "_").replace("-", "_")
        
        # Check exact enum match first
        for enum_val in DisputeReason:
            if clean_text == enum_val.value.lower():
                return enum_val
                
        # Check keyword containment
        for enum_val, keywords in self.KEYWORD_MAPPINGS.items():
            for kw in keywords:
                if kw in clean_text:
                    return enum_val
                    
        return DisputeReason.OTHER
    
    def encode_reason(self, reason: DisputeReason) -> int:
        """Encodes standard enum reason into numeric ID for ML feature vectors."""
        reason_map = {
            DisputeReason.GOODS_NOT_RECEIVED: 0,
            DisputeReason.GOODS_NOT_AS_DESCRIBED: 1,
            DisputeReason.UNAUTHORIZED_TRANSACTION: 2,
            DisputeReason.DUPLICATE_TRANSACTION: 3,
            DisputeReason.REFUND_NOT_RECEIVED: 4,
            DisputeReason.OTHER: 5
        }
        return reason_map.get(reason, 5)
