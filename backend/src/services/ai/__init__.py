"""
AI Services Package — Razorpay AI Risk Manager.
Exposes DeepSeek Language Layer, caching, evidence reasoning, and fallback generator.
"""

from src.services.ai.service import AIService
from src.services.ai.deepseek_client import DeepSeekClient
from src.services.ai.fallback import FallbackGenerator
from src.services.ai.cache import AICacheManager
from src.services.ai.evidence_reasoner import EvidenceReasoner
from src.services.ai.evidence_analysis_service import EvidenceAnalysisService
from src.services.ai.response_generator import AIResponseGenerator
from src.services.ai.prompt_builder import PromptBuilder
from src.services.ai.response_parser import ResponseParser
from src.services.ai.schemas import (
    MerchantDisputeExplanation,
    EvidenceGapExplanation,
    StructuredAIResponse,
    AIGenerationMetadata,
    EvidenceAnalysisResultSchema
)

__all__ = [
    "AIService",
    "DeepSeekClient",
    "FallbackGenerator",
    "AICacheManager",
    "EvidenceReasoner",
    "EvidenceAnalysisService",
    "AIResponseGenerator",
    "PromptBuilder",
    "ResponseParser",
    "MerchantDisputeExplanation",
    "EvidenceGapExplanation",
    "StructuredAIResponse",
    "AIGenerationMetadata",
    "EvidenceAnalysisResultSchema"
]
