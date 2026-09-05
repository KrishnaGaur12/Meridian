"""
Component 8 — Fraud Detection ML Model Wrapper (Hardened).
PRIMARY ML MODEL #1 WRAPPER.
Loads trained scikit-learn/XGBoost Pipeline from models/fraud_pipeline.joblib.
Extracts features and predicts fraud probability and risk level.
"""

from typing import Dict, Any, TypedDict
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from config.settings import FRAUD_PIPELINE_PATH, FRAUD_FEATURE_NAMES, FRAUD_PROBABILITY_HIGH, FRAUD_PROBABILITY_MEDIUM
from src.components.reason_classifier import ReasonClassifier
from src.components.fraud_rules import FraudRuleEngine
from src.utils.logger import get_logger

logger = get_logger("FraudModelWrapper")

class FraudPredictionResult(TypedDict):
    fraud_probability: float
    risk_level: str
    is_model_trained: bool
    feature_contributions: Dict[str, float]

class FraudModelWrapper:
    """Predicts fraud risk using trained pipeline or heuristic rule fallback."""
    
    def __init__(self, pipeline_path: Path = FRAUD_PIPELINE_PATH):
        self.pipeline_path = pipeline_path
        self.pipeline = None
        self.reason_classifier = ReasonClassifier()
        self.rule_engine = FraudRuleEngine()
        self._load_pipeline()
        
    def _load_pipeline(self):
        """Loads trained joblib pipeline if exists."""
        if self.pipeline_path.exists():
            try:
                self.pipeline = joblib.load(self.pipeline_path)
                logger.info(f"Loaded trained Fraud Pipeline from {self.pipeline_path}")
            except Exception as e:
                logger.warning(f"Could not load Fraud Pipeline ({e}). Will use rule fallback.")
                self.pipeline = None
        else:
            logger.info("Fraud ML pipeline file not found. Will use rule fallback until trained.")

    def extract_features(self, dispute_payload: Dict[str, Any]) -> pd.DataFrame:
        """Extracts and encodes exact feature vector expected by Fraud Model."""
        reason_enum = self.reason_classifier.classify(dispute_payload.get("dispute_reason", ""))
        reason_encoded = self.reason_classifier.encode_reason(reason_enum)
        
        tx_amt = float(dispute_payload.get("transaction_amount", 1000.0))
        cust_avg = float(dispute_payload.get("customer_avg_amount", tx_amt))
        dev_ratio = round(tx_amt / max(cust_avg, 50.0), 4)
        
        feature_dict = {
            "transaction_amount": tx_amt,
            "customer_avg_amount": cust_avg,
            "amount_deviation_ratio": dev_ratio,
            "dispute_amount": float(dispute_payload.get("dispute_amount", tx_amt)),
            "customer_dispute_count": int(dispute_payload.get("customer_dispute_count", 0)),
            "merchant_dispute_rate": float(dispute_payload.get("merchant_dispute_rate", 0.01)),
            "days_since_payment": int(dispute_payload.get("days_since_payment", 7)),
            "dispute_velocity_24h": int(dispute_payload.get("dispute_velocity_24h", 0)),
            "dispute_velocity_7d": int(dispute_payload.get("dispute_velocity_7d", 0)),
            "is_duplicate_flag": int(dispute_payload.get("is_duplicate_flag", 0)),
            "transaction_hour": int(dispute_payload.get("transaction_hour", 14)),
            "transaction_day_of_week": int(dispute_payload.get("transaction_day_of_week", 2)),
            "reason_code_encoded": reason_encoded,
            "merchant_high_risk_flag": int(dispute_payload.get("merchant_high_risk_flag", 0)),
            "customer_account_age_days": int(dispute_payload.get("customer_account_age_days", 90)),
            "ip_billing_mismatch": int(dispute_payload.get("ip_billing_mismatch", 0))
        }
        
        return pd.DataFrame([feature_dict])[FRAUD_FEATURE_NAMES]

    def predict(self, dispute_payload: Dict[str, Any]) -> FraudPredictionResult:
        """Predicts fraud probability and risk level."""
        df_features = self.extract_features(dispute_payload)
        
        if self.pipeline is not None:
            try:
                probs = self.pipeline.predict_proba(df_features)
                fraud_prob = float(probs[0][1])
                is_trained = True
            except Exception as e:
                logger.warning(f"Error during ML prediction ({e}), falling back to rules.")
                rule_results = self.rule_engine.evaluate(dispute_payload)
                fraud_prob = self.rule_engine.compute_aggregate_rule_risk(rule_results)
                is_trained = False
        else:
            rule_results = self.rule_engine.evaluate(dispute_payload)
            fraud_prob = self.rule_engine.compute_aggregate_rule_risk(rule_results)
            is_trained = False
            
        fraud_prob = round(float(np.clip(fraud_prob, 0.01, 0.99)), 4)
        
        if fraud_prob >= 0.85:
            risk_level = "CRITICAL"
        elif fraud_prob >= FRAUD_PROBABILITY_HIGH:
            risk_level = "HIGH"
        elif fraud_prob >= FRAUD_PROBABILITY_MEDIUM:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        return FraudPredictionResult(
            fraud_probability=fraud_prob,
            risk_level=risk_level,
            is_model_trained=is_trained,
            feature_contributions=df_features.to_dict(orient="records")[0]
        )
