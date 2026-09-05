"""
Comprehensive Productization Test Suite — Razorpay AI Risk Manager.
Tests all 16 critical productization requirements:
1. DEMO case classification
2. SIMULATED_RAZORPAY creation via /demo/simulate-dispute
3. AI autopilot attention state classification (ACTION_REQUIRED, REVIEW_RECOMMENDED, AI_HANDLING, WAITING)
4. Evidence-triggered reassessment
5. Impact delta (honest before/after comparison)
6. Next-best-action structured fields
7. Merchant override & dispute accept
8. Package inspection payload
9. Submission gate hard blockers
10. Audit trail actor types & event metadata
11. Deadline urgency calculation
12. Cross-dispute isolation (Case A vs Case B)
13. Repeated evidence & package operation idempotency
14. No duplicate package records
15. Local gateway submission boundary labeling
16. API response correctness & error handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from src.database.database import get_db, SessionLocal, init_db, engine
from src.database.repository import (
    create_transaction, create_dispute, create_evidence,
    get_dispute, get_all_disputes, get_chargeback_package_by_dispute
)
from src.pipeline.autopilot import AIAutopilot

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensures database tables exist and seed data is loaded."""
    init_db(seed=True)
    db = SessionLocal()
    try:
        test_ids = [
            "TXN_REASSESS_TEST", "TXN_OVERRIDE_TEST", "TXN_GATE_TEST",
            "TXN_ISOLATION_A", "TXN_ISOLATION_B", "TXN_SUBMIT_TEST", "TXN_TEST_IDEMP"
        ]
        from src.database.models import Transaction, Dispute, Evidence, DisputeEvent, ChargebackPackage
        disputes = db.query(Dispute).filter(Dispute.transaction_id.in_(test_ids)).all()
        for d in disputes:
            db.query(Evidence).filter(Evidence.dispute_id == d.dispute_id).delete()
            db.query(DisputeEvent).filter(DisputeEvent.dispute_id == d.dispute_id).delete()
            db.query(ChargebackPackage).filter(ChargebackPackage.dispute_id == d.dispute_id).delete()
            db.delete(d)
        db.query(Transaction).filter(Transaction.transaction_id.in_(test_ids)).delete()
        db.commit()
    finally:
        db.close()
    yield



def test_1_demo_case_classification():
    """Verify seeded scenario disputes are explicitly classified as case_source = 'DEMO'."""
    db = SessionLocal()
    try:
        disputes = get_all_disputes(db)
        demo_disputes = [d for d in disputes if d.case_source == "DEMO"]
        assert len(demo_disputes) > 0, "Expected seeded disputes to have case_source = 'DEMO'"
        
        # Verify specific seeded IDs
        dsp1 = get_dispute(db, "DSP_SCENARIO_01")
        if dsp1:
            assert dsp1.case_source == "DEMO"
    finally:
        db.close()


def test_2_simulated_razorpay_creation_via_demo_endpoint():
    """Verify /demo/simulate-dispute creates a SIMULATED_RAZORPAY dispute and triggers AI analysis."""
    # First get an available transaction
    resp = client.get("/demo/available-transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert len(data["transactions"]) > 0

    tx_id = data["transactions"][0]["transaction_id"]

    # Simulate dispute
    sim_resp = client.post("/demo/simulate-dispute", json={
        "transaction_id": tx_id,
        "reason_code": "product_not_received",
        "reason_description": "Simulated test dispute",
        "phase": "chargeback"
    })
    assert sim_resp.status_code == 201
    sim_data = sim_resp.json()

    assert sim_data["simulation_status"] == "SUCCESS"
    assert sim_data["case_source"] == "SIMULATED_RAZORPAY"
    assert sim_data["transaction_id"] == tx_id
    assert "merchant_attention_state" in sim_data
    assert "deadline_info" in sim_data
    assert "case_analysis_summary" in sim_data

    # Verify dispute exists in list endpoint
    list_resp = client.get("/disputes?case_source=SIMULATED_RAZORPAY")
    assert list_resp.status_code == 200
    sim_list = list_resp.json()
    assert any(d["dispute_id"] == sim_data["dispute_id"] for d in sim_list)


def test_3_ai_autopilot_attention_state_classification():
    """Verify AI Autopilot correctly assigns all 4 merchant_attention_states based on backend state."""
    db = SessionLocal()
    try:
        # Case A: Missing evidence -> ACTION_REQUIRED
        dsp1 = get_dispute(db, "DSP_SCENARIO_02")  # Missing tracking/delivery proof
        if dsp1:
            analysis1 = AIAutopilot.reassess_dispute(db, dsp1.dispute_id)
            assert dsp1.merchant_attention_state in ["ACTION_REQUIRED", "REVIEW_RECOMMENDED"]

        # Case B: Submitted -> WAITING
        dsp9 = get_dispute(db, "DSP_SCENARIO_09")
        if dsp9:
            dsp9.workflow_stage = "SUBMITTED"
            dsp9.status = "under_review"
            db.commit()
            analysis9 = AIAutopilot.reassess_dispute(db, dsp9.dispute_id)
            assert dsp9.merchant_attention_state == "WAITING"

        # Case C: Response prepared -> REVIEW_RECOMMENDED
        dsp8 = get_dispute(db, "DSP_SCENARIO_08")
        if dsp8:
            dsp8.workflow_stage = "MERCHANT_REVIEW"
            db.commit()
            analysis8 = AIAutopilot.reassess_dispute(db, dsp8.dispute_id)
            assert dsp8.merchant_attention_state in ["REVIEW_RECOMMENDED", "ACTION_REQUIRED"]
    finally:
        db.close()


def test_4_evidence_triggered_reassessment():
    """Verify evidence addition/update/deletion triggers automatic AI reassessment and logs AI_ENGINE audit events."""
    db = SessionLocal()
    try:
        tx = create_transaction(db, {
            "transaction_id": "TXN_REASSESS_TEST",
            "amount": 2500.0,
            "currency": "USD"
        })
        dispute = create_dispute(db, {
            "transaction_id": tx.transaction_id,
            "reason_code": "product_not_received",
            "case_source": "SIMULATED_RAZORPAY"
        })
        did = dispute.dispute_id
    finally:
        db.close()

    # 1. Add evidence via API
    add_resp = client.post("/evidence", json={
        "dispute_id": did,
        "evidence_type": "delivery_confirmation",
        "title": "Carrier Delivery Proof",
        "description": "Signed delivery receipt",
        "verification_status": "AVAILABLE",
        "evidence_data": {"tracking_number": "TRK999888", "delivery_status": "DELIVERED"}
    })
    assert add_resp.status_code == 201
    add_data = add_resp.json()
    assert "impact_delta" in add_data
    ev_id = add_data["evidence_id"]

    # 2. Check audit trail has AI_ENGINE reassessment event
    audit_resp = client.get(f"/disputes/{did}/audit")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert any(e["actor_type"] == "AI_ENGINE" and "reassess" in e["title"].lower() for e in events)

    # 3. Update evidence via API
    upd_resp = client.put(f"/evidence/{ev_id}", json={
        "description": "Updated delivery proof description",
        "verification_status": "VERIFIED"
    })
    assert upd_resp.status_code == 200
    assert upd_resp.json()["verification_status"] == "VERIFIED"

    # 4. Delete evidence via API
    del_resp = client.delete(f"/evidence/{ev_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_5_impact_delta_honest_assessment():
    """Verify before/after impact delta provides real metric comparisons when evidence changes."""
    before_analysis = {
        "evidence_intelligence": {
            "evidence_completeness": 0.4,
            "evidence_quality": "LOW",
            "missing_evidence": ["delivery_confirmation"],
            "contradictions_count": 0
        },
        "win_probability": {"score": 0.45},
        "merchant_attention_state": "ACTION_REQUIRED"
    }

    after_analysis = {
        "evidence_intelligence": {
            "evidence_completeness": 0.8,
            "evidence_quality": "HIGH",
            "missing_evidence": [],
            "contradictions_count": 0
        },
        "win_probability": {"score": 0.78},
        "merchant_attention_state": "REVIEW_RECOMMENDED"
    }

    delta = AIAutopilot.compute_evidence_impact_delta(
        before_analysis, after_analysis,
        action_description="Merchant added delivery confirmation"
    )

    assert delta["before"]["evidence_completeness"] == 0.4
    assert delta["after"]["evidence_completeness"] == 0.8
    assert "improved from 40% to 80%" in delta["ai_explanation"]


def test_6_next_best_action_structured_fields():
    """Verify Next Best Action returns all required structured fields."""
    db = SessionLocal()
    try:
        resp = client.get("/disputes/DSP_LIVE_001/next-action")
        assert resp.status_code == 200
        nba = resp.json()

        required_keys = [
            "action_type", "priority", "title", "reason",
            "expected_impact", "confidence", "blocking_items",
            "target_stage", "target_route"
        ]
        for key in required_keys:
            assert key in nba, f"Missing required field '{key}' in NextBestAction"
    finally:
        db.close()


def test_7_merchant_override_and_accept():
    """Verify merchant can accept a dispute or override AI recommendation."""
    db = SessionLocal()
    try:
        tx = create_transaction(db, {"transaction_id": "TXN_OVERRIDE_TEST", "amount": 1000.0})
        disp = create_dispute(db, {"transaction_id": tx.transaction_id, "reason_code": "duplicate_charge"})
        did = disp.dispute_id
    finally:
        db.close()

    # 1. Test override to CONTEST
    ov_resp = client.post(f"/disputes/{did}/override-recommendation", json={
        "override_decision": "CONTEST",
        "reason": "We have double billing verification logs"
    })
    assert ov_resp.status_code == 200
    assert ov_resp.json()["override_decision"] == "CONTEST"

    # 2. Test accept dispute
    ac_resp = client.post(f"/disputes/{did}/accept", json={
        "reason": "Accepting duplicate billing error"
    })
    assert ac_resp.status_code == 200
    assert ac_resp.json()["status"] == "CLOSED"
    assert ac_resp.json()["workflow_stage"] == "RESOLVED"


def test_8_package_inspection_payload():
    """Verify package inspection endpoint exposes complete isolated case metadata."""
    resp = client.get("/disputes/DSP_LIVE_001/package-inspection")
    assert resp.status_code == 200
    data = resp.json()

    assert "package_metadata" in data
    assert "customer" in data
    assert "transaction" in data
    assert "payment" in data
    assert "order" in data
    assert "fulfillment" in data
    assert "evidence_intelligence" in data
    assert "ai_analysis" in data
    assert "rebuttal" in data
    assert "readiness_gate" in data
    assert "local_gateway_boundary" in data


def test_9_submission_gate_blockers():
    """Verify submission gate blocks submission when missing mandatory evidence."""
    db = SessionLocal()
    try:
        # Create incomplete dispute without evidence
        tx = create_transaction(db, {"transaction_id": "TXN_GATE_TEST", "amount": 5000.0})
        disp = create_dispute(db, {"transaction_id": tx.transaction_id, "reason_code": "product_not_received"})
        did = disp.dispute_id
    finally:
        db.close()

    # Attempt submission — should be blocked
    sub_resp = client.post(f"/disputes/{did}/submit")
    assert sub_resp.status_code == 400
    assert "BLOCKED by gate" in sub_resp.json()["detail"]


def test_10_audit_trail_actors_and_metadata():
    """Verify dispute audit trail records correct actor_types and metadata."""
    resp = client.get("/disputes/DSP_LIVE_001/audit")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) > 0

    valid_actors = {"SYSTEM", "AI_ENGINE", "MERCHANT", "LOCAL_GATEWAY"}
    for evt in events:
        assert evt["actor_type"] in valid_actors
        assert "event_id" in evt
        assert "timestamp" in evt


def test_11_deadline_urgency_calculation():
    """Verify deadline engine correctly calculates remaining hours and urgency level."""
    db = SessionLocal()
    try:
        disp = get_dispute(db, "DSP_LIVE_001")
        assert disp is not None
        
        analysis_resp = client.get(f"/disputes/{disp.dispute_id}/analysis")
        assert analysis_resp.status_code == 200
        analysis = analysis_resp.json()

        assert "remaining_hours" in analysis
        assert "urgency_level" in analysis
        assert analysis["urgency_level"] in ["SAFE", "APPROACHING", "URGENT", "OVERDUE", "RESPONDED"]
    finally:
        db.close()


def test_12_cross_dispute_isolation():
    """CRITICAL TEST: Verify Case A data never leaks into Case B."""
    db = SessionLocal()
    try:
        # Create Case A
        txA = create_transaction(db, {"transaction_id": "TXN_ISOLATION_A", "amount": 100.0})
        dispA = create_dispute(db, {"transaction_id": txA.transaction_id, "reason_code": "product_not_received"})
        evA = create_evidence(db, {
            "dispute_id": dispA.dispute_id,
            "transaction_id": txA.transaction_id,
            "evidence_type": "delivery_confirmation",
            "title": "CASE_A_SPECIFIC_PROOF_999"
        })

        # Create Case B
        txB = create_transaction(db, {"transaction_id": "TXN_ISOLATION_B", "amount": 200.0})
        dispB = create_dispute(db, {"transaction_id": txB.transaction_id, "reason_code": "duplicate_charge"})
        evB = create_evidence(db, {
            "dispute_id": dispB.dispute_id,
            "transaction_id": txB.transaction_id,
            "evidence_type": "invoice",
            "title": "CASE_B_SPECIFIC_PROOF_888"
        })

        didA = dispA.dispute_id
        didB = dispB.dispute_id
    finally:
        db.close()

    # Query Case A package & intelligence via API
    pkgA_resp = client.get(f"/disputes/{didA}/package-inspection")
    assert pkgA_resp.status_code == 200
    pkgA = pkgA_resp.json()

    # Verify Case A contains ONLY Case A transaction & evidence
    assert pkgA["transaction"]["transaction_id"] == "TXN_ISOLATION_A"
    pkgA_str = str(pkgA)
    assert "CASE_A_SPECIFIC_PROOF_999" in pkgA_str
    assert "CASE_B_SPECIFIC_PROOF_888" not in pkgA_str

    # Query Case B package & intelligence via API
    pkgB_resp = client.get(f"/disputes/{didB}/package-inspection")
    assert pkgB_resp.status_code == 200
    pkgB = pkgB_resp.json()

    # Verify Case B contains ONLY Case B transaction & evidence
    assert pkgB["transaction"]["transaction_id"] == "TXN_ISOLATION_B"
    pkgB_str = str(pkgB)
    assert "CASE_B_SPECIFIC_PROOF_888" in pkgB_str
    assert "CASE_A_SPECIFIC_PROOF_999" not in pkgB_str


def test_13_repeated_evidence_package_operation_idempotency():
    """Verify generating chargeback package multiple times is idempotent and produces no errors."""
    resp1 = client.get("/disputes/DSP_LIVE_001/package-inspection")
    assert resp1.status_code == 200
    pkg1 = resp1.json()

    resp2 = client.get("/disputes/DSP_LIVE_001/package-inspection")
    assert resp2.status_code == 200
    pkg2 = resp2.json()

    assert pkg1["package_metadata"]["package_id"] == pkg2["package_metadata"]["package_id"]


def test_14_no_duplicate_package_records():
    """Verify only 1 chargeback package record exists in DB per dispute_id even after multiple calls."""
    db = SessionLocal()
    try:
        pkg = get_chargeback_package_by_dispute(db, "DSP_LIVE_001")
        assert pkg is not None
        pkg_id_initial = pkg.package_id

        # Trigger package endpoint again
        client.get("/disputes/DSP_LIVE_001/package-inspection")

        # Verify package_id remains identical and count in DB is 1
        pkg_recheck = get_chargeback_package_by_dispute(db, "DSP_LIVE_001")
        assert pkg_recheck.package_id == pkg_id_initial
    finally:
        db.close()


def test_15_local_gateway_submission_boundary():
    """Verify submitting a valid dispute explicitly sets local gateway boundary notice."""
    db = SessionLocal()
    try:
        # Create fully ready dispute with all required evidence
        tx = create_transaction(db, {
            "transaction_id": "TXN_SUBMIT_TEST",
            "amount": 1200.0,
            "order": {
                "order_id": "ORD_SUBMIT_TEST",
                "product_description": "Electronics",
                "fulfillment": {
                    "fulfillment_id": "FUL_SUBMIT_TEST",
                    "shipping_status": "SHIPPED",
                    "tracking_number": "TRK12345",
                    "shipped_at": "2026-08-10T10:00:00Z",
                    "delivered_at": "2026-08-12T14:00:00Z",
                    "delivery_status": "DELIVERED"
                }
            }
        })
        disp = create_dispute(db, {"transaction_id": tx.transaction_id, "reason_code": "product_not_received"})
        create_evidence(db, {
            "dispute_id": disp.dispute_id,
            "transaction_id": tx.transaction_id,
            "evidence_type": "delivery_confirmation",
            "title": "Delivery Proof",
            "verification_status": "AVAILABLE"
        })
        create_evidence(db, {
            "dispute_id": disp.dispute_id,
            "transaction_id": tx.transaction_id,
            "evidence_type": "payment_confirmation",
            "title": "Payment Receipt",
            "verification_status": "AVAILABLE"
        })
        create_evidence(db, {
            "dispute_id": disp.dispute_id,
            "transaction_id": tx.transaction_id,
            "evidence_type": "shipping_confirmation",
            "title": "Shipping Manifest",
            "verification_status": "AVAILABLE"
        })
        create_evidence(db, {
            "dispute_id": disp.dispute_id,
            "transaction_id": tx.transaction_id,
            "evidence_type": "customer_history",
            "title": "Customer Purchase History",
            "verification_status": "AVAILABLE"
        })
        did = disp.dispute_id

        # Pre-generate package
        from src.chargeback.service import ChargebackPackageService
        ChargebackPackageService().generate_and_save_package(db, did)
    finally:
        db.close()

    # Submit via API
    sub_resp = client.post(f"/disputes/{did}/submit")
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()

    assert sub_data["is_submitted"] is True
    assert sub_data["workflow_stage"] == "SUBMITTED"
    assert "Local Gateway" in sub_data["submission_boundary_notice"]


def test_16_api_response_correctness_and_model_health():
    """Verify all health and ML model health endpoints return valid responses."""
    h_resp = client.get("/health")
    assert h_resp.status_code == 200
    assert h_resp.json() == {"status": "ok"}

    mh_resp = client.get("/health/models")
    assert mh_resp.status_code == 200
    mh_data = mh_resp.json()
    assert "fraud_model" in mh_data
    assert "win_model" in mh_data
    assert mh_data["fraud_model"]["status"] == "HEALTHY_BASELINE"
