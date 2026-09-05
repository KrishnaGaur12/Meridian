"""
Script: train_fraud.py
PRIMARY ML MODEL #1 BENCHMARK & TRAINING SCRIPT.
Benchmarks 4 classifiers (Dummy, Logistic Regression, Random Forest, XGBoost) on processed fraud data.
Selects best performing model based on Validation ROC-AUC & PR-AUC, performs threshold tuning,
and serializes model pipeline to models/fraud_pipeline.joblib.
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
    average_precision_score, confusion_matrix
)

from config.settings import PROCESSED_DATA_DIR, FRAUD_PIPELINE_PATH, FRAUD_MODEL_PATH, FRAUD_FEATURE_NAMES, REPORTS_DIR
from src.utils.feature_engineering import get_fraud_preprocessor
from src.utils.logger import get_logger

logger = get_logger("TrainFraudBenchmark")

def main():
    logger.info("Starting Fraud Model Benchmark & Training Pipeline...")
    
    train_csv = PROCESSED_DATA_DIR / "fraud_train.csv"
    val_csv = PROCESSED_DATA_DIR / "fraud_val.csv"
    
    if not train_csv.exists():
        logger.error("Processed training data not found. Please run 'python scripts/prepare_data.py' first.")
        return

    df_train = pd.read_csv(train_csv)
    df_val = pd.read_csv(val_csv)
    
    X_train = df_train[FRAUD_FEATURE_NAMES]
    y_train = df_train['is_fraud']
    X_val = df_val[FRAUD_FEATURE_NAMES]
    y_val = df_val['is_fraud']

    # Define Benchmark Classifiers
    scale_pos_weight = (len(y_train) - sum(y_train)) / float(max(1, sum(y_train)))
    
    models = {
        "Dummy (Stratified)": DummyClassifier(strategy="stratified", random_state=42),
        "Logistic Regression": LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=6, class_weight='balanced', random_state=42, n_jobs=-1),
        "XGBoost": XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.05, scale_pos_weight=scale_pos_weight, random_state=42, n_jobs=-1)
    }

    benchmark_results = {}
    best_name = None
    best_auc = -1.0
    best_pipeline = None

    for name, clf in models.items():
        pipe = Pipeline([
            ('preprocessor', get_fraud_preprocessor()),
            ('clf', clf)
        ])
        pipe.fit(X_train, y_train)
        
        val_probs = pipe.predict_proba(X_val)[:, 1]
        val_preds_50 = (val_probs >= 0.50).astype(int)
        
        auc = roc_auc_score(y_val, val_probs)
        pr_auc = average_precision_score(y_val, val_probs)
        f1 = f1_score(y_val, val_preds_50, zero_division=0)
        prec = precision_score(y_val, val_preds_50, zero_division=0)
        rec = recall_score(y_val, val_preds_50, zero_division=0)
        
        logger.info(f"Model: {name:<20} | ROC-AUC: {auc:.4f} | PR-AUC: {pr_auc:.4f} | F1: {f1:.4f}")
        
        benchmark_results[name] = {
            "roc_auc": round(float(auc), 4),
            "pr_auc": round(float(pr_auc), 4),
            "f1_at_50": round(float(f1), 4),
            "precision_at_50": round(float(prec), 4),
            "recall_at_50": round(float(rec), 4)
        }
        
        if auc > best_auc:
            best_auc = auc
            best_name = name
            best_pipeline = pipe

    logger.info(f"\n---> Selected Best Fraud Model: '{best_name}' (Validation ROC-AUC: {best_auc:.4f})")

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

    logger.info(f"Optimal Fraud Decision Threshold: {best_thresh} (Validation F1: {best_thresh_f1:.4f})")

    # Save Best Pipeline
    joblib.dump(best_pipeline, FRAUD_PIPELINE_PATH)
    joblib.dump(best_pipeline.named_steps['clf'], FRAUD_MODEL_PATH)
    logger.info(f"Saved best Fraud pipeline to {FRAUD_PIPELINE_PATH}")

    # Save benchmark summary metadata
    train_summary = {
        "best_model_name": best_name,
        "best_validation_roc_auc": round(float(best_auc), 4),
        "optimal_threshold": best_thresh,
        "optimal_val_f1": round(float(best_thresh_f1), 4),
        "benchmark_comparison": benchmark_results,
        "threshold_sweep": threshold_sweep
    }
    with open(REPORTS_DIR / "fraud_train_summary.json", "w", encoding="utf-8") as f:
        json.dump(train_summary, f, indent=2)

if __name__ == "__main__":
    main()
