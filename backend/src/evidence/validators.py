"""
Evidence Verification & Validation Engine.
Assigns verification status: AVAILABLE, UNVERIFIED, INVALID, or MISSING.
Never fabricates data; extracts proof from DB entities & explicit Evidence table records.
"""

from typing import Dict, Any, Tuple, Optional
from src.database.models import Dispute, Transaction, Customer, Payment, Order, Fulfillment, Evidence

def verify_payment_confirmation(tx: Optional[Transaction], payment: Optional[Payment]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies payment confirmation evidence."""
    if not tx and not payment:
        return "MISSING", "No payment or transaction record found in database.", {}
    
    pay_status = payment.payment_status if payment else tx.transaction_status
    amount = tx.amount if tx else 0.0
    
    if amount <= 0:
        return "INVALID", "Transaction amount is less than or equal to zero.", {"amount": amount}

    data = {
        "transaction_id": tx.transaction_id if tx else None,
        "payment_id": payment.payment_id if payment else None,
        "amount": amount,
        "currency": tx.currency if tx else "USD",
        "payment_method": payment.payment_method if payment else (tx.payment_method if tx else None),
        "card_network": payment.card_network if payment else None,
        "last4": payment.last4 if payment else None,
        "auth_code": payment.auth_code if payment else None,
        "payment_status": pay_status,
        "timestamp": tx.timestamp if tx else None
    }

    if pay_status in ("CAPTURED", "SUCCESS"):
        return "AVAILABLE", "Payment captured successfully with valid authorization.", data
    elif pay_status in ("AUTHORIZED", "PENDING"):
        return "UNVERIFIED", "Payment authorized but not yet fully captured.", data
    else:
        return "INVALID", f"Payment status '{pay_status}' is invalid or failed.", data

def verify_shipping_confirmation(order: Optional[Order], fulfillment: Optional[Fulfillment]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies shipping confirmation evidence."""
    if not fulfillment:
        return "MISSING", "No fulfillment or shipping record found in database.", {}
    
    data = {
        "order_id": order.order_id if order else None,
        "fulfillment_id": fulfillment.fulfillment_id,
        "shipping_status": fulfillment.shipping_status,
        "tracking_number": fulfillment.tracking_number,
        "shipped_at": fulfillment.shipped_at
    }

    if fulfillment.shipped_at and fulfillment.tracking_number:
        return "AVAILABLE", "Shipping confirmed with valid tracking number and timestamp.", data
    elif fulfillment.tracking_number and not fulfillment.shipped_at:
        return "UNVERIFIED", "Tracking number exists but shipping timestamp is missing.", data
    else:
        return "INVALID", "Shipping record incomplete or tracking invalid.", data

def verify_delivery_confirmation(fulfillment: Optional[Fulfillment]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies delivery confirmation evidence strictly without inferring delivery from shipping."""
    if not fulfillment:
        return "MISSING", "No fulfillment record found in database.", {}

    data = {
        "fulfillment_id": fulfillment.fulfillment_id,
        "delivery_status": fulfillment.delivery_status,
        "tracking_number": fulfillment.tracking_number,
        "delivered_at": fulfillment.delivered_at
    }

    if fulfillment.delivery_status == "DELIVERED" and fulfillment.delivered_at:
        return "AVAILABLE", "Order delivery confirmed with proof of delivery timestamp.", data
    elif fulfillment.delivery_status == "DELIVERED" and not fulfillment.delivered_at:
        return "UNVERIFIED", "Delivery status marked DELIVERED but delivery timestamp is missing.", data
    elif fulfillment.delivery_status in ("FAILED", "RETURNED"):
        return "INVALID", f"Delivery status is '{fulfillment.delivery_status}'.", data
    elif not fulfillment.delivery_status and not fulfillment.delivered_at:
        return "UNVERIFIED" if fulfillment.shipping_status == "SHIPPED" else "MISSING", "Delivery status and timestamp are omitted.", data
    else:
        return "UNVERIFIED", f"Delivery status is currently '{fulfillment.delivery_status}'.", data

def verify_customer_history(customer: Optional[Customer], tx: Optional[Transaction]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies customer history & profile evidence."""
    if not customer:
        return "MISSING", "No customer profile record found in database.", {}

    data = {
        "customer_id": customer.customer_id,
        "account_age_days": customer.account_age_days,
        "verification_status": customer.verification_status,
        "country": customer.country,
        "previous_chargebacks": customer.previous_chargebacks,
        "avg_transaction_amount_30d": customer.avg_transaction_amount_30d
    }

    if customer.verification_status == "VERIFIED" and customer.account_age_days >= 0:
        return "AVAILABLE", "Verified customer profile with historical transaction history.", data
    elif customer.verification_status != "VERIFIED":
        return "UNVERIFIED", f"Customer account verification status is '{customer.verification_status}'.", data
    else:
        return "INVALID", "Customer account age or profile parameters invalid.", data

def verify_authentication(payment: Optional[Payment], tx: Optional[Transaction]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies 3DS / AVS / CVV authentication evidence."""
    if not payment and not tx:
        return "MISSING", "No payment authentication record found in database.", {}

    avs = payment.avs_match if payment else "N"
    cvv = payment.cvv_match if payment else "N"
    auth_code = payment.auth_code if payment else "NONE"

    data = {
        "avs_match": avs,
        "cvv_match": cvv,
        "auth_code": auth_code,
        "is_international": tx.is_international if tx else 0,
        "device_type": tx.device_type if tx else "unknown"
    }

    if avs == "Y" and cvv == "Y":
        return "AVAILABLE", "Full AVS and CVV security match confirmed.", data
    elif avs in ("Y", "PARTIAL") or cvv == "Y":
        return "UNVERIFIED", f"Partial security match (AVS: {avs}, CVV: {cvv}).", data
    else:
        return "UNVERIFIED", f"Authentication unverified or match failed (AVS: {avs}, CVV: {cvv}).", data

def verify_invoice(order: Optional[Order], tx: Optional[Transaction]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies order invoice evidence."""
    if not order:
        return "MISSING", "No order invoice found in database.", {}

    data = {
        "order_id": order.order_id,
        "product_description": order.product_description,
        "order_amount": order.order_amount,
        "order_status": order.order_status,
        "created_at": order.created_at
    }

    if order.order_amount > 0 and order.product_description:
        return "AVAILABLE", "Valid order invoice present in database.", data
    elif not order.product_description:
        return "UNVERIFIED", "Order invoice found but product description is blank.", data
    else:
        return "INVALID", "Order invoice amount is non-positive.", data

def verify_transaction_history(customer: Optional[Customer], tx: Optional[Transaction]) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies transaction history evidence."""
    if not tx or not customer:
        return "MISSING", "No transaction history available in database.", {}

    data = {
        "customer_id": customer.customer_id,
        "transaction_velocity_1h": tx.transaction_velocity_1h,
        "transaction_velocity_24h": tx.transaction_velocity_24h,
        "previous_chargebacks": customer.previous_chargebacks,
        "avg_transaction_amount_30d": customer.avg_transaction_amount_30d
    }
    return "AVAILABLE", "Customer transaction velocity and dispute history retrieved.", data

def verify_generic_evidence_record(evidence_records: list, ev_type: str) -> Tuple[str, str, Dict[str, Any]]:
    """Verifies explicit Evidence table records for types like refund_record, communication_record."""
    matching = [e for e in evidence_records if e.evidence_type == ev_type]
    if not matching:
        return "MISSING", f"No record for '{ev_type}' found in database.", {}
    
    ev_item = matching[0]
    status = ev_item.verification_status or "AVAILABLE"
    return status, ev_item.description or f"Retrieved {ev_type} record.", ev_item.evidence_data
