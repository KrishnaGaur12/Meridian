"""
Risk Assessment API Endpoint.
Integrates Fraud Model V2 and Risk Engine decision logic with DB persistence.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import get_transaction, create_risk_assessment
from src.components.fraud_model_v2 import FraudModelV2Wrapper
from src.schemas.api_schemas import RiskAssessmentResponseSchema

router = APIRouter(prefix="/transactions", tags=["Risk Assessment"])

# Global singleton or reusable instance of FraudModelV2Wrapper
fraud_v2_model = FraudModelV2Wrapper()

@router.post("/{transaction_id}/risk-assessment", response_model=RiskAssessmentResponseSchema, status_code=status.HTTP_200_OK)
def run_risk_assessment_endpoint(transaction_id: str, db: Session = Depends(get_db)):
    """
    Executes ML Fraud Model V2 prediction and Risk Engine decision logic for a transaction.
    Stores the assessment in the database and returns the result.
    """
    tx = get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found."
        )

    # Extract 12 ML feature parameters from transaction record
    payload = {
        "transaction_hour": tx.transaction_hour,
        "account_age_days": tx.account_age_days,
        "previous_chargebacks": tx.previous_chargebacks,
        "merchant_category": tx.merchant_category,
        "transaction_country": tx.transaction_country,
        "device_type": tx.device_type,
        "is_international": tx.is_international,
        "is_high_risk_merchant": tx.is_high_risk_merchant,
        "transaction_amount": tx.amount,
        "transaction_velocity_1h": tx.transaction_velocity_1h,
        "transaction_velocity_24h": tx.transaction_velocity_24h,
        "avg_transaction_amount_30d": tx.avg_transaction_amount_30d
    }

    try:
        prediction = fraud_v2_model.predict(payload)
        risk_score = float(prediction["fraud_probability"])
        risk_level = prediction["risk_level"]
        model_version = prediction["model_version"]

        # Risk Engine decision logic mapping
        if risk_level == "CRITICAL" or risk_score >= 0.70:
            decision = "BLOCK"
        elif risk_level == "HIGH" or risk_score >= 0.50:
            decision = "REVIEW"
        elif risk_level == "MEDIUM" or risk_score >= 0.30:
            decision = "REVIEW"
        else:
            decision = "ALLOW"

        # Persist to database
        assessment = create_risk_assessment(db, {
            "transaction_id": tx.transaction_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "decision": decision,
            "model_version": model_version
        })

        return RiskAssessmentResponseSchema(
            transaction_id=assessment.transaction_id,
            risk_score=assessment.risk_score,
            risk_level=assessment.risk_level,
            decision=assessment.decision,
            model_version=assessment.model_version
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute risk assessment: {str(e)}"
        )
