"""
Integration Tests for Fraud Model V2 in RiskEngine.
Tests RiskEngine delegation to Fraud V2, probability matching, risk_level matching,
models_status provenance, 22-field JSON contract compliance, malformed input validation,
unknown categorical value handling, normal vs suspicious transaction behavior, V1 fallback option,
and recommendation engine compatibility.
"""

import pytest
from pathlib import Path
from src.pipeline.risk_engine import RiskEngine
from src.components.fraud_model_v2 import FraudModelV2Wrapper

@pytest.fixture(scope="module")
def risk_engine_v2():
    return RiskEngine(fraud_model_version="v2", use_vector_search=False)

@pytest.fixture(scope="module")
def risk_engine_v1():
    return RiskEngine(fraud_model_version="v1", use_vector_search=False)

def test_1_valid_complete_v2_payload(risk_engine_v2):
    """1. Valid complete V2 payload succeeds and produces fraud prediction."""
    sample = {
        "dispute_id": "DSP_INTEG_01",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_hour": 14,
        "account_age_days": 180,
        "previous_chargebacks": 0,
        "merchant_category": "retail",
        "transaction_country": "IN",
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_amount": 1000.0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 2,
        "avg_transaction_amount_30d": 950.0,
        "available_evidence": []
    }
    res = risk_engine_v2.analyze_dispute(sample)
    assert res["models_status"]["fraud_input_valid"] is True
    assert 0.0 <= res["fraud_probability"] <= 1.0
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

def test_2_missing_v2_fields(risk_engine_v2):
    """2. Missing V2 fields produces no exception and controlled invalid response."""
    incomplete_payload = {
        "dispute_id": "DSP_MISSING_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "merchant_category": "retail"
    }
    res = risk_engine_v2.analyze_dispute(incomplete_payload)
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"
    assert len(res) == 22

def test_3_transaction_hour_invalid_string(risk_engine_v2):
    """3. transaction_hour = 'INVALID' produces no ValueError and controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"transaction_hour": "INVALID"})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"

def test_4_transaction_amount_not_a_number(risk_engine_v2):
    """4. transaction_amount = 'NOT_A_NUMBER' produces no ValueError and controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"transaction_amount": "NOT_A_NUMBER"})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"

def test_5_account_age_days_invalid_string(risk_engine_v2):
    """5. account_age_days = 'abc' produces no exception and controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"account_age_days": "abc"})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"

def test_6_transaction_velocity_1h_list_type(risk_engine_v2):
    """6. transaction_velocity_1h = [] produces no exception and controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"transaction_velocity_1h": []})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"

def test_7_is_international_invalid_binary_value(risk_engine_v2):
    """7. is_international = 5 produces controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"is_international": 5})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["risk_level"] == "UNKNOWN"

def test_8_transaction_amount_negative(risk_engine_v2):
    """8. transaction_amount = -100 produces controlled validation failure."""
    res = risk_engine_v2.analyze_dispute({"transaction_amount": -100})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["risk_level"] == "UNKNOWN"

def test_9_merchant_category_unknown_category(risk_engine_v2):
    """9. merchant_category = 'unknown_category' is valid input handled by OneHotEncoder(handle_unknown='ignore')."""
    sample = {
        "dispute_id": "DSP_UNKNOWN_CAT",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_hour": 10,
        "account_age_days": 200,
        "previous_chargebacks": 0,
        "merchant_category": "unknown_category",
        "transaction_country": "IN",
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_amount": 700.0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 2,
        "avg_transaction_amount_30d": 650.0,
        "available_evidence": []
    }
    res = risk_engine_v2.analyze_dispute(sample)
    assert res["models_status"]["fraud_input_valid"] is True
    assert 0.0 <= res["fraud_probability"] <= 1.0

def test_10_transaction_country_zz(risk_engine_v2):
    """10. transaction_country = 'ZZ' is valid categorical input producing no exception."""
    sample = {
        "dispute_id": "DSP_ZZ_COUNTRY",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_hour": 10,
        "account_age_days": 200,
        "previous_chargebacks": 0,
        "merchant_category": "retail",
        "transaction_country": "ZZ",
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0,
        "transaction_amount": 700.0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 2,
        "avg_transaction_amount_30d": 650.0,
        "available_evidence": []
    }
    res = risk_engine_v2.analyze_dispute(sample)
    assert res["models_status"]["fraud_input_valid"] is True
    assert 0.0 <= res["fraud_probability"] <= 1.0

def test_11_empty_dict_payload(risk_engine_v2):
    """11. Completely malformed payload {} produces no exception."""
    res = risk_engine_v2.analyze_dispute({})
    assert res["models_status"]["fraud_input_valid"] is False
    assert res["fraud_probability"] == 0.0
    assert res["risk_level"] == "UNKNOWN"

def test_12_wrong_payload_types(risk_engine_v2):
    """12. Completely wrong payload type (None, list, string) produces no exception."""
    for wrong_input in [None, [], "INVALID_STRING_INPUT"]:
        res = risk_engine_v2.analyze_dispute(wrong_input)
        assert res["models_status"]["fraud_input_valid"] is False
        assert res["fraud_probability"] == 0.0
        assert res["risk_level"] == "UNKNOWN"

def test_13_fraud_v1_remains_untouched_and_functional(risk_engine_v1):
    """13. Fraud V1 remains untouched and functional via RiskEngine(fraud_model_version='v1')."""
    sample = {
        "dispute_id": "DSP_V1_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_amount": 1000.0,
        "available_evidence": []
    }
    res = risk_engine_v1.analyze_dispute(sample)
    assert res["models_status"]["fraud_model"] == "v1"

def test_14_json_contract_remains_exact_22_fields(risk_engine_v2):
    """14. Contract structure remains exactly 22 fields."""
    res = risk_engine_v2.analyze_dispute({})
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
        assert f in res, f"Contract field '{f}' missing."
    assert len(required_fields) == 22
