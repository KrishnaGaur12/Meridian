"""
Script: evaluate_fraud.py
PRIMARY ML MODEL #1 EVALUATION & REPORTING SCRIPT.
Evaluates saved Fraud model pipeline on held-out test data calculating Precision, Recall, F1,
ROC-AUC, PR-AUC / Average Precision, and Confusion Matrix.
Saves metrics to reports/fraud_metrics.json and exports confusion matrix and ROC/PR plots.
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
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix,
    precision_score, recall_score, f1_score, average_precision_score,
    roc_curve, precision_recall_curve
)

from config.settings import PROCESSED_DATA_DIR, FRAUD_PIPELINE_PATH, FRAUD_FEATURE_NAMES, REPORTS_DIR
from src.utils.logger import get_logger

logger = get_logger("EvaluateFraudScript")

def main():
    logger.info("Starting Fraud Model Evaluation on Held-Out Test Set...")
    
    if not FRAUD_PIPELINE_PATH.exists():
        logger.error("Fraud model pipeline file not found. Please run 'python scripts/train_fraud.py' first.")
        return

    test_csv = PROCESSED_DATA_DIR / "fraud_test.csv"
    if not test_csv.exists():
        logger.error("Fraud test dataset not found. Please run 'python scripts/prepare_data.py' first.")
        return

    df_test = pd.read_csv(test_csv)
    X_test = df_test[FRAUD_FEATURE_NAMES]
    y_test = df_test['is_fraud']

    pipeline = joblib.load(FRAUD_PIPELINE_PATH)
    y_probs = pipeline.predict_proba(X_test)[:, 1]
    
    # Load optimal threshold from train summary if available
    train_summary_file = REPORTS_DIR / "fraud_train_summary.json"
    optimal_thresh = 0.50
    if train_summary_file.exists():
        with open(train_summary_file, "r") as f:
            ts = json.load(f)
            optimal_thresh = ts.get("optimal_threshold", 0.50)

    y_preds = (y_probs >= optimal_thresh).astype(int)

    precision = precision_score(y_test, y_preds, zero_division=0)
    recall = recall_score(y_test, y_preds, zero_division=0)
    f1 = f1_score(y_test, y_preds, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_probs)
    pr_auc = average_precision_score(y_test, y_probs)
    cm = confusion_matrix(y_test, y_preds)

    # Threshold evaluation sweep
    threshold_metrics = {}
    for t in [0.30, 0.40, 0.50, 0.60, 0.70]:
        t_preds = (y_probs >= t).astype(int)
        threshold_metrics[str(t)] = {
            "precision": round(float(precision_score(y_test, t_preds, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, t_preds, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, t_preds, zero_division=0)), 4)
        }

    metrics_payload = {
        "model_file": FRAUD_PIPELINE_PATH.name,
        "test_sample_count": len(y_test),
        "class_distribution": {
            "legitimate_count": int((y_test == 0).sum()),
            "fraud_count": int((y_test == 1).sum())
        },
        "optimal_threshold": optimal_thresh,
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "confusion_matrix": {
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "true_positives": int(cm[1][1])
        },
        "threshold_sweep": threshold_metrics
    }

    # Export metrics to reports/fraud_metrics.json
    metrics_json_path = REPORTS_DIR / "fraud_metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    logger.info(f"Saved Fraud metrics report to {metrics_json_path}")

    # Plot 1: Confusion Matrix PNG
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f'Fraud Model Confusion Matrix (Thresh={optimal_thresh})')
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ['Legitimate', 'Fraud'])
    plt.yticks(tick_marks, ['Legitimate', 'Fraud'])
    
    thresh_val = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], 'd'),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh_val else "black")
    plt.tight_layout()
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(REPORTS_DIR / "fraud_confusion_matrix.png", dpi=150)
    plt.close()

    # Plot 2: ROC & Precision-Recall Curves PNG
    fpr, tpr, _ = roc_curve(y_test, y_probs)
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_probs)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC Curve (AUC = {roc_auc:.3f})')
    ax1.plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('Fraud Model ROC Curve')
    ax1.legend(loc="lower right")

    ax2.plot(rec_curve, prec_curve, color='blue', lw=2, label=f'PR Curve (AP = {pr_auc:.3f})')
    ax2.set_xlabel('Recall')
    ax2.set_ylabel('Precision')
    ax2.set_title('Fraud Model Precision-Recall Curve')
    ax2.legend(loc="lower left")

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "fraud_roc_pr_curve.png", dpi=150)
    plt.close()

    # Print summary to console
    print("\n==================================================")
    print("   HELD-OUT EVALUATION: FRAUD DETECTION MODEL     ")
    print("==================================================")
    print(f"Optimal Threshold Used : {optimal_thresh}")
    print(f"Test Sample Count      : {len(y_test)}")
    print("--------------------------------------------------")
    print(f"Precision              : {precision:.4f}")
    print(f"Recall                 : {recall:.4f}")
    print(f"F1-Score               : {f1:.4f}")
    print(f"ROC-AUC                : {roc_auc:.4f}")
    print(f"PR-AUC (Avg Precision) : {pr_auc:.4f}")
    print("--------------------------------------------------")
    print("Confusion Matrix:")
    print(f"  True Negatives (Legit Correct)  : {cm[0][0]}")
    print(f"  False Positives (False Alarm)  : {cm[0][1]}")
    print(f"  False Negatives (Missed Fraud) : {cm[1][0]}")
    print(f"  True Positives (Fraud Caught)   : {cm[1][1]}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
