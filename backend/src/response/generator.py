"""
AI Response Generator Implementations.
Provides deterministic MockResponseGenerator for testing/offline use,
and ConfigurableResponseGenerator for external LLM providers (Ollama / OpenAI).
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.utils.logger import get_logger

logger = get_logger("ResponseGenerator")

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

class BaseResponseGenerator(ABC):
    """Abstract interface for AI Response Generator."""

    @abstractmethod
    def generate(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured response dictionary from case data."""
        pass

class MockResponseGenerator(BaseResponseGenerator):
    """
    Deterministic rule-based Response Generator.
    Used for automated testing, offline development, and safe fallback.
    Never fabricates facts; builds response strictly from verified evidence.
    """

    def generate(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
        dispute = input_case.get("dispute", {})
        tx = input_case.get("transaction", {})
        risk = input_case.get("risk_assessment", {})
        evidence_items = input_case.get("verified_evidence", [])

        disp_id = dispute.get("dispute_id", "DSP_UNKNOWN")
        reason = dispute.get("reason_code", "fraudulent_transaction")
        reason_desc = dispute.get("reason_description", "")
        tx_id = tx.get("transaction_id", "TXN_UNKNOWN")
        amount = tx.get("amount", 0.0)
        currency = tx.get("currency", "USD")

        # Map evidence items by type
        ev_map = {item.get("evidence_type"): item for item in evidence_items}

        available_types = [
            t for t, item in ev_map.items() if item.get("status") == "AVAILABLE"
        ]
        unverified_types = [
            t for t, item in ev_map.items() if item.get("status") == "UNVERIFIED"
        ]
        missing_types = [
            t for t, item in ev_map.items() if item.get("status") == "MISSING"
        ]

        # Determine Merchant Position based ONLY on verified evidence (not risk score alone)
        if len(available_types) >= 3 and not missing_types:
            merchant_position = "CONTEST"
        elif len(available_types) >= 2:
            merchant_position = "PARTIAL_CONTEST"
        else:
            merchant_position = "INSUFFICIENT_EVIDENCE"

        # Hard Rule: For product_not_received, CONTEST requires AVAILABLE delivery_confirmation
        if reason in ("product_not_received", "GOODS_NOT_RECEIVED"):
            deliv_status_check = ev_map.get("delivery_confirmation", {}).get("status")
            if deliv_status_check != "AVAILABLE" and merchant_position == "CONTEST":
                merchant_position = "PARTIAL_CONTEST" if len(available_types) >= 2 else "INSUFFICIENT_EVIDENCE"

        # Build key facts and citations strictly from available evidence
        key_facts: List[str] = []
        citations: List[Dict[str, Any]] = []

        # 1. Transaction & Payment Fact
        # 1. Payment Confirmation Fact
        pay_ev = ev_map.get("payment_confirmation")
        if pay_ev and pay_ev.get("status") == "AVAILABLE":
            pay_data = pay_ev.get("data") or {}
            auth_code = pay_data.get("auth_code", "AUTH_CONFIRMED")
            pay_fact = f"Transaction {tx_id} of {currency} {amount:.2f} was successfully authorized (Auth Code: {auth_code}) and captured."
            key_facts.append(pay_fact)
            citations.append({
                "claim": pay_fact,
                "evidence_refs": ["payment_confirmation"]
            })
        elif pay_ev and pay_ev.get("status") == "UNVERIFIED":
            pay_fact = f"Transaction {tx_id} of {currency} {amount:.2f} authorization record is present but unverified."
            key_facts.append(pay_fact)
            citations.append({
                "claim": pay_fact,
                "evidence_refs": ["payment_confirmation"]
            })

        # 2. Shipping Confirmation Fact
        ship_ev = ev_map.get("shipping_confirmation")
        if ship_ev and ship_ev.get("status") == "AVAILABLE":
            ship_data = ship_ev.get("data") or {}
            tracking = ship_data.get("tracking_number", "")
            shipped_at = ship_data.get("shipped_at", "")
            ship_fact = f"Order was shipped via carrier with tracking number '{tracking}' on {shipped_at}."
            key_facts.append(ship_fact)
            citations.append({
                "claim": ship_fact,
                "evidence_refs": ["shipping_confirmation"]
            })

        # 3. Delivery Confirmation Fact
        deliv_ev = ev_map.get("delivery_confirmation")
        if deliv_ev and deliv_ev.get("status") == "AVAILABLE":
            deliv_data = deliv_ev.get("data") or {}
            delivered_at = deliv_data.get("delivered_at", "")
            tracking = deliv_data.get("tracking_number", "")
            deliv_fact = f"Order delivery was confirmed by carrier (Tracking: '{tracking}') on {delivered_at}."
            key_facts.append(deliv_fact)
            citations.append({
                "claim": deliv_fact,
                "evidence_refs": ["delivery_confirmation"]
            })
        elif deliv_ev and deliv_ev.get("status") == "UNVERIFIED":
            deliv_data = deliv_ev.get("data") or {}
            deliv_stat = deliv_data.get("delivery_status")
            if deliv_stat == "DELIVERED":
                deliv_fact = "Fulfillment record is marked DELIVERED, but proof of delivery timestamp is missing so delivery cannot be independently verified."
            else:
                deliv_fact = f"Delivery confirmation is unverified (status: {deliv_stat or 'OMITTED'})."
            key_facts.append(deliv_fact)
            citations.append({
                "claim": deliv_fact,
                "evidence_refs": ["delivery_confirmation"]
            })

        # 4. Customer History Fact
        cust_ev = ev_map.get("customer_history")
        if cust_ev and cust_ev.get("status") == "AVAILABLE":
            cust_data = cust_ev.get("data") or {}
            age = cust_data.get("account_age_days", 0)
            status_ver = cust_data.get("verification_status", "VERIFIED")
            cust_fact = f"Customer account profile is verified ({status_ver}) with an account age of {age} days."
            key_facts.append(cust_fact)
            citations.append({
                "claim": cust_fact,
                "evidence_refs": ["customer_history"]
            })

        # 5. Authentication Fact
        auth_ev = ev_map.get("authentication")
        if auth_ev and auth_ev.get("status") == "AVAILABLE":
            auth_data = auth_ev.get("data") or {}
            avs = auth_data.get("avs_match", "Y")
            cvv = auth_data.get("cvv_match", "Y")
            auth_fact = f"Card payment passed full security verification with AVS match '{avs}' and CVV match '{cvv}'."
            key_facts.append(auth_fact)
            citations.append({
                "claim": auth_fact,
                "evidence_refs": ["authentication"]
            })


        # Limitations list for missing evidence
        limitations = []
        for m_type in missing_types:
            limitations.append(f"Evidence '{m_type}' is missing from database records.")

        # Build response text
        title = f"Chargeback Defense Statement — Dispute {disp_id} ({reason})"
        summary = (
            f"Merchant response for dispute {disp_id} regarding charge of {currency} {amount:.2f}. "
            f"Position: {merchant_position}. Verified available evidence items: {len(available_types)}."
        )

        resp_lines = []
        resp_lines.append(f"REF: Chargeback Defense Statement for Dispute {disp_id}")
        resp_lines.append(f"Reason Code: {reason}")
        resp_lines.append(f"Transaction ID: {tx_id} | Amount: {currency} {amount:.2f}\n")
        resp_lines.append("SUMMARY OF MERCHANT POSITION:")
        resp_lines.append(f"We respectfully {merchant_position.lower().replace('_', ' ')} this dispute based on verified database records.")
        resp_lines.append("\nVERIFIED EVIDENCE & FACTS:")
        for fact in key_facts:
            resp_lines.append(f"- {fact}")

        if limitations:
            resp_lines.append("\nLIMITATIONS & MISSING RECORDS:")
            for lim in limitations:
                resp_lines.append(f"- {lim}")

        resp_lines.append("\nCONCLUSION:")
        if merchant_position == "CONTEST":
            resp_lines.append("The compelling verified evidence demonstrates full order fulfillment and payment authorization. We request that the dispute be resolved in favor of the merchant.")
        elif merchant_position == "PARTIAL_CONTEST":
            resp_lines.append("Partial evidence supports transaction validity, but missing items are noted for operator review.")
        else:
            resp_lines.append("Current evidence is insufficient to fully contest the dispute. Operator review recommended.")

        response_text = "\n".join(resp_lines)

        return {
            "title": title,
            "summary": summary,
            "merchant_position": merchant_position,
            "response_text": response_text,
            "key_facts": key_facts,
            "supporting_evidence": available_types,
            "limitations": limitations,
            "evidence_citations": citations,
            "generated_at": utc_now_iso(),
            "generator_version": "mock_response_v1"
        }

class ConfigurableResponseGenerator(BaseResponseGenerator):
    """
    Pluggable LLM Response Generator supporting external AI providers (Ollama / OpenAI / Custom).
    Uses environment variables (AI_PROVIDER, AI_MODEL, AI_API_KEY).
    Falls back gracefully to MockResponseGenerator if provider is unconfigured or fails.
    """

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "deepseek").lower()
        self.model = os.getenv("AI_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
        self.api_key = os.getenv("AI_API_KEY", os.getenv("DEEPSEEK_API_KEY", None))
        self.mock_fallback = MockResponseGenerator()

    def generate(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
        if self.provider == "mock" or not self.provider:
            logger.info("Using deterministic MockResponseGenerator provider.")
            return self.mock_fallback.generate(input_case)

        try:
            if self.provider == "deepseek":
                res = self._call_deepseek(input_case)
                if res:
                    return res
            elif self.provider == "ollama":
                res = self._call_ollama(input_case)
                if res:
                    return res
            elif self.provider in ("openai", "custom"):
                res = self._call_custom_provider(input_case)
                if res:
                    return res
        except Exception as e:
            logger.warning(f"AI Provider '{self.provider}' failed: {e}. Falling back to MockResponseGenerator.")

        return self.mock_fallback.generate(input_case)

    def _call_deepseek(self, input_case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calls DeepSeek API via dedicated AI service client."""
        from src.services.ai.deepseek_client import DeepSeekClient
        from src.services.ai.prompt_builder import PromptBuilder
        from src.services.ai.response_parser import ResponseParser

        client = DeepSeekClient(api_key=self.api_key, model=self.model)
        if not client.is_available():
            return None

        messages = PromptBuilder.build_response_draft_prompt(input_case)
        res = client.chat_completion(messages, json_mode=True, temperature=0.1)
        if res and res.get("content"):
            parsed = ResponseParser.parse_to_dict(res["content"])
            if parsed:
                parsed["generated_at"] = utc_now_iso()
                parsed["generator_version"] = f"deepseek_{self.model}"
                return parsed
        return None

    def _call_ollama(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
        """Calls local Ollama API if configured."""
        import urllib.request
        from config.settings import OLLAMA_URL
        from src.response.prompts import SYSTEM_PROMPT

        prompt = f"{SYSTEM_PROMPT}\n\nINPUT CASE DATA:\n{json.dumps(input_case, indent=2)}\n\nRespond with valid JSON matching AIResponseSchema."
        req_data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            response_json = json.loads(data.get("response", "{}"))
            response_json["generated_at"] = utc_now_iso()
            response_json["generator_version"] = f"ollama_{self.model}"
            return response_json

    def _call_custom_provider(self, input_case: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for OpenAI / Custom REST endpoint integration."""
        return self.mock_fallback.generate(input_case)

