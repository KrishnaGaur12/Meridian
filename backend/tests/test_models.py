"""
Unit tests for ML model wrappers (Components 8 & 9).
"""

import pytest
from src.components.fraud_model import FraudModelWrapper
from src.components.win_probability import WinProbabilityModelWrapper

def test_fraud_model_prediction():
    wrapper = FraudModelWrapper()
    payload = {
        "transaction_amount": 5000.0,
        "dispute_amount": 5000.0,
        "customer_dispute_count": 0,
        "merchant_dispute_rate": 0.01,
        "days_since_payment": 5,
        "dispute_velocity_24h": 0,
        "is_duplicate_flag": 0,
        "dispute_reason": "GOODS_NOT_RECEIVED"
    }
    res = wrapper.predict(payload)
    assert "fraud_probability" in res
    assert "risk_level" in res
    assert 0.0 <= res["fraud_probability"] <= 1.0
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

def test_win_probability_prediction():
    wrapper = WinProbabilityModelWrapper()
    payload = {
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "dispute_amount": 5000.0,
        "merchant_historical_win_rate": 0.75,
        "previous_disputes_won_count": 10
    }
    res = wrapper.predict(
        dispute_payload=payload,
        completeness_score=1.0,
        evidence_quality_score=0.9,
        contradiction_count=0,
        contradiction_severity="NONE",
        fraud_prob=0.10,
        available_evidence=[{"document_type": "invoice"}, {"document_type": "proof_of_delivery"}]
    )
    assert "win_probability" in res
    assert 0.0 <= res["win_probability"] <= 1.0
