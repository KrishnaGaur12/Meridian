"""
Component 4 — Evidence Validation Engine (Hardened).
Performs deterministic data validation checks (ID alignment, timestamp logic, document integrity,
cross-dispute document isolation) to calculate an evidence quality score and document warnings.
"""

from typing import List, Dict, Any, TypedDict, Optional
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger("EvidenceValidator")

class ValidationResult(TypedDict):
    is_valid: bool
    quality_score: float
    passed_checks: List[str]
    failed_checks: List[str]
    warnings: List[str]
    valid_documents: List[Dict[str, Any]]

class EvidenceValidator:
    """Validates provided evidence documents against dispute context with zero cross-dispute leakage."""
    
    def validate(
        self,
        dispute_payload: Dict[str, Any],
        available_evidence: List[Dict[str, Any]]
    ) -> ValidationResult:
        passed_checks = []
        failed_checks = []
        warnings = []
        valid_documents = []
        
        target_dispute_id = str(dispute_payload.get("dispute_id", ""))
        target_customer_id = str(dispute_payload.get("customer_id", ""))
        target_order_id = str(dispute_payload.get("order_id", dispute_payload.get("transaction_id", "")))
        
        dispute_ts_str = dispute_payload.get("dispute_timestamp")
        dispute_dt = self._parse_iso_date(dispute_ts_str)
        
        if not available_evidence:
            failed_checks.append("NO_EVIDENCE_PROVIDED")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                warnings=["No evidence documents provided by merchant."],
                valid_documents=[]
            )
            
        for doc in available_evidence:
            doc_id = doc.get("document_id", doc.get("evidence_id", "UNKNOWN"))
            doc_type = doc.get("document_type", doc.get("evidence_type", "UNKNOWN"))
            ver_status = str(doc.get("verification_status", "AVAILABLE")).upper()
            content = str(doc.get("content", doc.get("description", doc.get("title", ""))))

            # Check 0: Reject explicitly unreadable or invalid status
            if ver_status in ["INVALID", "UNREADABLE"]:
                failed_checks.append(f"STATUS_{ver_status}_{doc_id}")
                warnings.append(f"Document {doc_id} ({doc_type}) is marked as {ver_status}.")
                continue

            # Check 1: Non-empty document content or title
            if len(content.strip()) < 3 and not doc.get("title"):
                failed_checks.append(f"EMPTY_DOC_CONTENT_{doc_id}")
                warnings.append(f"Document {doc_id} ({doc_type}) has insufficient content.")
                continue

                
            # Check 2: Strict Cross-Dispute Document Isolation
            doc_cust = str(doc.get("customer_id", ""))
            if doc_cust and target_customer_id and doc_cust != target_customer_id:
                failed_checks.append(f"CUSTOMER_ID_MISMATCH_{doc_id}")
                warnings.append(f"SECURITY: Document {doc_id} customer ID ({doc_cust}) does not match dispute customer ID ({target_customer_id}). Document rejected.")
                continue
                
            doc_ord = str(doc.get("order_id", ""))
            if doc_ord and target_order_id and doc_ord != target_order_id:
                failed_checks.append(f"ORDER_ID_MISMATCH_{doc_id}")
                warnings.append(f"SECURITY: Document {doc_id} order ID ({doc_ord}) does not match dispute order ID ({target_order_id}). Document rejected.")
                continue
                
            doc_disp = str(doc.get("dispute_id", ""))
            if doc_disp and target_dispute_id and doc_disp != target_dispute_id:
                failed_checks.append(f"DISPUTE_ID_MISMATCH_{doc_id}")
                warnings.append(f"SECURITY: Document {doc_id} dispute ID ({doc_disp}) does not match current dispute ID ({target_dispute_id}). Document rejected.")
                continue
                
            passed_checks.append(f"CROSS_ENTITY_MATCH_{doc_id}")
                
            # Check 3: Timestamp order sanity (Doc timestamp <= Dispute timestamp)
            doc_ts_str = doc.get("timestamp")
            doc_dt = self._parse_iso_date(doc_ts_str)
            if doc_dt and dispute_dt:
                if doc_dt > dispute_dt:
                    failed_checks.append(f"TIMESTAMP_POSTDATED_{doc_id}")
                    warnings.append(f"Document {doc_id} timestamp ({doc_ts_str}) is after dispute timestamp ({dispute_ts_str}).")
                else:
                    passed_checks.append(f"TIMESTAMP_VALID_{doc_id}")
                    
            valid_documents.append(doc)
            
        # Calculate overall evidence quality score
        total_evaluations = len(passed_checks) + len(failed_checks)
        if total_evaluations == 0:
            quality_score = 0.0
        else:
            quality_score = round(len(passed_checks) / total_evaluations, 4)
            
        is_valid = len(valid_documents) > 0 and quality_score >= 0.50
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=quality_score,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            valid_documents=valid_documents
        )
        
    def _parse_iso_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parses ISO timestamp string safely."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
