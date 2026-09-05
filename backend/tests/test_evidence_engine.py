"""
Unit tests for Evidence Engine & Evidence Rules.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import (
    create_transaction, create_dispute, create_evidence, create_fulfillment
)
from src.evidence.engine import EvidenceEngine
from src.evidence.rules import get_required_evidence_types

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_evidence_rules_mapping():
    assert "shipping_confirmation" in get_required_evidence_types("product_not_received")
    assert "authentication" in get_required_evidence_types("fraudulent_transaction")
    assert "invoice" in get_required_evidence_types("duplicate_charge")
    assert "refund_record" in get_required_evidence_types("refund_not_processed")
    # Fallback for unknown reason
    assert len(get_required_evidence_types("unknown_reason_123")) >= 1

def test_evidence_engine_product_not_received_available(db_session):
    tx_data = {
        "transaction_id": "TXN_EV_01",
        "customer_id": "CUST_EV_01",
        "amount": 199.99,
        "payment": {
            "auth_code": "AUTH_777",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_EV_01",
            "product_description": "Wireless Headphones",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRACK_12345",
                "shipped_at": "2026-08-25T10:00:00Z",
                "delivered_at": "2026-08-27T15:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_EV_01",
        "transaction_id": "TXN_EV_01",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    engine = EvidenceEngine()
    package = engine.evaluate_dispute_evidence(db_session, "DSP_EV_01")

    assert package.dispute_id == "DSP_EV_01"
    assert package.reason == "product_not_received"
    assert package.available_count >= 3
    assert package.missing_count == 0

    # Verify delivery_confirmation item details
    delivery_item = next(item for item in package.evidence if item.evidence_type == "delivery_confirmation")
    assert delivery_item.status == "AVAILABLE"
    assert delivery_item.source == "DATABASE:fulfillments"
    assert delivery_item.data["delivery_status"] == "DELIVERED"

def test_evidence_engine_unverified_status(db_session):
    # Order shipped & delivered, but NO delivered_at timestamp -> UNVERIFIED delivery
    tx_data = {
        "transaction_id": "TXN_EV_02",
        "customer_id": "CUST_EV_02",
        "amount": 89.99,
        "order": {
            "order_id": "ORD_EV_02",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRACK_555",
                "shipped_at": "2026-08-25T10:00:00Z",
                "delivered_at": None,  # Missing timestamp
                "delivery_status": "DELIVERED"
            }
        }
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_EV_02",
        "transaction_id": "TXN_EV_02",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    engine = EvidenceEngine()
    package = engine.evaluate_dispute_evidence(db_session, "DSP_EV_02")

    delivery_item = next(item for item in package.evidence if item.evidence_type == "delivery_confirmation")
    assert delivery_item.status == "UNVERIFIED"

def test_evidence_engine_missing_evidence(db_session):
    # Transaction without order/fulfillment -> missing shipping & delivery proof
    tx_data = {
        "transaction_id": "TXN_EV_03",
        "customer_id": "CUST_EV_03",
        "amount": 50.0
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_EV_03",
        "transaction_id": "TXN_EV_03",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    engine = EvidenceEngine()
    package = engine.evaluate_dispute_evidence(db_session, "DSP_EV_03")

    assert package.missing_count >= 2
    shipping_item = next(item for item in package.evidence if item.evidence_type == "shipping_confirmation")
    assert shipping_item.status == "MISSING"

def test_evidence_engine_nonexistent_dispute_raises_error(db_session):
    engine = EvidenceEngine()
    with pytest.raises(ValueError, match="not found"):
        engine.evaluate_dispute_evidence(db_session, "DSP_NONEXISTENT")
