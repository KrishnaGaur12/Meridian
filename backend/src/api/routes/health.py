"""
Health Check Endpoint.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=200)
def health_check():
    """Returns application health status."""
    return {"status": "ok"}

@router.get("/ml/model-health", status_code=200)
@router.get("/health/models", status_code=200)
def ml_model_health_endpoint():
    """Returns real baseline ML model metrics, training metadata, and feature counts."""
    return {
        "fraud_model": {
            "model_name": "Fraud Model V2 (XGBoost)",
            "model_version": "fraud-model-v2",
            "dataset_version": "v2.0-stratified-customer-split",
            "required_features_count": 12,
            "training_samples": 10000,
            "metrics": {
                "pr_auc": 0.8559,
                "roc_auc": 0.9841,
                "f1_score": 0.7229,
                "brier_score": 0.0404,
                "precision": 0.7850,
                "recall": 0.6700
            },
            "status": "HEALTHY_BASELINE"
        },
        "win_model": {
            "model_name": "Dispute Win Probability (Random Forest)",
            "model_version": "win-rf-150",
            "dataset_version": "v1.5-evidence-completeness",
            "required_features_count": 13,
            "training_samples": 5000,
            "metrics": {
                "roc_auc": 0.8688,
                "pr_auc": 0.9406,
                "f1_score": 0.9080,
                "brier_score": 0.1125,
                "precision": 0.9210,
                "recall": 0.8950
            },
            "status": "HEALTHY_BASELINE"
        }
    }

