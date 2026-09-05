"""
Chargeback Package Generator.
Combines dispute metadata, transaction details, risk prediction, verified evidence,
AI response, and evidence traceability into a final reviewable Chargeback Package.
"""

from typing import Dict, Any, List
import uuid
from datetime import datetime, timezone

from src.evidence.schemas import EvidencePackageSchema
from src.response.schemas import AIResponseSchema
from src.chargeback.schemas import ChargebackPackageSchema
from src.utils.logger import get_logger

logger = get_logger("ChargebackPackageGenerator")

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class ChargebackPackageGenerator:
    """Assembles final Chargeback Package from all backend components."""

    def assemble_package(
        self,
        dispute_data: Dict[str, Any],
        transaction_data: Dict[str, Any],
        risk_assessment_data: Dict[str, Any],
        evidence_package: EvidencePackageSchema,
        ai_response: AIResponseSchema
    ) -> ChargebackPackageSchema:
        """
        Combines case information, risk assessment, evidence summary, and AI response.
        Determines package status (READY_FOR_REVIEW, INCOMPLETE, INSUFFICIENT_EVIDENCE).
        """
        dispute_id = dispute_data.get("dispute_id", "DSP_UNKNOWN")
        pkg_id = f"PKG_{dispute_id}"

        avail_count = evidence_package.available_count
        missing_count = evidence_package.missing_count
        unver_count = evidence_package.unverified_count

        position = ai_response.merchant_position

        # Check delivery confirmation for product_not_received
        reason_code = dispute_data.get("reason_code", "")
        deliv_item = next((item for item in evidence_package.evidence if item.evidence_type == "delivery_confirmation"), None)
        deliv_is_available = (deliv_item is not None and deliv_item.status == "AVAILABLE")

        # Package status determination rules
        if missing_count == 0 and unver_count == 0 and position == "CONTEST":
            package_status = "READY_FOR_REVIEW"
        elif missing_count > 0 or unver_count > 0:
            if avail_count >= 3 and position in ("CONTEST", "PARTIAL_CONTEST"):
                package_status = "READY_FOR_REVIEW"
            else:
                package_status = "INCOMPLETE"
        else:
            package_status = "INSUFFICIENT_EVIDENCE"

        # Defense-in-Depth Safety Gate: product_not_received requires AVAILABLE delivery evidence for READY_FOR_REVIEW
        if reason_code in ("product_not_received", "GOODS_NOT_RECEIVED") and not deliv_is_available:
            if package_status == "READY_FOR_REVIEW":
                package_status = "INCOMPLETE"

        if position == "INSUFFICIENT_EVIDENCE":
            package_status = "INSUFFICIENT_EVIDENCE"

        evidence_summary = {
            "total": evidence_package.evidence_count,
            "available": avail_count,
            "missing": missing_count,
            "unverified": unver_count,
            "invalid": evidence_package.invalid_count
        }

        package = ChargebackPackageSchema(
            package_id=pkg_id,
            package_status=package_status,
            dispute=dispute_data,
            transaction=transaction_data,
            risk_assessment=risk_assessment_data,
            evidence_summary=evidence_summary,
            evidence=evidence_package.evidence,
            ai_response=ai_response,
            evidence_citations=ai_response.evidence_citations,
            generated_at=utc_now_iso(),
            package_version="1.0"
        )

        logger.info(f"Assembled Chargeback Package '{pkg_id}' with status '{package_status}'.")
        return package
