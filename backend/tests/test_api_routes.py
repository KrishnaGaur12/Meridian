"""
Integration tests for FastAPI REST API endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.database.database import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    """Re-creates database tables before each test run."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_and_get_transaction_endpoint():
    payload = {
        "transaction_id": "TXN_API_100",
        "customer_id": "CUST_API_100",
        "amount": 150.75,
        "currency": "USD",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "US",
        "transaction_hour": 14,
        "account_age_days": 200,
        "previous_chargebacks": 0,
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 2,
        "avg_transaction_amount_30d": 120.0
    }

    # POST /transactions
    create_resp = client.post("/transactions", json=payload)
    assert create_resp.status_code == 201
    res_data = create_resp.json()
    assert res_data["transaction_id"] == "TXN_API_100"
    assert res_data["amount"] == 150.75

    # GET /transactions/{transaction_id}
    get_resp = client.get("/transactions/TXN_API_100")
    assert get_resp.status_code == 200
    assert get_resp.json()["transaction_id"] == "TXN_API_100"

def test_get_transaction_not_found():
    response = client.get("/transactions/NON_EXISTENT_TXN")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_create_and_get_dispute_endpoint():
    # Setup transaction
    tx_payload = {
        "transaction_id": "TXN_API_200",
        "customer_id": "CUST_API_200",
        "amount": 299.00
    }
    client.post("/transactions", json=tx_payload)

    # POST /disputes
    disp_payload = {
        "dispute_id": "DSP_API_200",
        "transaction_id": "TXN_API_200",
        "reason_code": "fraudulent_transaction",
        "reason_description": "Unauthorized charge reported"
    }
    create_resp = client.post("/disputes", json=disp_payload)
    assert create_resp.status_code == 201
    disp_data = create_resp.json()
    assert disp_data["dispute_id"] == "DSP_API_200"

    # GET /disputes/{dispute_id}
    get_resp = client.get("/disputes/DSP_API_200")
    assert get_resp.status_code == 200
    assert get_resp.json()["dispute_id"] == "DSP_API_200"

def test_create_dispute_for_missing_transaction():
    disp_payload = {
        "dispute_id": "DSP_API_INVALID",
        "transaction_id": "TXN_DOES_NOT_EXIST",
        "reason_code": "duplicate_charge"
    }
    response = client.post("/disputes", json=disp_payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_risk_assessment_endpoint():
    tx_payload = {
        "transaction_id": "TXN_API_RISK_300",
        "customer_id": "CUST_API_300",
        "amount": 750.00,
        "transaction_hour": 3,
        "account_age_days": 10,
        "previous_chargebacks": 2,
        "is_international": 1,
        "is_high_risk_merchant": 1,
        "transaction_velocity_1h": 5,
        "transaction_velocity_24h": 12,
        "avg_transaction_amount_30d": 50.0
    }
    client.post("/transactions", json=tx_payload)

    # POST /transactions/{id}/risk-assessment
    risk_resp = client.post("/transactions/TXN_API_RISK_300/risk-assessment")
    assert risk_resp.status_code == 200
    data = risk_resp.json()
    assert data["transaction_id"] == "TXN_API_RISK_300"
    assert "risk_score" in data
    assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert data["decision"] in ("ALLOW", "REVIEW", "BLOCK")

def test_evidence_endpoint():
    # Setup full transaction + order + fulfillment
    tx_payload = {
        "transaction_id": "TXN_API_EVD_400",
        "customer_id": "CUST_API_400",
        "amount": 199.99,
        "order": {
            "order_id": "ORD_API_400",
            "product_description": "Smart Watch",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRACK_API_400",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    client.post("/transactions", json=tx_payload)

    disp_payload = {
        "dispute_id": "DSP_API_EVD_400",
        "transaction_id": "TXN_API_EVD_400",
        "reason_code": "product_not_received"
    }
    client.post("/disputes", json=disp_payload)

    # POST /disputes/{id}/evidence
    evd_resp = client.post("/disputes/DSP_API_EVD_400/evidence")
    assert evd_resp.status_code == 200
    package = evd_resp.json()
    assert package["dispute_id"] == "DSP_API_EVD_400"
    assert package["reason"] == "product_not_received"
    assert package["evidence_count"] == 4
    assert package["available_count"] >= 3
