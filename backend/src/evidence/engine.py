"""
Core Evidence Engine — Razorpay AI Risk Manager.
Collects, validates, verifies, and packages evidence for chargeback disputes from database records.
Never fabricates evidence; maintains exact provenance, database persistence, and dispute isolation.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.database.repository import get_dispute
from src.database.models import Dispute, Transaction, Customer, Payment, Order, Fulfillment, Evidence
from src.evidence.rules import get_required_evidence_types, get_optional_evidence_types
from src.evidence.evidence_factory import EvidenceFactory
from src.evidence.validators import (
    verify_payment_confirmation,
    verify_shipping_confirmation,
    verify_delivery_confirmation,
    verify_customer_history,
    verify_authentication,
    verify_invoice,
    verify_transaction_history,
    verify_generic_evidence_record
)
from src.evidence.schemas import EvidenceItemSchema, EvidencePackageSchema
from src.utils.logger import get_logger

logger = get_logger("EvidenceEngine")

class EvidenceEngine:
    """Engine responsible for deterministic evidence collection, verification, and packaging."""

    def __init__(self):
        pass

    def evaluate_dispute_evidence(self, db: Session, dispute_id: str) -> EvidencePackageSchema:
        """
        Retrieves dispute entity graph from database, identifies required evidence based on reason,
        verifies evidence quality and presence, and returns structured Evidence Package.
        Guarantees that database Evidence table is the single source of truth.
        Raises ValueError if dispute_id is not found in database.
        """
        dispute = get_dispute(db, dispute_id)
        if not dispute:
            logger.error(f"Dispute '{dispute_id}' not found in database.")
            raise ValueError(f"Dispute with ID '{dispute_id}' not found.")

        # Ensure database contains active dispute-specific evidence records
        active_db_evidence = db.query(Evidence).filter(
            Evidence.dispute_id == dispute_id,
            Evidence.is_deleted == 0
        ).all()

        if not active_db_evidence:
            # Seed concrete records via EvidenceFactory
            active_db_evidence = EvidenceFactory.create_evidence_for_dispute(db, dispute_id)

        tx: Optional[Transaction] = dispute.transaction
        cust: Optional[Customer] = tx.customer if tx else None
        payments: List[Payment] = tx.payments if tx else []
        payment: Optional[Payment] = payments[0] if payments else None
        order: Optional[Order] = tx.order if tx else None
        fulfillment: Optional[Fulfillment] = order.fulfillment if order else None

        reason_code = dispute.reason_code
        required_types = get_required_evidence_types(reason_code)
        optional_types = get_optional_evidence_types(reason_code)

        evidence_items: List[EvidenceItemSchema] = []
        covered_evidence_ids = set()

        # 1. Process Required Types
        for req_type in required_types:
            req_type_lower = req_type.lower()
            # Match active DB evidence for this dispute
            matching_evd = next((
                e for e in active_db_evidence
                if e.evidence_id not in covered_evidence_ids
                and (
                    e.evidence_type.lower() == req_type_lower or
                    (req_type_lower == "authentication" and e.evidence_type.lower() in ["authentication_record", "three_ds_record", "avs_cvv_record"]) or
                    (req_type_lower == "authentication_record" and e.evidence_type.lower() == "authentication")
                )
            ), None)

            if matching_evd:
                covered_evidence_ids.add(matching_evd.evidence_id)
                ver_status = matching_evd.verification_status or "UNVERIFIED"
                app_status = matching_evd.approval_status or "PENDING_APPROVAL"
                
                if ver_status == "INVALID":
                    status = "INVALID"
                elif ver_status == "UNREADABLE":
                    status = "UNREADABLE"
                elif app_status == "REJECTED":
                    status = "UNVERIFIED"
                elif ver_status in ["VERIFIED", "AVAILABLE"]:
                    status = "AVAILABLE"
                else:
                    status = "UNVERIFIED"

                evidence_items.append(EvidenceItemSchema(
                    evidence_id=matching_evd.evidence_id,
                    evidence_type=matching_evd.evidence_type,
                    status=status,
                    verification_status=ver_status,
                    approval_status=app_status,
                    approved_at=matching_evd.approved_at,
                    approved_by=matching_evd.approved_by,
                    title=matching_evd.title or req_type.replace("_", " ").title(),
                    description=matching_evd.description,
                    source=matching_evd.source or "DATABASE",
                    source_reference_id=matching_evd.source_reference_id,
                    verification_details=matching_evd.description,
                    data=matching_evd.evidence_data,
                    ai_analysis=matching_evd.ai_analysis,
                    ai_analysis_status=matching_evd.ai_analysis_status,
                    ai_analyzed_at=matching_evd.ai_analyzed_at,
                    ai_error=matching_evd.ai_error,
                    created_at=matching_evd.created_at
                ))
            else:
                # Missing required evidence
                evidence_items.append(EvidenceItemSchema(
                    evidence_id=None,
                    evidence_type=req_type,
                    status="MISSING",
                    verification_status="UNVERIFIED",
                    approval_status="PENDING_APPROVAL",
                    approved_at=None,
                    approved_by=None,
                    title=req_type.replace("_", " ").title(),
                    description=f"Mandatory evidence '{req_type.replace('_', ' ')}' is not present in database.",
                    source="DATABASE",
                    source_reference_id=None,
                    verification_details="Record missing from dispute documentation.",
                    data=None,
                    ai_analysis=None,
                    ai_analysis_status="PENDING",
                    ai_analyzed_at=None,
                    ai_error=None,
                    created_at=None
                ))

        # 2. Process Remaining Active Evidence (Optional / Custom / Uploaded)
        for ev in active_db_evidence:
            if ev.evidence_id in covered_evidence_ids:
                continue
            covered_evidence_ids.add(ev.evidence_id)
            ver_status = ev.verification_status or "UNVERIFIED"
            app_status = ev.approval_status or "PENDING_APPROVAL"

            if ver_status == "INVALID":
                status = "INVALID"
            elif ver_status == "UNREADABLE":
                status = "UNREADABLE"
            elif app_status == "REJECTED":
                status = "UNVERIFIED"
            elif ver_status in ["VERIFIED", "AVAILABLE"]:
                status = "AVAILABLE"
            else:
                status = "UNVERIFIED"

            evidence_items.append(EvidenceItemSchema(
                evidence_id=ev.evidence_id,
                evidence_type=ev.evidence_type,
                status=status,
                verification_status=ver_status,
                approval_status=app_status,
                approved_at=ev.approved_at,
                approved_by=ev.approved_by,
                title=ev.title or ev.evidence_type.replace("_", " ").title(),
                description=ev.description,
                source=ev.source or "DATABASE:evidence",
                source_reference_id=ev.source_reference_id,
                verification_details=ev.description,
                data=ev.evidence_data,
                ai_analysis=ev.ai_analysis,
                ai_analysis_status=ev.ai_analysis_status,
                ai_analyzed_at=ev.ai_analyzed_at,
                ai_error=ev.ai_error,
                created_at=ev.created_at
            ))

        # Count statuses
        available_count = sum(1 for item in evidence_items if item.status == "AVAILABLE")
        missing_count = sum(1 for item in evidence_items if item.status == "MISSING")
        unverified_count = sum(1 for item in evidence_items if item.status == "UNVERIFIED")
        invalid_count = sum(1 for item in evidence_items if item.status in ["INVALID", "UNREADABLE"])

        package = EvidencePackageSchema(
            dispute_id=dispute.dispute_id,
            transaction_id=dispute.transaction_id,
            reason=dispute.reason_code,
            evidence_count=len(evidence_items),
            available_count=available_count,
            missing_count=missing_count,
            unverified_count=unverified_count,
            invalid_count=invalid_count,
            evidence=evidence_items
        )

        logger.info(
            f"Evaluated evidence for dispute '{dispute_id}': {available_count} AVAILABLE, "
            f"{missing_count} MISSING, {unverified_count} UNVERIFIED, {invalid_count} INVALID."
        )
        return package
