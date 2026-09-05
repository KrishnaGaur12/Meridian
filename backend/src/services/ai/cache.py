"""
AI Cache Manager for Razorpay AI Risk Manager.
Provides in-memory caching for LLM-generated explanations and response drafts with
hash-based invalidation upon evidence mutation or dispute state changes.
"""

import time
import hashlib
import json
import threading
from typing import Dict, Any, Optional

from config.settings import AI_CACHE_TTL_SECONDS
from src.utils.logger import get_logger

logger = get_logger("AICacheManager")


class AICacheManager:
    """Thread-safe in-memory cache for AI Language Layer generations."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AICacheManager, cls).__new__(cls)
                    cls._instance._cache: Dict[str, Dict[str, Any]] = {}
                    cls._instance._dispute_index: Dict[str, set] = {}
                    cls._instance._cache_lock = threading.RLock()
        return cls._instance

    @staticmethod
    def compute_state_hash(context: Dict[str, Any]) -> str:
        """Computes deterministic hash from core dispute and evidence properties."""
        hash_keys = {
            "dispute_id": context.get("dispute_id"),
            "reason_code": context.get("reason_code"),
            "amount": context.get("amount"),
            "status": context.get("status"),
            "workflow_stage": context.get("workflow_stage"),
            "backend_decision_code": context.get("backend_decision_code") or context.get("recommendation_code"),
            "evidence_completeness": context.get("evidence_completeness"),
            "available_count": len(context.get("available_evidence", [])),
            "missing_count": len(context.get("missing_evidence", [])),
        }
        serialized = json.dumps(hash_keys, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def build_key(self, dispute_id: str, task_type: str, context: Dict[str, Any]) -> str:
        """Constructs a cache key combining dispute ID, task type, and state hash."""
        state_hash = self.compute_state_hash(context)
        return f"{dispute_id}:{task_type}:{state_hash}"

    def get(self, key: str) -> Optional[Any]:
        """Retrieves cached item if present and not expired."""
        with self._cache_lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            if time.time() > entry["expires_at"]:
                logger.debug(f"Cache key '{key}' expired. Evicting.")
                del self._cache[key]
                return None

            return entry["value"]

    def set(self, key: str, value: Any, dispute_id: str, ttl: Optional[int] = None) -> None:
        """Sets cached item with expiration and indexes it by dispute_id."""
        ttl_val = ttl or AI_CACHE_TTL_SECONDS
        expires_at = time.time() + ttl_val

        with self._cache_lock:
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "dispute_id": dispute_id
            }

            if dispute_id not in self._dispute_index:
                self._dispute_index[dispute_id] = set()
            self._dispute_index[dispute_id].add(key)

    def invalidate_dispute(self, dispute_id: str) -> int:
        """Invalidates all cached entries associated with a specific dispute."""
        with self._cache_lock:
            keys_to_delete = self._dispute_index.pop(dispute_id, set())
            count = 0
            for key in keys_to_delete:
                if key in self._cache:
                    del self._cache[key]
                    count += 1

            if count > 0:
                logger.info(f"Invalidated {count} cached AI items for dispute '{dispute_id}'.")
            return count

    def clear(self) -> None:
        """Clears entire AI cache."""
        with self._cache_lock:
            self._cache.clear()
            self._dispute_index.clear()
            logger.info("Cleared entire AI generation cache.")
