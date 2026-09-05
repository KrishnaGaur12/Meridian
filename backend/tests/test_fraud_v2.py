"""
Unit Tests for Fraud Detection Model V2 (Public Transaction-Level Dataset).
Tests dataset loading, column presence, target binary values, ID exclusion,
customer-level zero overlap, pipeline prediction range, joblib serialization, and wrapper response schema.
"""

import pytest
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from config.settings import (
    FRAUD_V2_DATASET_PATH, FRAUD_V2_PIPELINE_PATH, PROCESSED_DATA_DIR,
    FRAUD_V2_ALL_FEATURES, FRAUD_V2_NUMERIC_FEATURES, FRAUD_V2_CATEGORICAL_FEATURES, FRAUD_V2_BINARY_FEATURES
)
from src.components.fraud_model_v2 import FraudModelV2Wrapper

def test_1_dataset_loads_successfully():
    """Verifies public external fraud dataset loads and has expected 5,000 row count."""
    assert FRAUD_V2_DATASET_PATH.exists(), f"Dataset file missing at {FRAUD_V2_DATASET_PATH}"
    df = pd.read_csv(FRAUD_V2_DATASET_PATH)
    assert len(df) == 5000, f"Expected 5,000 rows, got {len(df)}"

def test_2_required_columns_exist():
    """Verifies all expected feature columns and identifiers exist in raw dataset."""
    df = pd.read_csv(FRAUD_V2_DATASET_PATH)
    expected_cols = [
        "transaction_id", "customer_id", "transaction_hour", "account_age_days",
        "previous_chargebacks", "merchant_category", "transaction_country",
        "device_type", "is_international", "is_high_risk_merchant",
        "transaction_amount", "transaction_velocity_1h", "transaction_velocity_24h",
        "avg_transaction_amount_30d", "risk_label"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Required column '{col}' missing from dataset."

def test_3_target_contains_0_and_1():
    """Verifies risk_label target column is binary (0 and 1)."""
    df = pd.read_csv(FRAUD_V2_DATASET_PATH)
    unique_labels = set(df["risk_label"].unique())
    assert unique_labels == {0, 1}, f"Target labels should be {{0, 1}}, got {unique_labels}"

def test_4_ids_excluded_from_model_features():
    """Verifies transaction_id and customer_id are excluded from model training feature list."""
    assert "transaction_id" not in FRAUD_V2_ALL_FEATURES
    assert "customer_id" not in FRAUD_V2_ALL_FEATURES
    assert len(FRAUD_V2_ALL_FEATURES) == 12

def test_5_train_val_test_customer_sets_do_not_overlap():
    """Verifies zero customer overlap across train, validation, and test splits."""
    train_df = pd.read_csv(PROCESSED_DATA_DIR / "fraud_v2_train.csv")
    val_df = pd.read_csv(PROCESSED_DATA_DIR / "fraud_v2_val.csv")
    test_df = pd.read_csv(PROCESSED_DATA_DIR / "fraud_v2_test.csv")
    
    train_cust = set(train_df["customer_id"].unique())
    val_cust = set(val_df["customer_id"].unique())
    test_cust = set(test_df["customer_id"].unique())
    
    assert len(train_cust.intersection(val_cust)) == 0, "Train and Val customer sets overlap!"
    assert len(train_cust.intersection(test_cust)) == 0, "Train and Test customer sets overlap!"
    assert len(val_cust.intersection(test_cust)) == 0, "Val and Test customer sets overlap!"

def test_6_pipeline_produces_probability_between_0_and_1():
    """Verifies loaded pipeline outputs probability strictly in range [0.0, 1.0]."""
    assert FRAUD_V2_PIPELINE_PATH.exists()
    pipe = joblib.load(FRAUD_V2_PIPELINE_PATH)
    
    sample_df = pd.DataFrame([{
        "transaction_hour": 14,
        "account_age_days": 120,
        "previous_chargebacks": 0,
        "transaction_amount": 250.0,
        "transaction_velocity_1h": 1,
        "transaction_velocity_24h": 3,
        "avg_transaction_amount_30d": 200.0,
        "merchant_category": "electronics",
        "transaction_country": "US",
        "device_type": "mobile",
        "is_international": 0,
        "is_high_risk_merchant": 0
    }])
    
    probs = pipe.predict_proba(sample_df)[:, 1]
    prob = probs[0]
    assert 0.0 <= prob <= 1.0, f"Probability out of range: {prob}"

def test_7_saved_pipeline_loads_and_predicts_correctly():
    """Verifies joblib pipeline loads cleanly and returns predictable array shape."""
    pipe = joblib.load(FRAUD_V2_PIPELINE_PATH)
    test_df = pd.read_csv(PROCESSED_DATA_DIR / "fraud_v2_test.csv")[FRAUD_V2_ALL_FEATURES].head(5)
    probs = pipe.predict_proba(test_df)
    assert probs.shape == (5, 2)

def test_8_v2_model_wrapper_returns_expected_schema():
    """Verifies FraudModelV2Wrapper returns required prediction keys and data types."""
    wrapper = FraudModelV2Wrapper()
    assert wrapper.is_trained, "Fraud V2 wrapper reported untrained status."
    
    sample_payload = {
        "transaction_hour": 3,
        "account_age_days": 5,
        "previous_chargebacks": 2,
        "transaction_amount": 95000.0,
        "transaction_velocity_1h": 4,
        "transaction_velocity_24h": 8,
        "avg_transaction_amount_30d": 1200.0,
        "merchant_category": "online_services",
        "transaction_country": "CA",
        "device_type": "desktop",
        "is_international": 1,
        "is_high_risk_merchant": 1
    }
    
    res = wrapper.predict(sample_payload)
    assert "fraud_probability" in res
    assert "risk_level" in res
    assert "model_version" in res
    assert "is_model_trained" in res
    assert res["model_version"] == "fraud_v2"
    assert 0.0 <= res["fraud_probability"] <= 1.0
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
