"""
Script: prepare_fraud_v2_data.py
Ingests public transaction fraud dataset (data/external/fraud_dataset.csv).
Performs customer-level grouped splitting based on customer_id (70% Train / 15% Val / 15% Test).
Verifies ZERO customer overlap across splits and saves processed CSV files.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import FRAUD_V2_DATASET_PATH, PROCESSED_DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("PrepareFraudV2Data")

def main():
    logger.info("Initializing Fraud Model V2 Data Preparation...")
    
    if not FRAUD_V2_DATASET_PATH.exists():
        raise FileNotFoundError(f"Fraud V2 external dataset not found at {FRAUD_V2_DATASET_PATH}")
        
    df = pd.read_csv(FRAUD_V2_DATASET_PATH)
    logger.info(f"Loaded raw dataset from {FRAUD_V2_DATASET_PATH} — Shape: {df.shape}")
    
    total_rows = len(df)
    total_fraud = int(df["risk_label"].sum())
    total_non_fraud = total_rows - total_fraud
    total_cust = df["customer_id"].nunique()
    
    logger.info(f"Dataset Stats — Total Rows: {total_rows} | Fraud: {total_fraud} ({total_fraud/total_rows:.2%}) | Non-Fraud: {total_non_fraud} | Unique Customers: {total_cust}")
    
    # 1. Customer-level Grouped Split: 70% Train, 30% Temp (Val + Test)
    gss1 = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=42)
    train_idx, temp_idx = next(gss1.split(df, groups=df["customer_id"]))
    
    df_train = df.iloc[train_idx].copy().reset_index(drop=True)
    df_temp = df.iloc[temp_idx].copy().reset_index(drop=True)
    
    # 2. Split Temp into 50% Val (15% overall) and 50% Test (15% overall)
    gss2 = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=42)
    val_idx, test_idx = next(gss2.split(df_temp, groups=df_temp["customer_id"]))
    
    df_val = df_temp.iloc[val_idx].copy().reset_index(drop=True)
    df_test = df_temp.iloc[test_idx].copy().reset_index(drop=True)
    
    train_customers = set(df_train["customer_id"].unique())
    val_customers = set(df_val["customer_id"].unique())
    test_customers = set(df_test["customer_id"].unique())
    
    # Leakage Verification
    overlap_train_val = train_customers.intersection(val_customers)
    overlap_train_test = train_customers.intersection(test_customers)
    overlap_val_test = val_customers.intersection(test_customers)
    
    logger.info("\n--- CUSTOMER LEAKAGE VERIFICATION ---")
    logger.info(f"Train Customers: {len(train_customers)}")
    logger.info(f"Val Customers  : {len(val_customers)}")
    logger.info(f"Test Customers : {len(test_customers)}")
    logger.info(f"Overlap Train-Val  : {len(overlap_train_val)}")
    logger.info(f"Overlap Train-Test : {len(overlap_train_test)}")
    logger.info(f"Overlap Val-Test   : {len(overlap_val_test)}")
    
    if len(overlap_train_val) > 0 or len(overlap_train_test) > 0 or len(overlap_val_test) > 0:
        raise ValueError("CRITICAL DATA LEAKAGE ERROR: Customer IDs overlap across train/val/test splits!")
        
    logger.info("VERIFICATION PASSED: Zero customer overlap across all 3 splits!")
    
    def log_split_stats(name: str, split_df: pd.DataFrame):
        rows = len(split_df)
        f_count = int(split_df["risk_label"].sum())
        nf_count = rows - f_count
        f_rate = f_count / float(max(1, rows))
        c_count = split_df["customer_id"].nunique()
        logger.info(f"Split {name:<6} — Rows: {rows:<4} | Fraud: {f_count:<3} ({f_rate:.2%}) | Non-Fraud: {nf_count:<4} | Unique Cust: {c_count}")

    logger.info("\n--- SPLIT STATISTICS SUMMARY ---")
    log_split_stats("TRAIN", df_train)
    log_split_stats("VAL", df_val)
    log_split_stats("TEST", df_test)
    
    # Save Processed CSVs
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    train_path = PROCESSED_DATA_DIR / "fraud_v2_train.csv"
    val_path = PROCESSED_DATA_DIR / "fraud_v2_val.csv"
    test_path = PROCESSED_DATA_DIR / "fraud_v2_test.csv"
    
    df_train.to_csv(train_path, index=False)
    df_val.to_csv(val_path, index=False)
    df_test.to_csv(test_path, index=False)
    
    logger.info(f"\nSaved processed V2 datasets to:\n - {train_path}\n - {val_path}\n - {test_path}")

if __name__ == "__main__":
    main()
