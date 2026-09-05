"""
Script: prepare_data.py
Preprocesses datasets, performs feature scaling/transformation and stratified train/val/test splits,
saving output matrices into data/processed/.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from sklearn.model_selection import train_test_split
from config.settings import SYNTHETIC_DATA_DIR, PROCESSED_DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("PrepareDataScript")

def main():
    logger.info("Starting Data Preparation & Feature Engineering...")
    
    fraud_raw = SYNTHETIC_DATA_DIR / "raw_fraud_transactions.csv"
    win_raw = SYNTHETIC_DATA_DIR / "raw_win_disputes.csv"
    
    if not fraud_raw.exists() or not win_raw.exists():
        logger.error("Raw synthetic datasets not found. Please run 'python scripts/download_data.py' first.")
        return

    # 1. Prepare Fraud Data Splits
    logger.info("Processing Fraud Detection Dataset...")
    df_fraud = pd.read_csv(fraud_raw)
    
    train_fraud, test_fraud = train_test_split(df_fraud, test_size=0.20, random_state=42, stratify=df_fraud['is_fraud'])
    train_fraud, val_fraud = train_test_split(train_fraud, test_size=0.15, random_state=42, stratify=train_fraud['is_fraud'])
    
    train_fraud.to_csv(PROCESSED_DATA_DIR / "fraud_train.csv", index=False)
    val_fraud.to_csv(PROCESSED_DATA_DIR / "fraud_val.csv", index=False)
    test_fraud.to_csv(PROCESSED_DATA_DIR / "fraud_test.csv", index=False)
    logger.info(f"Fraud splits created: Train={len(train_fraud)}, Val={len(val_fraud)}, Test={len(test_fraud)}")

    # 2. Prepare Win Probability Data Splits
    logger.info("Processing Win Probability Dataset...")
    df_win = pd.read_csv(win_raw)
    
    train_win, test_win = train_test_split(df_win, test_size=0.20, random_state=42, stratify=df_win['merchant_won'])
    train_win, val_win = train_test_split(train_win, test_size=0.15, random_state=42, stratify=train_win['merchant_won'])
    
    train_win.to_csv(PROCESSED_DATA_DIR / "win_train.csv", index=False)
    val_win.to_csv(PROCESSED_DATA_DIR / "win_val.csv", index=False)
    test_win.to_csv(PROCESSED_DATA_DIR / "win_test.csv", index=False)
    logger.info(f"Win probability splits created: Train={len(train_win)}, Val={len(val_win)}, Test={len(test_win)}")
    
    logger.info("All data preparation & feature matrix splits completed successfully.")

if __name__ == "__main__":
    main()
