"""
Script: evaluate_win_probability.py
PRIMARY ML MODEL #2 EVALUATION & REPORTING SCRIPT.
Evaluates saved Win Probability model pipeline on held-out test data calculating Precision, Recall, F1,
ROC-AUC, PR-AUC, Brier score, Confusion Matrix, and Probability Calibration Curve.
Exports metrics to reports/win_probability_metrics.json and plots to reports/.
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
    brier_score_loss, roc_curve, precision_recall_curve
)
from sklearn.calibration import calibration_curve

from config.settings import PROCESSED_DATA_DIR, WIN_PIPELINE_PATH, WIN_FEATURE_NAMES, REPORTS_DIR
from src.utils.logger import get_logger

logger = get_logger("EvaluateWinProbabilityScript")

def main():
    logger.info("Starting Win Probability Model Evaluation on Held-Out Test Set...")
    
    if not WIN_PIPELINE_PATH.exists():
        logger.error("Win probability pipeline file not found. Please run 'python scripts/train_win_probability.py' first.")
        return

    test_csv = PROCESSED_DATA_DIR / "win_test.csv"
    if not test_csv.exists():
        logger.error("Win probability test dataset not found. Please run 'python scripts/prepare_data.py' first.")
        return

    df_test = pd.read_csv(test_csv)
    X_test = df_test[WIN_FEATURE_NAMES]
    y_test = df_test['merchant_won']

    pipeline = joblib.load(WIN_PIPELINE_PATH)
    y_probs = pipeline.predict_proba(X_test)[:, 1]
    
    train_summary_file = REPORTS_DIR / "win_train_summary.json"
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
    brier = brier_score_loss(y_test, y_probs)
    cm = confusion_matrix(y_test, y_preds)

    metrics_payload = {
        "model_file": WIN_PIPELINE_PATH.name,
        "test_sample_count": len(y_test),
        "class_distribution": {
            "merchant_lost_count": int((y_test == 0).sum()),
            "merchant_won_count": int((y_test == 1).sum())
        },
        "optimal_threshold": optimal_thresh,
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "brier_score": round(float(brier), 4),
        "confusion_matrix": {
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "true_positives": int(cm[1][1])
        }
    }

    metrics_json_path = REPORTS_DIR / "win_probability_metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    logger.info(f"Saved Win Probability metrics report to {metrics_json_path}")

    # Plot 1: Confusion Matrix PNG
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    plt.title(f'Win Model Confusion Matrix (Thresh={optimal_thresh})')
    plt.colorbar()
    tick_marks = np.arange(2)
    plt.xticks(tick_marks, ['Lost', 'Won'])
    plt.yticks(tick_marks, ['Lost', 'Won'])
    
    thresh_val = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], 'd'),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh_val else "black")
    plt.tight_layout()
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(REPORTS_DIR / "win_confusion_matrix.png", dpi=150)
    plt.close()

    # Plot 2: ROC & PR Curve
    fpr, tpr, _ = roc_curve(y_test, y_probs)
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_probs)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.plot(fpr, tpr, color='forestgreen', lw=2, label=f'ROC Curve (AUC = {roc_auc:.3f})')
    ax1.plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('Win Model ROC Curve')
    ax1.legend(loc="lower right")

    ax2.plot(rec_curve, prec_curve, color='green', lw=2, label=f'PR Curve (AP = {pr_auc:.3f})')
    ax2.set_xlabel('Recall')
    ax2.set_ylabel('Precision')
    ax2.set_title('Win Model Precision-Recall Curve')
    ax2.legend(loc="lower left")

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "win_roc_pr_curve.png", dpi=150)
    plt.close()

    # Plot 3: Calibration Curve PNG
    fraction_of_positives, mean_predicted_value = calibration_curve(y_test, y_probs, n_bins=10)
    
    plt.figure(figsize=(6, 5))
    plt.plot(mean_predicted_value, fraction_of_positives, "s-", color="darkgreen", label=f"Win Model (Brier={brier:.3f})")
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.ylabel("Fraction of Positives (Actual Win Rate)")
    plt.xlabel("Mean Predicted Probability")
    plt.title("Win Probability Calibration Curve")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "win_calibration_curve.png", dpi=150)
    plt.close()

    print("\n==================================================")
    print("   HELD-OUT EVALUATION: WIN PROBABILITY ML MODEL  ")
    print("==================================================")
    print(f"Optimal Threshold Used : {optimal_thresh}")
    print(f"Test Sample Count      : {len(y_test)}")
    print("--------------------------------------------------")
    print(f"Precision              : {precision:.4f}")
    print(f"Recall                 : {recall:.4f}")
    print(f"F1-Score               : {f1:.4f}")
    print(f"ROC-AUC                : {roc_auc:.4f}")
    print(f"Brier Score            : {brier:.4f}")
    print("--------------------------------------------------")
    print("Confusion Matrix:")
    print(f"  True Negatives (Lost Correct)  : {cm[0][0]}")
    print(f"  False Positives (False Win)    : {cm[0][1]}")
    print(f"  False Negatives (Missed Win)   : {cm[1][0]}")
    print(f"  True Positives (Win Correct)   : {cm[1][1]}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
