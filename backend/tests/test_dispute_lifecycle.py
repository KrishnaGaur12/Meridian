import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(seed=True)
    yield

def test_dispute_lifecycle_and_deadline_engine():
    # 1. Fetch transactions list to get valid transaction ID
    tx_resp = client.get("/transactions")
    assert tx_resp.status_code == 200

    txs = tx_resp.json()
    assert len(txs) > 0
    target_tx = txs[0]
    tx_id = target_tx["transaction_id"]

    # 2. Create new dispute for existing transaction
    create_payload = {
        "transaction_id": tx_id,
        "reason_code": "product_not_received",
        "reason_description": "Item was not delivered to customer address",
        "phase": "chargeback"
    }

    create_resp = client.post("/disputes", json=create_payload)
    assert create_resp.status_code == 201
    dispute_data = create_resp.json()

    assert "dispute_id" in dispute_data
    assert dispute_data["transaction_id"] == tx_id
    assert dispute_data["reason_code"] == "product_not_received"
    assert dispute_data["phase"] == "chargeback"
    assert dispute_data["respond_by"] is not None
    assert dispute_data["remaining_time_human"] is not None
    assert dispute_data["deadline_status"] in ["ON_TRACK", "APPROACHING", "OVERDUE", "RESPONDED"]
    assert dispute_data["workflow_stage"] == "DISPUTE_RAISED"

    dispute_id = dispute_data["dispute_id"]

    # 3. Retrieve dispute timeline events
    timeline_resp = client.get(f"/disputes/{dispute_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    assert len(timeline) >= 3
    event_types = [evt["event_type"] for evt in timeline]
    assert "DISPUTE_RAISED" in event_types
    assert "MERCHANT_NOTIFIED" in event_types
    assert "AI_ANALYSIS_STARTED" in event_types

    # 4. Execute AI Case & Evidence Intelligence analysis endpoint
    analysis_resp = client.get(f"/disputes/{dispute_id}/analysis")
    assert analysis_resp.status_code == 200
    analysis = analysis_resp.json()

    assert analysis["dispute_id"] == dispute_id
    assert "case_summary" in analysis
    assert "risk_analysis" in analysis
    assert "evidence_intelligence" in analysis
    assert "win_probability" in analysis
    assert "recommendation" in analysis
    assert "next_actions" in analysis

    assert analysis["risk_analysis"]["model_version"] == "v2"
    assert analysis["recommendation"]["decision"] in ["CONTEST", "ACCEPT", "INVESTIGATE"]
