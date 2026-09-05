"""
Evidence Requirement Service — Razorpay AI Risk Manager.
Defines required and optional evidence types for every dispute reason category according to card network regulations.
"""

from typing import List, Dict, Any, Optional

class EvidenceRequirementService:
    """Service to query deterministic evidence requirements per dispute reason."""

    REQUIREMENTS: Dict[str, Dict[str, Any]] = {
        "product_not_received": {
            "category": "PRODUCT_NOT_RECEIVED",
            "required": [
                "payment_confirmation",
                "shipping_confirmation",
                "delivery_confirmation",
                "customer_history"
            ],
            "optional": [
                "invoice",
                "customer_communication"
            ],
            "description": "Proof that product was ordered, paid for, shipped, and delivered to cardholder."
        },
        "fraudulent_transaction": {
            "category": "UNAUTHORIZED_OR_FRAUDULENT",
            "required": [
                "payment_confirmation",
                "authentication",
                "customer_history"
            ],
            "optional": [
                "three_ds_record",
                "avs_cvv_record",
                "device_fingerprint",
                "transaction_history"
            ],
            "description": "Proof of cardholder authorization, 3DS authentication, and AVS/CVV matching."
        },
        "duplicate_charge": {
            "category": "DUPLICATE_CHARGE",
            "required": [
                "payment_confirmation",
                "invoice",
                "transaction_history"
            ],
            "optional": [
                "duplicate_transaction_comparison",
                "customer_communication"
            ],
            "description": "Proof comparing transactions to substantiate legitimate distinct or single billing."
        },
        "refund_not_processed": {
            "category": "REFUND_NOT_PROCESSED",
            "required": [
                "payment_confirmation",
                "refund_record",
                "terms_of_service"
            ],
            "optional": [
                "refund_policy",
                "refund_transaction_status",
                "customer_communication"
            ],
            "description": "Proof of refund terms and execution/ineligibility of requested customer credit."
        },
        "product_unacceptable": {
            "category": "PRODUCT_UNACCEPTABLE",
            "required": [
                "payment_confirmation",
                "invoice",
                "delivery_confirmation"
            ],
            "optional": [
                "product_description",
                "refund_policy",
                "customer_communication"
            ],
            "description": "Proof that product delivered matched accurate listing description and return terms."
        },
        "product_not_as_described": {
            "category": "PRODUCT_NOT_AS_DESCRIBED",
            "required": [
                "payment_confirmation",
                "invoice",
                "delivery_confirmation",
                "product_description"
            ],
            "optional": [
                "refund_policy",
                "customer_communication"
            ],
            "description": "Proof that delivered goods adhered to published specifications and merchant terms."
        },
        "subscription_canceled": {
            "category": "SUBSCRIPTION_CANCELED",
            "required": [
                "payment_confirmation",
                "cancellation_record",
                "terms_of_service"
            ],
            "optional": [
                "usage_log",
                "customer_communication"
            ],
            "description": "Proof of active subscription agreement and cancellation timestamp records."
        },
        "credit_not_processed": {
            "category": "CREDIT_NOT_PROCESSED",
            "required": [
                "payment_confirmation",
                "refund_record",
                "terms_of_service"
            ],
            "optional": [
                "refund_policy",
                "refund_transaction_status",
                "customer_communication"
            ],
            "description": "Proof of cardholder credit processing status or policy governing reversals."
        },
        "digital_goods": {
            "category": "DIGITAL_GOODS",
            "required": [
                "payment_confirmation",
                "digital_delivery",
                "account_access",
                "usage_log"
            ],
            "optional": [
                "customer_history"
            ],
            "description": "Proof of digital content transmission, user login, and service utilization log."
        },
        "service_not_provided": {
            "category": "SERVICE_NOT_PROVIDED",
            "required": [
                "payment_confirmation",
                "service_order",
                "service_completion_record"
            ],
            "optional": [
                "customer_communication"
            ],
            "description": "Proof of service agreement and completed fulfillment or milestone sign-off."
        },
        "other": {
            "category": "OTHER",
            "required": [
                "payment_confirmation",
                "customer_history",
                "invoice"
            ],
            "optional": [
                "customer_communication"
            ],
            "description": "Standard baseline transaction, customer relationship, and billing documentation."
        }
    }

    REASON_ALIASES: Dict[str, str] = {
        "GOODS_NOT_RECEIVED": "product_not_received",
        "PRODUCT_NOT_RECEIVED": "product_not_received",
        "GOODS_NOT_AS_DESCRIBED": "product_not_as_described",
        "PRODUCT_NOT_AS_DESCRIBED": "product_not_as_described",
        "PRODUCT_UNACCEPTABLE": "product_unacceptable",
        "UNAUTHORIZED_TRANSACTION": "fraudulent_transaction",
        "UNAUTHORIZED": "fraudulent_transaction",
        "FRAUDULENT": "fraudulent_transaction",
        "FRAUD": "fraudulent_transaction",
        "DUPLICATE_TRANSACTION": "duplicate_charge",
        "DUPLICATE_CHARGE": "duplicate_charge",
        "REFUND_NOT_RECEIVED": "refund_not_processed",
        "REFUND_NOT_PROCESSED": "refund_not_processed",
        "CREDIT_NOT_PROCESSED": "credit_not_processed",
        "DIGITAL_GOODS": "digital_goods",
        "SERVICE_NOT_PROVIDED": "service_not_provided",
        "OTHER": "other"
    }

    @classmethod
    def normalize_reason(cls, reason_code: str) -> str:
        code_clean = str(reason_code or "").strip().upper()
        if code_clean in cls.REASON_ALIASES:
            return cls.REASON_ALIASES[code_clean]
        lower_clean = str(reason_code or "").strip().lower()
        if lower_clean in cls.REQUIREMENTS:
            return lower_clean
        if lower_clean.upper() in cls.REASON_ALIASES:
            return cls.REASON_ALIASES[lower_clean.upper()]
        return "other"

    @classmethod
    def get_requirements(cls, reason_code: str) -> Dict[str, Any]:
        normalized = cls.normalize_reason(reason_code)
        return cls.REQUIREMENTS.get(normalized, cls.REQUIREMENTS["other"])

    @classmethod
    def get_required_types(cls, reason_code: str) -> List[str]:
        req = cls.get_requirements(reason_code)
        return list(req.get("required", ["payment_confirmation", "customer_history"]))

    @classmethod
    def get_optional_types(cls, reason_code: str) -> List[str]:
        req = cls.get_requirements(reason_code)
        return list(req.get("optional", []))

    @classmethod
    def get_all_applicable_types(cls, reason_code: str) -> List[str]:
        req = cls.get_requirements(reason_code)
        return list(req.get("required", [])) + list(req.get("optional", []))
