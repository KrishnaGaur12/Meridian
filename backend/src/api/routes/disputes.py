"""
Dispute API Endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.repository import (
    create_dispute, get_dispute, get_all_disputes, get_disputes_count, get_dispute_timeline, get_dispute_case_analysis,
    calculate_deadline_info, transition_dispute_workflow_stage, get_case_readiness_and_gate, submit_dispute_package,
    get_dispute_audit_trail, get_dispute_explainability, get_dispute_next_action, get_dispute_command_center,
    get_required_evidence_mapping, simulate_dispute_outcome
)
from src.chargeback.service import ChargebackPackageService
from src.schemas.api_schemas import (
    DisputeCreateSchema, DisputeResponseSchema, DisputeTimelineEventSchema, DisputeCaseAnalysisSchema,
    DisputeWorkflowTransitionSchema, DisputeCaseReadinessSchema, DisputeSubmitRequestSchema, DisputeSubmitResponseSchema,
    DisputeOutcomeResponseSchema, AIExplainabilitySchema, NextBestActionSchema, DisputeAuditEventSchema,
    ChargebackPackageInspectionSchema, CommandCenterSnapshotSchema
)

router = APIRouter(prefix="/disputes", tags=["Disputes"])

def format_dispute_response(dispute) -> DisputeResponseSchema:
    """Helper to convert ORM Dispute entity to DisputeResponseSchema with calculated deadline info."""
    tx = dispute.transaction
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)
    
    return DisputeResponseSchema(
        dispute_id=dispute.dispute_id,
        transaction_id=dispute.transaction_id,
        customer_id=dispute.customer_id,
        reason_code=dispute.reason_code,
        reason_description=dispute.reason_description or "",
        status=dispute.status,
        phase=dispute.phase or "chargeback",
        respond_by=dispute.respond_by,
        workflow_stage=dispute.workflow_stage or "DISPUTE_RAISED",
        case_source=getattr(dispute, "case_source", "SIMULATED_RAZORPAY") or "SIMULATED_RAZORPAY",
        merchant_attention_state=getattr(dispute, "merchant_attention_state", "ACTION_REQUIRED") or "ACTION_REQUIRED",
        ai_last_checked=getattr(dispute, "ai_last_checked", None),
        attention_reason=None,
        created_at=dispute.created_at,
        remaining_hours=deadline_info["remaining_hours"],
        remaining_time_human=deadline_info["remaining_time_human"],
        is_overdue=deadline_info["is_overdue"],
        deadline_status=deadline_info["deadline_status"],
        urgency_level=deadline_info["urgency_level"],
        amount=tx.amount if tx else None,
        currency=tx.currency if tx else "USD"
    )

@router.get("", response_model=List[DisputeResponseSchema], status_code=status.HTTP_200_OK)
def list_disputes_endpoint(
    case_source: Optional[str] = None,
    status: Optional[str] = None,
    workflow_stage: Optional[str] = None,
    merchant_attention_state: Optional[str] = None,
    search: Optional[str] = None,
    page: Optional[int] = Query(None, ge=1, description="1-indexed page number"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Items per page"),
    limit: Optional[int] = Query(None, ge=1, le=200, description="Max items to return"),
    offset: Optional[int] = Query(None, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """
    Retrieves dispute records from database with deadline metadata.
    Optimized for fast rendering: does not load heavy evidence text BLOBs.
    Supports filtering by case_source, status, workflow_stage, merchant_attention_state, search, and pagination.
    """
    effective_limit = limit
    effective_offset = offset

    if page is not None and page_size is not None:
        effective_limit = page_size
        effective_offset = (page - 1) * page_size
    elif page is not None and page_size is None:
        effective_limit = 50
        effective_offset = (page - 1) * 50

    disputes = get_all_disputes(
        db,
        case_source=case_source,
        status=status,
        workflow_stage=workflow_stage,
        merchant_attention_state=merchant_attention_state,
        search=search,
        limit=effective_limit,
        offset=effective_offset
    )
    return [format_dispute_response(d) for d in disputes]

@router.post("", response_model=DisputeResponseSchema, status_code=status.HTTP_201_CREATED)
def create_dispute_endpoint(payload: DisputeCreateSchema, db: Session = Depends(get_db)):
    """Creates a new merchant dispute case associated with an existing transaction."""
    try:
        data_dict = payload.model_dump()
        dispute = create_dispute(db, data_dict, auto_process=True)
        return format_dispute_response(dispute)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create dispute: {str(e)}"
        )

@router.get("/{dispute_id}", response_model=DisputeResponseSchema, status_code=status.HTTP_200_OK)
def get_dispute_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Retrieves a dispute by ID with calculated deadline metadata."""
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute with ID '{dispute_id}' not found."
        )
    return format_dispute_response(dispute)

@router.get("/{dispute_id}/timeline", response_model=List[DisputeTimelineEventSchema], status_code=status.HTTP_200_OK)
def get_dispute_timeline_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Retrieves chronological timeline events that actually occurred for a dispute."""
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute with ID '{dispute_id}' not found."
        )
    return get_dispute_timeline(db, dispute_id)

@router.get("/{dispute_id}/analysis", response_model=DisputeCaseAnalysisSchema, status_code=status.HTTP_200_OK)
def get_dispute_case_analysis_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Executes and returns full AI Case & Evidence Intelligence for a dispute using real database entities,
    Fraud Model V2, Evidence Engine, Win Probability Model, and Recommendation Engine.
    """
    try:
        analysis = get_dispute_case_analysis(db, dispute_id)
        return analysis
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI case analysis: {str(e)}"
        )

@router.post("/{dispute_id}/transition", response_model=DisputeResponseSchema, status_code=status.HTTP_200_OK)
def transition_dispute_stage_endpoint(
    dispute_id: str, payload: DisputeWorkflowTransitionSchema, db: Session = Depends(get_db)
):
    """
    Executes a controlled workflow stage transition with validation and timeline logging.
    Allows forward progress and rework/re-analysis.
    """
    try:
        dispute = transition_dispute_workflow_stage(
            db, dispute_id, payload.target_stage, payload.event_title, payload.event_desc
        )
        return format_dispute_response(dispute)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )

@router.get("/{dispute_id}/readiness", response_model=DisputeCaseReadinessSchema, status_code=status.HTTP_200_OK)
def get_dispute_readiness_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Evaluates real database entities to compute deterministic case readiness score and submission eligibility.
    """
    try:
        readiness = get_case_readiness_and_gate(db, dispute_id)
        return readiness
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )

@router.post("/{dispute_id}/submit", response_model=DisputeSubmitResponseSchema, status_code=status.HTTP_200_OK)
def submit_dispute_endpoint(
    dispute_id: str,
    payload: Optional[DisputeSubmitRequestSchema] = None,
    db: Session = Depends(get_db)
):
    """
    Executes the hard backend submission gate pipeline.
    Validates readiness, records merchant position, generates unique gateway reference ID,
    advances workflow_stage to SUBMITTED, and records gateway boundary submission.
    """
    try:
        position = payload.merchant_position if payload else "CONTEST"
        result = submit_dispute_package(db, dispute_id, merchant_position=position)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )


@router.post("/{dispute_id}/simulate-outcome", response_model=DisputeOutcomeResponseSchema, status_code=status.HTTP_200_OK)
def simulate_outcome_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Simulates the dispute outcome (WON or LOST) based on deterministic evaluation
    of evidence completeness, win probability, fraud risk, and merchant position.
    Records outcome event in dispute timeline.
    """
    try:
        outcome = simulate_dispute_outcome(db, dispute_id)
        return outcome
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(ve).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to simulate dispute outcome: {str(e)}"
        )


@router.get("/{dispute_id}/explainability", response_model=AIExplainabilitySchema, status_code=status.HTTP_200_OK)
def get_dispute_explainability_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Returns transparent AI explainability metrics for Fraud Model V2 and Win Probability model."""
    try:
        return get_dispute_explainability(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        print("EXPLAINABILITY ENDPOINT ERROR:", type(e), e)
        raise e


@router.get("/{dispute_id}/evidence-intelligence", status_code=status.HTTP_200_OK)
def get_evidence_intelligence_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Returns granular evidence requirements vs matched database records mapping."""
    try:
        return get_required_evidence_mapping(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{dispute_id}/next-action", response_model=NextBestActionSchema, status_code=status.HTTP_200_OK)
def get_dispute_next_action_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Computes deterministic Next Best Action for merchant."""
    try:
        return get_dispute_next_action(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{dispute_id}/audit", response_model=List[DisputeAuditEventSchema], status_code=status.HTTP_200_OK)
def get_dispute_audit_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Retrieves complete chronological audit log stream for dispute."""
    try:
        return get_dispute_audit_trail(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{dispute_id}/package-inspection", response_model=ChargebackPackageInspectionSchema, status_code=status.HTTP_200_OK)
def inspect_package_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Returns complete payload representation of chargeback package to be submitted."""
    try:
        return ChargebackPackageService().inspect_chargeback_package(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/{dispute_id}/command-center", response_model=CommandCenterSnapshotSchema, status_code=status.HTTP_200_OK)
def get_command_center_snapshot_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Aggregates a complete, single coherent Operations Command Center snapshot for a dispute."""
    try:
        return get_dispute_command_center(db, dispute_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


class MerchantAcceptSchema(BaseModel):
    reason: Optional[str] = Field(default="Merchant accepted dispute", description="Reason for acceptance")


class MerchantOverrideSchema(BaseModel):
    override_decision: str = Field(..., description="Merchant's override decision: CONTEST, ACCEPT, INVESTIGATE")
    reason: Optional[str] = Field(default="", description="Reason for override")


@router.post("/{dispute_id}/accept", status_code=status.HTTP_200_OK)
def accept_dispute_endpoint(dispute_id: str, payload: MerchantAcceptSchema = None, db: Session = Depends(get_db)):
    """
    Merchant accepts dispute (gives up contesting).
    Sets status to CLOSED, workflow_stage to RESOLVED, merchant_attention_state to WAITING.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    if dispute.workflow_stage in ["SUBMITTED", "RESOLVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dispute '{dispute_id}' is already {dispute.workflow_stage}."
        )

    previous_stage = dispute.workflow_stage
    reason = payload.reason if payload else "Merchant accepted dispute"

    dispute.status = "CLOSED"
    dispute.workflow_stage = "RESOLVED"
    dispute.merchant_attention_state = "WAITING"
    db.commit()

    from src.database.repository import create_dispute_event
    create_dispute_event(
        db, dispute_id,
        event_type="MERCHANT_ACCEPTED",
        title="Merchant Accepted Dispute",
        description=f"Merchant accepted dispute claim. Reason: {reason}",
        actor_type="MERCHANT",
        previous_stage=previous_stage,
        new_stage="RESOLVED",
        metadata={"reason": reason, "decision": "ACCEPT"}
    )

    try:
        from src.services.ai.cache import AICacheManager
        AICacheManager().invalidate_dispute(dispute_id)
    except Exception:
        pass

    return {
        "dispute_id": dispute_id,
        "status": "CLOSED",
        "workflow_stage": "RESOLVED",
        "merchant_attention_state": "WAITING",
        "message": "Dispute accepted by merchant.",
    }


@router.post("/{dispute_id}/override-recommendation", status_code=status.HTTP_200_OK)
def override_recommendation_endpoint(
    dispute_id: str, payload: MerchantOverrideSchema, db: Session = Depends(get_db)
):
    """
    Merchant overrides AI recommendation with their own decision.
    Records override with audit trail.
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    if dispute.workflow_stage in ["SUBMITTED", "RESOLVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot override — dispute is already {dispute.workflow_stage}."
        )

    valid_decisions = ["CONTEST", "ACCEPT", "INVESTIGATE"]
    if payload.override_decision.upper() not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid override decision. Must be one of: {', '.join(valid_decisions)}"
        )

    previous_stage = dispute.workflow_stage
    override_decision = payload.override_decision.upper()

    # Update workflow based on override
    if override_decision == "ACCEPT":
        dispute.status = "CLOSED"
        dispute.workflow_stage = "RESOLVED"
        dispute.merchant_attention_state = "WAITING"
    elif override_decision == "CONTEST":
        dispute.merchant_attention_state = "REVIEW_RECOMMENDED"
        if dispute.workflow_stage not in ["READY_FOR_SUBMISSION", "SUBMITTED"]:
            dispute.workflow_stage = "MERCHANT_REVIEW"
    elif override_decision == "INVESTIGATE":
        dispute.merchant_attention_state = "ACTION_REQUIRED"

    db.commit()

    from src.database.repository import create_dispute_event
    create_dispute_event(
        db, dispute_id,
        event_type="MERCHANT_OVERRIDE",
        title=f"Merchant Override: {override_decision}",
        description=f"Merchant overrode AI recommendation to {override_decision}. Reason: {payload.reason or 'N/A'}",
        actor_type="MERCHANT",
        previous_stage=previous_stage,
        new_stage=dispute.workflow_stage,
        metadata={
            "override_decision": override_decision,
            "reason": payload.reason or "",
        }
    )

    try:
        from src.services.ai.cache import AICacheManager
        AICacheManager().invalidate_dispute(dispute_id)
    except Exception:
        pass


    return {
        "dispute_id": dispute_id,
        "override_decision": override_decision,
        "status": dispute.status,
        "workflow_stage": dispute.workflow_stage,
        "merchant_attention_state": dispute.merchant_attention_state,
        "message": f"Merchant override recorded: {override_decision}",
    }


@router.post("/{dispute_id}/reassess", status_code=status.HTTP_200_OK)
def reassess_dispute_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Manually triggers a full AI reassessment of the dispute case.
    Returns updated case analysis with impact delta.
    """
    from src.pipeline.autopilot import AIAutopilot
    try:
        result = AIAutopilot.reassess_dispute(db, dispute_id, trigger="MANUAL_REASSESSMENT")
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
