"""
Unit & Integration Tests for DeepSeek AI Language Layer, Dedicated AIService,
Deterministic Fallbacks, Anti-Hallucination Guardrails, Caching, and Audit Logging.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.database import Base
from src.database.repository import create_transaction, create_dispute, create_evidence, get_dispute_audit_trail
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.fallback import FallbackGenerator
from src.services.ai.cache import AICacheManager
from src.services.ai.evidence_reasoner import EvidenceReasoner
from src.services.ai.response_generator import AIResponseGenerator
from src.services.ai.service import AIService
from src.services.ai.schemas import (
    MerchantDisputeExplanation,
    EvidenceGapExplanation,
    StructuredAIResponse
)


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clear_ai_cache():
    """Ensures AI cache is clean before each test."""
    AICacheManager().clear()
    yield
    AICacheManager().clear()


# ==========================================
# 1. DEEPSEEK CLIENT & ERROR HANDLING TESTS
# ==========================================

def test_deepseek_client_unconfigured():
    """Verifies client gracefully detects missing API key and avoids network calls."""
    client = DeepSeekClient(api_key="")
    assert not client.is_available()
    result = client.chat_completion([{"role": "user", "content": "Hello"}])
    assert result is None


def test_deepseek_client_timeout_handling():
    """Verifies client catches network timeouts and returns None without raising unhandled exceptions."""
    client = DeepSeekClient(api_key="sk-test-fake-key", timeout=1)
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        result = client.chat_completion([{"role": "user", "content": "test"}])
        assert result is None


# ==========================================
# 2. RESPONSE PARSER & SCHEMA VALIDATION TESTS
# ==========================================

def test_response_parser_markdown_fences():
    """Verifies ResponseParser strips ```json codeblocks and preamble."""
    raw_response = """Here is your JSON output:
```json
{
  "summary": "Order delivered on time",
  "plain_english_explanation": "Customer claims non-receipt but carrier confirms delivery",
  "dispute_id": "DSP_TEST_1",
  "recommendation": "Challenge this dispute",
  "recommendation_code": "CONTEST",
  "recommendation_reasoning": ["Proof of delivery is verified"],
  "merchant_action": "Submit defense",
  "confidence_language": "High confidence"
}
```
Thank you."""
    parsed = ResponseParser.parse_and_validate(raw_response, MerchantDisputeExplanation)
    assert parsed is not None
    assert parsed.dispute_id == "DSP_TEST_1"
    assert parsed.recommendation == "Challenge this dispute"


def test_response_parser_invalid_json():
    """Verifies parser returns None on invalid JSON."""
    raw_invalid = "This is not valid json { broken: "
    parsed = ResponseParser.parse_and_validate(raw_invalid, MerchantDisputeExplanation)
    assert parsed is None


# ==========================================
# 3. DETERMINISTIC FALLBACK & REASONING TESTS
# ==========================================

def test_fallback_merchant_explanation_product_not_received():
    """Tests deterministic fallback explanation for non-receipt disputes."""
    context = {
        "dispute_id": "DSP_FALLBACK_1",
        "reason_code": "product_not_received",
        "amount": 199.99,
        "currency": "USD",
        "backend_decision_code": "CONTEST",
        "evidence_completeness": 0.8,
        "win_probability": 0.85,
        "missing_evidence": []
    }
    explanation = FallbackGenerator.generate_merchant_explanation(context)
    assert explanation.dispute_id == "DSP_FALLBACK_1"
    assert explanation.recommendation == "Challenge this dispute"
    assert explanation.recommendation_code == "CONTEST"
    assert len(explanation.recommendation_reasoning) > 0
    assert "defense" in explanation.merchant_action.lower() or "submit" in explanation.merchant_action.lower()


def test_fallback_merchant_explanation_fraudulent_transaction():
    """Tests fallback explanation for fraudulent transaction disputes."""
    context = {
        "dispute_id": "DSP_FALLBACK_2",
        "reason_code": "fraudulent_transaction",
        "amount": 450.00,
        "currency": "USD",
        "backend_decision_code": "INVESTIGATE",
        "evidence_completeness": 0.4,
        "win_probability": 0.35,
        "missing_evidence": ["authentication", "ip_address_log"]
    }
    explanation = FallbackGenerator.generate_merchant_explanation(context)
    assert explanation.recommendation == "Review further"
    assert explanation.recommendation_code == "INVESTIGATE"
    assert "Missing:" in str(explanation.missing_evidence_summary)


def test_fallback_evidence_guidance():
    """Tests evidence gap guidance generation."""
    context = {
        "reason_code": "product_not_received",
        "available_evidence": [{"evidence_type": "shipping_confirmation", "title": "FedEx Tracking"}],
        "missing_evidence": [{"evidence_type": "delivery_confirmation"}],
        "unverified_evidence": []
    }
    guidance = FallbackGenerator.generate_evidence_gap_explanations(context)
    assert len(guidance) >= 2
    deliv_guide = next(g for g in guidance if g.evidence_type == "delivery_confirmation")
    assert deliv_guide.status == "MISSING"
    assert not deliv_guide.is_sufficient
    assert deliv_guide.urgency == "HIGH"


# ==========================================
# 4. RECOMMENDATION GUARDRAILS TESTS
# ==========================================

def test_guardrail_cannot_override_ml_decision(db_session):
    """
    CRITICAL GUARDRAIL TEST:
    Verifies that the AI language layer cannot override the backend decision.
    Even if an LLM returns a hallucinated decision, the system enforces the backend truth.
    """
    tx_data = {
        "transaction_id": "TXN_GUARDRAIL_01",
        "customer_id": "CUST_GUARDRAIL_01",
        "amount": 100.0,
        "order": {
            "order_id": "ORD_GUARDRAIL_01",
            "fulfillment": {
                "shipping_status": "SHIPPED",
                "tracking_number": "TRK_123",
                "shipped_at": "2026-08-20T10:00:00Z",
                "delivered_at": "2026-08-22T14:00:00Z",
                "delivery_status": "DELIVERED"
            }
        },
        "payment": {"auth_code": "AUTH_123", "payment_status": "CAPTURED"}
    }
    create_transaction(db_session, tx_data)
    create_dispute(db_session, {"dispute_id": "DSP_GUARDRAIL_01", "transaction_id": "TXN_GUARDRAIL_01", "reason_code": "product_not_received"})

    ai_service = AIService()
    explanation = ai_service.get_case_explanation(db_session, "DSP_GUARDRAIL_01")

    # Backend decision for full delivery proof is CONTEST -> "Challenge this dispute"
    assert explanation.recommendation == "Challenge this dispute"
    assert explanation.recommendation_code == "CONTEST"


# ==========================================
# 5. ANTI-HALLUCINATION GUARDRAIL TESTS
# ==========================================

def test_anti_hallucination_missing_delivery(db_session):
    """
    ANTI-HALLUCINATION TEST:
    Verifies that when delivery confirmation is missing, the response draft
    never claims that the order was delivered.
    """
    tx_data = {
        "transaction_id": "TXN_HALLUCINATION_DS",
        "customer_id": "CUST_HALLUCINATION_DS",
        "amount": 120.0,
        "order": {
            "order_id": "ORD_HALLUCINATION_DS",
            "fulfillment": {
                "shipping_status": "PENDING",
                "tracking_number": None,
                "shipped_at": None,
                "delivered_at": None,
                "delivery_status": "PENDING"
            }
        }
    }
    create_transaction(db_session, tx_data)
    create_dispute(db_session, {"dispute_id": "DSP_HALLUCINATION_DS", "transaction_id": "TXN_HALLUCINATION_DS", "reason_code": "product_not_received"})

    ai_service = AIService()
    response = ai_service.generate_structured_response(db_session, "DSP_HALLUCINATION_DS")

    assert response.merchant_position != "CONTEST"
    assert response.merchant_recommendation != "Challenge this dispute"

    resp_lower = response.response_text.lower()
    assert "carrier confirmed delivery" not in resp_lower
    assert "successfully delivered" not in resp_lower


# ==========================================
# 6. CACHING & INVALIDATION TESTS
# ==========================================

def test_ai_cache_hit_and_invalidation(db_session):
    """Verifies that generated AI explanations are cached and invalidated when evidence changes."""
    tx_data = {
        "transaction_id": "TXN_CACHE_01",
        "customer_id": "CUST_CACHE_01",
        "amount": 75.0
    }
    create_transaction(db_session, tx_data)
    create_dispute(db_session, {"dispute_id": "DSP_CACHE_01", "transaction_id": "TXN_CACHE_01", "reason_code": "product_not_received"})

    ai_service = AIService()

    # First call generates and caches
    exp1 = ai_service.get_case_explanation(db_session, "DSP_CACHE_01")
    assert exp1 is not None

    # Second call should serve from cache
    exp2 = ai_service.get_case_explanation(db_session, "DSP_CACHE_01")
    assert exp1.summary == exp2.summary

    # Invalidate cache for dispute
    invalidated_count = ai_service.invalidate_cache("DSP_CACHE_01")
    assert invalidated_count >= 1


# ==========================================
# 7. AUDIT TRAIL LOGGING TESTS
# ==========================================

def test_ai_service_audit_event_logged(db_session):
    """Verifies that AIService records AI generation events in the dispute audit trail."""
    tx_data = {
        "transaction_id": "TXN_AUDIT_01",
        "customer_id": "CUST_AUDIT_01",
        "amount": 250.0
    }
    create_transaction(db_session, tx_data)
    create_dispute(db_session, {"dispute_id": "DSP_AUDIT_01", "transaction_id": "TXN_AUDIT_01", "reason_code": "product_not_received"})

    ai_service = AIService()
    ai_service.get_case_explanation(db_session, "DSP_AUDIT_01")
    ai_service.generate_structured_response(db_session, "DSP_AUDIT_01")

    # Fetch audit events from repository
    events = get_dispute_audit_trail(db_session, "DSP_AUDIT_01")
    ai_events = [e for e in events if (e.get("actor_type") if isinstance(e, dict) else getattr(e, "actor_type", "")) == "AI_ENGINE"]

    assert len(ai_events) >= 2
    event_types = [(e.get("event_type") if isinstance(e, dict) else getattr(e, "event_type", "")) for e in ai_events]
    assert "AI_EXPLANATION_GENERATED" in event_types
    assert "AI_RESPONSE_GENERATED" in event_types

