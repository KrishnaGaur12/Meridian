"""
Evidence Engine API Endpoints.
Retrieves, creates, updates, deletes evidence with automatic AI reassessment.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.evidence.engine import EvidenceEngine
from src.evidence.schemas import EvidencePackageSchema

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
import time

from src.database.models import Evidence, Dispute, DisputeEvent
from src.pipeline.autopilot import AIAutopilot

class CreateEvidenceRequest(BaseModel):
    evidence_id: Optional[str] = None
    dispute_id: str
    transaction_id: Optional[str] = "TXN_GENERIC"
    evidence_type: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    verification_status: Optional[str] = "AVAILABLE"
    evidence_data: Optional[Dict[str, Any]] = None

class UpdateEvidenceRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    verification_status: Optional[str] = None
    evidence_data: Optional[Dict[str, Any]] = None

router = APIRouter(prefix="", tags=["Evidence"])

evidence_engine = EvidenceEngine()

@router.post("/disputes/{dispute_id}/evidence", response_model=EvidencePackageSchema, status_code=status.HTTP_200_OK)
def generate_evidence_package_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """
    Executes Evidence Engine for a given dispute case.
    Gathers, validates, and verifies available evidence from the application database,
    and returns a structured Evidence Package.
    """
    try:
        package = evidence_engine.evaluate_dispute_evidence(db, dispute_id)
        return package
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate evidence package: {str(e)}"
        )

@router.post("/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence_endpoint(payload: CreateEvidenceRequest, db: Session = Depends(get_db)):
    """
    Persists a new evidence item to the SQLite database, logs a timeline event,
    and triggers automatic AI case reassessment with impact delta.
    """
    dispute = db.query(Dispute).filter(Dispute.dispute_id == payload.dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute #{payload.dispute_id} not found.")

    # Capture BEFORE analysis for impact delta
    try:
        from src.database.repository import get_dispute_case_analysis
        before_analysis = get_dispute_case_analysis(db, payload.dispute_id)
    except Exception:
        before_analysis = None

    evidence_id = payload.evidence_id or f"EVD_UPL_{int(time.time() * 1000)}"
    txn_id = payload.transaction_id if payload.transaction_id != "TXN_GENERIC" else dispute.transaction_id

    new_item = Evidence(
        evidence_id=evidence_id,
        dispute_id=payload.dispute_id,
        transaction_id=txn_id,
        evidence_type=payload.evidence_type,
        title=payload.title or payload.evidence_type.replace("_", " ").title(),
        description=payload.description or f"Uploaded {payload.evidence_type} proof document.",
        source="MERCHANT_UPLOAD",
        verification_status=payload.verification_status or "AVAILABLE",
        evidence_data_json=json.dumps(payload.evidence_data or {"uploaded": True}),
    )

    db.add(new_item)

    # Log immutable dispute timeline event
    evt = DisputeEvent(
        event_id=f"EVT_{int(time.time() * 1000)}",
        dispute_id=payload.dispute_id,
        event_type="EVIDENCE_COLLECTION",
        title="Merchant added evidence proof",
        description=f"Uploaded {new_item.title} document.",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="EVIDENCE_COLLECTION",
    )
    db.add(evt)

    if dispute.workflow_stage not in ["READY_FOR_SUBMISSION", "SUBMITTED"]:
        dispute.workflow_stage = "EVIDENCE_COLLECTION"

    db.commit()
    db.refresh(new_item)

    # Trigger AI reassessment
    impact_delta = None
    try:
        from src.services.ai.cache import AICacheManager
        AICacheManager().invalidate_dispute(payload.dispute_id)
        reassessment = AIAutopilot.reassess_dispute(db, payload.dispute_id, trigger="EVIDENCE_ADDED")
        after_analysis = reassessment.get("case_analysis")
        if before_analysis and after_analysis:
            impact_delta = AIAutopilot.compute_evidence_impact_delta(
                before_analysis, after_analysis,
                action_description=f"Merchant added {new_item.title}"
            )
        else:
            impact_delta = reassessment.get("impact_delta")
    except Exception:
        pass

    return {
        "evidence_id": new_item.evidence_id,
        "dispute_id": new_item.dispute_id,
        "evidence_type": new_item.evidence_type,
        "title": new_item.title,
        "description": new_item.description,
        "status": new_item.verification_status,
        "verification_status": new_item.verification_status,
        "data": payload.evidence_data or {},
        "impact_delta": impact_delta,
    }


@router.put("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def update_evidence_endpoint(evidence_id: str, payload: UpdateEvidenceRequest, db: Session = Depends(get_db)):
    """
    Updates an existing evidence item and triggers automatic AI case reassessment.
    """
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    dispute_id = evidence.dispute_id

    # Capture BEFORE analysis
    try:
        from src.database.repository import get_dispute_case_analysis
        before_analysis = get_dispute_case_analysis(db, dispute_id)
    except Exception:
        before_analysis = None

    # Apply updates
    if payload.title is not None:
        evidence.title = payload.title
    if payload.description is not None:
        evidence.description = payload.description
    if payload.verification_status is not None:
        evidence.verification_status = payload.verification_status
    if payload.evidence_data is not None:
        evidence.evidence_data_json = json.dumps(payload.evidence_data)

    # Log timeline event
    evt = DisputeEvent(
        event_id=f"EVT_{int(time.time() * 1000)}",
        dispute_id=dispute_id,
        event_type="EVIDENCE_UPDATED",
        title="Evidence record updated",
        description=f"Updated evidence item {evidence_id} ({evidence.evidence_type}).",
        actor_type="MERCHANT",
    )
    db.add(evt)
    db.commit()
    db.refresh(evidence)

    # Trigger AI reassessment
    impact_delta = None
    try:
        from src.services.ai.cache import AICacheManager
        AICacheManager().invalidate_dispute(dispute_id)
        reassessment = AIAutopilot.reassess_dispute(db, dispute_id, trigger="EVIDENCE_UPDATED")
        after_analysis = reassessment.get("case_analysis")
        if before_analysis and after_analysis:
            impact_delta = AIAutopilot.compute_evidence_impact_delta(
                before_analysis, after_analysis,
                action_description=f"Merchant updated {evidence.title}"
            )
        else:
            impact_delta = reassessment.get("impact_delta")
    except Exception:
        pass

    return {
        "evidence_id": evidence.evidence_id,
        "dispute_id": evidence.dispute_id,
        "evidence_type": evidence.evidence_type,
        "title": evidence.title,
        "description": evidence.description,
        "verification_status": evidence.verification_status,
        "impact_delta": impact_delta,
    }


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def delete_evidence_endpoint(evidence_id: str, db: Session = Depends(get_db)):
    """
    Removes an evidence item and triggers automatic AI case reassessment.
    Hard-deletes the evidence record.
    """
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    dispute_id = evidence.dispute_id
    evidence_title = evidence.title
    evidence_type = evidence.evidence_type

    # Capture BEFORE analysis
    try:
        from src.database.repository import get_dispute_case_analysis
        before_analysis = get_dispute_case_analysis(db, dispute_id)
    except Exception:
        before_analysis = None

    # Log timeline event before deletion
    evt = DisputeEvent(
        event_id=f"EVT_{int(time.time() * 1000)}",
        dispute_id=dispute_id,
        event_type="EVIDENCE_REMOVED",
        title="Evidence record removed",
        description=f"Removed evidence item {evidence_id} ({evidence_type}: {evidence_title}).",
        actor_type="MERCHANT",
    )
    db.add(evt)

    # Hard delete
    db.delete(evidence)
    db.commit()

    # Trigger AI reassessment
    impact_delta = None
    try:
        from src.services.ai.cache import AICacheManager
        AICacheManager().invalidate_dispute(dispute_id)
        reassessment = AIAutopilot.reassess_dispute(db, dispute_id, trigger="EVIDENCE_REMOVED")
        after_analysis = reassessment.get("case_analysis")
        if before_analysis and after_analysis:
            impact_delta = AIAutopilot.compute_evidence_impact_delta(
                before_analysis, after_analysis,
                action_description=f"Merchant removed {evidence_title}"
            )
        else:
            impact_delta = reassessment.get("impact_delta")
    except Exception:
        pass


    return {
        "evidence_id": evidence_id,
        "dispute_id": dispute_id,
        "deleted": True,
        "evidence_type": evidence_type,
        "title": evidence_title,
        "impact_delta": impact_delta,
    }
