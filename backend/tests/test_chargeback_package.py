"""
Unit tests for Chargeback Package Generator and Database Persistence.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import (
    create_transaction, create_dispute, get_chargeback_package_by_dispute
)
from src.chargeback.service import ChargebackPackageService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_generate_complete_chargeback_package(db_session):
    tx_data = {
        "transaction_id": "TXN_PKG_100",
        "customer_id": "CUST_PKG_100",
        "amount": 450.00,
        "payment": {
            "auth_code": "AUTH_PKG_100",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_PKG_100",
            "product_description": "Mechanical Gaming Keyboard",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_PKG_100",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_PKG_100",
        "transaction_id": "TXN_PKG_100",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    service = ChargebackPackageService()
    pkg = service.generate_and_save_package(db_session, "DSP_PKG_100")

    assert pkg.package_id == "PKG_DSP_PKG_100"
    assert pkg.package_status == "READY_FOR_REVIEW"
    assert pkg.ai_response.merchant_position == "CONTEST"
    assert pkg.evidence_summary["available"] >= 3

    # Verify DB persistence
    saved_pkg = get_chargeback_package_by_dispute(db_session, "DSP_PKG_100")
    assert saved_pkg is not None
    assert saved_pkg.package_status == "READY_FOR_REVIEW"
    assert saved_pkg.merchant_position == "CONTEST"
    assert "package_id" in saved_pkg.package_data

def test_generate_incomplete_chargeback_package(db_session):
    tx_data = {
        "transaction_id": "TXN_PKG_200",
        "customer_id": "CUST_PKG_200",
        "amount": 120.00
    }
    create_transaction(db_session, tx_data)

    disp_data = {
        "dispute_id": "DSP_PKG_200",
        "transaction_id": "TXN_PKG_200",
        "reason_code": "product_not_received"
    }
    create_dispute(db_session, disp_data)

    service = ChargebackPackageService()
    pkg = service.generate_and_save_package(db_session, "DSP_PKG_200")

    assert pkg.package_status in ("INCOMPLETE", "INSUFFICIENT_EVIDENCE")
    assert pkg.evidence_summary["missing"] > 0
