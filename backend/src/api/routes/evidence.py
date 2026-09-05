"""
Evidence Engine API Endpoints.
Retrieves, uploads, creates, verifies, approves, rejects, updates, replaces, and deletes evidence
with automatic AI reassessment, DeepSeek evidence verification, ML recalculation, and package synchronization.
"""

from typing import Optional, Dict, Any, List
import json
import time

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import Evidence, Dispute, DisputeEvent, utc_now_iso
from src.database.repository import (
    get_dispute, get_dispute_case_analysis, approve_dispute_evidence,
    reject_dispute_evidence, calculate_deadline_info, create_dispute_event
)
from src.evidence.engine import EvidenceEngine
from src.evidence.schemas import (
    EvidencePackageSchema, EvidenceApprovalResponseSchema, EvidenceDetailSchema
)
from src.evidence.file_processor import EvidenceFileProcessor
from src.pipeline.analysis_service import analyze_dispute
from src.pipeline.autopilot import AIAutopilot
from src.services.ai.service import AIService
from src.services.ai.evidence_analysis_service import EvidenceAnalysisService
from src.services.ai.schemas import EvidenceAnalysisResultSchema
from src.utils.id_generator import generate_evidence_id, generate_event_id
from src.utils.logger import get_logger

logger = get_logger("EvidenceAPI")
router = APIRouter(prefix="", tags=["Evidence"])

evidence_engine = EvidenceEngine()
ai_service = AIService()


class CreateEvidenceRequest(BaseModel):
    evidence_id: Optional[str] = None
    dispute_id: Optional[str] = None
    transaction_id: Optional[str] = "TXN_GENERIC"
    evidence_type: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    source: Optional[str] = "MERCHANT_UPLOAD"
    source_reference_id: Optional[str] = None
    verification_status: Optional[str] = "UNVERIFIED"
    approval_status: Optional[str] = "PENDING_APPROVAL"
    metadata: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    evidence_data: Optional[Dict[str, Any]] = None


class UpdateEvidenceRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    evidence_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    verification_status: Optional[str] = None
    approval_status: Optional[str] = None
    evidence_data: Optional[Dict[str, Any]] = None


class ApproveEvidenceRequest(BaseModel):
    approved_by: Optional[str] = "MERCHANT"


class RejectEvidenceRequest(BaseModel):
    reason: Optional[str] = ""


def format_evidence_detail_response(ev: Evidence) -> EvidenceDetailSchema:
    """Helper to convert Evidence ORM model to EvidenceDetailSchema with AI verification results."""
    return EvidenceDetailSchema(
        evidence_id=ev.evidence_id,
        dispute_id=ev.dispute_id,
        transaction_id=ev.transaction_id,
        evidence_type=ev.evidence_type,
        title=ev.title,
        description=ev.description,
        verification_status=ev.verification_status or "UNVERIFIED",
        approval_status=ev.approval_status or "PENDING_APPROVAL",
        approved_at=ev.approved_at,
        approved_by=ev.approved_by,
        source=ev.source or "DATABASE",
        source_reference_id=ev.source_reference_id,
        extracted_text=ev.extracted_text or ev.raw_content,
        data=ev.evidence_data,
        ai_analysis=ev.ai_analysis,
        ai_analysis_status=ev.ai_analysis_status or "PENDING",
        ai_analyzed_at=ev.ai_analyzed_at,
        ai_error=ev.ai_error,
        created_at=ev.created_at,
        updated_at=ev.updated_at
    )


# --- 1. GET DISPUTE EVIDENCE PACKAGE ---
@router.get("/disputes/{dispute_id}/evidence", response_model=EvidencePackageSchema, status_code=status.HTTP_200_OK)
def get_dispute_evidence_endpoint(dispute_id: str, db: Session = Depends(get_db)):
    """Retrieves and evaluates available evidence package for a dispute from active DB evidence."""
    try:
        package = evidence_engine.evaluate_dispute_evidence(db, dispute_id)
        return package
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate evidence package: {str(e)}"
        )


# --- 2. GET SINGLE EVIDENCE ITEM ---
@router.get("/disputes/{dispute_id}/evidence/{evidence_id}", response_model=EvidenceDetailSchema, status_code=status.HTTP_200_OK)
def get_dispute_evidence_item_endpoint(dispute_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """Retrieves detailed record for a specific evidence item including persisted AI verification analysis."""
    ev = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")
    return format_evidence_detail_response(ev)


@router.get("/evidence/{evidence_id}", response_model=EvidenceDetailSchema, status_code=status.HTTP_200_OK)
def get_evidence_item_alias_endpoint(evidence_id: str, db: Session = Depends(get_db)):
    """Direct alias for retrieving evidence item details."""
    ev = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return format_evidence_detail_response(ev)


# --- 3. ADD EVIDENCE (STRUCTURED OR VIA FORM) ---
@router.post("/disputes/{dispute_id}/evidence", status_code=status.HTTP_200_OK)
def add_dispute_evidence_endpoint(
    dispute_id: str,
    payload: Optional[CreateEvidenceRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Creates/adds a new evidence item, triggers DeepSeek AI verification, and updates dispute intelligence.
    """
    if not payload or not payload.evidence_type:
        try:
            return evidence_engine.evaluate_dispute_evidence(db, dispute_id)
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence_id = payload.evidence_id or generate_evidence_id()
    txn_id = dispute.transaction_id
    now = utc_now_iso()

    content_dict = payload.content or payload.evidence_data or payload.metadata or {}
    raw_str = json.dumps(content_dict)
    text_content = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in content_dict.items() if v]) or raw_str

    new_item = Evidence(
        evidence_id=evidence_id,
        dispute_id=dispute_id,
        transaction_id=txn_id,
        evidence_type=payload.evidence_type,
        title=payload.title or payload.evidence_type.replace("_", " ").title(),
        description=payload.description or f"Added {payload.evidence_type} proof.",
        source=payload.source or "MERCHANT_UPLOAD",
        source_reference_id=payload.source_reference_id,
        file_path=None,
        mime_type="application/json",
        file_size=len(raw_str.encode("utf-8")),
        document_hash=EvidenceFileProcessor.compute_hash(raw_str.encode("utf-8")),
        content_hash=EvidenceAnalysisService.compute_content_hash(text_content, content_dict),
        raw_content=raw_str,
        extracted_text=text_content,
        content_json=raw_str,
        key_entities_json=raw_str,
        evidence_data_json=raw_str,
        verification_status=payload.verification_status or "UNVERIFIED",
        verification_confidence=1.0,
        verification_errors_json="[]",
        approval_status=payload.approval_status or "PENDING_APPROVAL",
        ai_analysis_status="PENDING",
        approved_at=None,
        approved_by=None,
        created_at=now,
        updated_at=now,
        is_deleted=0
    )
    db.add(new_item)

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_ADDED",
        title=f"Merchant Added Evidence: {new_item.title}",
        description=f"Added {new_item.title} ({new_item.evidence_type}). Verification: {new_item.verification_status}.",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="MERCHANT_REVIEW",
        metadata={
            "evidence_id": new_item.evidence_id,
            "evidence_type": new_item.evidence_type,
            "verification_status": new_item.verification_status,
            "approval_status": new_item.approval_status
        }
    )

    db.commit()
    db.refresh(new_item)

    # Trigger DeepSeek AI Evidence Verification
    ai_verification_result = None
    try:
        ai_verification_result = ai_service.analyze_evidence(db, new_item.evidence_id)
        db.refresh(new_item)
    except Exception as ai_err:
        logger.warning(f"AI evidence verification error: {ai_err}")

    # Rerun authoritative dispute analysis pipeline
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_ADDED", broadcast=True)
    impact_delta = {
        "win_probability_delta": 0.05,
        "risk_score_delta": 0.0,
        "action_description": f"Merchant added {new_item.title}",
        "previous_win_prob": 0.50,
        "new_win_prob": analysis.get("win_probability", {}).get("score", 0.55),
        "previous_recommendation": "INVESTIGATE",
        "new_recommendation": analysis.get("recommendation", {}).get("decision", "CONTEST")
    }

    return {
        "success": True,
        "evidence_id": new_item.evidence_id,
        "dispute_id": new_item.dispute_id,
        "evidence_type": new_item.evidence_type,
        "title": new_item.title,
        "description": new_item.description,
        "verification_status": new_item.verification_status,
        "approval_status": new_item.approval_status,
        "ai_analysis": new_item.ai_analysis or (ai_verification_result.model_dump() if ai_verification_result else None),
        "ai_analysis_status": new_item.ai_analysis_status,
        "content": new_item.content,
        "impact_delta": impact_delta,
        "case_analysis": analysis
    }


@router.post("/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence_endpoint(payload: CreateEvidenceRequest, db: Session = Depends(get_db)):
    """Direct alias for creating evidence."""
    dispute_id = payload.dispute_id
    if not dispute_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dispute_id is required.")
    return add_dispute_evidence_endpoint(dispute_id=dispute_id, payload=payload, db=db)


# --- 4. UPLOAD EVIDENCE FILE ---
@router.post("/disputes/{dispute_id}/evidence/upload", status_code=status.HTTP_201_CREATED)
async def upload_dispute_evidence_file_endpoint(
    dispute_id: str,
    file: UploadFile = File(...),
    evidence_type: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Uploads a new evidence document file for a dispute:
    1. Validates & hashes file
    2. Extracts text and business facts from PDF, DOCX, TXT, CSV, JSON, or image
    3. Persists record in DB
    4. Triggers DeepSeek AI Evidence Verification
    5. Updates dispute risk intelligence
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    file_bytes = await file.read()
    filename = file.filename or "uploaded_evidence.pdf"

    proc_result = EvidenceFileProcessor.process_and_analyze(
        file_bytes=file_bytes,
        filename=filename,
        content_type=file.content_type,
        preferred_evidence_type=evidence_type
    )

    if not proc_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=proc_result.get("error", "File upload processing failed.")
        )

    ev_id = generate_evidence_id()
    now = utc_now_iso()
    ev_type = proc_result["evidence_type"]
    doc_title = title or filename or ev_type.replace("_", " ").title()
    doc_desc = description or proc_result["analysis"]["interpretation"]
    extracted_txt = proc_result.get("extracted_text", "")
    facts_dict = proc_result.get("facts", {})
    content_hash = EvidenceAnalysisService.compute_content_hash(extracted_txt, facts_dict)

    new_item = Evidence(
        evidence_id=ev_id,
        dispute_id=dispute_id,
        transaction_id=dispute.transaction_id,
        evidence_type=ev_type,
        title=doc_title,
        description=doc_desc,
        source="MERCHANT_FILE_UPLOAD",
        source_reference_id=filename,
        file_path=proc_result.get("file_info", {}).get("file_path"),
        mime_type=file.content_type or "application/octet-stream",
        file_size=proc_result.get("file_size", len(file_bytes)),
        document_hash=proc_result.get("document_hash"),
        content_hash=content_hash,
        raw_content=proc_result.get("raw_content", ""),
        extracted_text=extracted_txt,
        content_json=json.dumps(facts_dict),
        key_entities_json=json.dumps(facts_dict),
        evidence_data_json=json.dumps(facts_dict),
        verification_status=proc_result["verification_status"],
        verification_confidence=1.0,
        verification_errors_json="[]",
        approval_status="PENDING_APPROVAL",
        ai_analysis_status="PENDING",
        approved_at=None,
        approved_by=None,
        created_at=now,
        updated_at=now,
        is_deleted=0
    )
    db.add(new_item)

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_FILE_UPLOADED",
        title=f"Uploaded {doc_title}",
        description=f"Uploaded '{filename}'. Extracted {len(extracted_txt)} chars. Verification queued.",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="MERCHANT_REVIEW",
        metadata={
            "evidence_id": ev_id,
            "filename": filename,
            "verification_status": new_item.verification_status,
            "approval_status": "PENDING_APPROVAL"
        }
    )

    db.commit()
    db.refresh(new_item)

    # Trigger DeepSeek AI Evidence Verification
    ai_verification_result = None
    try:
        ai_verification_result = ai_service.analyze_evidence(db, new_item.evidence_id)
        db.refresh(new_item)
    except Exception as ai_err:
        logger.warning(f"AI evidence verification error on upload: {ai_err}")

    # Authoritative dispute analysis
    analysis = analyze_dispute(dispute_id, db, trigger="FILE_UPLOADED", broadcast=True)
    impact_delta = {
        "win_probability_delta": 0.15,
        "risk_score_delta": 0.0,
        "action_description": f"Merchant uploaded {doc_title}",
        "previous_win_prob": 0.50,
        "new_win_prob": analysis.get("win_probability", {}).get("score", 0.65),
        "previous_recommendation": "INVESTIGATE",
        "new_recommendation": analysis.get("recommendation", {}).get("decision", "CONTEST")
    }

    return {
        "success": True,
        "evidence_id": new_item.evidence_id,
        "dispute_id": new_item.dispute_id,
        "evidence_type": new_item.evidence_type,
        "title": new_item.title,
        "description": new_item.description,
        "verification_status": new_item.verification_status,
        "approval_status": new_item.approval_status,
        "ai_analysis": new_item.ai_analysis or (ai_verification_result.model_dump() if ai_verification_result else None),
        "ai_analysis_status": new_item.ai_analysis_status,
        "file_info": proc_result.get("file_info"),
        "facts": facts_dict,
        "analysis": proc_result.get("analysis"),
        "impact_delta": impact_delta,
        "case_analysis": analysis
    }


@router.post("/evidence/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidence_file_alias_endpoint(
    file: UploadFile = File(...),
    dispute_id: str = Form(...),
    evidence_type: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Direct alias for file upload."""
    return await upload_dispute_evidence_file_endpoint(
        dispute_id=dispute_id, file=file, evidence_type=evidence_type,
        title=title, description=description, db=db
    )


# --- 5. EDIT EVIDENCE (PATCH / PUT) ---
@router.patch("/disputes/{dispute_id}/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
@router.put("/disputes/{dispute_id}/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def edit_dispute_evidence_endpoint(
    dispute_id: str,
    evidence_id: str,
    payload: UpdateEvidenceRequest,
    db: Session = Depends(get_db)
):
    """
    Merchant edits an evidence record:
    1. Validates dispute and evidence association
    2. If content changes, resets approval_status and re-runs AI verification
    3. Persists changes to DB
    4. Automatically reruns analyze_dispute()
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    content_changed = False
    if payload.title is not None:
        evidence.title = payload.title
    if payload.description is not None:
        evidence.description = payload.description
    if payload.evidence_type is not None:
        evidence.evidence_type = payload.evidence_type
        content_changed = True
    if payload.content is not None or payload.evidence_data is not None:
        new_content = payload.content or payload.evidence_data
        evidence.content = new_content
        text_content = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in new_content.items() if v])
        evidence.extracted_text = text_content
        content_changed = True

    if content_changed:
        evidence.approval_status = "PENDING_APPROVAL"
        evidence.approved_at = None
        evidence.approved_by = None
        evidence.content_hash = EvidenceAnalysisService.compute_content_hash(
            evidence.extracted_text or "",
            evidence.key_entities or evidence.evidence_data
        )

    if payload.verification_status is not None:
        evidence.verification_status = payload.verification_status
    if payload.approval_status is not None and not content_changed:
        evidence.approval_status = payload.approval_status

    evidence.updated_at = utc_now_iso()

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_EDITED",
        title=f"Evidence Edited: {evidence.title}",
        description=f"Merchant updated evidence '{evidence.title}'. Approval reset to {evidence.approval_status}.",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="MERCHANT_REVIEW",
        metadata={
            "evidence_id": evidence.evidence_id,
            "evidence_type": evidence.evidence_type,
            "approval_status": evidence.approval_status,
            "content_changed": content_changed
        }
    )

    db.commit()
    db.refresh(evidence)

    # Re-run AI verification if content changed
    if content_changed:
        try:
            ai_service.analyze_evidence(db, evidence.evidence_id, force_reanalyze=True)
            db.refresh(evidence)
        except Exception as ai_err:
            logger.warning(f"AI re-verification failed on edit: {ai_err}")

    # Rerun authoritative pipeline
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_EDITED", broadcast=True)
    impact_delta = {
        "win_probability_delta": 0.05,
        "risk_score_delta": 0.0,
        "action_description": f"Merchant updated {evidence.title}",
        "previous_win_prob": 0.50,
        "new_win_prob": analysis.get("win_probability", {}).get("score", 0.55),
        "previous_recommendation": "INVESTIGATE",
        "new_recommendation": analysis.get("recommendation", {}).get("decision", "CONTEST")
    }

    return {
        "success": True,
        "evidence_id": evidence.evidence_id,
        "dispute_id": evidence.dispute_id,
        "title": evidence.title,
        "description": evidence.description,
        "verification_status": evidence.verification_status,
        "approval_status": evidence.approval_status,
        "ai_analysis": evidence.ai_analysis,
        "ai_analysis_status": evidence.ai_analysis_status,
        "impact_delta": impact_delta,
        "case_analysis": analysis
    }


@router.put("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def update_evidence_alias_endpoint(
    evidence_id: str,
    payload: UpdateEvidenceRequest,
    db: Session = Depends(get_db)
):
    """Direct alias for editing evidence by evidence_id."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return edit_dispute_evidence_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, payload=payload, db=db)


# --- 6. REPLACE EVIDENCE FILE ---
@router.put("/disputes/{dispute_id}/evidence/{evidence_id}/file", status_code=status.HTTP_200_OK)
@router.post("/disputes/{dispute_id}/evidence/{evidence_id}/replace", status_code=status.HTTP_200_OK)
async def replace_dispute_evidence_file_endpoint(
    dispute_id: str,
    evidence_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Replaces backing document for an existing evidence record:
    1. Validates dispute and evidence association
    2. Rehashes, extracts text and facts from new file
    3. Resets approval_status = 'PENDING_APPROVAL'
    4. Triggers DeepSeek AI Verification
    5. Automatically reruns authoritative analyze_dispute()
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    file_bytes = await file.read()
    filename = file.filename or "replacement_evidence.pdf"

    proc_result = EvidenceFileProcessor.process_and_analyze(
        file_bytes=file_bytes,
        filename=filename,
        content_type=file.content_type,
        preferred_evidence_type=evidence.evidence_type
    )

    if not proc_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=proc_result.get("error", "Replacement file validation failed.")
        )

    extracted_txt = proc_result.get("extracted_text", "")
    facts_dict = proc_result.get("facts", {})
    content_hash = EvidenceAnalysisService.compute_content_hash(extracted_txt, facts_dict)
    now = utc_now_iso()

    evidence.source = "MERCHANT_FILE_UPLOAD"
    evidence.source_reference_id = filename
    evidence.file_path = proc_result.get("file_info", {}).get("file_path")
    evidence.mime_type = file.content_type or "application/octet-stream"
    evidence.file_size = proc_result.get("file_size", len(file_bytes))
    evidence.document_hash = proc_result.get("document_hash")
    evidence.content_hash = content_hash
    evidence.raw_content = proc_result.get("raw_content", "")
    evidence.extracted_text = extracted_txt
    evidence.content_json = json.dumps(facts_dict)
    evidence.key_entities_json = json.dumps(facts_dict)
    evidence.evidence_data_json = json.dumps(facts_dict)
    evidence.verification_status = proc_result["verification_status"]
    evidence.approval_status = "PENDING_APPROVAL"
    evidence.approved_at = None
    evidence.approved_by = None
    evidence.updated_at = now
    evidence.title = filename or evidence.title
    evidence.description = proc_result["analysis"]["interpretation"]

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_REPLACED",
        title=f"Evidence Document Replaced: {evidence.title}",
        description=f"Replaced document with '{filename}'. Extracted {len(extracted_txt)} chars. Approval reset to PENDING_APPROVAL.",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="MERCHANT_REVIEW",
        metadata={
            "evidence_id": evidence_id,
            "filename": filename,
            "verification_status": evidence.verification_status,
            "approval_status": "PENDING_APPROVAL"
        }
    )

    db.commit()
    db.refresh(evidence)

    # Trigger DeepSeek AI Verification
    try:
        ai_service.analyze_evidence(db, evidence.evidence_id, force_reanalyze=True)
        db.refresh(evidence)
    except Exception as ai_err:
        logger.warning(f"AI evidence verification error on replacement: {ai_err}")

    # Rerun authoritative pipeline
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_REPLACED", broadcast=True)
    impact_delta = {
        "win_probability_delta": 0.10,
        "risk_score_delta": 0.0,
        "action_description": f"Merchant replaced file with {filename}",
        "previous_win_prob": 0.50,
        "new_win_prob": analysis.get("win_probability", {}).get("score", 0.60),
        "previous_recommendation": "INVESTIGATE",
        "new_recommendation": analysis.get("recommendation", {}).get("decision", "CONTEST")
    }

    return {
        "success": True,
        "evidence_id": evidence.evidence_id,
        "dispute_id": evidence.dispute_id,
        "verification_status": evidence.verification_status,
        "approval_status": evidence.approval_status,
        "ai_analysis": evidence.ai_analysis,
        "ai_analysis_status": evidence.ai_analysis_status,
        "analysis": proc_result.get("analysis"),
        "impact_delta": impact_delta,
        "case_analysis": analysis
    }


@router.post("/evidence/{evidence_id}/replace", status_code=status.HTTP_200_OK)
async def replace_evidence_alias_endpoint(
    evidence_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Direct alias for replacing evidence file."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return await replace_dispute_evidence_file_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, file=file, db=db)


# --- 7. TRIGGER / RETRY AI EVIDENCE VERIFICATION ---
@router.post("/disputes/{dispute_id}/evidence/{evidence_id}/verify", response_model=EvidenceAnalysisResultSchema, status_code=status.HTTP_200_OK)
def verify_dispute_evidence_ai_endpoint(
    dispute_id: str,
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """
    Explicit endpoint to trigger or retry DeepSeek AI verification for an evidence document.
    Forces re-analysis even if a previous analysis exists.
    """
    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    try:
        result = ai_service.analyze_evidence(db, evidence_id, force_reanalyze=True)
        # Recalculate dispute case readiness & win metrics
        analyze_dispute(dispute_id, db, trigger="AI_EVIDENCE_VERIFIED", broadcast=True)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI evidence verification failed: {str(e)}")


@router.post("/evidence/{evidence_id}/verify", response_model=EvidenceAnalysisResultSchema, status_code=status.HTTP_200_OK)
def verify_evidence_ai_alias_endpoint(
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """Direct alias for triggering or retrying AI evidence verification."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return verify_dispute_evidence_ai_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, db=db)


# --- 8. GET PERSISTED AI EVIDENCE ANALYSIS ---
@router.get("/disputes/{dispute_id}/evidence/{evidence_id}/analysis", response_model=EvidenceAnalysisResultSchema, status_code=status.HTTP_200_OK)
def get_evidence_ai_analysis_endpoint(
    dispute_id: str,
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the persisted DeepSeek AI verification analysis for an evidence document.
    If not yet analyzed, triggers the analysis pipeline.
    """
    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    if evidence.ai_analysis and evidence.ai_analysis_status in ["VERIFIED", "REJECTED", "NEEDS_REVIEW", "FAILED"]:
        try:
            return EvidenceAnalysisResultSchema.model_validate(evidence.ai_analysis)
        except Exception:
            pass

    # If not yet analyzed or invalid cached representation, run analysis pipeline
    return ai_service.analyze_evidence(db, evidence_id, force_reanalyze=False)


@router.get("/evidence/{evidence_id}/analysis", response_model=EvidenceAnalysisResultSchema, status_code=status.HTTP_200_OK)
def get_evidence_analysis_alias_endpoint(
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """Direct alias for retrieving persisted AI evidence analysis."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return get_evidence_ai_analysis_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, db=db)


# --- 9. DELETE EVIDENCE (SOFT DELETE) ---
@router.delete("/disputes/{dispute_id}/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def delete_dispute_evidence_endpoint(
    dispute_id: str,
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """
    Soft-deletes an evidence item:
    1. Sets is_deleted = 1
    2. Recalculates required evidence & submission readiness
    3. Reruns analyze_dispute()
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")

    evidence_title = evidence.title
    evidence_type = evidence.evidence_type

    evidence.is_deleted = 1
    evidence.updated_at = utc_now_iso()

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_DELETED",
        title=f"Evidence Removed: {evidence_title}",
        description=f"Merchant removed evidence item '{evidence_title}' ({evidence_type}).",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage="MERCHANT_REVIEW",
        metadata={
            "evidence_id": evidence_id,
            "evidence_type": evidence_type,
            "title": evidence_title
        }
    )

    db.commit()

    # Rerun authoritative pipeline
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_DELETED", broadcast=True)
    impact_delta = {
        "win_probability_delta": -0.10,
        "risk_score_delta": 0.0,
        "action_description": f"Merchant removed {evidence_title}",
        "previous_win_prob": 0.65,
        "new_win_prob": analysis.get("win_probability", {}).get("score", 0.55),
        "previous_recommendation": "CONTEST",
        "new_recommendation": analysis.get("recommendation", {}).get("decision", "INVESTIGATE")
    }

    return {
        "success": True,
        "evidence_id": evidence_id,
        "dispute_id": dispute_id,
        "deleted": True,
        "evidence_type": evidence_type,
        "title": evidence_title,
        "impact_delta": impact_delta,
        "case_analysis": analysis
    }


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def delete_evidence_alias_endpoint(
    evidence_id: str,
    db: Session = Depends(get_db)
):
    """Direct alias for deleting evidence by evidence_id."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return delete_dispute_evidence_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, db=db)


# --- 10. APPROVE EVIDENCE ---
@router.post("/disputes/{dispute_id}/evidence/{evidence_id}/approve", status_code=status.HTTP_200_OK)
def approve_dispute_evidence_endpoint(
    dispute_id: str,
    evidence_id: str,
    payload: Optional[ApproveEvidenceRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Approves an evidence item for a dispute:
    1. Validates dispute and evidence existence and association
    2. Validates evidence is not deleted, invalid, or unreadable
    3. Persists approval_status = 'APPROVED', approved_at, and approved_by = 'MERCHANT' to DB
    4. Commits transaction to database immediately
    5. Executes full authoritative analyze_dispute() reassessment
    6. Returns refreshed dispute, evidence, ML, AI, and package state
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    ver_status = (evidence.verification_status or "UNVERIFIED").upper()
    if ver_status in ["INVALID", "UNREADABLE"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot approve evidence with verification status '{ver_status}'. Please replace document with a readable file."
        )

    approver = payload.approved_by if payload and payload.approved_by else "MERCHANT"
    now = utc_now_iso()

    evidence.verification_status = "VERIFIED"
    evidence.approval_status = "APPROVED"
    evidence.approved_at = now
    evidence.approved_by = approver
    evidence.updated_at = now

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_APPROVED",
        title=f"Evidence Approved: {evidence.title}",
        description=f"Merchant approved evidence '{evidence.title}' ({evidence.evidence_type}).",
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage=dispute.workflow_stage,
        metadata={
            "evidence_id": evidence_id,
            "evidence_type": evidence.evidence_type,
            "approval_status": "APPROVED",
            "approved_at": now,
            "approved_by": approver
        }
    )

    db.commit()
    db.refresh(evidence)

    # Authoritative dispute reassessment
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_APPROVED", broadcast=True)
    db.refresh(dispute)
    deadline_info = calculate_deadline_info(dispute.respond_by, dispute.status, dispute.workflow_stage)

    return {
        "success": True,
        "message": f"Evidence '{evidence.title}' approved successfully. Dispute reassessed.",
        "evidence": {
            "evidence_id": evidence.evidence_id,
            "dispute_id": evidence.dispute_id,
            "evidence_type": evidence.evidence_type,
            "title": evidence.title,
            "description": evidence.description,
            "verification_status": evidence.verification_status,
            "approval_status": evidence.approval_status,
            "ai_analysis": evidence.ai_analysis,
            "ai_analysis_status": evidence.ai_analysis_status,
            "approved_at": evidence.approved_at,
            "approved_by": evidence.approved_by,
            "source": evidence.source,
            "created_at": evidence.created_at,
            "updated_at": evidence.updated_at
        },
        "dispute": {
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
            "deadline_info": deadline_info
        },
        "ml_assessment": {
            "ml_status": "OK",
            "prediction_source": "MODEL",
            "model_version": "fraud-model-v2",
            "risk_score": analysis.get("risk_analysis", {}).get("fraud_probability", 0.0),
            "risk_level": analysis.get("risk_analysis", {}).get("risk_level", "LOW"),
            "win_probability": analysis.get("win_probability", {}).get("score", 0.5),
            "confidence": analysis.get("win_probability", {}).get("confidence_level", "MEDIUM"),
            "core_recommendation": analysis.get("recommendation", {}).get("decision", "INVESTIGATE")
        },
        "ai_analysis": analysis,
        "submission_readiness": analysis.get("submission_readiness", "NOT_READY"),
        "submission_blockers": analysis.get("submission_blockers", [])
    }


@router.post("/evidence/{evidence_id}/approve", status_code=status.HTTP_200_OK)
def approve_evidence_alias_endpoint(
    evidence_id: str,
    payload: Optional[ApproveEvidenceRequest] = None,
    db: Session = Depends(get_db)
):
    """Direct alias for approving evidence by evidence_id."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return approve_dispute_evidence_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, payload=payload, db=db)


# --- 11. REJECT EVIDENCE ---
@router.post("/disputes/{dispute_id}/evidence/{evidence_id}/reject", status_code=status.HTTP_200_OK)
def reject_dispute_evidence_endpoint(
    dispute_id: str,
    evidence_id: str,
    payload: Optional[RejectEvidenceRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Rejects an evidence item and triggers automatic case reassessment:
    1. Sets approval_status = 'REJECTED'
    2. Commits to database
    3. Excludes rejected evidence from defense bundle and submission
    4. Automatically reruns analyze_dispute()
    """
    dispute = get_dispute(db, dispute_id)
    if not dispute:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dispute '{dispute_id}' not found.")

    evidence = db.query(Evidence).filter(
        Evidence.evidence_id == evidence_id,
        Evidence.dispute_id == dispute_id,
        Evidence.is_deleted == 0
    ).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found for dispute '{dispute_id}'.")

    reason = payload.reason if payload else ""
    now = utc_now_iso()

    evidence.approval_status = "REJECTED"
    evidence.updated_at = now

    create_dispute_event(
        db, dispute_id,
        event_type="EVIDENCE_REJECTED",
        title=f"Evidence Rejected: {evidence.title}",
        description=f"Merchant rejected evidence '{evidence.title}' ({evidence.evidence_type}). {reason}".strip(),
        actor_type="MERCHANT",
        previous_stage=dispute.workflow_stage,
        new_stage=dispute.workflow_stage,
        metadata={
            "evidence_id": evidence_id,
            "evidence_type": evidence.evidence_type,
            "approval_status": "REJECTED",
            "reason": reason
        }
    )

    db.commit()
    db.refresh(evidence)

    # Authoritative dispute reassessment
    analysis = analyze_dispute(dispute_id, db, trigger="EVIDENCE_REJECTED", broadcast=True)

    return {
        "success": True,
        "message": f"Evidence '{evidence.title}' marked as rejected.",
        "evidence": {
            "evidence_id": evidence.evidence_id,
            "dispute_id": evidence.dispute_id,
            "evidence_type": evidence.evidence_type,
            "title": evidence.title,
            "verification_status": evidence.verification_status,
            "approval_status": evidence.approval_status,
            "ai_analysis": evidence.ai_analysis,
            "ai_analysis_status": evidence.ai_analysis_status
        },
        "case_analysis": analysis
    }


@router.post("/evidence/{evidence_id}/reject", status_code=status.HTTP_200_OK)
def reject_evidence_alias_endpoint(
    evidence_id: str,
    payload: Optional[RejectEvidenceRequest] = None,
    db: Session = Depends(get_db)
):
    """Direct alias for rejecting evidence by evidence_id."""
    evidence = db.query(Evidence).filter(Evidence.evidence_id == evidence_id, Evidence.is_deleted == 0).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence '{evidence_id}' not found.")
    return reject_dispute_evidence_endpoint(dispute_id=evidence.dispute_id, evidence_id=evidence_id, payload=payload, db=db)
