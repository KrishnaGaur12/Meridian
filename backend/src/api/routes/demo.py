"""
Razorpay Demo Simulation API Endpoints.
Creates SIMULATED_RAZORPAY disputes with full AI analysis pipeline trigger.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_db, resolve_database_mode
from src.database.repository import (
    get_all_transactions, get_transaction, create_dispute,
    get_dispute, get_all_disputes, get_eligible_transactions
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
def list_available_transactions(request: Request, db: Session = Depends(get_db)):
    """
    Lists transactions eligible for dispute simulation in the active database.
    Eligible transactions: status == SUCCESS/CAPTURED and no active dispute exists.
    """
    mode = resolve_database_mode(request)
    eligible_txns = get_eligible_transactions(db)
    all_txns = get_all_transactions(db)
    all_disputes = get_all_disputes(db)

    active_dispute_tx_ids = {
        d.transaction_id for d in all_disputes
        if (d.status or "").upper() not in ["WON", "LOST", "CLOSED"]
    }

    formatted_eligible = []
    for tx in eligible_txns:
        formatted_eligible.append({
            "transaction_id": tx.transaction_id,
            "customer_id": tx.customer_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "merchant_category": tx.merchant_category,
            "timestamp": tx.timestamp,
            "is_eligible": True,
            "has_active_dispute": False,
        })

    all_formatted = []
    for tx in all_txns:
        has_active = tx.transaction_id in active_dispute_tx_ids
        all_formatted.append({
            "transaction_id": tx.transaction_id,
            "customer_id": tx.customer_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "merchant_category": tx.merchant_category,
            "timestamp": tx.timestamp,
            "is_eligible": not has_active and (tx.transaction_status or "").upper() in ["SUCCESS", "CAPTURED"],
            "has_active_dispute": has_active,
        })

    # If in DEMO mode and no undisputed transactions exist, return all_formatted for showcase compatibility
    tx_list = formatted_eligible if (mode == "LIVE" or formatted_eligible) else all_formatted

    return {
        "total": len(tx_list),
        "total_eligible": len(formatted_eligible),
        "total_transactions": len(all_formatted),
        "transactions": tx_list,
        "all_transactions": all_formatted
    }


@router.post("/simulate-dispute", status_code=status.HTTP_201_CREATED)
def simulate_razorpay_dispute(payload: SimulateDisputeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Creates a SIMULATED_RAZORPAY dispute and triggers the full AI analysis pipeline.

    Pipeline:
    1. Validates transaction exists in active database
    2. Validates transaction is eligible (SUCCESS status, no active dispute in LIVE mode)
    3. Creates dispute with case_source=SIMULATED_RAZORPAY
    4. Calculates response deadline
    5. Creates initial timeline events
    6. Triggers AI analysis (via AIAutopilot.reassess_dispute)
    7. Generates evidence requirements evaluation
    8. Calculates merchant attention state
    9. Returns complete case snapshot
    """
    mode = resolve_database_mode(request)

    # 1. Validate transaction exists
    tx = get_transaction(db, payload.transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{payload.transaction_id}' not found in active database."
        )

    # 2. Validate reason code 'other' requires description
    if payload.reason_code.lower() == "other" and not (payload.reason_description or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason_description is mandatory when dispute reason code is 'other'."
        )

    # 3. Create dispute (in LIVE mode, enforce strict eligibility)
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
        }, enforce_eligibility=(mode == "LIVE"))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create dispute: {str(e)}")

    # 4. Trigger AI analysis pipeline
    try:
        reassessment = AIAutopilot.reassess_dispute(db, dispute.dispute_id, trigger="DISPUTE_CREATED")
        case_analysis = reassessment.get("case_analysis", {})
    except Exception:
        case_analysis = {}

    # 5. Re-fetch dispute with updated state
    dispute = get_dispute(db, dispute.dispute_id)

    # 6. Build response
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
