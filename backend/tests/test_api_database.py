"""
Unit tests for Database Models & Repository functions.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import (
    create_customer, get_customer,
    create_transaction, get_transaction,
    create_payment, get_payments_for_transaction,
    create_order, create_fulfillment,
    create_dispute, get_dispute,
    create_evidence, get_evidence_by_dispute,
    create_risk_assessment, get_latest_risk_assessment
)

@pytest.fixture
def db_session():
    """In-memory SQLite session fixture for isolated database testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_customer_crud(db_session):
    cust_data = {
        "customer_id": "CUST_TEST_101",
        "account_age_days": 365,
        "verification_status": "VERIFIED",
        "country": "US",
        "previous_chargebacks": 0,
        "avg_transaction_amount_30d": 150.0
    }
    cust = create_customer(db_session, cust_data)
    assert cust.customer_id == "CUST_TEST_101"

    retrieved = get_customer(db_session, "CUST_TEST_101")
    assert retrieved is not None
    assert retrieved.account_age_days == 365

def test_transaction_and_payment_crud(db_session):
    tx_data = {
        "transaction_id": "TXN_TEST_202",
        "customer_id": "CUST_TEST_101",
        "amount": 250.0,
        "currency": "USD",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "US",
        "transaction_hour": 14,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "payment": {
            "payment_id": "PAY_TEST_202",
            "card_network": "visa",
            "last4": "1111",
            "auth_code": "AUTH9999"
        }
    }
    tx = create_transaction(db_session, tx_data)
    assert tx.transaction_id == "TXN_TEST_202"
    assert tx.amount == 250.0

    retrieved = get_transaction(db_session, "TXN_TEST_202")
    assert retrieved is not None
    assert len(retrieved.payments) == 1
    assert retrieved.payments[0].auth_code == "AUTH9999"

def test_dispute_and_evidence_crud(db_session):
    # Setup prerequisite transaction
    tx_data = {
        "transaction_id": "TXN_TEST_303",
        "customer_id": "CUST_TEST_303",
        "amount": 499.0
    }
    create_transaction(db_session, tx_data)

    # Create dispute
    disp_data = {
        "dispute_id": "DSP_TEST_303",
        "transaction_id": "TXN_TEST_303",
        "reason_code": "product_not_received",
        "reason_description": "Customer claims item not delivered"
    }
    dispute = create_dispute(db_session, disp_data)
    assert dispute.dispute_id == "DSP_TEST_303"

    # Create evidence
    evd_data = {
        "evidence_id": "EVD_TEST_303",
        "dispute_id": "DSP_TEST_303",
        "transaction_id": "TXN_TEST_303",
        "evidence_type": "delivery_confirmation",
        "verification_status": "AVAILABLE",
        "evidence_data": {"tracking_number": "TRACK123"}
    }
    evidence = create_evidence(db_session, evd_data)
    assert evidence.evidence_id == "EVD_TEST_303"

    retrieved_evd = get_evidence_by_dispute(db_session, "DSP_TEST_303")
    assert len(retrieved_evd) == 1
    assert retrieved_evd[0].evidence_data["tracking_number"] == "TRACK123"

def test_risk_assessment_crud(db_session):
    tx_data = {"transaction_id": "TXN_TEST_404", "customer_id": "CUST_404", "amount": 100.0}
    create_transaction(db_session, tx_data)

    asm_data = {
        "assessment_id": "ASM_TEST_404",
        "transaction_id": "TXN_TEST_404",
        "risk_score": 0.12,
        "risk_level": "LOW",
        "decision": "ALLOW",
        "model_version": "fraud-model-v2"
    }
    asm = create_risk_assessment(db_session, asm_data)
    assert asm.assessment_id == "ASM_TEST_404"

    latest = get_latest_risk_assessment(db_session, "TXN_TEST_404")
    assert latest is not None
    assert latest.risk_score == 0.12
    assert latest.decision == "ALLOW"
