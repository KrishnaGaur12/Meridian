"""
Unit and Integration Tests for Round 2 Workflow: Stage Transitions, Case Readiness,
Idempotent Package Generation, Submission Gate, and Deadline Urgency.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(seed=True)
    yield

def test_round2_dispute_workflow_and_submission_gate():
    # 1. Fetch valid dispute case from database
    disputes_resp = client.get("/disputes")
    assert disputes_resp.status_code == 200
    disputes = disputes_resp.json()
    assert len(disputes) > 0
    dispute_id = disputes[0]["dispute_id"]

    # 2. Check case readiness endpoint
    readiness_resp = client.get(f"/disputes/{dispute_id}/readiness")
    assert readiness_resp.status_code == 200
    readiness = readiness_resp.json()

    assert "readiness_status" in readiness
    assert "readiness_percentage" in readiness
    assert "can_submit" in readiness
    assert "evidence_mapping" in readiness
    assert "deadline_info" in readiness

    # 3. Test controlled workflow stage transition
    transition_payload = {
        "target_stage": "EVIDENCE_ANALYSIS",
        "event_title": "Evidence Analysis Initiated",
        "event_desc": "Evaluated database evidence integrity."
    }
    trans_resp = client.post(f"/disputes/{dispute_id}/transition", json=transition_payload)
    # Stage transition should succeed or fail gracefully based on allowed graph
    assert trans_resp.status_code in [200, 400]

    # 4. Test idempotent package generation (POST /disputes/{id}/generate-package)
    pkg_resp_1 = client.post(f"/disputes/{dispute_id}/generate-package")
    assert pkg_resp_1.status_code == 200
    pkg_1 = pkg_resp_1.json()

    pkg_resp_2 = client.post(f"/disputes/{dispute_id}/generate-package")
    assert pkg_resp_2.status_code == 200
    pkg_2 = pkg_resp_2.json()

    # Verify idempotency: package_id should remain identical, no duplicates
    assert pkg_1["package_id"] == pkg_2["package_id"]

    # 5. Test Submission Gate (POST /disputes/{id}/submit)
    submit_resp = client.post(f"/disputes/{dispute_id}/submit")
    assert submit_resp.status_code in [200, 400]

    if submit_resp.status_code == 200:
        sub_data = submit_resp.json()
        assert sub_data["workflow_stage"] == "SUBMITTED"
        assert sub_data["is_submitted"] is True
        assert "submission_boundary_notice" in sub_data
    else:
        err_detail = submit_resp.json()["detail"]
        assert "Submission BLOCKED" in err_detail or "gate" in err_detail.lower()

def test_deadline_urgency_level_calculation():
    from src.database.repository import calculate_deadline_info
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)

    # Safe: > 72h
    safe_deadline = (now + timedelta(hours=100)).isoformat()
    safe_info = calculate_deadline_info(safe_deadline)
    assert safe_info["urgency_level"] == "SAFE"

    # Approaching: 48h (<= 72h and > 24h)
    appr_deadline = (now + timedelta(hours=48)).isoformat()
    appr_info = calculate_deadline_info(appr_deadline)
    assert appr_info["urgency_level"] == "APPROACHING"

    # Urgent: 12h (<= 24h)
    urg_deadline = (now + timedelta(hours=12)).isoformat()
    urg_info = calculate_deadline_info(urg_deadline)
    assert urg_info["urgency_level"] == "URGENT"

    # Overdue: -2h (<= 0h)
    over_deadline = (now - timedelta(hours=2)).isoformat()
    over_info = calculate_deadline_info(over_deadline)
    assert over_info["urgency_level"] == "OVERDUE"
