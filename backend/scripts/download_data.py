"""
Script: download_data.py
Generates realistic synthetic Razorpay-shaped dispute & transaction datasets,
as well as 5 distinct scenario JSON files for end-to-end pipeline testing.
"""

import sys
from pathlib import Path

# Add project root to python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.data_generator import (
    generate_fraud_dataset,
    generate_win_probability_dataset,
    generate_scenario_files
)
from config.settings import SYNTHETIC_DATA_DIR
from src.utils.logger import get_logger

logger = get_logger("DownloadDataScript")

def main():
    logger.info("Initializing Data Preparation & Generation Process...")
    
    # 1. Generate Synthetic Fraud Dataset
    logger.info("Generating synthetic fraud transaction dataset (2,000 samples)...")
    df_fraud = generate_fraud_dataset(n_samples=2000, random_state=42)
    fraud_path = SYNTHETIC_DATA_DIR / "raw_fraud_transactions.csv"
    df_fraud.to_csv(fraud_path, index=False)
    logger.info(f"Saved raw fraud dataset to {fraud_path}")
    
    # 2. Generate Synthetic Win Probability Dataset
    logger.info("Generating synthetic win probability dataset (2,000 samples)...")
    df_win = generate_win_probability_dataset(n_samples=2000, random_state=42)
    win_path = SYNTHETIC_DATA_DIR / "raw_win_disputes.csv"
    df_win.to_csv(win_path, index=False)
    logger.info(f"Saved raw win probability dataset to {win_path}")
    
    # 3. Generate Scenario JSON Disputes
    logger.info("Creating 5 distinct scenario JSON files for CLI demonstration...")
    scenario_paths = generate_scenario_files()
    for name, p in scenario_paths.items():
        logger.info(f"Created scenario file '{name}': {p}")
        
    logger.info("Data generation process completed successfully.")

if __name__ == "__main__":
    main()
