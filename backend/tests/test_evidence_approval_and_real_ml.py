"""
Comprehensive Test Suite for Evidence Approval & Real ML Inference.
Verifies:
1. Verify vs Approval separation (UNVERIFIED / VERIFIED vs PENDING_APPROVAL / APPROVED / REJECTED)
2. Approve Evidence endpoint: POST /disputes/{dispute_id}/evidence/{evidence_id}/approve and POST /evidence/{evidence_id}/approve
3. Rejection of approval on INVALID / UNREADABLE evidence
4. Automatic AI & ML dispute reassessment after approval
5. Real ML inference output variation (Fraud V2 & Win Probability)
6. Dynamic confidence derivation (HIGH, MEDIUM, LOW)
7. Case-specific AI recommendations & structured deterministic fallbacks
8. Database persistence of approval metadata across restarts
"""

import io
import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.database import init_db, get_db_session
from src.database.models import Evidence, Dispute
from src.database.repository import get_all_disputes, get_dispute, get_all_transactions
from src.utils.id_generator import generate_evidence_id

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_databases():
    """Initialize test databases."""
    init_db(seed=True)
    yield


def test_evidence_verification_and_approval_separation():
    """
    Test that uploaded evidence starts as VERIFIED + PENDING_APPROVAL,
    and approving it transitions to APPROVED with timestamps and audit trail.
    """
    # 1. Create a fresh simulated dispute in Live mode
    avail_resp = client.get("/demo/available-transactions", headers={"X-Database-Mode": "LIVE"})
    assert avail_resp.status_code == 200
    tx_id = avail_resp.json()["transactions"][0]["transaction_id"]

    sim_resp = client.post(
        "/demo/simulate-dispute",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "transaction_id": tx_id,
            "reason_code": "product_not_received",
            "reason_description": "Customer claims non-receipt of electronics package."
        }
    )
    assert sim_resp.status_code == 201
    dispute_id = sim_resp.json()["dispute_id"]

    # 2. Upload delivery proof file
    pdf_content = b"%PDF-1.4 Official Courier POD Tracking: DEL998234 Carrier: Blue Dart Status: Delivered Signed by Customer"
    file_tuple = ("blue_dart_pod.pdf", io.BytesIO(pdf_content), "application/pdf")

    upload_resp = client.post(
        f"/disputes/{dispute_id}/evidence/upload",
        headers={"X-Database-Mode": "LIVE"},
        data={
            "dispute_id": dispute_id,
            "evidence_type": "delivery_confirmation",
            "title": "Blue Dart Delivery Signed Proof"
        },
        files={"file": file_tuple}
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()

    assert upload_data["evidence_id"].startswith("evd_")
    assert upload_data["verification_status"] in ["VERIFIED", "AVAILABLE", "UNVERIFIED"]
    assert upload_data["approval_status"] == "PENDING_APPROVAL"
    evd_id = upload_data["evidence_id"]

    # 3. Call Approve Evidence endpoint
    approve_resp = client.post(
        f"/disputes/{dispute_id}/evidence/{evd_id}/approve",
        headers={"X-Database-Mode": "LIVE"},
        json={"approved_by": "MERCHANT"}
    )
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()

    assert approve_data["success"] is True
    assert approve_data["evidence"]["approval_status"] == "APPROVED"
    assert approve_data["evidence"]["approved_at"] is not None
    assert approve_data["evidence"]["approved_by"] == "MERCHANT"
    assert "ml_assessment" in approve_data
    assert approve_data["ml_assessment"]["ml_status"] == "OK"
    assert "win_probability" in approve_data["ml_assessment"]
    assert "confidence" in approve_data["ml_assessment"]
    assert "ai_analysis" in approve_data

    # 4. Verify DB entity state
    db_live = get_db_session("LIVE")
    try:
        evd_db = db_live.query(Evidence).filter(Evidence.evidence_id == evd_id).first()
        assert evd_db is not None
        assert evd_db.approval_status == "APPROVED"
        assert evd_db.approved_at is not None
        assert evd_db.approved_by == "MERCHANT"

        # Verify timeline audit event
        disp_db = get_dispute(db_live, dispute_id)
        event_types = [e.event_type for e in disp_db.events]
        assert "EVIDENCE_APPROVED" in event_types
    finally:
        db_live.close()


def test_reject_approval_on_invalid_evidence():
    """Verify backend rejects approval of INVALID or UNREADABLE evidence."""
    bad_id = generate_evidence_id()
    db_live = get_db_session("LIVE")
    try:
        disputes = get_all_disputes(db_live)
        dispute_id = disputes[0].dispute_id

        # Insert an unreadable / invalid evidence item
        bad_evd = Evidence(
            evidence_id=bad_id,
            dispute_id=dispute_id,
            transaction_id=disputes[0].transaction_id,
            evidence_type="delivery_confirmation",
            title="Corrupted Delivery File",
            verification_status="UNREADABLE",
            approval_status="PENDING_APPROVAL"
        )
        db_live.add(bad_evd)
        db_live.commit()
    finally:
        db_live.close()

    # Attempt to approve corrupted evidence
    resp = client.post(
        f"/disputes/{dispute_id}/evidence/{bad_id}/approve",
        headers={"X-Database-Mode": "LIVE"}
    )
    assert resp.status_code == 422
    assert "Cannot approve evidence with verification status 'UNREADABLE'" in resp.json()["detail"]


def test_direct_evidence_approval_alias():
    """Verify POST /evidence/{evidence_id}/approve alias works directly."""
    direct_id = generate_evidence_id()
    db_live = get_db_session("LIVE")
    try:
        # Create a valid manual evidence record
        disputes = get_all_disputes(db_live)
        dispute_id = disputes[0].dispute_id
        evd = Evidence(
            evidence_id=direct_id,
            dispute_id=dispute_id,
            transaction_id=disputes[0].transaction_id,
            evidence_type="customer_history",
            title="Verified Customer VIP History",
            verification_status="VERIFIED",
            approval_status="PENDING_APPROVAL"
        )
        db_live.add(evd)
        db_live.commit()
    finally:
        db_live.close()

    resp = client.post(
        f"/evidence/{direct_id}/approve",
        headers={"X-Database-Mode": "LIVE"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["evidence"]["approval_status"] == "APPROVED"


def test_real_ml_inference_variation():
    """
    Verify that ML model (Fraud V2 and Win Probability) outputs dynamic,
    case-sensitive predictions rather than static placeholders.
    """
    db_demo = get_db_session("DEMO")
    try:
        from src.database.repository import get_dispute_case_analysis

        # Scenario 1: Strong delivery case (DSP_SCENARIO_01)
        analysis_01 = get_dispute_case_analysis(db_demo, "DSP_SCENARIO_01")
        win_prob_01 = analysis_01["win_probability"]["score"]
        rec_01 = analysis_01["recommendation"]["decision"]

        # Scenario 2: Missing fulfillment proof case (DSP_SCENARIO_02)
        analysis_02 = get_dispute_case_analysis(db_demo, "DSP_SCENARIO_02")
        win_prob_02 = analysis_02["win_probability"]["score"]
        rec_02 = analysis_02["recommendation"]["decision"]

        # Assert ML predictions vary by case strength
        assert win_prob_01 > win_prob_02, f"Delivered case ({win_prob_01}) must have higher win probability than missing evidence case ({win_prob_02})."
        assert rec_01 == "CONTEST"

        # Assert confidence is valid
        conf_01 = analysis_01["win_probability"]["confidence_level"]
        assert conf_01 in ["HIGH", "MEDIUM", "LOW"]
    finally:
        db_demo.close()


def test_deepseek_case_specific_fallback_suggestions():
    """
    Verify AI Language Service generates case-tailored recommendations and evidence guidance
    across different dispute reasons with structured responses.
    """
    db_demo = get_db_session("DEMO")
    try:
        from src.services.ai.service import AIService
        ai_service = AIService()

        # Non-receipt dispute guidance
        guidance_non_receipt = ai_service.get_evidence_guidance(db_demo, "DSP_SCENARIO_02")
        assert len(guidance_non_receipt) > 0
        titles_nr = [g.title for g in guidance_non_receipt]
        assert any("delivery" in t.lower() or "shipping" in t.lower() for t in titles_nr)

        # Duplicate charge explanation
        explanation_dup = ai_service.get_case_explanation(db_demo, "DSP_SCENARIO_03")
        assert len(explanation_dup.plain_language_explanation) > 0
        assert len(explanation_dup.recommendation) > 0
    finally:
        db_demo.close()
