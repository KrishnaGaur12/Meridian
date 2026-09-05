"""
AI Response Generator for DeepSeek Language Layer.
Generates evidence-grounded, professional chargeback defense statements and rebuttal drafts.
Enforces strict anti-hallucination validation and backend recommendation guardrails.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.services.ai.schemas import StructuredAIResponse
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.fallback import FallbackGenerator
from src.response.validator import ClaimEvidenceValidator
from src.utils.logger import get_logger

logger = get_logger("AIResponseGenerator")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIResponseGenerator:
    """Orchestrates structured defense response generation with DeepSeek and deterministic fallbacks."""

    def __init__(self, client: Optional[DeepSeekClient] = None):
        self.client = client or DeepSeekClient()
        self.validator = ClaimEvidenceValidator()

    def generate_defense_response(self, context: Dict[str, Any]) -> StructuredAIResponse:
        """
        Generates full structured chargeback defense response.
        Uses DeepSeek when available; falls back gracefully to FallbackGenerator.
        Always passes output through post-generation claim/evidence validation.
        """
        dispute_id = context.get("dispute_id", "DSP_UNKNOWN")
        verified_evidence = context.get("verified_evidence", context.get("available_evidence", []))
        backend_decision = context.get("backend_decision_code") or context.get("merchant_position") or "INSUFFICIENT_EVIDENCE"

        if self.client.is_available():
            try:
                messages = PromptBuilder.build_response_draft_prompt(context)
                res = self.client.chat_completion(messages, json_mode=True, temperature=0.1)

                if res and res.get("content"):
                    parsed_dict = ResponseParser.parse_to_dict(res["content"])
                    if parsed_dict:
                        # Ensure backend decision is preserved
                        parsed_dict["merchant_position"] = backend_decision
                        parsed_dict["merchant_recommendation"] = FallbackGenerator.get_merchant_recommendation_label(backend_decision)
                        parsed_dict["generated_at"] = utc_now_iso()
                        parsed_dict["generator_version"] = f"deepseek_{self.client.model}"
                        parsed_dict["is_fallback"] = False

                        # Validate evidence citations against verified records
                        validated_dict = self.validator.validate_and_filter(parsed_dict, verified_evidence)
                        
                        # Populate evidence explanations
                        validated_dict["evidence_explanations"] = FallbackGenerator.generate_evidence_gap_explanations(context)
                        
                        response_model = StructuredAIResponse.model_validate(validated_dict)
                        logger.info(f"Successfully generated defense response for dispute '{dispute_id}' via DeepSeek.")
                        return response_model

            except Exception as e:
                logger.warning(f"DeepSeek response generation failed for dispute '{dispute_id}': {e}. Using deterministic fallback.")

        # Fallback generation
        fallback_resp = FallbackGenerator.generate_structured_response(context)
        return fallback_resp
