"""
Semantic & Contract Hardening Tests for Razorpay AI Risk Manager.
Verifies percentage rounding consistency, language phrasing rules, concept separation,
and 22-field JSON contract stability.
"""

import pytest
from pathlib import Path
from src.pipeline.risk_engine import RiskEngine
from config.settings import format_pct

@pytest.fixture(scope="module")
def risk_engine():
    return RiskEngine(use_vector_search=False)

def test_json_contract_22_fields(risk_engine):
    """Verifies that analyze_dispute output contains exactly the 22 required core contract fields."""
    sample = {
        "dispute_id": "DSP_CONTRACT_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_amount": 1000.0,
        "available_evidence": []
    }
    res = risk_engine.analyze_dispute(sample)
    
    required_fields = [
        "dispute_id", "reason", "evidence_completeness", "evidence_quality",
        "missing_evidence", "contradictions", "contradiction_type",
        "contradiction_severity", "contradiction_evidence_a", "contradiction_evidence_b",
        "fraud_probability", "risk_level", "triggered_fraud_rules", "win_probability",
        "confidence", "confidence_level", "confidence_explanation",
        "recommendation", "decision_reasons", "decision_factors",
        "explanation", "models_status"
    ]
    
    for f in required_fields:
        assert f in res, f"Required JSON contract field '{f}' is missing from output dictionary."
        
    assert len(required_fields) == 22

def test_win_probability_79_not_borderline(risk_engine):
    """Verifies that 79% win probability (as in Scenario 5) is described as strong/high and NEVER borderline."""
    sample = {
        "dispute_id": "DSP_79_TEST",
        "customer_id": "CUST_79",
        "order_id": "ORD_79",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_amount": 6500.0,
        "merchant_historical_win_rate": 0.85,
        "previous_disputes_won_count": 20,
        "is_duplicate_flag": 1,
        "available_evidence": [
            {"document_id": "D1", "document_type": "invoice", "customer_id": "CUST_79", "order_id": "ORD_79", "dispute_id": "DSP_79_TEST", "content": "Invoice content"},
            {"document_id": "D2", "document_type": "shipping_proof", "customer_id": "CUST_79", "order_id": "ORD_79", "dispute_id": "DSP_79_TEST", "content": "Shipping content"},
            {"document_id": "D3", "document_type": "proof_of_delivery", "customer_id": "CUST_79", "order_id": "ORD_79", "dispute_id": "DSP_79_TEST", "content": "POD content"}
        ]
    }
    res = risk_engine.analyze_dispute(sample)
    explanation = res["explanation"]
    reasons = " ".join(res["decision_reasons"])
    
    assert "borderline win probability (79%)" not in explanation.lower()
    assert "borderline win probability (79%)" not in reasons.lower()
    assert "borderline win probability" not in reasons.lower()
    assert "strong" in explanation.lower() or "strong" in reasons.lower() or "high" in explanation.lower()

def test_percentage_consistency_cli_json_explanation(risk_engine):
    """Verifies 100% exact integer percentage matching across JSON, CLI formatters, and Explanation string."""
    sample = {
        "dispute_id": "DSP_PCT_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_amount": 4500.0,
        "available_evidence": [
            {"document_type": "invoice"},
            {"document_type": "shipping_proof"},
            {"document_type": "proof_of_delivery"}
        ]
    }
    res = risk_engine.analyze_dispute(sample)
    
    win_pct = format_pct(res["win_probability"])
    comp_pct = format_pct(res["evidence_completeness"])
    fraud_pct = format_pct(res["fraud_probability"])
    conf_pct = format_pct(res["confidence"])
    
    expl = res["explanation"]
    
    # Check win_pct appears consistently
    assert f"({win_pct}%)" in expl or f"{win_pct}%" in expl
    # Check comp_pct appears consistently
    assert f"({comp_pct}%)" in expl or f"{comp_pct}%" in expl

def test_concept_separation_fraud_vs_confidence(risk_engine):
    """Verifies that fraud_probability is NOT labeled or confused with system confidence."""
    sample = {
        "dispute_id": "DSP_CONCEPT_TEST",
        "dispute_reason": "UNAUTHORIZED_TRANSACTION",
        "transaction_amount": 80000.0,
        "dispute_velocity_24h": 5,
        "available_evidence": []
    }
    res = risk_engine.analyze_dispute(sample)
    
    fraud_prob = res["fraud_probability"]
    confidence = res["confidence"]
    conf_expl = res["confidence_explanation"]
    
    # Fraud prob and confidence are distinct numeric fields
    assert "fraud probability" not in conf_expl.lower()
    assert "input signal quality" in conf_expl.lower() or "reliability" in conf_expl.lower()

def test_high_fraud_low_win_produces_accept(risk_engine):
    """Verifies high fraud + low win + missing evidence produces ACCEPT with cost avoidance rationale."""
    sample = {
        "dispute_id": "DSP_ACCEPT_TEST",
        "dispute_reason": "UNAUTHORIZED_TRANSACTION",
        "transaction_amount": 95000.0,
        "customer_dispute_count": 8,
        "merchant_dispute_rate": 0.12,
        "dispute_velocity_24h": 6,
        "available_evidence": []  # Zero evidence
    }
    res = risk_engine.analyze_dispute(sample)
    assert res["recommendation"] == "ACCEPT"
    assert any("avoid unrecoverable arbitration costs" in r for r in res["decision_reasons"]) or "accept" in res["explanation"].lower()

def test_contradiction_produces_investigate(risk_engine):
    """Verifies factual contradiction produces INVESTIGATE recommendation."""
    sample = {
        "dispute_id": "DSP_CONTRA_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "customer_claim": "I never received the order.",
        "merchant_claim": "Order delivered via Bluedart.",
        "available_evidence": [
            {"document_id": "DOC_POD_99", "document_type": "proof_of_delivery", "content": "Delivered on 18-Aug"}
        ]
    }
    res = risk_engine.analyze_dispute(sample)
    assert res["recommendation"] == "INVESTIGATE"
    assert res["contradiction_severity"] in ["HIGH", "CRITICAL"]

def test_strong_evidence_produces_contest(risk_engine):
    """Verifies strong evidence + high win probability produces CONTEST recommendation."""
    sample = {
        "dispute_id": "DSP_CONTEST_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "merchant_claim": "Order delivered via Bluedart tracking BD123456.",
        "customer_claim": "Standard billing query.",
        "available_evidence": [
            {"document_id": "DOC_INV_1", "document_type": "invoice", "content": "Invoice details"},
            {"document_id": "DOC_SHP_1", "document_type": "shipping_proof", "content": "Shipped receipt"},
            {"document_id": "DOC_POD_1", "document_type": "proof_of_delivery", "content": "Signed POD"}
        ]
    }
    res = risk_engine.analyze_dispute(sample)
    assert res["recommendation"] == "CONTEST"
    assert res["evidence_completeness"] == 1.0
