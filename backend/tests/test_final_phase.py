"""
Automated Test Suite for Final Phase — Razorpay AI Risk Manager.
Tests AI Explainability Engine, Granular Evidence Intelligence, Next Best Action Engine,
Audit Trail, Package Inspection, Command Center aggregation, and ML Model Health API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from src.database.database import Base, get_db, _run_migrations, init_db, engine
from src.database.repository import (


    create_transaction, create_dispute, create_evidence, create_dispute_event,
    get_dispute_explainability, get_dispute_next_action, get_dispute_audit_trail,
    get_dispute_command_center
)
from src.explainability.engine import AIExplainabilityEngine
from src.actions.engine import NextBestActionEngine
from src.chargeback.service import ChargebackPackageService

from sqlalchemy.pool import StaticPool

# In-memory SQLite for testing with StaticPool
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    init_db(engine, seed=False)
    Base.metadata.create_all(bind=test_engine)
    _run_migrations(test_engine)
    db = TestingSessionLocal()

    # Seed test transaction & dispute
    tx = create_transaction(db, {
        "transaction_id": "TXN_FINAL_001",
        "customer_id": "CUST_FINAL_001",
        "merchant_id": "MERCHANT_001",
        "amount": 9999.0,
        "currency": "INR",
        "payment_method": "credit_card",
        "merchant_category": "electronics",
        "transaction_country": "IN",
        "account_age_days": 180,
        "previous_chargebacks": 1,
        "is_international": 1,
        "is_high_risk_merchant": 0,
        "transaction_velocity_1h": 4,
        "payment": {
            "payment_id": "PAY_FINAL_001",
            "card_network": "VISA",
            "last4": "4242",
            "avs_match": "Y",
            "cvv_match": "M"
        },
        "order": {
            "order_id": "ORD_FINAL_001",
            "product_description": "Smart Tablet Device",
            "fulfillment": {
                "fulfillment_id": "FUL_FINAL_001",
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK998877",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        }
    })

    dispute = create_dispute(db, {
        "dispute_id": "DSP_FINAL_001",
        "transaction_id": tx.transaction_id,
        "reason_code": "product_not_received",
        "reason_description": "Customer claims item was not delivered",
        "status": "OPEN"
    })

    create_evidence(db, {
        "evidence_id": "EVD_FINAL_001",
        "dispute_id": dispute.dispute_id,
        "transaction_id": tx.transaction_id,
        "evidence_type": "delivery_confirmation",
        "title": "FedEx Proof of Delivery",
        "description": "Signed delivery receipt",
        "verification_status": "AVAILABLE"
    })

    create_dispute_event(
        db=db,
        dispute_id=dispute.dispute_id,
        event_type="DISPUTE_RAISED",
        title="Dispute Case Opened",
        description="Bank notified merchant of chargeback.",
        actor_type="SYSTEM",
        new_stage="DISPUTE_RAISED"
    )

    db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)



def test_explainability_engine():
    db = TestingSessionLocal()
    expl = get_dispute_explainability(db, "DSP_FINAL_001")
    db.close()

    assert expl["dispute_id"] == "DSP_FINAL_001"
    assert "fraud_explainability" in expl
    assert "win_explainability" in expl

    fraud_expl = expl["fraud_explainability"]
    assert "top_risk_factors" in fraud_expl
    assert "supporting_factors" in fraud_expl
    assert "explanation_summary" in fraud_expl
    assert fraud_expl["model_version"] == "fraud-model-v2"

    win_expl = expl["win_explainability"]
    assert win_expl["win_probability"] > 0.0
    assert len(win_expl["evidence_contribution"]) > 0


def test_next_best_action_engine():
    db = TestingSessionLocal()
    action = get_dispute_next_action(db, "DSP_FINAL_001")
    db.close()

    assert "action_type" in action
    assert "priority" in action
    assert "title" in action
    assert "reason" in action
    assert "target_stage" in action
    assert "target_route" in action


def test_audit_trail_logging():
    db = TestingSessionLocal()
    create_dispute_event(
        db=db,
        dispute_id="DSP_FINAL_001",
        event_type="EVIDENCE_VERIFIED",
        title="Delivery Proof Verified",
        description="Carrier tracking signature verified.",
        actor_type="AI_ENGINE",
        previous_stage="EVIDENCE_COLLECTION",
        new_stage="EVIDENCE_ANALYSIS",
        metadata={"confidence": 0.95}
    )

    audit = get_dispute_audit_trail(db, "DSP_FINAL_001")
    db.close()

    assert len(audit) >= 2
    latest = audit[-1]
    assert latest["event_type"] == "EVIDENCE_VERIFIED"
    assert latest["actor_type"] == "AI_ENGINE"
    assert latest["metadata"]["confidence"] == 0.95


def test_package_inspection():
    db = TestingSessionLocal()
    service = ChargebackPackageService()
    pkg_inspection = service.inspect_chargeback_package(db, "DSP_FINAL_001")
    db.close()

    assert "package_metadata" in pkg_inspection
    assert "customer" in pkg_inspection
    assert "transaction" in pkg_inspection
    assert "evidence_intelligence" in pkg_inspection
    assert "ai_analysis" in pkg_inspection
    assert "rebuttal" in pkg_inspection
    assert "readiness_gate" in pkg_inspection
    assert "local_gateway_boundary" in pkg_inspection


def test_command_center_snapshot():
    db = TestingSessionLocal()
    snapshot = get_dispute_command_center(db, "DSP_FINAL_001")
    db.close()

    assert snapshot["dispute_id"] == "DSP_FINAL_001"
    assert "dispute" in snapshot
    assert "case_analysis" in snapshot
    assert "explainability" in snapshot
    assert "next_action" in snapshot
    assert "package_inspection" in snapshot
    assert "audit_trail" in snapshot


def test_rest_api_endpoints():
    r_expl = client.get("/disputes/DSP_FINAL_001/explainability")
    print("DEBUG EXPLAINABILITY STATUS & CONTENT:", r_expl.status_code, r_expl.content.decode())
    assert r_expl.status_code == 200

    assert r_expl.json()["dispute_id"] == "DSP_FINAL_001"

    r_action = client.get("/disputes/DSP_FINAL_001/next-action")
    assert r_action.status_code == 200
    assert "action_type" in r_action.json()

    r_audit = client.get("/disputes/DSP_FINAL_001/audit")
    assert r_audit.status_code == 200
    assert isinstance(r_audit.json(), list)

    r_pkg = client.get("/disputes/DSP_FINAL_001/package-inspection")
    assert r_pkg.status_code == 200
    assert "package_metadata" in r_pkg.json()

    r_cmd = client.get("/disputes/DSP_FINAL_001/command-center")
    assert r_cmd.status_code == 200
    assert r_cmd.json()["dispute_id"] == "DSP_FINAL_001"

    r_ml = client.get("/ml/model-health")
    assert r_ml.status_code == 200
    assert "fraud_model" in r_ml.json()
    assert "win_model" in r_ml.json()
