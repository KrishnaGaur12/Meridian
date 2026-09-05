"""
Script: train_win_probability.py
PRIMARY ML MODEL #2 BENCHMARK & TRAINING SCRIPT.
Benchmarks 4 classifiers (Dummy, Logistic Regression, Random Forest, XGBoost) on processed win probability dataset.
Selects best performing model pipeline, performs threshold tuning, and serializes pipeline to models/win_pipeline.joblib.
"""

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import numpy as np
import joblib
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    average_precision_score, brier_score_loss
)

from config.settings import PROCESSED_DATA_DIR, WIN_PIPELINE_PATH, WIN_MODEL_PATH, WIN_FEATURE_NAMES, REPORTS_DIR
from src.utils.feature_engineering import get_win_preprocessor
from src.utils.logger import get_logger

logger = get_logger("TrainWinProbabilityBenchmark")

def main():
    logger.info("Starting Win Probability Model Benchmark & Training Pipeline...")
    
    train_csv = PROCESSED_DATA_DIR / "win_train.csv"
    val_csv = PROCESSED_DATA_DIR / "win_val.csv"
    
    if not train_csv.exists():
        logger.error("Processed training data not found. Please run 'python scripts/prepare_data.py' first.")
        return

    df_train = pd.read_csv(train_csv)
    df_val = pd.read_csv(val_csv)
    
    X_train = df_train[WIN_FEATURE_NAMES]
    y_train = df_train['merchant_won']
    X_val = df_val[WIN_FEATURE_NAMES]
    y_val = df_val['merchant_won']

    models = {
        "Dummy (Stratified)": DummyClassifier(strategy="stratified", random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42, n_jobs=-1),
        "XGBoost": XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=-1)
    }

    benchmark_results = {}
    best_name = None
    best_auc = -1.0
    best_pipeline = None

    for name, clf in models.items():
        pipe = Pipeline([
            ('preprocessor', get_win_preprocessor()),
            ('clf', clf)
        ])
        pipe.fit(X_train, y_train)
        
        val_probs = pipe.predict_proba(X_val)[:, 1]
        val_preds_50 = (val_probs >= 0.50).astype(int)
        
        auc = roc_auc_score(y_val, val_probs)
        pr_auc = average_precision_score(y_val, val_probs)
        brier = brier_score_loss(y_val, val_probs)
        f1 = f1_score(y_val, val_preds_50, zero_division=0)
        
        logger.info(f"Model: {name:<20} | ROC-AUC: {auc:.4f} | Brier: {brier:.4f} | F1: {f1:.4f}")
        
        benchmark_results[name] = {
            "roc_auc": round(float(auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "brier_score": round(float(brier), 4),
            "f1_at_50": round(float(f1), 4)
        }
        
        if auc > best_auc:
            best_auc = auc
            best_name = name
            best_pipeline = pipe

    logger.info(f"\n---> Selected Best Win Probability Model: '{best_name}' (Validation ROC-AUC: {best_auc:.4f})")

    # Threshold Sweep on Validation Set for Best Model
    best_val_probs = best_pipeline.predict_proba(X_val)[:, 1]
    threshold_sweep = {}
    best_thresh = 0.50
    best_thresh_f1 = -1.0
    
    for thresh in [0.30, 0.40, 0.50, 0.60, 0.70]:
        t_preds = (best_val_probs >= thresh).astype(int)
        t_f1 = f1_score(y_val, t_preds, zero_division=0)
        t_prec = precision_score(y_val, t_preds, zero_division=0)
        t_rec = recall_score(y_val, t_preds, zero_division=0)
        
        threshold_sweep[str(thresh)] = {
            "f1": round(float(t_f1), 4),
            "precision": round(float(t_prec), 4),
            "recall": round(float(t_rec), 4)
        }
        if t_f1 > best_thresh_f1:
            best_thresh_f1 = t_f1
            best_thresh = thresh

    # Save Best Pipeline
    joblib.dump(best_pipeline, WIN_PIPELINE_PATH)
    joblib.dump(best_pipeline.named_steps['clf'], WIN_MODEL_PATH)
    logger.info(f"Saved best Win Probability pipeline to {WIN_PIPELINE_PATH}")

    # Save benchmark summary metadata
    train_summary = {
        "best_model_name": best_name,
        "best_validation_roc_auc": round(float(best_auc), 4),
        "optimal_threshold": best_thresh,
        "benchmark_comparison": benchmark_results,
        "threshold_sweep": threshold_sweep
    }
    with open(REPORTS_DIR / "win_train_summary.json", "w", encoding="utf-8") as f:
        json.dump(train_summary, f, indent=2)

if __name__ == "__main__":
    main()
