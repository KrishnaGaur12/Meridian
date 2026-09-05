"""
End-to-End Workflow Integration Test.
Verifies full pipeline: Transaction Creation -> DB Storage -> Dispute Creation -> ML & Risk Engine Assessment -> Evidence Engine Retrieval & Verification -> Final Evidence Package.
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

def test_full_end_to_end_chargeback_workflow():
    """
    Demonstrates one complete end-to-end synthetic chargeback case.
    """
    # 1. Create Transaction with payment, order, and fulfillment details
    txn_payload = {
        "transaction_id": "TXN_E2E_999",
        "customer_id": "CUST_E2E_999",
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
            "payment_id": "PAY_E2E_999",
            "card_network": "visa",
            "last4": "4242",
            "avs_match": "Y",
            "cvv_match": "Y",
            "auth_code": "AUTH_E2E_APPROVED",
            "payment_status": "CAPTURED"
        },
        "order": {
            "order_id": "ORD_E2E_999",
            "product_description": "Mechanical Wireless Gaming Keyboard",
            "order_amount": 349.99,
            "order_status": "COMPLETED",
            "fulfillment": {
                "fulfillment_id": "FUL_E2E_999",
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_RAZOR_888",
                "shipped_at": "2026-08-25T09:15:00Z",
                "delivered_at": "2026-08-27T14:30:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }

    # Step 1: POST /transactions
    tx_resp = client.post("/transactions", json=txn_payload)
    assert tx_resp.status_code == 201, f"Create transaction failed: {tx_resp.text}"
    created_tx = tx_resp.json()
    assert created_tx["transaction_id"] == "TXN_E2E_999"

    # Step 2: GET /transactions/{id} (Verify DB storage)
    get_tx_resp = client.get("/transactions/TXN_E2E_999")
    assert get_tx_resp.status_code == 200
    assert get_tx_resp.json()["amount"] == 349.99

    # Step 3: POST /disputes (Create chargeback case)
    dispute_payload = {
        "dispute_id": "DSP_E2E_999",
        "transaction_id": "TXN_E2E_999",
        "reason_code": "product_not_received",
        "reason_description": "Customer claims item was never delivered"
    }
    disp_resp = client.post("/disputes", json=dispute_payload)
    assert disp_resp.status_code == 201, f"Create dispute failed: {disp_resp.text}"
    created_disp = disp_resp.json()
    assert created_disp["dispute_id"] == "DSP_E2E_999"

    # Step 4: POST /transactions/{id}/risk-assessment (Run ML & Risk Engine)
    risk_resp = client.post("/transactions/TXN_E2E_999/risk-assessment")
    assert risk_resp.status_code == 200, f"Risk assessment failed: {risk_resp.text}"
    risk_data = risk_resp.json()
    assert risk_data["transaction_id"] == "TXN_E2E_999"
    assert "risk_score" in risk_data
    assert risk_data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert risk_data["decision"] in ("ALLOW", "REVIEW", "BLOCK")

    # Step 5: POST /disputes/{id}/evidence (Run Evidence Engine)
    evd_resp = client.post("/disputes/DSP_E2E_999/evidence")
    assert evd_resp.status_code == 200, f"Evidence generation failed: {evd_resp.text}"
    package = evd_resp.json()

    # Step 6: Verify evidence package structure
    assert package["dispute_id"] == "DSP_E2E_999"
    assert package["transaction_id"] == "TXN_E2E_999"
    assert package["reason"] == "product_not_received"
    assert package["evidence_count"] == 4
    assert package["available_count"] == 4  # All 4 items: payment, shipping, delivery, customer_history should be AVAILABLE
    assert package["missing_count"] == 0

    # Inspect delivery proof details
    delivery_item = next(item for item in package["evidence"] if item["evidence_type"] == "delivery_confirmation")
    assert delivery_item["status"] == "AVAILABLE"
    assert delivery_item["source"] == "DATABASE:fulfillments"
    assert delivery_item["data"]["tracking_number"] == "TRK_RAZOR_888"
    assert delivery_item["data"]["delivery_status"] == "DELIVERED"
