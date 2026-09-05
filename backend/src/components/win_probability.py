"""
Component 9 — Win Probability ML Model Wrapper (Hardened).
PRIMARY ML MODEL #2 WRAPPER.
Loads trained scikit-learn/XGBoost Pipeline from models/win_pipeline.joblib to predict merchant win probability.
"""

from typing import Dict, Any, TypedDict, List
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from config.settings import WIN_PIPELINE_PATH, WIN_FEATURE_NAMES
from src.components.reason_classifier import ReasonClassifier
from src.utils.logger import get_logger

logger = get_logger("WinProbabilityModelWrapper")

class WinProbabilityResult(TypedDict):
    win_probability: float
    is_model_trained: bool
    ml_status: str
    prediction_source: str
    confidence: str
    feature_summary: Dict[str, Any]

class WinProbabilityModelWrapper:
    """Predicts probability of merchant winning dispute defense using ML or calibrated fallback."""
    
    def __init__(self, pipeline_path: Path = WIN_PIPELINE_PATH):
        self.pipeline_path = pipeline_path
        self.pipeline = None
        self.reason_classifier = ReasonClassifier()
        self._load_pipeline()
        
    def _load_pipeline(self):
        """Loads trained joblib pipeline if exists."""
        if self.pipeline_path.exists():
            try:
                self.pipeline = joblib.load(self.pipeline_path)
                logger.info(f"Loaded trained Win Probability Pipeline from {self.pipeline_path}")
            except Exception as e:
                logger.warning(f"Could not load Win Probability Pipeline ({e}). Will use fallback.")
                self.pipeline = None
        else:
            logger.info("Win Probability ML pipeline file not found. Will use fallback until trained.")

    def extract_features(
        self,
        dispute_payload: Dict[str, Any],
        completeness_score: float,
        evidence_quality_score: float,
        contradiction_count: int,
        contradiction_max_severity: int,
        fraud_prob: float,
        available_evidence: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Extracts exact feature vector required by Win Probability Model."""
        reason_enum = self.reason_classifier.classify(dispute_payload.get("dispute_reason", dispute_payload.get("reason_code", "")))
        reason_encoded = self.reason_classifier.encode_reason(reason_enum)
        
        provided_types = set()
        for d in available_evidence:
            dtype = str(d.get("document_type", d.get("evidence_type", ""))).lower().strip()
            if dtype:
                provided_types.add(dtype)

        has_inv = 1 if (provided_types & {"invoice", "payment_confirmation", "payment_receipt", "receipt"}) else 0
        has_ship = 1 if (provided_types & {"shipping_proof", "shipping_confirmation", "carrier_manifest", "dispatch_proof"}) else 0
        has_pod = 1 if (provided_types & {"proof_of_delivery", "delivery_confirmation", "delivery_proof", "delivery_receipt"}) else 0
        has_comm = 1 if (provided_types & {"customer_communication", "customer_history", "chat_log", "support_ticket"}) else 0
        
        try:
            raw_win_rate = dispute_payload.get("merchant_historical_win_rate", 0.65)
            historical_win_rate = float(raw_win_rate)
        except (ValueError, TypeError):
            historical_win_rate = 0.65

        try:
            raw_won = dispute_payload.get("previous_disputes_won_count", 5)
            prev_won_count = int(raw_won)
        except (ValueError, TypeError):
            prev_won_count = 5

        try:
            raw_amt = dispute_payload.get("dispute_amount", dispute_payload.get("transaction_amount", dispute_payload.get("amount", 1000.0)))
            amount = float(raw_amt)
        except (ValueError, TypeError):
            amount = 1000.0


        feature_dict = {
            "reason_code_encoded": reason_encoded,
            "evidence_completeness_score": float(completeness_score),
            "has_invoice": has_inv,
            "has_shipping_proof": has_ship,
            "has_proof_of_delivery": has_pod,
            "has_customer_communication": has_comm,
            "contradiction_count": int(contradiction_count),
            "contradiction_max_severity": int(contradiction_max_severity),
            "fraud_probability": float(fraud_prob),
            "merchant_historical_win_rate": historical_win_rate,
            "previous_disputes_won_count": prev_won_count,
            "dispute_amount": amount,
            "evidence_quality_score": float(evidence_quality_score)
        }
        
        return pd.DataFrame([feature_dict])[WIN_FEATURE_NAMES]

    def predict(
        self,
        dispute_payload: Dict[str, Any],
        completeness_score: float,
        evidence_quality_score: float,
        contradiction_count: int,
        contradiction_severity: str,
        fraud_prob: float,
        available_evidence: List[Dict[str, Any]]
    ) -> WinProbabilityResult:
        """Predicts win probability with real ML model and certainty-derived confidence."""
        severity_map = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        sev_val = severity_map.get(contradiction_severity, 0)
        
        df_features = self.extract_features(
            dispute_payload=dispute_payload,
            completeness_score=completeness_score,
            evidence_quality_score=evidence_quality_score,
            contradiction_count=contradiction_count,
            contradiction_max_severity=sev_val,
            fraud_prob=fraud_prob,
            available_evidence=available_evidence
        )
        
        if self.pipeline is not None:
            try:
                probs = self.pipeline.predict_proba(df_features)
                win_prob = float(probs[0][1])
                is_trained = True
                ml_status = "OK"
                pred_source = "MODEL"
            except Exception as e:
                logger.warning(f"Error during Win ML prediction ({e}), using fallback.")
                win_prob = self._heuristic_fallback(completeness_score, evidence_quality_score, contradiction_count, sev_val, fraud_prob)
                is_trained = False
                ml_status = "UNAVAILABLE"
                pred_source = "RULE_FALLBACK"
        else:
            win_prob = self._heuristic_fallback(completeness_score, evidence_quality_score, contradiction_count, sev_val, fraud_prob)
            is_trained = False
            ml_status = "UNAVAILABLE"
            pred_source = "RULE_FALLBACK"
            
        win_prob = round(float(np.clip(win_prob, 0.01, 0.99)), 4)
        
        # Derive confidence from model margin / certainty
        margin = abs(win_prob - 0.50)
        if margin >= 0.25:
            confidence = "HIGH"
        elif margin >= 0.10:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return WinProbabilityResult(
            win_probability=win_prob,
            is_model_trained=is_trained,
            ml_status=ml_status,
            prediction_source=pred_source,
            confidence=confidence,
            feature_summary=df_features.to_dict(orient="records")[0]
        )
        
    def _heuristic_fallback(
        self,
        completeness: float,
        quality: float,
        contradictions: int,
        severity_val: int,
        fraud_prob: float
    ) -> float:
        """Deterministic mathematical formula for win probability fallback."""
        base = (completeness * 0.45) + (quality * 0.25)
        penalty = (contradictions * 0.15) + (severity_val * 0.08) + (fraud_prob * 0.25)
        raw_score = 0.35 + base - penalty
        return float(np.clip(raw_score, 0.05, 0.95))
