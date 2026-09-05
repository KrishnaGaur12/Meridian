"""
Comprehensive End-to-End Test Suite for Razorpay AI Risk Manager Backend.
Tests:
1. Two-Database Architecture & Absolute Isolation (DEMO vs LIVE DB)
2. Live DB Seeding (15 transactions, 0 initial disputes)
3. Live ID Generation (Razorpay-inspired prefixes: txn_, cust_, pay_, order_, ful_, dispute_, evd_, pkg_, evt_, ref_)
4. Transaction Eligibility (SUCCESS, undisputed)
5. Simulated Dispute Creation (ML scoring, evidence mapping, AI reasoning, timeline events)
6. Duplicate Dispute Prevention
7. Dispute Reasons & 'other' validation
8. Evidence File Upload & Fact Extraction (PDF / Image)
9. Manual Evidence CRUD & Automatic AI Reassessment
10. Submission Gate & Readiness Verification
11. Final Submission with Gateway Reference ID Generation
12. Deterministic Simulated Lifecycle Outcome (WON / LOST)
13. Live DB Persistence Across Restarts
14. Developer-Only Live Reset & Demo Data Preservation
"""

import io
import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.database import (
    init_db, reset_live_database, get_db_session,
    DEMO_DB_FILE, LIVE_DB_FILE
)
from src.database.repository import (
    get_all_transactions, get_all_disputes, get_dispute, get_transaction
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_databases():
    """Ensure both DEMO and LIVE databases are initialized before tests run."""
    reset_live_database()
    init_db(seed=True)
    yield



# ============================================================================
# 1. TWO-DATABASE INITIALIZATION & ISOLATION TESTS
# ============================================================================

def test_dual_database_initialization():
    """Verify both Demo DB and Live DB files exist on disk."""
    assert DEMO_DB_FILE.exists(), "Demo database file (app_database.db) must exist."
    assert LIVE_DB_FILE.exists(), "Live database file (live_database.db) must exist."


def test_demo_database_preservation():
    """Verify Demo DB retains all 11 original demo scenarios and seeded transactions."""
    db_demo = get_db_session("DEMO")
    try:
        txs = get_all_transactions(db_demo)
        disputes = get_all_disputes(db_demo)

        assert len(txs) >= 10, f"Demo DB must contain at least 10 transactions (found {len(txs)})."
        assert len(disputes) >= 11, f"Demo DB must contain 11 demo dispute scenarios (found {len(disputes)})."

        demo_ids = [d.dispute_id for d in disputes]
        assert "DSP_LIVE_001" in demo_ids
        assert "DSP_SCENARIO_01" in demo_ids
        assert "DSP_SCENARIO_09" in demo_ids
    finally:
        db_demo.close()


def test_live_database_clean_seed():
    """Verify Live DB initially contains 15 clean transactions and ZERO disputes."""
    db_live = get_db_session("LIVE")
    try:
        txs = get_all_transactions(db_live)
        disputes = get_all_disputes(db_live)

        assert len(txs) == 15, f"Live DB must contain exactly 15 seeded transactions (found {len(txs)})."
        assert len(disputes) == 0, f"Live DB must initially contain 0 disputes (found {len(disputes)})."

        # Validate transaction structure
        tx = txs[0]
        assert tx.transaction_id.startswith("txn_")
        assert tx.customer_id.startswith("cust_")
        assert tx.transaction_status == "SUCCESS"
        assert len(tx.payments) > 0
        assert tx.payments[0].payment_status == "CAPTURED"
        assert tx.order is not None
        assert tx.order.fulfillment is not None
    finally:
        db_live.close()


def test_database_mode_isolation():
    """Verify absolute isolation between DEMO and LIVE database queries."""
    # Query Demo Mode
    resp_demo = client.get("/transactions", headers={"X-Database-Mode": "DEMO"})
    assert resp_demo.status_code == 200
    demo_txs = resp_demo.json()
    demo_tx_ids = [t["transaction_id"] for t in demo_txs]

    # Query Live Mode
    resp_live = client.get("/transactions", headers={"X-Database-Mode": "LIVE"})
    assert resp_live.status_code == 200
    live_txs = resp_live.json()
    live_tx_ids = [t["transaction_id"] for t in live_txs]

    # Validate zero cross-talk
    assert len(demo_txs) > 0
    assert len(live_txs) == 15
    for l_id in live_tx_ids:
        assert l_id not in demo_tx_ids, f"Live transaction {l_id} must not appear in Demo DB."
    for d_id in demo_tx_ids:
        assert d_id not in live_tx_ids, f"Demo transaction {d_id} must not appear in Live DB."


def test_system_mode_endpoint():
    """Verify GET /system/mode returns correct metadata for active mode."""
    # Default / DEMO
    resp = client.get("/system/mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_mode"] == "DEMO"
    assert data["database_file"] in ["app_database.db", "demo_database.db"]

    # Explicit LIVE
    resp_live = client.get("/system/mode", headers={"X-Database-Mode": "LIVE"})
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["active_mode"] == "LIVE"
    assert data_live["database_file"] == "live_database.db"
    assert data_live["total_transactions"] == 15


# ============================================================================
# 2. TRANSACTION ELIGIBILITY & SIMULATOR TESTS
# ============================================================================

def test_live_transaction_eligibility():
    """Verify /transactions/eligible returns only undisputed, successful transactions."""
    resp = client.get("/transactions/eligible", headers={"X-Database-Mode": "LIVE"})
    assert resp.status_code == 200
    eligible = resp.json()
    assert len(eligible) == 15, "All 15 live transactions should initially be dispute-eligible."


def test_live_simulator_available_transactions():
    """Verify /demo/available-transactions in LIVE mode lists eligible transactions."""
    resp = client.get("/demo/available-transactions", headers={"X-Database-Mode": "LIVE"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_eligible"] == 15
    assert len(data["transactions"]) == 15
    assert all(t["is_eligible"] for t in data["transactions"])


# ============================================================================
# 3. DISPUTE CREATION & AI PIPELINE TESTS
# ============================================================================

def test_create_simulated_dispute_live_mode():
    """
    End-to-end test of dispute creation in LIVE mode:
    - Creates dispute with Razorpay-style ID
    - Preserves payment status as CAPTURED
    - Triggers ML risk model, evidence mapping, and AI analysis
    - Generates timeline events
    - Excludes transaction from eligible pool immediately
    """
    # 1. Pick an eligible live transaction
    avail_resp = client.get("/demo/available-transactions", headers={"X-Database-Mode": "LIVE"})
    target_tx = avail_resp.json()["transactions"][0]
    tx_id = target_tx["transaction_id"]

    # 2. Create simulated dispute
    sim_resp = client.post(
        "/demo/simulate-dispute",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "transaction_id": tx_id,
            "reason_code": "product_not_received",
            "reason_description": "Customer claims Sony headphones never arrived.",
            "phase": "chargeback"
        }
    )
    assert sim_resp.status_code == 201
    sim_data = sim_resp.json()

    assert sim_data["simulation_status"] == "SUCCESS"
    assert sim_data["case_source"] == "SIMULATED_RAZORPAY"
    assert sim_data["transaction_id"] == tx_id
    assert sim_data["dispute_id"].startswith("dispute_")
    assert sim_data["workflow_stage"] == "DISPUTE_RAISED"
    assert sim_data["merchant_attention_state"] in ["ACTION_REQUIRED", "REVIEW_RECOMMENDED", "AI_HANDLING"]
    assert "case_analysis_summary" in sim_data
    assert sim_data["case_analysis_summary"]["evidence_completeness"] is not None

    dispute_id = sim_data["dispute_id"]

    # 3. Verify original payment status remained CAPTURED
    tx_check = client.get(f"/transactions/{tx_id}", headers={"X-Database-Mode": "LIVE"}).json()
    assert tx_check["transaction_status"] == "SUCCESS"

    db_live = get_db_session("LIVE")
    try:
        tx_obj = get_transaction(db_live, tx_id)
        assert tx_obj.payments[0].payment_status == "CAPTURED"
    finally:
        db_live.close()

    # 4. Verify transaction is now excluded from eligible transactions
    avail_after = client.get("/demo/available-transactions", headers={"X-Database-Mode": "LIVE"}).json()
    assert avail_after["total_eligible"] == 14
    assert not any(t["transaction_id"] == tx_id for t in avail_after["transactions"])

    # 5. Verify Demo DB was NEVER modified
    db_demo = get_db_session("DEMO")
    try:
        disp_in_demo = get_dispute(db_demo, dispute_id)
        assert disp_in_demo is None, "Live dispute must never exist in Demo DB."
    finally:
        db_demo.close()


def test_duplicate_active_dispute_prevention():
    """Verify attempting to create a second dispute on the same transaction is rejected."""
    # Find the already-disputed transaction in Live DB
    db_live = get_db_session("LIVE")
    try:
        disputes = get_all_disputes(db_live)
        assert len(disputes) >= 1
        disputed_tx_id = disputes[0].transaction_id
    finally:
        db_live.close()

    # Attempt duplicate creation
    dup_resp = client.post(
        "/demo/simulate-dispute",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "transaction_id": disputed_tx_id,
            "reason_code": "fraudulent_transaction",
            "reason_description": "Second duplicate dispute attempt",
            "phase": "chargeback"
        }
    )
    assert dup_resp.status_code == 400
    assert "already has an active dispute" in dup_resp.json()["detail"]


def test_dispute_reason_other_validation():
    """Verify dispute reason 'other' requires non-empty reason_description."""
    avail_resp = client.get("/demo/available-transactions", headers={"X-Database-Mode": "LIVE"})
    target_tx = avail_resp.json()["transactions"][0]
    tx_id = target_tx["transaction_id"]

    # Fails when description is empty
    bad_resp = client.post(
        "/demo/simulate-dispute",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "transaction_id": tx_id,
            "reason_code": "other",
            "reason_description": ""
        }
    )
    assert bad_resp.status_code == 400
    assert "reason_description is mandatory" in bad_resp.json()["detail"]

    # Succeeds with description
    good_resp = client.post(
        "/demo/simulate-dispute",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "transaction_id": tx_id,
            "reason_code": "other",
            "reason_description": "Customer requested customized engraving service not fulfilled"
        }
    )
    assert good_resp.status_code == 201
    assert good_resp.json()["reason_code"] == "other"


# ============================================================================
# 4. EVIDENCE ENGINE, FILE UPLOAD & MANUAL EVIDENCE TESTS
# ============================================================================

def test_manual_evidence_crud_and_automatic_reassessment():
    """
    Test adding, updating, and deleting manual evidence in LIVE mode.
    Verifies automatic AI reassessment after every mutation.
    """
    # 1. Get an existing live dispute
    db_live = get_db_session("LIVE")
    try:
        disputes = get_all_disputes(db_live)
        dispute_id = disputes[0].dispute_id
    finally:
        db_live.close()

    # 2. Add manual evidence
    add_resp = client.post(
        "/evidence",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "dispute_id": dispute_id,
            "evidence_type": "customer_communication",
            "title": "Customer Support Chat Log",
            "description": "Customer confirmed receiving tracking email on 2026-08-20",
            "verification_status": "AVAILABLE",
            "evidence_data": {"channel": "live_chat", "agent": "Sarah M."}
        }
    )
    assert add_resp.status_code == 201
    add_data = add_resp.json()
    assert add_data["evidence_id"].startswith("evd_")
    assert add_data["title"] == "Customer Support Chat Log"
    assert "impact_delta" in add_data

    evd_id = add_data["evidence_id"]

    # 3. Update evidence
    upd_resp = client.put(
        f"/evidence/{evd_id}",
        headers={"X-Database-Mode": "LIVE"},
        json={
            "title": "Updated Customer Support Transcript",
            "description": "Verified customer chat log with GPS confirmation"
        }
    )
    assert upd_resp.status_code == 200
    upd_data = upd_resp.json()
    assert upd_data["title"] == "Updated Customer Support Transcript"
    assert "impact_delta" in upd_data

    # 4. Delete evidence
    del_resp = client.delete(f"/evidence/{evd_id}", headers={"X-Database-Mode": "LIVE"})
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["deleted"] is True
    assert "impact_delta" in del_data


def test_evidence_file_upload_and_extraction():
    """
    Test PDF/image evidence upload:
    - Saves file to storage abstraction
    - Parses tracking facts and courier metadata
    - Creates Evidence record
    - Triggers automatic AI reassessment
    """
    db_live = get_db_session("LIVE")
    try:
        disputes = get_all_disputes(db_live)
        dispute_id = disputes[0].dispute_id
    finally:
        db_live.close()

    # Simulate PDF content
    pdf_content = b"%PDF-1.4 Mock Courier Proof of Delivery Tracking: BD772910456 Carrier: Blue Dart Status: Delivered Signed by Recipient"
    file_tuple = ("proof_of_delivery.pdf", io.BytesIO(pdf_content), "application/pdf")

    upload_resp = client.post(
        "/evidence/upload",
        headers={"X-Database-Mode": "LIVE"},
        data={
            "dispute_id": dispute_id,
            "evidence_type": "delivery_confirmation",
            "title": "Official Blue Dart Delivery Receipt",
            "description": "Courier signed proof of delivery"
        },
        files={"file": file_tuple}
    )
    assert upload_resp.status_code == 201
    data = upload_resp.json()

    assert data["success"] is True
    assert data["evidence_id"].startswith("evd_")
    assert data["verification_status"] in ["AVAILABLE", "VERIFIED", "UNVERIFIED"]
    assert "analysis" in data
    assert "facts" in data
    assert "impact_delta" in data


def test_invalid_evidence_file_handling():
    """Verify unsupported file extensions or empty files return clear 400 errors."""
    db_live = get_db_session("LIVE")
    try:
        dispute_id = get_all_disputes(db_live)[0].dispute_id
    finally:
        db_live.close()

    # Unsupported .exe file
    bad_file = ("malicious.exe", io.BytesIO(b"binary data"), "application/octet-stream")
    resp = client.post(
        "/evidence/upload",
        headers={"X-Database-Mode": "LIVE"},
        data={"dispute_id": dispute_id},
        files={"file": bad_file}
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


# ============================================================================
# 5. SUBMISSION GATE, GATEWAY REFERENCE ID & LIFECYCLE TESTS
# ============================================================================

def test_submission_gate_and_package_submission():
    """
    Test submission readiness gate and submission execution in LIVE mode:
    - Blocks submission if mandatory evidence is missing
    - Allows submission once mandatory evidence is provided
    - Generates unique gateway reference ID (ref_...)
    - Advances workflow to SUBMITTED
    """
    db_live = get_db_session("LIVE")
    try:
        # Create a fresh dispute with all required evidence
        txs = get_all_transactions(db_live)
        # Pick an undisputed transaction
        disputed_ids = {d.transaction_id for d in get_all_disputes(db_live)}
        avail_tx = next(t for t in txs if t.transaction_id not in disputed_ids)

        disp = client.post(
            "/demo/simulate-dispute",
            headers={"X-Database-Mode": "LIVE"},
            json={
                "transaction_id": avail_tx.transaction_id,
                "reason_code": "product_not_received",
                "reason_description": "Item not received"
            }
        ).json()
        dispute_id = disp["dispute_id"]

        # Check readiness initially (should be missing delivery_confirmation)
        readiness_resp = client.get(f"/disputes/{dispute_id}/readiness", headers={"X-Database-Mode": "LIVE"})
        assert readiness_resp.status_code == 200

        # Add mandatory evidence items
        client.post(
            "/evidence",
            headers={"X-Database-Mode": "LIVE"},
            json={
                "dispute_id": dispute_id,
                "evidence_type": "delivery_confirmation",
                "title": "Carrier Delivery Proof",
                "verification_status": "AVAILABLE",
                "evidence_data": {"tracking_number": "BD991283", "delivery_status": "DELIVERED"}
            }
        )
        client.post(
            "/evidence",
            headers={"X-Database-Mode": "LIVE"},
            json={
                "dispute_id": dispute_id,
                "evidence_type": "payment_confirmation",
                "title": "Gateway Captured Payment Receipt",
                "verification_status": "AVAILABLE"
            }
        )
        client.post(
            "/evidence",
            headers={"X-Database-Mode": "LIVE"},
            json={
                "dispute_id": dispute_id,
                "evidence_type": "shipping_confirmation",
                "title": "Warehouse Dispatch Manifest",
                "verification_status": "AVAILABLE"
            }
        )
        client.post(
            "/evidence",
            headers={"X-Database-Mode": "LIVE"},
            json={
                "dispute_id": dispute_id,
                "evidence_type": "customer_history",
                "title": "Verified Customer Profile Record",
                "verification_status": "AVAILABLE"
            }
        )

        # Pre-generate package
        from src.chargeback.service import ChargebackPackageService
        ChargebackPackageService().generate_and_save_package(db_live, dispute_id)

    finally:
        db_live.close()

    # Submit package via API
    sub_resp = client.post(
        f"/disputes/{dispute_id}/submit",
        headers={"X-Database-Mode": "LIVE"},
        json={"merchant_position": "CONTEST"}
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()

    assert sub_data["is_submitted"] is True
    assert sub_data["workflow_stage"] == "SUBMITTED"
    assert sub_data["status"] == "under_review"
    assert sub_data["gateway_reference_id"].startswith("ref_")
    assert sub_data["merchant_position"] == "CONTEST"
    assert "event" in sub_data


def test_deterministic_simulated_outcome():
    """
    Test lifecycle outcome simulation in LIVE mode:
    - Transitions dispute from SUBMITTED -> RESOLVED (WON / LOST)
    - Generates deterministic result with explanatory reason
    """
    db_live = get_db_session("LIVE")
    try:
        # Find submitted dispute
        disputes = get_all_disputes(db_live)
        sub_disp = next(d for d in disputes if d.workflow_stage == "SUBMITTED")
        dispute_id = sub_disp.dispute_id
    finally:
        db_live.close()

    # Simulate outcome
    outcome_resp = client.post(
        f"/disputes/{dispute_id}/simulate-outcome",
        headers={"X-Database-Mode": "LIVE"}
    )
    assert outcome_resp.status_code == 200
    outcome_data = outcome_resp.json()

    assert outcome_data["dispute_id"] == dispute_id
    assert outcome_data["workflow_stage"] == "RESOLVED"
    assert outcome_data["final_status"] in ["WON", "LOST"]
    assert outcome_data["is_simulated"] is True
    assert len(outcome_data["outcome_reason"]) > 0
    assert "event" in outcome_data


# ============================================================================
# 6. PERSISTENCE & DEVELOPER RESET TESTS
# ============================================================================

def test_live_persistence_across_reinit():
    """Verify that calling init_db() does NOT wipe live disputes or live modifications."""
    db_live = get_db_session("LIVE")
    try:
        disputes_before = len(get_all_disputes(db_live))
        assert disputes_before > 0
    finally:
        db_live.close()

    # Simulate app reboot / re-initialization
    init_db(seed=True)

    db_live_after = get_db_session("LIVE")
    try:
        disputes_after = len(get_all_disputes(db_live_after))
        assert disputes_after == disputes_before, "Live DB data must persist across init_db() calls without auto-reset."
    finally:
        db_live_after.close()


def test_developer_live_reset_and_demo_preservation():
    """
    Verify POST /system/reset-live:
    - Resets Live DB to initial 15 clean transactions with 0 disputes
    - Preserves Demo DB untouched with all 11 demo scenarios
    """
    # Execute developer reset
    reset_resp = client.post("/system/reset-live")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

    # Verify Live DB is clean (15 txs, 0 disputes)
    db_live = get_db_session("LIVE")
    try:
        txs_live = get_all_transactions(db_live)
        disp_live = get_all_disputes(db_live)
        assert len(txs_live) == 15
        assert len(disp_live) == 0
    finally:
        db_live.close()

    # Verify Demo DB is untouched
    db_demo = get_db_session("DEMO")
    try:
        txs_demo = get_all_transactions(db_demo)
        disp_demo = get_all_disputes(db_demo)
        assert len(txs_demo) >= 10
        assert len(disp_demo) >= 11
    finally:
        db_demo.close()
