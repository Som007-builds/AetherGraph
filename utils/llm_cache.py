# utils/llm_cache.py
"""
In-process LRU cache for LLM calls.

Prevents duplicate API calls for identical prompts within a single process
lifetime (e.g. repeated contradiction checks on the same claim pair during
a batch run).

The cache is keyed by (provider, prompt_hash) so switching providers
produces independent cache entries.

Architecture note:
    Redis integration is the natural next step for cross-process / cross-worker
    caching. The interface here is designed to be drop-in replaceable:
    swap _store from an LRU dict to a Redis client without changing call sites.

Usage:
    from utils.llm_cache import get_cached, set_cached, cache_stats

    cached = get_cached(provider, prompt)
    if cached is not None:
        return cached
    result = actual_llm_call(...)
    set_cached(provider, prompt, result)
    return result
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)

_MAX_SIZE   = 512          # Maximum number of cached responses
_store: OrderedDict[str, str] = OrderedDict()
_lock   = threading.Lock()
_hits   = 0
_misses = 0


def _make_key(provider: str, prompt: str) -> str:
    """Deterministic cache key: provider + SHA-256 of prompt."""
    digest = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:32]
    return f"{provider}:{digest}"


def get_cached(provider: str, prompt: str) -> str | None:
    """
    Return cached LLM response, or None on cache miss.
    Moves the accessed entry to the end (LRU eviction order).
    """
    global _hits, _misses
    key = _make_key(provider, prompt)
    with _lock:
        if key in _store:
            _store.move_to_end(key)
            _hits += 1
            logger.debug(f"[llm_cache] HIT  {key[:20]}… (hits={_hits})")
            return _store[key]
        _misses += 1
        return None


def set_cached(provider: str, prompt: str, response: str) -> None:
    """
    Store an LLM response. Evicts the oldest entry if the cache is full.
    """
    key = _make_key(provider, prompt)
    with _lock:
        if key in _store:
            _store.move_to_end(key)
        _store[key] = response
        if len(_store) > _MAX_SIZE:
            evicted_key, _ = _store.popitem(last=False)
            logger.debug(f"[llm_cache] EVICT {evicted_key[:20]}…")


def invalidate(provider: str, prompt: str) -> bool:
    """Remove a specific entry. Returns True if it was present."""
    key = _make_key(provider, prompt)
    with _lock:
        if key in _store:
            del _store[key]
            return True
        return False


def clear() -> None:
    """Clear the entire cache (useful in tests)."""
    global _hits, _misses
    with _lock:
        _store.clear()
        _hits   = 0
        _misses = 0


def cache_stats() -> dict:
    """Return cache statistics for the metrics endpoint."""
    with _lock:
        total = _hits + _misses
        hit_rate = (_hits / total) if total > 0 else 0.0
        return {
            "size":     len(_store),
            "max_size": _MAX_SIZE,
            "hits":     _hits,
            "misses":   _misses,
            "hit_rate": round(hit_rate, 4),
        }
