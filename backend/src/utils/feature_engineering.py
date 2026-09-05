"""
Feature Engineering & Column Transformation Utilities.
Builds standardized scikit-learn ColumnTransformer objects to ensure 100% preprocessing consistency
between offline training scripts and real-time inference wrappers.
"""

import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from config.settings import (
    FRAUD_FEATURE_NAMES, WIN_FEATURE_NAMES,
    FRAUD_V2_NUMERIC_FEATURES, FRAUD_V2_CATEGORICAL_FEATURES, FRAUD_V2_BINARY_FEATURES
)

def get_fraud_preprocessor() -> ColumnTransformer:
    """Returns ColumnTransformer for Fraud Detection V1 features."""
    numeric_features = [
        "transaction_amount", "customer_avg_amount", "amount_deviation_ratio",
        "dispute_amount", "customer_dispute_count", "merchant_dispute_rate",
        "days_since_payment", "dispute_velocity_24h", "dispute_velocity_7d",
        "transaction_hour", "transaction_day_of_week", "customer_account_age_days"
    ]
    categorical_features = [
        "is_duplicate_flag", "reason_code_encoded", "merchant_high_risk_flag", "ip_billing_mismatch"
    ]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ],
        remainder="passthrough"
    )
    return preprocessor

def get_fraud_v2_preprocessor() -> ColumnTransformer:
    """Returns ColumnTransformer for Fraud Detection V2 features (Public Dataset)."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), FRAUD_V2_NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FRAUD_V2_CATEGORICAL_FEATURES),
            ("bin", "passthrough", FRAUD_V2_BINARY_FEATURES)
        ],
        remainder="drop"
    )
    return preprocessor

def get_win_preprocessor() -> ColumnTransformer:
    """Returns ColumnTransformer for Win Probability features."""
    numeric_features = [
        "evidence_completeness_score", "contradiction_count", "contradiction_max_severity",
        "fraud_probability", "merchant_historical_win_rate", "previous_disputes_won_count",
        "dispute_amount", "evidence_quality_score"
    ]
    categorical_features = [
        "reason_code_encoded", "has_invoice", "has_shipping_proof",
        "has_proof_of_delivery", "has_customer_communication"
    ]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ],
        remainder="passthrough"
    )
    return preprocessor
