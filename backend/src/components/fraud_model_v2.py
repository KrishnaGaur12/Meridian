"""
Component 8 (V2) — Fraud Detection ML Model Wrapper (Public Transaction-Level Dataset).
Loads trained sklearn Pipeline from models/fraud_v2_pipeline.joblib.
Operates on pre-authorization transaction feature schema.
Kept completely isolated from RiskEngine (V1 remains active pipeline default).
"""

from typing import Dict, Any, TypedDict
import pandas as pd
import joblib
from pathlib import Path

from config.settings import FRAUD_V2_PIPELINE_PATH, FRAUD_V2_ALL_FEATURES, format_pct
from src.schemas.transaction_input import validate_transaction_input
from src.utils.logger import get_logger

logger = get_logger("FraudModelV2Wrapper")

class FraudV2Prediction(TypedDict):
    fraud_probability: float
    risk_level: str
    model_version: str
    is_model_trained: bool

class FraudModelV2Wrapper:
    """Wrapper around trained Fraud V2 scikit-learn Pipeline."""
    
    def __init__(self, pipeline_path: Path = FRAUD_V2_PIPELINE_PATH):
        self.pipeline_path = pipeline_path
        self.pipeline = None
        self.is_trained = False
        self._load_pipeline()

    def _load_pipeline(self):
        if self.pipeline_path.exists():
            try:
                self.pipeline = joblib.load(self.pipeline_path)
                self.is_trained = True
                logger.info(f"Loaded trained Fraud V2 Pipeline from {self.pipeline_path}")
            except Exception as e:
                logger.warning(f"Failed to load Fraud V2 pipeline from {self.pipeline_path}: {e}")
                self.is_trained = False
        else:
            logger.warning(f"Fraud V2 pipeline file not found at {self.pipeline_path}.")
            self.is_trained = False

    @staticmethod
    def _safe_int(val, default: int) -> int:
        if val is None or isinstance(val, bool):
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(val, default: float) -> float:
        if val is None or isinstance(val, bool):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def extract_features(self, payload: Dict[str, Any]) -> pd.DataFrame:
        """Extracts and formats transaction features matching Fraud V2 schema safely."""
        is_valid, errors, validated = validate_transaction_input(payload)
        if is_valid and validated is not None:
            feature_dict = validated
        else:
            # Safe fallback conversion per feature without unhandled exceptions
            feature_dict = {
                "transaction_hour": self._safe_int(payload.get("transaction_hour"), 12),
                "account_age_days": self._safe_int(payload.get("account_age_days", payload.get("customer_account_age_days")), 180),
                "previous_chargebacks": self._safe_int(payload.get("previous_chargebacks", payload.get("customer_dispute_count")), 0),
                "transaction_amount": self._safe_float(payload.get("transaction_amount"), 100.0),
                "transaction_velocity_1h": self._safe_int(payload.get("transaction_velocity_1h"), 0),
                "transaction_velocity_24h": self._safe_int(payload.get("transaction_velocity_24h", payload.get("dispute_velocity_24h")), 0),
                "avg_transaction_amount_30d": self._safe_float(payload.get("avg_transaction_amount_30d", payload.get("customer_avg_amount")), 100.0),
                "merchant_category": str(payload.get("merchant_category", "retail")).strip().lower(),
                "transaction_country": str(payload.get("transaction_country", "US")).strip().upper(),
                "device_type": str(payload.get("device_type", "mobile")).strip().lower(),
                "is_international": self._safe_int(payload.get("is_international", payload.get("ip_billing_mismatch")), 0),
                "is_high_risk_merchant": self._safe_int(payload.get("is_high_risk_merchant", payload.get("merchant_high_risk_flag")), 0)
            }
        return pd.DataFrame([feature_dict])[FRAUD_V2_ALL_FEATURES]

    def predict(self, payload: Dict[str, Any]) -> FraudV2Prediction:
        """Predicts transaction fraud probability using Fraud V2 pipeline."""
        if not self.is_trained or self.pipeline is None:
            # Rule fallback if model file missing
            amt = self._safe_float(payload.get("transaction_amount"), 0.0)
            vel_1h = self._safe_int(payload.get("transaction_velocity_1h"), 0)
            is_intl = self._safe_int(payload.get("is_international"), 0)
            
            prob = 0.15
            if vel_1h >= 3 or is_intl == 1:
                prob = 0.55
            if amt >= 500.0 and vel_1h >= 2:
                prob = 0.85
                
            risk_level = "CRITICAL" if prob >= 0.70 else ("HIGH" if prob >= 0.50 else ("MEDIUM" if prob >= 0.30 else "LOW"))
            return FraudV2Prediction(
                fraud_probability=prob,
                risk_level=risk_level,
                model_version="fraud_v2_fallback",
                is_model_trained=False
            )
            
        df_feat = self.extract_features(payload)
        prob_array = self.pipeline.predict_proba(df_feat)
        prob = float(prob_array[0][1])
        prob = min(0.99, max(0.01, round(prob, 4)))

        if prob >= 0.70:
            risk_level = "CRITICAL"
        elif prob >= 0.50:
            risk_level = "HIGH"
        elif prob >= 0.30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return FraudV2Prediction(
            fraud_probability=prob,
            risk_level=risk_level,
            model_version="fraud_v2",
            is_model_trained=True
        )
