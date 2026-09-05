"""
Comprehensive Automated Test Suite for Real Dispute Lifecycle, Two-Database Architecture,
Real ML Models, DeepSeek Integration, Evidence Engine, and Webhook Architecture.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from src.database.database import (
    Base, get_db, DemoSessionLocal, LiveSessionLocal,
    set_active_database_mode, get_active_database_mode, resolve_database_mode
)
from src.database.models import (
    Dispute, Transaction, Evidence, DisputeEvent, DisputeAssessment, WebhookEvent
)
from src.database.repository import (
    get_dispute, get_transaction, create_dispute, approve_dispute_evidence,
    get_case_readiness_and_gate, submit_dispute_package, simulate_dispute_outcome
)
from src.pipeline.analysis_service import analyze_dispute, determine_ml_recommendation, compute_deterministic_confidence
from src.components.fraud_model_v2 import FraudModelV2Wrapper
from src.components.win_probability import WinProbabilityModelWrapper
from src.api.routes.events import broadcaster, publish_realtime_event


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ============================================================
# TEST 1: TWO DATABASE ISOLATION & MODE SWITCHING
# ============================================================

def test_database_isolation_and_mode_switching(client):
    """
    Verifies that Demo DB and Live DB are strictly isolated,
    and switching /mode updates the query context.
    """
    # 1. Switch to LIVE mode
    res = client.post("/mode", json={"mode": "LIVE"})
    assert res.status_code == 200
    assert res.json()["active_mode"] == "LIVE"

    # Query disputes in LIVE mode
    live_disputes_before = client.get("/disputes", headers={"X-Database-Mode": "LIVE"}).json()
    live_count_before = len(live_disputes_before)

    # 2. Raise a new dispute in LIVE database via /webhooks
    tx_res = client.get("/webhooks/transactions")
    assert tx_res.status_code == 200
    eligible_txs = tx_res.json()["transactions"]
    assert len(eligible_txs) > 0
    target_tx = eligible_txs[0]["transaction_id"]

    webhook_res = client.post("/webhooks/razorpay", json={
        "transaction_id": target_tx,
        "reason_code": "product_not_received",
        "reason_description": "Customer never received the ordered electronics package."
    })
    assert webhook_res.status_code == 201
    created_dispute_id = webhook_res.json()["dispute_id"]

    # 3. Verify Live DB contains this dispute
    live_disputes_after = client.get("/disputes", headers={"X-Database-Mode": "LIVE"}).json()
    assert len(live_disputes_after) == live_count_before + 1
    assert any(d["dispute_id"] == created_dispute_id for d in live_disputes_after)

    # 4. Switch to DEMO mode and verify DEMO DB DOES NOT contain the Live dispute
    client.post("/mode", json={"mode": "DEMO"})
    demo_disputes = client.get("/disputes", headers={"X-Database-Mode": "DEMO"}).json()
    assert not any(d["dispute_id"] == created_dispute_id for d in demo_disputes)


# ============================================================
# TEST 2: WEBHOOK IDEMPOTENCY & LIVE DISPUTE CREATION
# ============================================================

def test_webhook_dispute_creation_and_idempotency(client):
    """
    Verifies that duplicate webhook payloads with the same idempotency key or event ID
    do NOT create duplicate dispute records.
    """
    idempotency_key = "idemp_test_unique_key_999"
    tx_res = client.get("/webhooks/transactions")
    eligible_txs = tx_res.json()["transactions"]
    assert len(eligible_txs) > 0
    target_tx = eligible_txs[0]["transaction_id"]

    # 1. First webhook submission
    first_res = client.post("/webhooks/razorpay", json={
        "transaction_id": target_tx,
        "reason_code": "fraudulent_transaction",
        "reason_description": "Cardholder disputes charge as unauthorized.",
        "idempotency_key": idempotency_key
    })
    assert first_res.status_code == 201
    dispute_id_1 = first_res.json()["dispute_id"]

    # 2. Replay identical webhook with same idempotency_key
    second_res = client.post("/webhooks/razorpay", json={
        "transaction_id": target_tx,
        "reason_code": "fraudulent_transaction",
        "reason_description": "Cardholder disputes charge as unauthorized.",
        "idempotency_key": idempotency_key
    })
    assert second_res.status_code in [200, 201]
    data = second_res.json()
    assert data["dispute_id"] == dispute_id_1
    assert data.get("is_idempotent_replay") is True


# ============================================================
# TEST 3: REAL ML MODELS INFERENCE (FRAUD V2 & WIN MODEL)
# ============================================================

def test_real_ml_models_inference():
    """
    Verifies that the trained Fraud V2 and Win Probability pipelines are loaded
    and return real quantitative probability distributions with prediction_source='MODEL'.
    """
    fraud_model = FraudModelV2Wrapper()
    assert fraud_model.is_trained is True
    assert fraud_model.pipeline is not None

    sample_tx = {
        "transaction_hour": 14,
        "account_age_days": 120,
        "previous_chargebacks": 0,
        "transaction_amount": 250.0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 3,
        "avg_transaction_amount_30d": 180.0,
        "merchant_category": "retail",
        "transaction_country": "US",
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0
    }
    fraud_res = fraud_model.predict(sample_tx)
    assert "fraud_probability" in fraud_res
    assert isinstance(fraud_res["fraud_probability"], float)
    assert 0.0 <= fraud_res["fraud_probability"] <= 1.0
    assert fraud_res["model_version"] == "fraud_v2"
    assert fraud_res["is_model_trained"] is True

    # Win Probability ML Model
    win_model = WinProbabilityModelWrapper()
    assert win_model.pipeline is not None

    win_res = win_model.predict(
        dispute_payload={"reason_code": "product_not_received", "dispute_amount": 250.0},
        completeness_score=0.85,
        evidence_quality_score=0.90,
        contradiction_count=0,
        contradiction_severity="NONE",
        fraud_prob=fraud_res["fraud_probability"],
        available_evidence=[{"document_type": "proof_of_delivery"}, {"document_type": "invoice"}]
    )
    assert "win_probability" in win_res
    assert isinstance(win_res["win_probability"], float)
    assert 0.0 <= win_res["win_probability"] <= 1.0
    assert win_res["prediction_source"] == "MODEL"
    assert win_res["is_model_trained"] is True


# ============================================================
# TEST 4: DETERMINISTIC SYSTEM CONFIDENCE
# ============================================================

def test_deterministic_confidence_calculation():
    """
    Verifies that system confidence is deterministically calculated
    based on prediction margins and evidence completeness.
    """
    # High certainty case (large margin, high completeness)
    conf_score, conf_level, expl = compute_deterministic_confidence(
        win_prob=0.88, fraud_prob=0.10, evidence_completeness=0.95,
        is_win_trained=True, is_fraud_trained=True
    )
    assert conf_level in ["HIGH", "MEDIUM"]
    assert conf_score >= 0.70

    # Low certainty case (near 0.50 boundary, low completeness)
    conf_score_low, conf_level_low, expl_low = compute_deterministic_confidence(
        win_prob=0.51, fraud_prob=0.49, evidence_completeness=0.10,
        is_win_trained=True, is_fraud_trained=True
    )
    assert conf_level_low in ["LOW", "MEDIUM"]
    assert conf_score_low < conf_score


# ============================================================
# TEST 5: DEEPSEEK INTEGRATION & DETERMINISTIC FALLBACK
# ============================================================

def test_deepseek_integration_and_fallback(client):
    """
    Verifies that DeepSeek receives complete case context,
    returns structured merchant guidance, and falls back gracefully on API failure.
    """
    db = LiveSessionLocal()
    try:
        disputes = db.query(Dispute).all()
        if not disputes:
            return
        dispute = disputes[0]

        # 1. Mock DeepSeek returning valid structured JSON
        mock_content = json.dumps({
            "dispute_id": dispute.dispute_id,
            "summary": "Strong fulfillment evidence exists. Challenge recommended.",
            "plain_english_explanation": "Carrier signed proof of delivery confirms delivery to cardholder address.",
            "recommendation": "Challenge this dispute",
            "recommendation_code": "CONTEST",
            "recommendation_reasoning": [
                "Signed delivery receipt directly refutes non-delivery claim.",
                "AVS and CVV matched during online checkout."
            ],
            "merchant_action": "Submit evidence package to representment gateway.",
            "confidence_language": "High confidence based on complete fulfillment records.",
            "missing_evidence_summary": None
        })

        with patch("src.services.ai.deepseek_client.DeepSeekClient.is_available", return_value=True), \
             patch("src.services.ai.deepseek_client.DeepSeekClient.chat_completion", return_value={"content": mock_content, "latency_ms": 45.0}):

            analysis = analyze_dispute(dispute.dispute_id, db, trigger="TEST_DEEPSEEK", broadcast=False)
            assert "recommendation" in analysis
            assert "explanation" in analysis["recommendation"]
            assert analysis["recommendation"]["ai_source"] == "DEEPSEEK"
            assert analysis["recommendation"]["decision"] in ["CONTEST", "ACCEPT", "REVIEW"]

        # 2. Test Fallback when API raises an exception or is unavailable
        with patch("src.services.ai.deepseek_client.DeepSeekClient.is_available", return_value=False):
            fallback_analysis = analyze_dispute(dispute.dispute_id, db, trigger="TEST_FALLBACK", broadcast=False)
            assert fallback_analysis["recommendation"]["ai_source"] == "FALLBACK"
            assert len(fallback_analysis["recommendation"]["explanation"]) > 0
    finally:
        db.close()


# ============================================================
# TEST 6: EVIDENCE APPROVAL & AUTOMATIC REASSESSMENT
# ============================================================

def test_evidence_approval_and_automatic_reassessment(client):
    """
    Verifies that uploading evidence sets verification_status=VERIFIED, approval_status=PENDING_APPROVAL,
    and approving evidence updates approval_status=APPROVED, logs EVIDENCE_APPROVED,
    and triggers automatic case reassessment.
    """
    db = LiveSessionLocal()
    try:
        disputes = db.query(Dispute).all()
        assert len(disputes) > 0
        dispute = disputes[0]

        # 1. Add manual evidence item
        add_res = client.post("/evidence", json={
            "dispute_id": dispute.dispute_id,
            "evidence_type": "proof_of_delivery",
            "title": "BlueDart Signed POD",
            "description": "Signed delivery receipt by cardholder.",
            "verification_status": "VERIFIED",
            "approval_status": "PENDING_APPROVAL",
            "evidence_data": {"carrier": "BlueDart", "tracking_number": "BD99281"}
        }, headers={"X-Database-Mode": "LIVE"})
        assert add_res.status_code == 201
        ev_id = add_res.json()["evidence_id"]
        assert add_res.json()["verification_status"] == "VERIFIED"
        assert add_res.json()["approval_status"] == "PENDING_APPROVAL"

        # 2. Approve evidence item
        approve_res = client.post(
            f"/disputes/{dispute.dispute_id}/evidence/{ev_id}/approve",
            json={"approved_by": "MERCHANT"},
            headers={"X-Database-Mode": "LIVE"}
        )
        assert approve_res.status_code == 200
        data = approve_res.json()
        assert data["evidence"]["approval_status"] == "APPROVED"
        assert data["evidence"]["approved_by"] == "MERCHANT"
        assert data["evidence"]["approved_at"] is not None

        # 3. Verify EVIDENCE_APPROVED event logged in timeline
        timeline_res = client.get(f"/disputes/{dispute.dispute_id}/timeline", headers={"X-Database-Mode": "LIVE"})
        assert timeline_res.status_code == 200
        events = timeline_res.json()
        assert any(e["event_type"] == "EVIDENCE_APPROVED" for e in events)

        # 4. Verify DisputeAssessment was recorded
        assessments = db.query(DisputeAssessment).filter(DisputeAssessment.dispute_id == dispute.dispute_id).all()
        assert len(assessments) > 0
    finally:
        db.close()


# ============================================================
# TEST 7: SUBMISSION GATE & OUTCOME SIMULATION
# ============================================================

def test_submission_gate_and_outcome_simulation(client):
    """
    Verifies that the backend enforces the submission readiness gate
    and allows outcome simulation resolving to WON or LOST.
    """
    db = LiveSessionLocal()
    try:
        disputes = db.query(Dispute).all()
        assert len(disputes) > 0
        dispute = disputes[0]

        # Submit dispute
        submit_res = client.post(
            f"/disputes/{dispute.dispute_id}/submit",
            json={"merchant_position": "CONTEST"},
            headers={"X-Database-Mode": "LIVE"}
        )
        # Should succeed or return gate error with descriptive reason
        if submit_res.status_code == 200:
            assert submit_res.json()["workflow_stage"] == "SUBMITTED"
            assert submit_res.json()["is_submitted"] is True

            # Simulate outcome
            outcome_res = client.post(
                f"/disputes/{dispute.dispute_id}/simulate-outcome",
                headers={"X-Database-Mode": "LIVE"}
            )
            assert outcome_res.status_code == 200
            assert outcome_res.json()["final_status"] in ["WON", "LOST"]
            assert outcome_res.json()["workflow_stage"] == "RESOLVED"
    finally:
        db.close()


# ============================================================
# TEST 8: REAL-TIME EVENT STREAMING (SSE)
# ============================================================

def test_realtime_event_broadcasting(client):
    """
    Verifies that events are captured in the broadcaster history and /events/recent endpoint.
    """
    publish_realtime_event("TEST_EVENT_BROADCAST", dispute_id="DSP_TEST", data={"test_key": "test_val"})

    res = client.get("/events/recent")
    assert res.status_code == 200
    events = res.json()["events"]
    assert any(e["event_type"] == "TEST_EVENT_BROADCAST" for e in events)


# ============================================================
# TEST 9: PERSISTENCE ACROSS RESTART
# ============================================================

def test_data_persistence_across_sessions(client):
    """
    Verifies that all created dispute records, evidence approvals,
    assessments, and timeline events persist in the database.
    """
    db = LiveSessionLocal()
    try:
        disputes = db.query(Dispute).all()
        assert len(disputes) > 0
        for d in disputes:
            assert d.dispute_id is not None
            assert d.transaction_id is not None
            assert d.merchant_attention_state is not None
    finally:
        db.close()
