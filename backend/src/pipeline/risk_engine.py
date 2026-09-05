"""
End-to-End Orchestrator Pipeline — Razorpay AI Risk Engine (Hardened & Integrated V2).
Combines all AI & ML components into a single unified, transparent risk manager.
Uses Fraud Model V2 by default for transaction-level fraud predictions.
Strictly adheres to the 22-field JSON contract schema with 100% rounding consistency.
Fully hardened against missing or malformed input payloads.
"""

from typing import Dict, Any, Union
import json
from pathlib import Path

from src.components.reason_classifier import ReasonClassifier
from src.components.evidence_requirements import EvidenceRequirementEngine
from src.components.evidence_retrieval import EvidenceRetrievalEngine
from src.components.evidence_validation import EvidenceValidator
from src.components.completeness import EvidenceCompletenessEvaluator
from src.components.contradiction import ContradictionDetector
from src.components.fraud_rules import FraudRuleEngine
from src.components.fraud_model import FraudModelWrapper
from src.components.fraud_model_v2 import FraudModelV2Wrapper
from src.components.win_probability import WinProbabilityModelWrapper
from src.components.explanation import ExplanationGenerator
from src.components.recommendation import RecommendationEngine
from src.components.confidence import ConfidenceEngine
from src.schemas.transaction_input import validate_transaction_input
from config.settings import format_pct
from src.utils.logger import get_logger

logger = get_logger("RiskEnginePipeline")

class RiskEngine:
    """Master pipeline orchestrating all risk analysis components."""
    
    def __init__(
        self,
        fraud_model_version: str = "v2",
        enable_ollama: bool = False,
        use_vector_search: bool = True
    ):
        logger.info(f"Initializing Razorpay AI Risk Engine components (Fraud Model: {fraud_model_version})...")
        self.fraud_model_version = fraud_model_version.lower()
        
        self.reason_classifier = ReasonClassifier()
        self.requirement_engine = EvidenceRequirementEngine()
        self.retrieval_engine = EvidenceRetrievalEngine(use_vector_search=use_vector_search)
        self.validator = EvidenceValidator()
        self.completeness_evaluator = EvidenceCompletenessEvaluator()
        self.contradiction_detector = ContradictionDetector(enable_ollama=enable_ollama)
        self.fraud_rule_engine = FraudRuleEngine()
        
        if self.fraud_model_version == "v2":
            self.fraud_model = FraudModelV2Wrapper()
        else:
            self.fraud_model = FraudModelWrapper()
            
        self.win_model = WinProbabilityModelWrapper()
        self.recommendation_engine = RecommendationEngine()
        self.confidence_engine = ConfidenceEngine()
        self.explanation_generator = ExplanationGenerator(enable_ollama=enable_ollama)
        logger.info(f"Risk Engine ({self.fraud_model_version}) initialized successfully.")

    def analyze_dispute(self, dispute_input: Union[Dict[str, Any], str, Path, Any]) -> Dict[str, Any]:
        """
        Executes end-to-end AI risk analysis pipeline for a given dispute.
        Accepts dict payload or filepath to dispute JSON or arbitrary input.
        Returns complete structured risk analysis result complying with 22-field JSON contract.
        """
        if isinstance(dispute_input, (str, Path)):
            file_path = Path(dispute_input)
            if file_path.exists() and file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        dispute_payload = json.load(f)
                except Exception:
                    dispute_payload = {}
            else:
                dispute_payload = {}
        else:
            dispute_payload = dispute_input

        if not isinstance(dispute_payload, dict):
            dispute_payload = {}

        dispute_id = str(dispute_payload.get("dispute_id", "DSP_UNKNOWN"))
        raw_dup = dispute_payload.get("is_duplicate_flag", 0)
        try:
            is_dup_flag = int(raw_dup) if not isinstance(raw_dup, bool) else (1 if raw_dup else 0)
        except (ValueError, TypeError):
            is_dup_flag = 0

        logger.info(f"Starting risk engine analysis for dispute: {dispute_id}")

        # 1. Dispute Reason Classification
        reason_enum = self.reason_classifier.classify(dispute_payload)
        reason_str = reason_enum.value
        
        # 2. Evidence Requirements
        requirements = self.requirement_engine.get_requirements(reason_enum)
        
        # 3. Evidence Validation & Cross-Entity Isolation
        raw_evidence = dispute_payload.get("available_evidence", [])
        if not isinstance(raw_evidence, list):
            raw_evidence = []
        val_res = self.validator.validate(dispute_payload, raw_evidence)
        valid_evidence = val_res["valid_documents"]
        evidence_quality_score = val_res["quality_score"]
        quality_label = "HIGH" if evidence_quality_score >= 0.80 else ("MEDIUM" if evidence_quality_score >= 0.50 else "LOW")
        
        # 4. Evidence Retrieval over valid documents
        search_query = f"{reason_str} invoice delivery receipt shipping proof"
        retrieved_evidence = self.retrieval_engine.retrieve(search_query, valid_evidence, top_k=5)
        
        # 5. Evidence Completeness
        comp_res = self.completeness_evaluator.evaluate(
            required_evidence=requirements["required"],
            optional_evidence=requirements["optional"],
            available_evidence=valid_evidence
        )
        completeness_score = comp_res["completeness_score"]
        missing_required = comp_res["missing_required"]
        
        # 6. Contradiction Detection
        contra_res = self.contradiction_detector.detect(dispute_payload, valid_evidence)
        contradiction_count = len(contra_res["details"])
        
        # 7. Fraud Rule Evaluation
        rule_results = self.fraud_rule_engine.evaluate(dispute_payload)
        triggered_rules = [r["rule_name"] for r in rule_results if r["triggered"]]
        
        # 8. Fraud ML Model Prediction with Transaction Input Validation
        if self.fraud_model_version == "v2":
            is_valid_tx, val_errors, clean_tx_data = validate_transaction_input(dispute_payload)
            if is_valid_tx and clean_tx_data is not None:
                fraud_res = self.fraud_model.predict(clean_tx_data)
                fraud_probability = fraud_res["fraud_probability"]
                risk_level = fraud_res["risk_level"]
                fraud_model_trained = fraud_res["is_model_trained"]
                input_valid = True
            else:
                logger.warning(f"Fraud V2 transaction input invalid: {val_errors}")
                fraud_probability = 0.0
                risk_level = "UNKNOWN"
                fraud_model_trained = False
                input_valid = False
        else:
            fraud_res = self.fraud_model.predict(dispute_payload)
            fraud_probability = fraud_res["fraud_probability"]
            risk_level = fraud_res["risk_level"]
            fraud_model_trained = fraud_res["is_model_trained"]
            input_valid = True

        # 9. Win Probability ML Model Prediction
        win_res = self.win_model.predict(
            dispute_payload=dispute_payload,
            completeness_score=completeness_score,
            evidence_quality_score=evidence_quality_score,
            contradiction_count=contradiction_count,
            contradiction_severity=contra_res["severity"],
            fraud_prob=fraud_probability if fraud_probability is not None else 0.0,
            available_evidence=valid_evidence
        )
        win_probability = win_res["win_probability"]
        
        # 10. System Input Confidence Engine
        conf_res = self.confidence_engine.calculate(
            completeness_score=completeness_score,
            evidence_quality_score=evidence_quality_score,
            contradiction_confidence=contra_res["confidence"],
            fraud_model_trained=fraud_model_trained,
            win_model_trained=win_res["is_model_trained"]
        )
        confidence_score = conf_res["confidence_score"]
        
        # 11. Business Recommendation Engine
        rec_res = self.recommendation_engine.decide(
            completeness_score=completeness_score,
            evidence_quality_score=evidence_quality_score,
            missing_required=missing_required,
            has_contradiction=contra_res["contradiction"],
            contradiction_severity=contra_res["severity"],
            fraud_probability=fraud_probability if fraud_probability is not None else 0.0,
            win_probability=win_probability,
            confidence_score=confidence_score,
            is_duplicate_flag=is_dup_flag
        )
        recommendation = rec_res["recommendation"]
        
        # 12. Explanation Generator (Uses exact pipeline variables for 100% rounding match)
        explanation = self.explanation_generator.generate(
            dispute_id=dispute_id,
            reason=reason_str,
            completeness_score=completeness_score,
            evidence_quality=quality_label,
            missing_evidence=missing_required,
            contradictions_count=contradiction_count,
            fraud_probability=fraud_probability if fraud_probability is not None else 0.0,
            win_probability=win_probability,
            recommendation=recommendation,
            confidence=confidence_score,
            is_duplicate_flag=is_dup_flag
        )
        
        # Assemble exact 22-field JSON payload contract
        result = {
            "dispute_id": dispute_id,
            "reason": reason_str,
            "evidence_completeness": completeness_score,
            "evidence_quality": quality_label,
            "missing_evidence": missing_required,
            "contradictions": contradiction_count,
            "contradiction_type": contra_res["type"],
            "contradiction_severity": contra_res["severity"],
            "contradiction_evidence_a": contra_res["evidence_a"],
            "contradiction_evidence_b": contra_res["evidence_b"],
            "fraud_probability": fraud_probability,
            "risk_level": risk_level,
            "triggered_fraud_rules": triggered_rules,
            "win_probability": win_probability,
            "confidence": confidence_score,
            "confidence_level": conf_res["confidence_level"],
            "confidence_explanation": conf_res["formula_explanation"],
            "recommendation": recommendation,
            "decision_reasons": rec_res["decision_reasons"],
            "decision_factors": rec_res["decision_factors"],
            "explanation": explanation,
            "models_status": {
                "fraud_model": self.fraud_model_version,
                "fraud_model_trained": fraud_model_trained,
                "fraud_input_valid": input_valid,
                "win_model": "win_probability_v1",
                "win_model_trained": win_res["is_model_trained"]
            }
        }
        
        logger.info(f"Completed analysis for dispute {dispute_id}: {recommendation} (Confidence: {format_pct(confidence_score)}%)")
        return result
