"""
Complete End-to-End Integration Test for Full AI Chargeback System.
Verifies full flow: Transaction -> ML Engine -> Risk Engine -> Dispute -> Evidence Engine -> AI Response Generator -> Claim/Evidence Validator -> Chargeback Package Generator -> Persistence.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.database.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_full_end_to_end_ai_chargeback_package_pipeline():
    """
    Complete end-to-end integration test.
    """
    # 1. POST /transactions (Transaction + Customer + Payment + Order + Fulfillment)
    txn_payload = {
        "transaction_id": "TXN_E2E_FULL_999",
        "customer_id": "CUST_E2E_FULL_999",
        "merchant_id": "MERCHANT_RAZORPAY_DEMO",
        "amount": 349.99,
        "currency": "USD",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "US",
        "transaction_hour": 15,
        "account_age_days": 240,
        "previous_chargebacks": 0,
        "device_type": "desktop",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 1,
        "avg_transaction_amount_30d": 300.0,
        "payment": {
            "payment_id": "PAY_E2E_FULL_999",
            "card_network": "visa",
            "last4": "4242",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH_FULL_999",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_E2E_FULL_999",
            "product_description": "Wireless Noise Canceling Headphones",
            "order_amount": 349.99,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "FUL_E2E_FULL_999",
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_FULL_888",
                "shipped_at": "2026-08-25T09:15:00Z",
                "delivered_at": "2026-08-27T14:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    tx_resp = client.post("/transactions", json=txn_payload)
    assert tx_resp.status_code == 201

    # 2. POST /disputes (Create dispute case)
    dispute_payload = {
        "dispute_id": "DSP_E2E_FULL_999",
        "transaction_id": "TXN_E2E_FULL_999",
        "reason_code": "product_not_received",
        "reason_description": "Cardholder claims product was not delivered"
    }
    disp_resp = client.post("/disputes", json=dispute_payload)
    assert disp_resp.status_code == 201

    # 3. POST /transactions/{id}/risk-assessment (ML Engine + Risk Engine)
    risk_resp = client.post("/transactions/TXN_E2E_FULL_999/risk-assessment")
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert risk_data["transaction_id"] == "TXN_E2E_FULL_999"
    assert "risk_score" in risk_data

    # 4. POST /disputes/{id}/evidence (Evidence Engine)
    evd_resp = client.post("/disputes/DSP_E2E_FULL_999/evidence")
    assert evd_resp.status_code == 200
    evd_data = evd_resp.json()
    assert evd_data["available_count"] == 4

    # 5. POST /disputes/{id}/generate-response (AI Response Generator + Post-LLM Validator)
    ai_resp = client.post("/disputes/DSP_E2E_FULL_999/generate-response")
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert ai_data["merchant_position"] == "CONTEST"
    assert len(ai_data["evidence_citations"]) > 0

    # 6. POST /disputes/{id}/generate-package (Chargeback Package Generator + Persistence)
    pkg_resp = client.post("/disputes/DSP_E2E_FULL_999/generate-package")
    assert pkg_resp.status_code == 200
    package = pkg_resp.json()

    # Step 7: Verify final package compliance
    assert package["package_id"] == "PKG_DSP_E2E_FULL_999"
    assert package["package_status"] == "READY_FOR_REVIEW"
    assert package["dispute"]["dispute_id"] == "DSP_E2E_FULL_999"
    assert package["transaction"]["transaction_id"] == "TXN_E2E_FULL_999"
    assert package["risk_assessment"]["transaction_id"] == "TXN_E2E_FULL_999"
    assert package["evidence_summary"]["available"] == 4
    assert package["ai_response"]["merchant_position"] == "CONTEST"
    assert len(package["evidence_citations"]) > 0

    # Verify claim-to-evidence traceability mapping
    first_citation = package["evidence_citations"][0]
    assert "claim" in first_citation
    assert len(first_citation["evidence_refs"]) > 0
