"""
Scenario Integration Tests for 5 realistic synthetic scenario JSON files.
"""

import pytest
from pathlib import Path
from src.pipeline.risk_engine import RiskEngine
from src.utils.data_generator import generate_scenario_files

@pytest.fixture(scope="module")
def scenario_paths():
    return generate_scenario_files()

@pytest.fixture(scope="module")
def risk_engine():
    return RiskEngine(use_vector_search=False)

def test_scenario_1_contest(risk_engine, scenario_paths):
    res = risk_engine.analyze_dispute(scenario_paths["scenario_1_contest"])
    assert res["dispute_id"] == "DSP_SCENARIO_01"
    assert res["recommendation"] == "CONTEST"
    assert res["evidence_completeness"] == 1.0
    assert res["win_probability"] >= 0.60

def test_scenario_2_accept(risk_engine, scenario_paths):
    res = risk_engine.analyze_dispute(scenario_paths["scenario_2_accept"])
    assert res["dispute_id"] == "DSP_SCENARIO_02"
    assert res["recommendation"] == "ACCEPT"
    assert "proof_of_delivery" in res["missing_evidence"]

def test_scenario_3_investigate(risk_engine, scenario_paths):
    res = risk_engine.analyze_dispute(scenario_paths["scenario_3_investigate"])
    assert res["dispute_id"] == "DSP_SCENARIO_03"
    assert res["recommendation"] == "INVESTIGATE"
    assert res["contradiction_severity"] in ["HIGH", "CRITICAL"]

def test_scenario_4_high_fraud(risk_engine, scenario_paths):
    res = risk_engine.analyze_dispute(scenario_paths["scenario_4_high_fraud"])
    assert res["dispute_id"] == "DSP_SCENARIO_04"
    assert res["recommendation"] in ["INVESTIGATE", "ACCEPT"]
    assert res["risk_level"] in ["MEDIUM", "HIGH", "CRITICAL"]
    assert "DISPUTE_VELOCITY_SPIKE" in res["triggered_fraud_rules"]

def test_scenario_5_duplicate(risk_engine, scenario_paths):
    res = risk_engine.analyze_dispute(scenario_paths["scenario_5_duplicate"])
    assert res["dispute_id"] == "DSP_SCENARIO_05"
    assert "DUPLICATE_TRANSACTION_FLAG" in res["triggered_fraud_rules"]
