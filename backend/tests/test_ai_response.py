"""
Unit tests for AI Response Generator, Anti-Hallucination rules, and Post-LLM Claim/Evidence Validator.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import (
    create_transaction, create_dispute, create_evidence, create_fulfillment
)
from src.response.service import ResponseGeneratorService
from src.response.validator import ClaimEvidenceValidator
from src.response.generator import MockResponseGenerator

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_ai_response_complete_evidence(db_session):
    tx_data = {
        "transaction_id": "TXN_RESP_100",
        "customer_id": "CUST_RESP_100",
        "amount": 299.99,
        "payment": {
            "auth_code": "AUTH_OK_100",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_RESP_100",
            "product_description": "Wireless Earbuds",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_RESP_100",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_RESP_100",
        "transaction_id": "TXN_RESP_100",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    service = ResponseGeneratorService()
    resp = service.generate_response_for_dispute(db_session, "DSP_RESP_100")

    assert resp.merchant_position == "CONTEST"
    assert len(resp.supporting_evidence) >= 3
    assert len(resp.evidence_citations) > 0
    assert "TRK_RESP_100" in resp.response_text or any("TRK_RESP_100" in fact for fact in resp.key_facts)

def test_ai_response_missing_evidence(db_session):
    # Transaction without fulfillment details -> shipping & delivery missing
    tx_data = {
        "transaction_id": "TXN_RESP_200",
        "customer_id": "CUST_RESP_200",
        "amount": 150.00
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_RESP_200",
        "transaction_id": "TXN_RESP_200",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    service = ResponseGeneratorService()
    resp = service.generate_response_for_dispute(db_session, "DSP_RESP_200")

    assert resp.merchant_position in ("PARTIAL_CONTEST", "INSUFFICIENT_EVIDENCE")
    assert len(resp.limitations) > 0
    assert any("shipping_confirmation" in lim or "delivery_confirmation" in lim for lim in resp.limitations)

def test_mandatory_anti_hallucination_rule(db_session):
    """
    MANDATORY ANTI-HALLUCINATION TEST:
    Verifies that when delivery date / tracking number is missing,
    the AI response DOES NOT fabricate a delivery timestamp or tracking number.
    """
    tx_data = {
        "transaction_id": "TXN_HALLUCINATION_TEST",
        "customer_id": "CUST_HALLUCINATION_TEST",
        "amount": 99.00,
        "order": {
            "order_id": "ORD_HALLUCINATION_TEST",
            "fulfillment": {
                "shipping_status": "PENDING",
                "tracking_number": None,  # Missing tracking number
                "shipped_at": None,       # Missing shipping timestamp
                "delivered_at": None,     # Missing delivery timestamp
                "delivery_status": "PENDING"
            }
        }
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_HALLUCINATION_TEST",
        "transaction_id": "TXN_HALLUCINATION_TEST",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    service = ResponseGeneratorService()
    resp = service.generate_response_for_dispute(db_session, "DSP_HALLUCINATION_TEST")

    # Assert MUST NOT contain fabricated delivery or tracking claims
    for citation in resp.evidence_citations:
        assert "delivery_confirmation" not in citation.evidence_refs or "delivered on" not in citation.claim.lower()

    # Position MUST NOT be CONTEST when shipping & delivery are missing
    assert resp.merchant_position != "CONTEST"
    assert len(resp.limitations) >= 2

def test_dispute_reason_coverage(db_session):
    reasons = [
        "product_not_received",
        "fraudulent_transaction",
        "duplicate_charge",
        "refund_not_processed",
        "product_not_as_described"
    ]
    service = ResponseGeneratorService()

    for idx, reason in enumerate(reasons):
        tx_id = f"TXN_REASON_{idx}"
        disp_id = f"DSP_REASON_{idx}"
        create_transaction(db_session, {"transaction_id": tx_id, "customer_id": "CUST_REASON", "amount": 100.0})
        create_dispute(db_session, {"dispute_id": disp_id, "transaction_id": tx_id, "reason_code": reason})

        resp = service.generate_response_for_dispute(db_session, disp_id)
        assert resp.title is not None
        assert resp.merchant_position in ("CONTEST", "PARTIAL_CONTEST", "INSUFFICIENT_EVIDENCE")
