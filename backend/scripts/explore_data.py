"""
Script: explore_data.py
Explores raw & synthetic datasets, displaying statistical summaries, missing values,
class distributions, and correlation details.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from config.settings import SYNTHETIC_DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("ExploreDataScript")

def main():
    fraud_csv = SYNTHETIC_DATA_DIR / "raw_fraud_transactions.csv"
    win_csv = SYNTHETIC_DATA_DIR / "raw_win_disputes.csv"
    
    if not fraud_csv.exists() or not win_csv.exists():
        logger.error("Datasets not found. Please run 'python scripts/download_data.py' first.")
        return

    print("==================================================")
    print("      RAZORPAY AI RISK MANAGER — DATA EXPLORATION  ")
    print("==================================================")
    
    # Fraud Dataset EDA
    df_fraud = pd.read_csv(fraud_csv)
    print("\n--- 1. FRAUD DETECTION DATASET ---")
    print(f"Shape: {df_fraud.shape[0]} rows, {df_fraud.shape[1]} columns")
    print("\nClass Distribution ('is_fraud'):")
    fraud_counts = df_fraud['is_fraud'].value_counts(normalize=True)
    for val, pct in fraud_counts.items():
        label = "Fraud" if val == 1 else "Legitimate"
        print(f"  {label} ({val}): {pct*100:.2f}% ({df_fraud['is_fraud'].value_counts()[val]} samples)")
    print("\nSummary Statistics:")
    print(df_fraud.describe().round(2).T[['mean', 'std', 'min', '50%', 'max']])
    
    # Win Probability Dataset EDA
    df_win = pd.read_csv(win_csv)
    print("\n--- 2. WIN PROBABILITY DATASET ---")
    print(f"Shape: {df_win.shape[0]} rows, {df_win.shape[1]} columns")
    print("\nClass Distribution ('merchant_won'):")
    win_counts = df_win['merchant_won'].value_counts(normalize=True)
    for val, pct in win_counts.items():
        label = "Merchant Won" if val == 1 else "Merchant Lost"
        print(f"  {label} ({val}): {pct*100:.2f}% ({df_win['merchant_won'].value_counts()[val]} samples)")
    print("\nSummary Statistics:")
    print(df_win.describe().round(2).T[['mean', 'std', 'min', '50%', 'max']])
    print("\n==================================================")

if __name__ == "__main__":
    main()
