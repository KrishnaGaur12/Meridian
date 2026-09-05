"""
Merchant Productization Test Suite — Razorpay AI Risk Manager.
Tests dataset scenario expansion (DSP_SCENARIO_01 to 10), plain-English merchant next best actions,
explainability responses, and command center API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from src.database.database import Base, get_db, _run_migrations, init_db, engine
from src.database.repository import get_dispute, get_all_disputes

from src.actions.engine import NextBestActionEngine
from src.explainability.engine import AIExplainabilityEngine

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
    init_db(test_engine, seed=True)
    db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_expanded_seed_scenarios():
    db = TestingSessionLocal()
    disputes = get_all_disputes(db)
    db.close()

    assert len(disputes) >= 10, f"Expected at least 10 seeded disputes, found {len(disputes)}"
    
    # Check scenario 08
    dsp8 = next((d for d in disputes if d.dispute_id == "DSP_SCENARIO_08"), None)
    assert dsp8 is not None
    assert dsp8.transaction.amount == 45000.0


def test_plain_english_next_best_action():
    action = NextBestActionEngine.evaluate_next_action(
        dispute_id="DSP_SCENARIO_01",
        workflow_stage="EVIDENCE_COLLECTION",
        urgency_level="APPROACHING",
        recommendation_decision="CONTEST",
        can_submit=False,
        blocking_issues=["Delivery proof required"],
        warnings=[],
        missing_evidence=["delivery_confirmation"],
        has_contradictions=False,
        has_ai_response=False,
        has_package=False
    )

    assert action["action_type"] == "UPLOAD_EVIDENCE"
    assert action["priority"] in ["HIGH", "CRITICAL"]
    assert "Delivery Confirmation" in action["title"]
    assert len(action["reason"]) > 0


def test_command_center_api_contract():
    res = client.get("/disputes/DSP_SCENARIO_01/command-center")
    assert res.status_code == 200
    data = res.json()
    assert "dispute" in data
    assert "explainability" in data
    assert "next_action" in data
    assert "package_inspection" in data
    assert "audit_trail" in data
