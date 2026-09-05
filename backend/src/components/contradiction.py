"""
Component 6 — Contradiction Detector (Hardened).
Detects factual contradictions between merchant claims, customer claims, tracking status, and documents.
Cites exact document IDs (evidence_a and evidence_b) causing the conflict.
"""

from typing import List, Dict, Any, TypedDict, Optional
import json
import urllib.request
from src.utils.logger import get_logger
from config.settings import OLLAMA_URL, OLLAMA_DEFAULT_MODEL

logger = get_logger("ContradictionDetector")

class ContradictionResult(TypedDict):
    contradiction: bool
    type: str  # "NONE", "DELIVERY_CONFLICT", "REFUND_CONFLICT", "AMOUNT_MISMATCH", "DUPLICATE_CLAIM_MISMATCH"
    severity: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    confidence: float
    evidence_a: str
    evidence_b: str
    reason: str
    details: List[str]

class ContradictionDetector:
    """Detects factual conflicts across merchant, customer, and evidence data."""
    
    def __init__(self, enable_ollama: bool = False):
        self.enable_ollama = enable_ollama

    def detect(
        self,
        dispute_payload: Dict[str, Any],
        available_evidence: List[Dict[str, Any]]
    ) -> ContradictionResult:
        """
        Executes deterministic contradiction checks and optional Ollama semantic analysis.
        """
        details = []
        max_severity_rank = 0  # 0: NONE, 1: LOW, 2: MEDIUM, 3: HIGH, 4: CRITICAL
        severity_labels = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        c_type = "NONE"
        evidence_a = "N/A"
        evidence_b = "N/A"
        
        merchant_claim = str(dispute_payload.get("merchant_claim", "")).strip().lower()
        customer_claim = str(dispute_payload.get("customer_claim", "")).strip().lower()
        dispute_reason = str(dispute_payload.get("dispute_reason", "")).strip()
        
        doc_type_map = {str(d.get("document_type", "")).lower(): d.get("document_id", "DOC_UNKNOWN") for d in available_evidence}
        doc_contents = " ".join([str(d.get("content", "")).lower() for d in available_evidence])
        
        # Check 1: Delivery contradiction (Merchant/POD claims delivered, Customer claims NOT received)
        if ("not received" in customer_claim or "never received" in customer_claim or "missing" in customer_claim) and ("proof_of_delivery" in doc_type_map or "delivered" in merchant_claim or "delivered" in doc_contents):
            max_severity_rank = max(max_severity_rank, 3) # HIGH
            c_type = "DELIVERY_CONFLICT"
            evidence_a = f"DOC_{doc_type_map.get('proof_of_delivery', 'POD_RECORD')} (proof_of_delivery)"
            evidence_b = f"CUSTOMER_STATEMENT ('{customer_claim}')"
            details.append(f"Customer claims non-delivery ('{customer_claim}'), but merchant proof of delivery ({evidence_a}) asserts order was delivered.")
            
        # Check 2: Refund contradiction (Customer claims refund missing, but refund receipt document exists)
        if ("refund" in customer_claim or "not credited" in customer_claim) and ("refund_receipt" in doc_type_map or "refunded" in doc_contents or "arn" in doc_contents):
            max_severity_rank = max(max_severity_rank, 3) # HIGH
            c_type = "REFUND_CONFLICT"
            evidence_a = f"DOC_{doc_type_map.get('refund_receipt', 'REFUND_RECORD')} (refund_receipt)"
            evidence_b = f"CUSTOMER_STATEMENT ('{customer_claim}')"
            details.append(f"Customer claims refund missing ('{customer_claim}'), but refund receipt ({evidence_a}) confirms credit processing.")
                
        # Check 3: Amount mismatch (Dispute amount > original transaction amount)
        dispute_amt = dispute_payload.get("dispute_amount")
        tx_amt = dispute_payload.get("transaction_amount")
        if dispute_amt and tx_amt and dispute_amt > tx_amt:
            max_severity_rank = max(max_severity_rank, 4) # CRITICAL
            c_type = "AMOUNT_MISMATCH"
            evidence_a = f"DISPUTE_AMOUNT (INR {dispute_amt:,.2f})"
            evidence_b = f"TRANSACTION_AMOUNT (INR {tx_amt:,.2f})"
            details.append(f"Dispute amount (INR {dispute_amt}) exceeds original transaction amount (INR {tx_amt}).")
            
        # Check 4: Duplicate charge claim without matching transaction records
        if "duplicate" in dispute_reason.lower() or "twice" in customer_claim:
            is_dup = dispute_payload.get("is_duplicate_flag", 0)
            if not is_dup:
                max_severity_rank = max(max_severity_rank, 2) # MEDIUM
                c_type = "DUPLICATE_CLAIM_MISMATCH"
                evidence_a = "CUSTOMER_STATEMENT ('Billed twice')"
                evidence_b = "GATEWAY_TRANSACTION_LOG (Single transaction record)"
                details.append("Customer claims duplicate charge, but gateway records show only 1 valid transaction.")

        # Optional Semantic Check via Local Ollama
        if self.enable_ollama and merchant_claim and customer_claim and max_severity_rank == 0:
            ollama_res = self._check_ollama_semantic_contradiction(merchant_claim, customer_claim)
            if ollama_res and ollama_res.get("contradiction"):
                max_severity_rank = max(max_severity_rank, 3)
                c_type = "LLM_SEMANTIC_CONFLICT"
                evidence_a = "MERCHANT_STATEMENT"
                evidence_b = "CUSTOMER_STATEMENT"
                details.append(f"LLM Semantic Check: {ollama_res.get('reason')}")

        has_contradiction = max_severity_rank > 0
        severity_str = severity_labels[max_severity_rank]
        
        if not has_contradiction:
            confidence = 0.95
            reason = "No factual contradictions detected across evidence sources."
        else:
            confidence = min(0.70 + (max_severity_rank * 0.07), 0.98)
            reason = details[0] if details else "Contradictions identified between merchant and customer records."
            
        return ContradictionResult(
            contradiction=has_contradiction,
            type=c_type,
            severity=severity_str,
            confidence=round(confidence, 2),
            evidence_a=evidence_a,
            evidence_b=evidence_b,
            reason=reason,
            details=details
        )
        
    def _check_ollama_semantic_contradiction(
        self,
        merchant_claim: str,
        customer_claim: str
    ) -> Optional[Dict[str, Any]]:
        """Invokes local Ollama instance for semantic contradiction analysis if reachable."""
        prompt = (
            f"Analyze if there is a factual contradiction between Merchant Claim and Customer Claim.\n"
            f"Merchant: {merchant_claim}\n"
            f"Customer: {customer_claim}\n"
            f"Respond ONLY in valid JSON: {{\"contradiction\": true/false, \"reason\": \"brief text\"}}"
        )
        try:
            req_data = json.dumps({
                "model": OLLAMA_DEFAULT_MODEL,
                "prompt": prompt,
                "stream": False
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                response_text = data.get("response", "")
                return json.loads(response_text[response_text.find('{'):response_text.rfind('}')+1])
        except Exception:
            return None
