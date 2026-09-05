"""
Razorpay-inspired identifier generation utility.
Generates unique, collision-safe, unpredictable identifiers with standard entity prefixes.
"""

import secrets
import string

ALPHANUMERIC = string.ascii_letters + string.digits

def generate_prefixed_id(prefix: str, length: int = 14) -> str:
    """
    Generates a secure random identifier with the specified prefix.
    Example: generate_prefixed_id('txn') -> 'txn_8aK9pL2xM4v1wQ'
    """
    random_str = ''.join(secrets.choice(ALPHANUMERIC) for _ in range(length))
    return f"{prefix}_{random_str}"

def generate_transaction_id() -> str:
    return generate_prefixed_id("txn", 14)

def generate_customer_id() -> str:
    return generate_prefixed_id("cust", 14)

def generate_payment_id() -> str:
    return generate_prefixed_id("pay", 14)

def generate_order_id() -> str:
    return generate_prefixed_id("order", 14)

def generate_fulfillment_id() -> str:
    return generate_prefixed_id("ful", 14)

def generate_dispute_id() -> str:
    return generate_prefixed_id("dispute", 14)

def generate_evidence_id() -> str:
    return generate_prefixed_id("evd", 14)

def generate_package_id() -> str:
    return generate_prefixed_id("pkg", 14)

def generate_event_id() -> str:
    return generate_prefixed_id("evt", 14)

def generate_reference_id() -> str:
    return generate_prefixed_id("ref", 16)
