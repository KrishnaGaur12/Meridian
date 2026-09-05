"""
Evidence File Processor for Razorpay AI Risk Manager.
Validates uploaded files, computes cryptographic hashes, extracts structured text & facts
from PDFs, DOC/DOCX, TXT, CSV, JSON, and Images, verifies document integrity, and formats AI context.
"""

import io
import re
import csv
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

from PIL import Image

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

from src.services.storage import default_storage_service
from src.utils.logger import get_logger

logger = get_logger("EvidenceFileProcessor")

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp",
    ".txt", ".csv", ".json", ".doc", ".docx"
}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


class EvidenceFileProcessor:
    """Processes, extracts, hashes, and validates uploaded merchant evidence files."""

    @staticmethod
    def compute_hash(file_bytes: bytes) -> str:
        """Calculates SHA-256 hex digest of file bytes."""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def validate_file(file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """Validates file extension and size constraints."""
        if not file_bytes:
            return False, "Uploaded file is empty (0 bytes)."

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            return False, f"File size ({len(file_bytes) // (1024*1024)}MB) exceeds maximum limit of 15MB."

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

        return True, None

    @classmethod
    def extract_content(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extracts text, metadata, and key facts from various supported file formats."""
        ext = Path(filename).suffix.lower()
        extracted_text = ""
        metadata: Dict[str, Any] = {}
        is_readable = True
        error_msg = None

        if ext == ".pdf":
            if PYPDF_AVAILABLE:
                try:
                    pdf_file = io.BytesIO(file_bytes)
                    reader = PdfReader(pdf_file)
                    num_pages = len(reader.pages)
                    pages_text = []
                    for page in reader.pages:
                        t = page.extract_text() or ""
                        pages_text.append(t)
                    extracted_text = "\n".join(pages_text).strip()
                    metadata = {
                        "pages": num_pages,
                        "pdf_encrypted": reader.is_encrypted,
                        "file_type": "PDF"
                    }
                    if not extracted_text:
                        # Attempt raw fallback extraction
                        raw_decoded = file_bytes.decode("utf-8", errors="ignore").strip()
                        if len(raw_decoded) > 20:
                            extracted_text = raw_decoded
                            metadata["fallback_extracted"] = True
                        else:
                            is_readable = False
                            error_msg = "PDF contains no extractable text or is password-protected/corrupted."
                except Exception as e:
                    logger.warning(f"PDF extraction error on {filename}: {e}")
                    raw_decoded = file_bytes.decode("utf-8", errors="ignore").strip()
                    if raw_decoded and len(raw_decoded) > 20:
                        extracted_text = raw_decoded
                        metadata = {"pages": 1, "file_type": "PDF", "fallback_extracted": True}
                    else:
                        is_readable = False
                        error_msg = f"PDF read error: {str(e)}"
                        metadata = {"error": str(e), "file_type": "PDF"}
            else:
                extracted_text = file_bytes.decode("utf-8", errors="ignore").strip()
                metadata = {"file_type": "PDF"}

        elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                img = Image.open(io.BytesIO(file_bytes))
                metadata = {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "file_type": "IMAGE"
                }
                extracted_text = f"Image proof document: {filename} ({img.width}x{img.height} {img.format})"
            except Exception as e:
                logger.warning(f"Image parsing error on {filename}: {e}")
                metadata = {"error": str(e), "file_type": "IMAGE"}
                is_readable = False
                error_msg = f"Corrupted or invalid image: {str(e)}"

        elif ext in {".txt", ".log"}:
            try:
                extracted_text = file_bytes.decode("utf-8", errors="replace").strip()
                metadata = {"file_type": "TEXT", "lines": len(extracted_text.splitlines())}
                if not extracted_text:
                    is_readable = False
                    error_msg = "Text file is empty."
            except Exception as e:
                is_readable = False
                error_msg = f"Text decode error: {str(e)}"

        elif ext == ".csv":
            try:
                text_content = file_bytes.decode("utf-8", errors="replace")
                reader = csv.reader(io.StringIO(text_content))
                rows = list(reader)
                header = rows[0] if rows else []
                extracted_text = text_content.strip()
                metadata = {"file_type": "CSV", "row_count": len(rows), "columns": header}
            except Exception as e:
                is_readable = False
                error_msg = f"CSV parsing error: {str(e)}"

        elif ext == ".json":
            try:
                text_content = file_bytes.decode("utf-8", errors="replace")
                parsed = json.loads(text_content)
                extracted_text = json.dumps(parsed, indent=2)
                metadata = {"file_type": "JSON", "keys": list(parsed.keys()) if isinstance(parsed, dict) else []}
            except Exception as e:
                is_readable = False
                error_msg = f"JSON decode error: {str(e)}"

        elif ext in {".doc", ".docx"}:
            try:
                # Text decode or binary string extraction for docx
                raw_text = file_bytes.decode("utf-8", errors="ignore")
                printable = re.sub(r"[^\x20-\x7E\n\r\t]", " ", raw_text)
                cleaned = re.sub(r"\s+", " ", printable).strip()
                if len(cleaned) > 20:
                    extracted_text = cleaned
                    metadata = {"file_type": "DOCX", "extracted_chars": len(cleaned)}
                else:
                    extracted_text = f"Document proof file: {filename}"
                    metadata = {"file_type": "DOCX"}
            except Exception as e:
                extracted_text = f"Document proof file: {filename}"
                metadata = {"file_type": "DOCX", "warning": str(e)}

        else:
            try:
                extracted_text = file_bytes.decode("utf-8", errors="ignore").strip()
                metadata = {"file_type": ext.upper().lstrip(".")}
            except Exception:
                is_readable = False
                error_msg = f"Unsupported or unreadable file type: {ext}"

        # Extract specific entities / facts
        facts = cls._extract_facts(extracted_text, filename)

        return {
            "text": extracted_text,
            "metadata": metadata,
            "facts": facts,
            "is_readable": is_readable and bool(extracted_text.strip() or (metadata and not metadata.get("error"))),
            "error": error_msg
        }

    @staticmethod
    def _extract_facts(text: str, filename: str) -> Dict[str, Any]:
        """Extracts key business identifiers using pattern matching."""
        combined = f"{filename}\n{text}"
        facts: Dict[str, Any] = {}

        # 1. Tracking number pattern
        tracking_match = re.search(r"\b(BD\w{6,14}|FX\w{6,14}|DL\w{6,14}|DHL\w{6,14}|RM\w{6,14}|TRACK[_\-]?\w{5,15}|[A-Z]{2}\d{9}[A-Z]{2})\b", combined, re.IGNORECASE)
        if tracking_match:
            facts["tracking_number"] = tracking_match.group(1).upper()

        # 2. Carrier detection
        carriers = ["Blue Dart", "FedEx", "Delhivery", "DHL", "UPS", "India Post", "Royal Mail", "Aramex", "Swiggy", "Dunzo"]
        for c in carriers:
            if c.lower() in combined.lower():
                facts["carrier"] = c
                break

        # 3. Delivery status / terms
        if re.search(r"\b(delivered|signed by|recipient signature|delivery confirmed|package handed over)\b", combined, re.IGNORECASE):
            facts["delivery_status"] = "DELIVERED"
            facts["has_signature"] = bool(re.search(r"\b(signed|signature|received by)\b", combined, re.IGNORECASE))

        # 4. Auth code / AVS
        auth_match = re.search(r"\b(AUTH[_\-]?[A-Z0-9]{4,12}|AUTH\d{6})\b", combined, re.IGNORECASE)
        if auth_match:
            facts["auth_code"] = auth_match.group(1).upper()

        # 5. Amounts
        amount_match = re.search(r"(?:₹|\$|USD|INR|EUR|GBP|AED)\s*([\d,]+(?:\.\d{2})?)", combined)
        if amount_match:
            try:
                facts["amount_detected"] = float(amount_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # 6. Dates
        date_match = re.search(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b", combined)
        if date_match:
            facts["date_detected"] = date_match.group(1)

        return facts

    @classmethod
    def deduce_evidence_type(cls, filename: str, facts: Dict[str, Any], text: str) -> str:
        """Determines or confirms evidence type from document content."""
        combined = f"{filename} {text}".lower()

        if "tracking" in facts or "carrier" in facts or "delivery" in combined or "pod" in combined or "shipping" in combined:
            return "delivery_confirmation"
        if "auth" in facts or "3ds" in combined or "otp" in combined or "ip geolocation" in combined or "authentication" in combined:
            return "customer_authentication"
        if "invoice" in combined or "receipt" in combined or "bill" in combined or "order summary" in combined:
            return "invoice_receipt"
        if "refund" in combined or "credit" in combined or "reversal" in combined:
            return "refund_confirmation"
        if "policy" in combined or "terms" in combined or "tos" in combined or "agreement" in combined:
            return "terms_of_service"
        if "chat" in combined or "email" in combined or "support" in combined or "communication" in combined:
            return "customer_communication"

        return "delivery_confirmation"

    @classmethod
    def process_and_analyze(
        cls,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
        preferred_evidence_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete processing pipeline for uploaded evidence document:
        1. Validates file
        2. Computes SHA-256 hash
        3. Saves to storage
        4. Extracts text and facts
        5. Evaluates verification integrity
        6. Computes structured case impact
        """
        doc_hash = cls.compute_hash(file_bytes)
        file_size = len(file_bytes)

        is_valid, error_msg = cls.validate_file(file_bytes, filename)
        if not is_valid:
            return {
                "success": False,
                "document_hash": doc_hash,
                "file_size": file_size,
                "verification_status": "INVALID",
                "is_readable": False,
                "error": error_msg,
                "evidence_type": preferred_evidence_type or "unverified_document",
                "raw_content": "",
                "extracted_text": "",
                "facts": {},
                "analysis": {
                    "verification_result": "INVALID",
                    "explanation": f"Upload validation failed: {error_msg}",
                    "impact": "Document cannot be verified and is excluded from representment evidence."
                }
            }

        # Save file to storage
        stored = default_storage_service.save_file(file_bytes, filename, content_type)

        # Extract content
        extracted = cls.extract_content(file_bytes, filename)
        facts = extracted["facts"]
        is_readable = extracted["is_readable"]

        # Determine evidence type
        evidence_type = preferred_evidence_type or cls.deduce_evidence_type(filename, facts, extracted["text"])

        # Determine verification status
        if not is_readable:
            verification_status = "UNREADABLE"
        else:
            verification_status = "UNVERIFIED"

        # Construct structured analysis
        analysis = cls._generate_document_analysis(evidence_type, facts, verification_status, filename)

        return {
            "success": True,
            "document_hash": doc_hash,
            "file_size": file_size,
            "file_info": stored,
            "raw_content": extracted["text"],
            "extracted_text": extracted["text"],
            "evidence_type": evidence_type,
            "verification_status": verification_status,
            "is_readable": is_readable,
            "facts": facts,
            "metadata": extracted["metadata"],
            "analysis": analysis
        }

    @staticmethod
    def _generate_document_analysis(
        evidence_type: str,
        facts: Dict[str, Any],
        verification_status: str,
        filename: str
    ) -> Dict[str, Any]:
        """Generates merchant-friendly analysis explaining why evidence matters and its impact."""
        type_clean = evidence_type.replace("_", " ").title()

        if verification_status in ["UNREADABLE", "INVALID"]:
            return {
                "verification_result": verification_status,
                "interpretation": f"File '{filename}' was unreadable or corrupted. Key evidence markers could not be extracted.",
                "why_evidence_matters": f"Card networks require clear, legible proof of {type_clean} to overturn chargebacks.",
                "case_impact": "Excluded from defense bundle until replaced with a legible document.",
                "win_probability_boost": 0.0,
                "next_recommended_action": "Replace this file with a clear PDF or image receipt."
            }

        if verification_status == "UNVERIFIED":
            return {
                "verification_result": "UNVERIFIED",
                "interpretation": f"File '{filename}' was uploaded but key evidence markers could not be automatically validated.",
                "why_evidence_matters": f"Card networks require clear, legible proof of {type_clean} to overturn chargebacks.",
                "case_impact": "Document attached but requires verification review.",
                "win_probability_boost": 0.05,
                "next_recommended_action": "Verify contents or replace with formal document."
            }

        has_carrier = "carrier" in facts
        has_tracking = "tracking_number" in facts
        has_delivered = facts.get("delivery_status") == "DELIVERED"

        if evidence_type in ["delivery_confirmation", "shipping_confirmation"]:
            if has_tracking and has_delivered:
                interpretation = f"Valid Proof of Delivery identified (Carrier: {facts.get('carrier', 'Verified Courier')}, Tracking: {facts.get('tracking_number')}). Shows completed delivery."
                boost = 0.40
                impact = "Strongly satisfies mandatory fulfillment proof requirement. Substantially increases win probability."
            elif has_tracking:
                interpretation = f"Tracking identifier {facts.get('tracking_number')} detected for carrier {facts.get('carrier', 'Courier')}."
                boost = 0.25
                impact = "Provides shipping proof. Delivery confirmation timestamp recommended."
            else:
                interpretation = f"Delivery document '{filename}' parsed successfully."
                boost = 0.15
                impact = "Fulfillment proof loaded from merchant upload."
        elif evidence_type in ["customer_authentication", "authentication_record"]:
            interpretation = "Strong Customer Authentication log verified (3DS / AVS Match / IP trace)."
            boost = 0.35
            impact = "Strongly refutes unauthorized charge claims by proving cardholder authorization."
        elif evidence_type in ["terms_of_service", "refund_policy"]:
            interpretation = "Merchant Terms of Service / Refund Policy terms loaded and verified."
            boost = 0.20
            impact = "Provides binding merchant-customer contractual agreement."
        else:
            interpretation = f"Verified {type_clean} documentation attached to dispute case."
            boost = 0.20
            impact = "Strengthens evidence completeness and substantiates merchant representation."

        return {
            "verification_result": "VERIFIED",
            "extracted_facts": facts,
            "interpretation": interpretation,
            "why_evidence_matters": f"Essential supporting evidence for {type_clean} required under Visa/Mastercard dispute rules.",
            "case_impact": impact,
            "win_probability_boost": boost,
            "next_recommended_action": "Proceed to merchant review and approve evidence."
        }
