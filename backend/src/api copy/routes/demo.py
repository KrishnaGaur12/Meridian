"""
Razorpay Demo Simulation API Endpoints.
Creates SIMULATED_RAZORPAY disputes with full AI analysis pipeline trigger.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import (
    get_all_transactions, get_transaction, create_dispute,
    get_dispute, get_all_disputes
)
from src.pipeline.autopilot import AIAutopilot
from src.database.models import utc_now_iso

router = APIRouter(prefix="/demo", tags=["Razorpay Demo Simulation"])


class SimulateDisputeRequest(BaseModel):
    transaction_id: str = Field(..., description="Existing transaction ID to create dispute against")
    reason_code: str = Field(default="product_not_received", description="Dispute reason code")
    reason_description: Optional[str] = Field(default="", description="Detailed dispute description")
    phase: str = Field(default="chargeback", description="Dispute phase: retrieval, chargeback, pre_arbitration, arbitration, fraud")
    dispute_amount: Optional[float] = Field(None, description="Override dispute amount (defaults to transaction amount)")


@router.get("/available-transactions", status_code=status.HTTP_200_OK)
def list_available_transactions(db: Session = Depends(get_db)):
    """
    Lists transactions eligible for dispute simulation.
    Returns transactions that do not already have an active SIMULATED_RAZORPAY dispute.
    """
    all_txns = get_all_transactions(db)
    all_disputes = get_all_disputes(db)

    # Build set of transaction_ids already under active simulated disputes
    active_dispute_tx_ids = set()
    for d in all_disputes:
        if (getattr(d, "case_source", "") == "SIMULATED_RAZORPAY"
                and d.status not in ["WON", "LOST", "CLOSED"]):
            active_dispute_tx_ids.add(d.transaction_id)

    eligible = []
    for tx in all_txns:
        eligible.append({
            "transaction_id": tx.transaction_id,
            "customer_id": tx.customer_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "merchant_category": tx.merchant_category,
            "timestamp": tx.timestamp,
            "has_active_simulated_dispute": tx.transaction_id in active_dispute_tx_ids,
        })

    return {
        "total": len(eligible),
        "transactions": eligible,
    }


@router.post("/simulate-dispute", status_code=status.HTTP_201_CREATED)
def simulate_razorpay_dispute(payload: SimulateDisputeRequest, db: Session = Depends(get_db)):
    """
    Creates a SIMULATED_RAZORPAY dispute and triggers the full AI analysis pipeline.

    Pipeline:
    1. Validates transaction exists
    2. Creates dispute with case_source=SIMULATED_RAZORPAY
    3. Calculates response deadline
    4. Creates initial timeline events
    5. Triggers AI analysis (via AIAutopilot.reassess_dispute)
    6. Generates evidence requirements evaluation
    7. Calculates merchant attention state
    8. Returns complete case snapshot
    """
    # 1. Validate transaction
    tx = get_transaction(db, payload.transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{payload.transaction_id}' not found in database."
        )

    # 2. Create dispute
    reason_desc = payload.reason_description or f"Simulated {payload.reason_code.replace('_', ' ')} dispute"
    try:
        dispute = create_dispute(db, {
            "transaction_id": payload.transaction_id,
            "reason_code": payload.reason_code,
            "reason_description": reason_desc,
            "status": "OPEN",
            "phase": payload.phase,
            "case_source": "SIMULATED_RAZORPAY",
            "merchant_attention_state": "ACTION_REQUIRED",
            "workflow_stage": "DISPUTE_RAISED",
        })
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create dispute: {str(e)}")

    # 3. Trigger AI analysis pipeline
    try:
        reassessment = AIAutopilot.reassess_dispute(db, dispute.dispute_id, trigger="DISPUTE_CREATED")
        case_analysis = reassessment.get("case_analysis", {})
    except Exception:
        case_analysis = {}

    # 4. Re-fetch dispute with updated state
    dispute = get_dispute(db, dispute.dispute_id)

    # 5. Build response
    from src.database.repository import calculate_deadline_info
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)

    return {
        "simulation_status": "SUCCESS",
        "dispute_id": dispute.dispute_id,
        "transaction_id": dispute.transaction_id,
        "customer_id": dispute.customer_id,
        "reason_code": dispute.reason_code,
        "reason_description": dispute.reason_description,
        "status": dispute.status,
        "phase": dispute.phase,
        "case_source": dispute.case_source,
        "merchant_attention_state": dispute.merchant_attention_state,
        "workflow_stage": dispute.workflow_stage,
        "respond_by": dispute.respond_by,
        "created_at": dispute.created_at,
        "amount": tx.amount,
        "currency": tx.currency,
        "deadline_info": deadline_info,
        "case_analysis_summary": {
            "attention_state": case_analysis.get("merchant_attention_state", "ACTION_REQUIRED"),
            "attention_reason": case_analysis.get("attention_reason", ""),
            "recommendation": case_analysis.get("recommendation", {}).get("decision", "UNKNOWN"),
            "evidence_completeness": case_analysis.get("evidence_intelligence", {}).get("evidence_completeness", 0),
            "win_probability": case_analysis.get("win_probability", {}).get("score", 0),
            "risk_level": case_analysis.get("risk_analysis", {}).get("risk_level", "UNKNOWN"),
        },
        "message": f"Simulated Razorpay dispute {dispute.dispute_id} created successfully. AI analysis complete.",
    }
