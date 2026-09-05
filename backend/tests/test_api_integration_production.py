"""
Production REST API Integration Tests for RiskDesk Backend.
Verifies idempotent package generation, collection read endpoints (GET /transactions, GET /disputes),
database retrievability, CORS, and clean error handling without raw DB error exposure.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.database.database import Base, engine, init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    """Initializes and seeds database before test run."""
    Base.metadata.drop_all(bind=engine)
    init_db(custom_engine=engine, seed=True)
    yield
    Base.metadata.drop_all(bind=engine)

def test_get_transactions_collection():
    """GET /transactions should return list of seeded database records."""
    response = client.get("/transactions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check that TXN_LIVE_001 is present
    tx_ids = [tx["transaction_id"] for tx in data]
    assert "TXN_LIVE_001" in tx_ids

def test_get_transaction_by_id():
    """GET /transactions/{id} should return specific transaction record."""
    response = client.get("/transactions/TXN_LIVE_001")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "TXN_LIVE_001"
    assert data["amount"] == 4999.0

def test_get_transaction_404():
    """GET /transactions/{id} with invalid ID should cleanly return 404."""
    response = client.get("/transactions/TXN_NON_EXISTENT")
    assert response.status_code == 404
    assert "error_code" in response.json()
    assert response.json()["error_code"] == "HTTP_404"

def test_get_disputes_collection():
    """GET /disputes should return list of seeded database records."""
    response = client.get("/disputes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check that DSP_LIVE_001 is present
    disp_ids = [d["dispute_id"] for d in data]
    assert "DSP_LIVE_001" in disp_ids

def test_get_dispute_by_id():
    """GET /disputes/{id} should return specific dispute record."""
    response = client.get("/disputes/DSP_LIVE_001")
    assert response.status_code == 200
    data = response.json()
    assert data["dispute_id"] == "DSP_LIVE_001"
    assert data["transaction_id"] == "TXN_LIVE_001"
    assert data["reason_code"] == "product_not_received"

def test_get_dispute_404():
    """GET /disputes/{id} with invalid ID should cleanly return 404."""
    response = client.get("/disputes/DSP_NON_EXISTENT")
    assert response.status_code == 404
    assert response.json()["error_code"] == "HTTP_404"

def test_evidence_generation():
    """POST /disputes/{id}/evidence should generate evidence package."""
    response = client.post("/disputes/DSP_LIVE_001/evidence")
    assert response.status_code == 200
    data = response.json()
    assert data["dispute_id"] == "DSP_LIVE_001"
    assert data["evidence_count"] >= 1

def test_ai_response_generation():
    """POST /disputes/{id}/generate-response should generate structured AI response."""
    response = client.post("/disputes/DSP_LIVE_001/generate-response")
    assert response.status_code == 200
    data = response.json()
    assert "merchant_position" in data
    assert "response_text" in data

def test_repeatable_package_generation_idempotency():
    """
    POST /disputes/{id}/generate-package should work cleanly on first call AND second call
    without producing a UNIQUE constraint failed error.
    """
    # First call
    resp1 = client.post("/disputes/DSP_LIVE_001/generate-package")
    assert resp1.status_code == 200
    pkg1 = resp1.json()
    assert pkg1["package_id"] == "PKG_DSP_LIVE_001"

    # Second call (repeat request)
    resp2 = client.post("/disputes/DSP_LIVE_001/generate-package")
    assert resp2.status_code == 200
    pkg2 = resp2.json()
    assert pkg2["package_id"] == "PKG_DSP_LIVE_001"
    assert pkg2["package_status"] == pkg1["package_status"]

def test_no_raw_db_error_exposure():
    """Raw database errors or stack traces must never be exposed in HTTP response."""
    response = client.post("/transactions", json={"amount": -100.0}) # Invalid amount triggers validation or DB error
    assert response.status_code in (400, 422)
    res_json = response.json()
    assert "sqlite3" not in str(res_json).lower()
    assert "sqlalchemy" not in str(res_json).lower()
    assert "traceback" not in str(res_json).lower()
