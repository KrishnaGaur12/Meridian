"""
Integration tests for end-to-end RiskEngine pipeline execution.
"""

import pytest
from src.pipeline.risk_engine import RiskEngine

def test_risk_engine_end_to_end():
    engine = RiskEngine(use_vector_search=False)
    sample_dispute = {
        "dispute_id": "TEST_DSP_001",
        "transaction_id": "TEST_TXN_001",
        "customer_id": "CUST_TEST",
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "transaction_amount": 2500.0,
        "dispute_amount": 2500.0,
        "customer_dispute_count": 0,
        "merchant_dispute_rate": 0.01,
        "available_evidence": [
            {
                "document_id": "D1",
                "document_type": "invoice",
                "content": "Invoice for 2500 INR",
                "customer_id": "CUST_TEST",
                "order_id": "TEST_TXN_001"
            },
            {
                "document_id": "D2",
                "document_type": "shipping_proof",
                "content": "Shipping proof details",
                "customer_id": "CUST_TEST",
                "order_id": "TEST_TXN_001"
            },
            {
                "document_id": "D3",
                "document_type": "proof_of_delivery",
                "content": "Signed POD",
                "customer_id": "CUST_TEST",
                "order_id": "TEST_TXN_001"
            }
        ]
    }
    
    result = engine.analyze_dispute(sample_dispute)
    
    assert result["dispute_id"] == "TEST_DSP_001"
    assert result["reason"] == "GOODS_NOT_RECEIVED"
    assert result["evidence_completeness"] == 1.0
    assert result["recommendation"] in ["CONTEST", "ACCEPT", "INVESTIGATE"]
    assert 0.0 <= result["fraud_probability"] <= 1.0
    assert 0.0 <= result["win_probability"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert len(result["explanation"]) > 20
