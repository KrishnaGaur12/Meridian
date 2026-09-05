"""
Response Parser for DeepSeek AI Language Layer.
Sanitizes, parses, and validates LLM JSON outputs against Pydantic models.
Rejects invalid outputs and triggers graceful fallback.
"""

import json
import re
from typing import Optional, Type, TypeVar, Any, Dict
from pydantic import BaseModel, ValidationError

from src.utils.logger import get_logger

logger = get_logger("ResponseParser")

T = TypeVar("T", bound=BaseModel)


class ResponseParser:
    """Safely extracts, parses, and validates structured outputs from LLM responses."""

    @staticmethod
    def extract_json_string(text: str) -> str:
        """Extracts JSON substring, stripping markdown backticks or preamble text."""
        if not text or not isinstance(text, str):
            return ""

        trimmed = text.strip()

        # Check for ```json ... ``` blocks
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", trimmed, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1).strip()

        # Find first '{' and last '}'
        start_idx = trimmed.find("{")
        end_idx = trimmed.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return trimmed[start_idx:end_idx + 1].strip()

        return trimmed

    @classmethod
    def parse_to_dict(cls, text: str) -> Optional[Dict[str, Any]]:
        """Parses LLM text to a dictionary."""
        json_str = cls.extract_json_string(text)
        if not json_str:
            logger.warning("No JSON structure found in LLM response text.")
            return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as jde:
            logger.warning(f"Failed to decode JSON from LLM response: {jde}. Raw string: {json_str[:150]}")
            return None

    @classmethod
    def parse_and_validate(cls, text: str, model_cls: Type[T]) -> Optional[T]:
        """
        Parses LLM text and validates it against the provided Pydantic model class.
        Returns validated Pydantic model instance or None if invalid.
        """
        data = cls.parse_to_dict(text)
        if data is None:
            return None

        try:
            instance = model_cls.model_validate(data)
            return instance
        except ValidationError as ve:
            logger.warning(f"Pydantic schema validation failed for {model_cls.__name__}: {ve}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error validating {model_cls.__name__}: {e}")
            return None
