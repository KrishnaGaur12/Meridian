"""
Razorpay Webhook Architecture & Simulation Endpoints.
Operates EXCLUSIVELY on the LIVE database (data/live_database.db) with idempotency guarantees.
Webhook-created disputes are never mixed with Demo database records.
"""

from typing import Optional, Dict, Any, List
import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_db_session, LiveSessionLocal
from src.database.models import (
    Transaction, Dispute, Customer, Payment, WebhookEvent, utc_now_iso
)
from src.database.repository import (
    get_transaction, get_all_transactions, create_dispute,
    get_dispute, calculate_deadline_info, create_dispute_event
)
from src.pipeline.analysis_service import analyze_dispute
from src.api.routes.events import publish_realtime_event
from src.utils.id_generator import generate_dispute_id, generate_event_id
from src.utils.logger import get_logger

logger = get_logger("WebhooksRouter")

router = APIRouter(prefix="/webhooks", tags=["Razorpay Webhooks"])


def get_live_db():
    """Dependency ensuring strict Live database context for all webhook routes."""
    db = LiveSessionLocal()
    try:
        yield db
    finally:
        db.close()


class WebhookDisputeCreateRequest(BaseModel):
    transaction_id: str = Field(..., description="Live Transaction ID to raise dispute against")
    reason_code: str = Field(default="product_not_received", description="Dispute reason code")
    reason_description: Optional[str] = Field(default="", description="Detailed dispute explanation")
    phase: Optional[str] = Field(default="chargeback", description="Dispute phase: chargeback, retrieval, pre_arbitration, arbitration, fraud")
    dispute_amount: Optional[float] = Field(None, description="Dispute monetary amount")
    idempotency_key: Optional[str] = Field(None, description="Unique merchant idempotency key")
    event_id: Optional[str] = Field(None, description="Unique webhook event ID")


@router.get("/transactions", status_code=status.HTTP_200_OK)
def list_live_webhook_transactions(db: Session = Depends(get_live_db)):
    """
    Retrieves realistic transactions from LIVE database only.
    Used by /webhooks simulator page to pick transactions for raising real disputes.
    """
    all_txs = get_all_transactions(db)
    active_disputes = db.query(Dispute).filter(
        Dispute.status.notin_(["WON", "LOST", "CLOSED"])
    ).all()
    disputed_tx_ids = {d.transaction_id for d in active_disputes}

    eligible_txs = []
    all_formatted = []

    for tx in all_txs:
        has_active = tx.transaction_id in disputed_tx_ids
        is_success = (tx.transaction_status or "").upper() in ["SUCCESS", "CAPTURED"]
        is_eligible = is_success and not has_active

        item = {
            "transaction_id": tx.transaction_id,
            "customer_id": tx.customer_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "merchant_category": tx.merchant_category,
            "transaction_country": tx.transaction_country,
            "timestamp": tx.timestamp,
            "is_eligible": is_eligible,
            "has_active_dispute": has_active,
            "transaction_status": tx.transaction_status
        }
        all_formatted.append(item)
        if is_eligible:
            eligible_txs.append(item)

    return {
        "database": "LIVE",
        "total": len(eligible_txs),
        "total_eligible": len(eligible_txs),
        "total_transactions": len(all_formatted),
        "transactions": eligible_txs,
        "all_transactions": all_formatted
    }


def _process_webhook_dispute_creation(
    payload: WebhookDisputeCreateRequest,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None
) -> Dict[str, Any]:
    """Internal core handler for Razorpay dispute webhook creation with idempotency."""
    # 1. Check idempotency key or existing event_id
    idempotency_key = payload.idempotency_key or payload.event_id
    if idempotency_key:
        existing_event = db.query(WebhookEvent).filter(
            WebhookEvent.idempotency_key == idempotency_key
        ).first()
        if existing_event and existing_event.dispute_id:
            existing_dispute = get_dispute(db, existing_event.dispute_id)
            if existing_dispute:
                logger.info(f"Idempotent webhook replay detected for key {idempotency_key}. Returning dispute {existing_dispute.dispute_id}")
                return {
                    "is_idempotent_replay": True,
                    "event_id": existing_event.event_id,
                    "idempotency_key": idempotency_key,
                    "dispute_id": existing_dispute.dispute_id,
                    "status": existing_dispute.status,
                    "workflow_stage": existing_dispute.workflow_stage,
                    "analysis_status": "COMPLETED",
                    "message": "Webhook request already processed (idempotent replay)."
                }

    # 2. Validate transaction in LIVE database
    tx = get_transaction(db, payload.transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{payload.transaction_id}' not found in LIVE database."
        )

    # 3. Check for active dispute on this transaction
    active_dispute = db.query(Dispute).filter(
        Dispute.transaction_id == tx.transaction_id,
        Dispute.status.notin_(["WON", "LOST", "CLOSED"])
    ).first()
    if active_dispute:
        # Idempotently return active dispute
        return {
            "is_idempotent_replay": True,
            "dispute_id": active_dispute.dispute_id,
            "transaction_id": tx.transaction_id,
            "status": active_dispute.status,
            "workflow_stage": active_dispute.workflow_stage,
            "analysis_status": "COMPLETED",
            "message": f"Active dispute '{active_dispute.dispute_id}' already exists for transaction '{tx.transaction_id}'."
        }

    # 4. Validate reason code 'other' requires description
    reason_code = payload.reason_code.strip()
    reason_desc = (payload.reason_description or "").strip()
    if reason_code.lower() == "other" and not reason_desc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason_description is mandatory when dispute reason code is 'other'."
        )

    event_id = payload.event_id or f"evt_{uuid.uuid4().hex[:12]}"
    created_now = utc_now_iso()

    # 5. Persist WebhookEvent record
    webhook_event = WebhookEvent(
        event_id=event_id,
        idempotency_key=idempotency_key or event_id,
        event_type="payment.dispute.created",
        payload_json=json.dumps(payload.model_dump()),
        status="RECEIVED",
        created_at=created_now
    )
    db.add(webhook_event)
    db.commit()

    # 6. Create Actual Dispute in LIVE database
    dispute_id = generate_dispute_id()
    reason_text = reason_desc or f"Cardholder raised {reason_code.replace('_', ' ')} dispute via Razorpay."

    dispute = create_dispute(db, {
        "dispute_id": dispute_id,
        "transaction_id": tx.transaction_id,
        "reason_code": reason_code,
        "reason_description": reason_text,
        "status": "OPEN",
        "phase": payload.phase or "chargeback",
        "case_source": "REAL_RAZORPAY",
        "merchant_attention_state": "ACTION_REQUIRED",
        "workflow_stage": "DISPUTE_RAISED",
        "created_at": created_now
    }, enforce_eligibility=True, auto_process=True)

    # Update webhook event with dispute ID
    webhook_event.dispute_id = dispute.dispute_id
    webhook_event.status = "PROCESSED"
    webhook_event.processed_at = utc_now_iso()
    db.commit()

    # 7. Publish DISPUTE_CREATED event over SSE
    publish_realtime_event("DISPUTE_CREATED", dispute_id=dispute.dispute_id, data={
        "dispute_id": dispute.dispute_id,
        "transaction_id": tx.transaction_id,
        "amount": tx.amount,
        "currency": tx.currency,
        "reason_code": dispute.reason_code,
        "status": dispute.status,
        "workflow_stage": dispute.workflow_stage,
        "created_at": dispute.created_at,
        "case_source": "REAL_RAZORPAY"
    })

    # 8. Execute Authoritative Analysis
    # We execute authoritative analysis so client immediately has AI/ML results ready
    analysis_result = analyze_dispute(dispute.dispute_id, db, trigger="DISPUTE_CREATED", broadcast=True)

    db.refresh(dispute)
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)

    return {
        "event_id": event_id,
        "idempotency_key": idempotency_key,
        "dispute_id": dispute.dispute_id,
        "transaction_id": dispute.transaction_id,
        "customer_id": dispute.customer_id,
        "reason_code": dispute.reason_code,
        "reason_description": dispute.reason_description,
        "status": dispute.status,
        "phase": dispute.phase,
        "workflow_stage": dispute.workflow_stage,
        "merchant_attention_state": dispute.merchant_attention_state,
        "respond_by": dispute.respond_by,
        "created_at": dispute.created_at,
        "amount": tx.amount,
        "currency": tx.currency,
        "analysis_status": "COMPLETED",
        "deadline_info": deadline_info,
        "analysis_summary": {
            "fraud_probability": analysis_result.get("risk_analysis", {}).get("fraud_probability", 0.0),
            "win_probability": analysis_result.get("win_probability", {}).get("score", 0.5),
            "confidence": analysis_result.get("win_probability", {}).get("confidence_level", "MEDIUM"),
            "recommendation": analysis_result.get("recommendation", {}).get("decision", "REVIEW")
        },
        "message": f"Dispute '{dispute.dispute_id}' created and analyzed successfully in LIVE database."
    }


@router.post("/razorpay", status_code=status.HTTP_201_CREATED)
def handle_razorpay_webhook_endpoint(
    payload: WebhookDisputeCreateRequest,
    db: Session = Depends(get_live_db)
):
    """Primary Razorpay webhook endpoint for dispute creation."""
    return _process_webhook_dispute_creation(payload, db)


@router.post("/disputes", status_code=status.HTTP_201_CREATED)
def create_webhook_dispute_endpoint(
    payload: WebhookDisputeCreateRequest,
    db: Session = Depends(get_live_db)
):
    """Alias endpoint for creating disputes via webhook simulator in LIVE database."""
    return _process_webhook_dispute_creation(payload, db)


@router.post("", status_code=status.HTTP_201_CREATED)
def webhook_root_endpoint(
    payload: WebhookDisputeCreateRequest,
    db: Session = Depends(get_live_db)
):
    """Direct root /webhooks endpoint."""
    return _process_webhook_dispute_creation(payload, db)
