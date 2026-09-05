"""
Unit tests for deterministic components (1-7, 10-12).
"""

import pytest
from config.settings import DisputeReason
from src.components.reason_classifier import ReasonClassifier
from src.components.evidence_requirements import EvidenceRequirementEngine
from src.components.evidence_validation import EvidenceValidator
from src.components.completeness import EvidenceCompletenessEvaluator
from src.components.contradiction import ContradictionDetector
from src.components.fraud_rules import FraudRuleEngine
from src.components.recommendation import RecommendationEngine
from src.components.confidence import ConfidenceEngine
from src.components.explanation import ExplanationGenerator

def test_reason_classifier():
    classifier = ReasonClassifier()
    assert classifier.classify("Item never arrived") == DisputeReason.GOODS_NOT_RECEIVED
    assert classifier.classify("defective product") == DisputeReason.GOODS_NOT_AS_DESCRIBED
    assert classifier.classify("stolen card fraud") == DisputeReason.UNAUTHORIZED_TRANSACTION
    assert classifier.classify("charged twice") == DisputeReason.DUPLICATE_TRANSACTION
    assert classifier.classify("unknown reason xyz") == DisputeReason.OTHER

def test_evidence_requirements():
    engine = EvidenceRequirementEngine()
    reqs = engine.get_requirements(DisputeReason.GOODS_NOT_RECEIVED)
    assert "invoice" in reqs["required"]
    assert "proof_of_delivery" in reqs["required"]
    assert "shipping_proof" in reqs["required"]

def test_evidence_completeness():
    evaluator = EvidenceCompletenessEvaluator()
    required = ["invoice", "shipping_proof", "proof_of_delivery"]
    optional = ["customer_communication"]
    available = [
        {"document_type": "invoice"},
        {"document_type": "shipping_proof"}
    ]
    res = evaluator.evaluate(required, optional, available)
    assert res["completeness_score"] == pytest.approx(0.6667, abs=0.01)
    assert "proof_of_delivery" in res["missing_required"]

def test_evidence_validator_cross_entity_isolation():
    validator = EvidenceValidator()
    dispute_payload = {
        "dispute_id": "DSP_1",
        "customer_id": "CUST_1",
        "transaction_id": "TXN_1",
        "dispute_timestamp": "2026-08-20T10:00:00"
    }
    # Mismatched customer ID should be rejected
    mismatched_evidence = [
        {
            "document_id": "DOC_99",
            "document_type": "invoice",
            "content": "Valid invoice content for OTHER_CUST",
            "customer_id": "OTHER_CUST",
            "order_id": "TXN_1",
            "dispute_id": "DSP_1",
            "timestamp": "2026-08-15T10:00:00"
        }
    ]
    res = validator.validate(dispute_payload, mismatched_evidence)
    assert res["is_valid"] is False
    assert len(res["valid_documents"]) == 0
    assert any("SECURITY" in w for w in res["warnings"])

def test_contradiction_detector_citations():
    detector = ContradictionDetector()
    payload = {
        "dispute_reason": "GOODS_NOT_RECEIVED",
        "customer_claim": "I never received the order.",
        "merchant_claim": "Order delivered via Bluedart."
    }
    evidence = [{"document_id": "POD_101", "document_type": "proof_of_delivery", "content": "Delivered on 18-Aug"}]
    res = detector.detect(payload, evidence)
    assert res["contradiction"] is True
    assert res["severity"] == "HIGH"
    assert "POD_101" in res["evidence_a"]
    assert "CUSTOMER_STATEMENT" in res["evidence_b"]

def test_fraud_rule_engine():
    engine = FraudRuleEngine()
    payload = {
        "dispute_amount": 35000.0,
        "dispute_velocity_24h": 3,
        "customer_dispute_count": 4
    }
    rules = engine.evaluate(payload)
    triggered = [r["rule_name"] for r in rules if r["triggered"]]
    assert "HIGH_DISPUTE_AMOUNT" in triggered
    assert "DISPUTE_VELOCITY_SPIKE" in triggered
    assert "REPEAT_CUSTOMER_DISPUTES" in triggered

def test_recommendation_engine_matrix():
    rec = RecommendationEngine()
    # High win prob & completeness -> CONTEST
    r1 = rec.decide(0.9, 0.9, [], False, "NONE", 0.1, 0.85, 0.9)
    assert r1["recommendation"] == "CONTEST"
    
    # Low win prob -> ACCEPT
    r2 = rec.decide(0.2, 0.4, ["invoice", "pod"], False, "NONE", 0.1, 0.20, 0.8)
    assert r2["recommendation"] == "ACCEPT"
    
    # High severity contradiction -> INVESTIGATE
    r3 = rec.decide(0.9, 0.9, [], True, "HIGH", 0.1, 0.85, 0.9)
    assert r3["recommendation"] == "INVESTIGATE"

def test_confidence_engine():
    conf = ConfidenceEngine()
    res = conf.calculate(1.0, 1.0, 0.95, True, True)
    assert res["confidence_score"] >= 0.85
    assert res["confidence_level"] == "HIGH"
    assert "System Confidence" in res["formula_explanation"]

def test_explanation_generator_phrasing():
    gen = ExplanationGenerator()
    expl = gen.generate("DSP_1", "GOODS_NOT_RECEIVED", 1.0, "HIGH", [], 0, 0.10, 0.89, "CONTEST", 0.95)
    assert "DSP_1" in expl
    assert "CONTEST" in expl
    assert "high (89%)" in expl or "high" in expl
    assert "borderline" not in expl  # 89% should never be called borderline!
