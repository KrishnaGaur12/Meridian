"""
Comprehensive Regression Tests for Fulfillment Delivery Anti-Fabrication Fixes.
Verifies that missing or unverified delivery data is NEVER automatically converted
into fabricated delivery evidence or invalid CONTEST / READY_FOR_REVIEW decisions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import create_transaction, create_dispute, get_transaction
from src.evidence.engine import EvidenceEngine
from src.response.service import ResponseGeneratorService
from src.chargeback.service import ChargebackPackageService

PROHIBITED_DELIVERY_PHRASES = [
    "order was delivered",
    "delivery was confirmed",
    "confirmed delivery",
    "proof of delivery",
    "successfully delivered",
    "carrier confirmed delivery"
]

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_1_missing_delivery_data(db_session):
    """
    Test 1 — Missing delivery data:
    Input contains shipping_status and tracking_number, but NO delivery_status and NO delivered_at.
    """
    tx_payload = {
        "transaction_id": "TXN_NO_DELIV_01",
        "customer_id": "CUST_NO_DELIV_01",
        "amount": 199.99,
        "order": {
            "order_id": "ORD_NO_DELIV_01",
            "product_description": "Wireless Headphones",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_TEST_001"
                # Omitted delivery_status and delivered_at
            }
        }
    }
    tx = create_transaction(db_session, tx_payload)
    assert tx.order.fulfillment.delivery_status is None
    assert tx.order.fulfillment.delivered_at is None

    disp_payload = {
        "dispute_id": "DSP_NO_DELIV_01",
        "transaction_id": "TXN_NO_DELIV_01",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_payload)

    # 1. Evidence Engine Check
    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_NO_DELIV_01")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status != "AVAILABLE"

    # 2. AI Response Generator Check
    resp_service = ResponseGeneratorService()
    ai_resp = resp_service.generate_response_for_dispute(db_session, "DSP_NO_DELIV_01")
    assert ai_resp.merchant_position != "CONTEST"
    
    resp_text_lower = ai_resp.response_text.lower()
    for phrase in PROHIBITED_DELIVERY_PHRASES:
        assert phrase not in resp_text_lower, f"Prohibited phrase '{phrase}' found in response text when delivery is missing!"

    # 3. Chargeback Package Status Check
    pkg_service = ChargebackPackageService()
    chg_pkg = pkg_service.generate_and_save_package(db_session, "DSP_NO_DELIV_01")
    assert chg_pkg.package_status != "READY_FOR_REVIEW"
    assert chg_pkg.package_status in ("INCOMPLETE", "INSUFFICIENT_EVIDENCE")

def test_2_delivered_without_timestamp(db_session):
    """
    Test 2 — DELIVERED status without timestamp:
    delivery_status is 'DELIVERED' but delivered_at is None.
    """
    tx_payload = {
        "transaction_id": "TXN_NO_TS_02",
        "customer_id": "CUST_NO_TS_02",
        "amount": 150.00,
        "order": {
            "order_id": "ORD_NO_TS_02",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_NO_TS",
                "delivery_status": "DELIVERED",
                "delivered_at": None
            }
        }
    }
    create_transaction(db_session, tx_payload)
    create_dispute(db_session, {"dispute_id": "DSP_NO_TS_02", "transaction_id": "TXN_NO_TS_02", "reason_code": "product_not_received"})

    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_NO_TS_02")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status == "UNVERIFIED"

    resp_service = ResponseGeneratorService()
    ai_resp = resp_service.generate_response_for_dispute(db_session, "DSP_NO_TS_02")
    assert ai_resp.merchant_position != "CONTEST"

def test_3_explicit_confirmed_delivery(db_session):
    """
    Test 3 — Explicit confirmed delivery:
    delivery_status is 'DELIVERED' and valid delivered_at timestamp is present.
    """
    tx_payload = {
        "transaction_id": "TXN_CONFIRMED_03",
        "customer_id": "CUST_CONFIRMED_03",
        "amount": 250.00,
        "payment": {"auth_code": "AUTH_OK", "payment_status": "CAPTURED"},
        "order": {
            "order_id": "ORD_CONFIRMED_03",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_OK_999",
                "shipped_at": "2026-08-25T10:00:00Z",
                "delivery_status": "DELIVERED",
                "delivered_at": "2026-08-27T14:30:00Z"
            }
        }
    }
    create_transaction(db_session, tx_payload)
    create_dispute(db_session, {"dispute_id": "DSP_CONFIRMED_03", "transaction_id": "TXN_CONFIRMED_03", "reason_code": "product_not_received"})

    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_CONFIRMED_03")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status == "AVAILABLE"

    resp_service = ResponseGeneratorService()
    ai_resp = resp_service.generate_response_for_dispute(db_session, "DSP_CONFIRMED_03")
    assert ai_resp.merchant_position == "CONTEST"

def test_4_shipped_order(db_session):
    """
    Test 4 — SHIPPED order:
    delivery_status is 'SHIPPED', delivered_at is None.
    """
    tx_payload = {
        "transaction_id": "TXN_SHIPPED_04",
        "customer_id": "CUST_SHIPPED_04",
        "amount": 80.00,
        "order": {
            "order_id": "ORD_SHIPPED_04",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_SHIP_04",
                "shipped_at": "2026-08-28T09:00:00Z",
                "delivery_status": "SHIPPED",
                "delivered_at": None
            }
        }
    }
    create_transaction(db_session, tx_payload)
    create_dispute(db_session, {"dispute_id": "DSP_SHIPPED_04", "transaction_id": "TXN_SHIPPED_04", "reason_code": "product_not_received"})

    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_SHIPPED_04")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status != "AVAILABLE"

def test_5_failed_delivery(db_session):
    """
    Test 5 — FAILED delivery:
    delivery_status is 'FAILED'.
    """
    tx_payload = {
        "transaction_id": "TXN_FAILED_05",
        "customer_id": "CUST_FAILED_05",
        "amount": 110.00,
        "order": {
            "order_id": "ORD_FAILED_05",
            "fulfillment": {
                "delivery_status": "FAILED"
            }
        }
    }
    create_transaction(db_session, tx_payload)
    create_dispute(db_session, {"dispute_id": "DSP_FAILED_05", "transaction_id": "TXN_FAILED_05", "reason_code": "product_not_received"})

    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_FAILED_05")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status == "INVALID"

def test_6_returned_delivery(db_session):
    """
    Test 6 — RETURNED delivery:
    delivery_status is 'RETURNED'.
    """
    tx_payload = {
        "transaction_id": "TXN_RETURNED_06",
        "customer_id": "CUST_RETURNED_06",
        "amount": 125.00,
        "order": {
            "order_id": "ORD_RETURNED_06",
            "fulfillment": {
                "delivery_status": "RETURNED"
            }
        }
    }
    create_transaction(db_session, tx_payload)
    create_dispute(db_session, {"dispute_id": "DSP_RETURNED_06", "transaction_id": "TXN_RETURNED_06", "reason_code": "product_not_received"})

    engine = EvidenceEngine()
    pkg = engine.evaluate_dispute_evidence(db_session, "DSP_RETURNED_06")
    deliv_item = next(i for i in pkg.evidence if i.evidence_type == "delivery_confirmation")
    assert deliv_item.status == "INVALID"
