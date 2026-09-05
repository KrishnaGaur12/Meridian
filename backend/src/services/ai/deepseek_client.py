"""
DeepSeek LLM Client for Razorpay AI Risk Manager.
Provides robust, timeout-bounded HTTP client communication with the DeepSeek API.
Ensures zero runtime crashes through strict error handling and offline/unconfigured detection.
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from config.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS
)
from src.utils.logger import get_logger

logger = get_logger("DeepSeekClient")


class DeepSeekClientError(Exception):
    """Base exception for DeepSeek client errors."""
    pass


class DeepSeekClient:
    """
    HTTP client for DeepSeek OpenAI-compatible chat completions API.
    Designed with strict fault tolerance and timeout guarantees.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = (os.getenv("DEEPSEEK_API_KEY", DEEPSEEK_API_KEY) or "").strip()

        if base_url is not None:
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = (os.getenv("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL) or "https://api.deepseek.com").rstrip("/")

        if model is not None:
            self.model = model.strip()
        else:
            self.model = (os.getenv("DEEPSEEK_MODEL", DEEPSEEK_MODEL) or "deepseek-chat").strip()

        self.timeout = timeout if timeout is not None else int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", str(DEEPSEEK_TIMEOUT_SECONDS)))


    def is_available(self) -> bool:
        """Checks if DeepSeek API key is configured and non-empty."""
        return bool(self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = True,
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Optional[Dict[str, Any]]:
        """
        Executes chat completion against DeepSeek API.
        Returns dictionary containing 'content', 'latency_ms', and 'raw_response' or None on failure.
        """
        if not self.is_available():
            logger.debug("DeepSeek API key is not configured. Skipping API call.")
            return None

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

        start_time = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.getcode()
                raw_body = resp.read().decode("utf-8")
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                if status_code != 200:
                    logger.warning(f"DeepSeek API returned HTTP status {status_code}: {raw_body[:200]}")
                    return None

                data = json.loads(raw_body)
                choices = data.get("choices", [])
                if not choices:
                    logger.warning("DeepSeek response contained no choices.")
                    return None

                message = choices[0].get("message", {})
                content = message.get("content", "")

                logger.info(f"DeepSeek completion succeeded in {latency_ms}ms (model: {self.model}).")
                return {
                    "content": content,
                    "latency_ms": latency_ms,
                    "model": self.model,
                    "provider": "deepseek",
                    "raw_response": data
                }

        except urllib.error.HTTPError as http_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_body = ""
            try:
                error_body = http_err.read().decode("utf-8", errors="ignore")[:300]
            except Exception:
                pass
            logger.warning(f"DeepSeek HTTP error {http_err.code} in {latency_ms}ms: {error_body}")
            return None

        except urllib.error.URLError as url_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"DeepSeek connection / URL error in {latency_ms}ms: {url_err.reason}")
            return None

        except TimeoutError:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"DeepSeek request timed out after {self.timeout}s ({latency_ms}ms).")
            return None

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"Unexpected error communicating with DeepSeek ({latency_ms}ms): {e}")
            return None
