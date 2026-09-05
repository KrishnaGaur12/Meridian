"""
Evidence Reasoner for DeepSeek AI Language Layer.
Translates technical evidence statuses, completeness metrics, and card network requirements
into clear, merchant-actionable guidance.
"""

from typing import Dict, Any, List, Optional
from src.services.ai.schemas import EvidenceGapExplanation
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.fallback import FallbackGenerator
from src.utils.logger import get_logger

logger = get_logger("EvidenceReasoner")


class EvidenceReasoner:
    """Reasoning engine for dispute evidence analysis and merchant guidance."""

    def __init__(self, client: Optional[DeepSeekClient] = None):
        self.client = client or DeepSeekClient()

    def analyze_evidence_gaps(self, context: Dict[str, Any]) -> List[EvidenceGapExplanation]:
        """
        Produces merchant-friendly explanations for all required evidence items.
        Attempts DeepSeek generation if available; falls back seamlessly on error/offline.
        """
        # If DeepSeek is available, attempt language enhancement
        if self.client.is_available():
            try:
                messages = PromptBuilder.build_evidence_guidance_prompt(context)
                res = self.client.chat_completion(messages, json_mode=True)
                if res and res.get("content"):
                    data = ResponseParser.parse_to_dict(res["content"])
                    if data and "evidence_explanations" in data:
                        parsed_items = []
                        for raw_item in data["evidence_explanations"]:
                            try:
                                item_model = EvidenceGapExplanation.model_validate(raw_item)
                                parsed_items.append(item_model)
                            except Exception as ve:
                                logger.warning(f"Skipping invalid evidence explanation item: {ve}")

                        if parsed_items:
                            logger.info(f"Successfully generated {len(parsed_items)} evidence explanations via DeepSeek.")
                            return parsed_items
            except Exception as e:
                logger.warning(f"DeepSeek evidence reasoning failed: {e}. Using deterministic fallback.")

        # Fallback generator
        return FallbackGenerator.generate_evidence_gap_explanations(context)
