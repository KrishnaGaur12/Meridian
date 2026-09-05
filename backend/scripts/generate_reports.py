"""
Script: generate_reports.py
Aggregates benchmark results, computes model feature importances,
and outputs reports/feature_importance.json, reports/evaluation_summary.json,
and reports/feature_importance.png.
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
import matplotlib.pyplot as plt

from config.settings import (
    FRAUD_PIPELINE_PATH, WIN_PIPELINE_PATH,
    FRAUD_FEATURE_NAMES, WIN_FEATURE_NAMES, REPORTS_DIR
)
from src.utils.logger import get_logger

logger = get_logger("GenerateReportsScript")

def main():
    logger.info("Generating Comprehensive Risk Manager Performance Reports...")
    
    if not FRAUD_PIPELINE_PATH.exists() or not WIN_PIPELINE_PATH.exists():
        logger.error("Trained pipeline binaries not found. Run training scripts first.")
        return

    fraud_pipe = joblib.load(FRAUD_PIPELINE_PATH)
    win_pipe = joblib.load(WIN_PIPELINE_PATH)

    feature_importance_dict = {}

    # Extract Fraud Model Feature Importances
    fraud_clf = fraud_pipe.named_steps['clf']
    if hasattr(fraud_clf, 'feature_importances_'):
        importances = fraud_clf.feature_importances_
        # Map back to raw features if length matches
        if len(importances) == len(FRAUD_FEATURE_NAMES):
            fraud_fi = {name: round(float(imp), 4) for name, imp in zip(FRAUD_FEATURE_NAMES, importances)}
        else:
            fraud_fi = {f"feat_{i}": round(float(imp), 4) for i, imp in enumerate(importances)}
        feature_importance_dict["fraud_model"] = dict(sorted(fraud_fi.items(), key=lambda x: x[1], reverse=True))
    elif hasattr(fraud_clf, 'coef_'):
        coefs = np.abs(fraud_clf.coef_[0])
        fraud_fi = {name: round(float(c), 4) for name, c in zip(FRAUD_FEATURE_NAMES, coefs[:len(FRAUD_FEATURE_NAMES)])}
        feature_importance_dict["fraud_model"] = dict(sorted(fraud_fi.items(), key=lambda x: x[1], reverse=True))

    # Extract Win Model Feature Importances
    win_clf = win_pipe.named_steps['clf']
    if hasattr(win_clf, 'feature_importances_'):
        importances = win_clf.feature_importances_
        if len(importances) == len(WIN_FEATURE_NAMES):
            win_fi = {name: round(float(imp), 4) for name, imp in zip(WIN_FEATURE_NAMES, importances)}
        else:
            win_fi = {f"feat_{i}": round(float(imp), 4) for i, imp in enumerate(importances)}
        feature_importance_dict["win_model"] = dict(sorted(win_fi.items(), key=lambda x: x[1], reverse=True))
    elif hasattr(win_clf, 'coef_'):
        coefs = np.abs(win_clf.coef_[0])
        win_fi = {name: round(float(c), 4) for name, c in zip(WIN_FEATURE_NAMES, coefs[:len(WIN_FEATURE_NAMES)])}
        feature_importance_dict["win_model"] = dict(sorted(win_fi.items(), key=lambda x: x[1], reverse=True))

    # Save feature_importance.json
    fi_path = REPORTS_DIR / "feature_importance.json"
    with open(fi_path, "w", encoding="utf-8") as f:
        json.dump(feature_importance_dict, f, indent=2)
    logger.info(f"Saved feature importances report to {fi_path}")

    # Combine metrics into evaluation_summary.json
    fraud_metrics = {}
    if (REPORTS_DIR / "fraud_metrics.json").exists():
        with open(REPORTS_DIR / "fraud_metrics.json", "r") as f:
            fraud_metrics = json.load(f)

    win_metrics = {}
    if (REPORTS_DIR / "win_probability_metrics.json").exists():
        with open(REPORTS_DIR / "win_probability_metrics.json", "r") as f:
            win_metrics = json.load(f)

    eval_summary = {
        "system_name": "Razorpay AI Risk Manager",
        "fraud_detection_model": fraud_metrics,
        "win_probability_model": win_metrics,
        "feature_importances": feature_importance_dict
    }

    summary_path = REPORTS_DIR / "evaluation_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)
    logger.info(f"Saved evaluation summary to {summary_path}")

    # Plot Feature Importance Bar Chart PNG
    if "fraud_model" in feature_importance_dict:
        fig, ax = plt.subplots(figsize=(10, 6))
        items = list(feature_importance_dict["fraud_model"].items())[:10]
        names = [item[0] for item in items]
        vals = [item[1] for item in items]
        
        ax.barh(names, vals, color='navy')
        ax.invert_yaxis()
        ax.set_xlabel("Importance / Coefficient Magnitude")
        ax.set_title("Top Fraud Detection Model Features")
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "feature_importance.png", dpi=150)
        plt.close()

    logger.info("All performance reports and charts generated successfully.")

if __name__ == "__main__":
    main()
