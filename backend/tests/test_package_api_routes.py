"""
API Route Tests for AI Response Generator and Chargeback Package Generator Endpoints.
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

def test_generate_response_endpoint():
    # Create transaction & dispute
    tx_payload = {"transaction_id": "TXN_API_RSP_100", "customer_id": "CUST_API_100", "amount": 199.99}
    client.post("/transactions", json=tx_payload)

    disp_payload = {"dispute_id": "DSP_API_RSP_100", "transaction_id": "TXN_API_RSP_100", "reason_code": "fraudulent_transaction"}
    client.post("/disputes", json=disp_payload)

    # POST /disputes/{id}/generate-response
    response = client.post("/disputes/DSP_API_RSP_100/generate-response")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "merchant_position" in data
    assert "response_text" in data
    assert "evidence_citations" in data

def test_generate_response_not_found():
    response = client.post("/disputes/NON_EXISTENT_DSP/generate-response")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_generate_package_endpoint():
    tx_payload = {
        "transaction_id": "TXN_API_PKG_200",
        "customer_id": "CUST_API_200",
        "amount": 299.99,
        "order": {
            "order_id": "ORD_API_PKG_200",
            "product_description": "Smart Watch",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_API_PKG_200",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    }
    client.post("/transactions", json=tx_payload)

    disp_payload = {"dispute_id": "DSP_API_PKG_200", "transaction_id": "TXN_API_PKG_200", "reason_code": "product_not_received"}
    client.post("/disputes", json=disp_payload)

    # POST /disputes/{id}/generate-package
    response = client.post("/disputes/DSP_API_PKG_200/generate-package")
    assert response.status_code == 200
    data = response.json()
    assert data["package_id"] == "PKG_DSP_API_PKG_200"
    assert data["package_status"] in ("READY_FOR_REVIEW", "INCOMPLETE", "INSUFFICIENT_EVIDENCE")
    assert "ai_response" in data
    assert "evidence_summary" in data
    assert "evidence_citations" in data

def test_generate_package_not_found():
    response = client.post("/disputes/NON_EXISTENT_DSP/generate-package")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
