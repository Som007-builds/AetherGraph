# utils/llm_parser.py
"""
Centralized, robust LLM output normalization.

Replaces the 12+ ad-hoc json.loads() calls scattered across agents.
Every function here is defensive: it NEVER crashes, only returns None
or a safe fallback and logs the issue.

Public API:
    safe_json_parse(raw, context)      -> dict | list | None
    normalize_claim_output(raw)         -> list[dict]
    normalize_llm_output(raw, schema)   -> dict
    validate_claim(claim)               -> dict | None
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


# ─── Core Parser ─────────────────────────────────────────────────────────────

def safe_json_parse(raw: str | None, context: str = "") -> dict | list | None:
    """
    Parse LLM output into a Python dict or list.

    Handles:
    - Markdown fences  (```json ... ```)
    - Raw list outputs ([{...}] instead of {"key": [...]})
    - Partial JSON with trailing garbage text
    - Null / empty responses
    - Control character corruption (\x00–\x1F)
    - Double-encoded JSON strings

    Args:
        raw:     The raw string returned by the LLM.
        context: Optional label for log messages (e.g. "reader.extract_claims").

    Returns:
        Parsed dict or list, or None if all parsing attempts fail.
    """
    tag = f"[llm_parser:{context}]" if context else "[llm_parser]"

    if not raw or not raw.strip():
        logger.debug(f"{tag} Empty or null LLM response.")
        return None

    cleaned = raw.strip()

    # 1. Strip markdown fences  ```json ... ```  or  ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # 2. Remove control characters that break json.loads
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # 3. Direct parse attempt (fastest path)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 4. Extract first JSON object {...}
    obj_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # 5. Extract first JSON array [...]
    arr_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    # 6. Truncate at last valid closing brace / bracket (trailing garbage)
    for end_char, start_char in [("}", "{"), ("]", "[")]:
        last_idx = cleaned.rfind(end_char)
        if last_idx != -1:
            first_idx = cleaned.find(start_char)
            if first_idx != -1 and first_idx < last_idx:
                candidate = cleaned[first_idx : last_idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass

    # 7. Double-encoded: the string itself is a JSON string
    if cleaned.startswith('"') and cleaned.endswith('"'):
        try:
            inner = json.loads(cleaned)
            if isinstance(inner, str):
                return json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            pass

    logger.debug(
        f"{tag} All parse attempts failed. Raw snippet: {raw[:300]!r}"
    )
    return None


# ─── Claim Normalization ──────────────────────────────────────────────────────

# Minimum/maximum bounds for numeric claim fields
_CONFIDENCE_MIN = 0.0
_CONFIDENCE_MAX = 1.0
_MIN_CLAIM_LENGTH = 20


def validate_claim(claim: Any) -> dict | None:
    """
    Validate and normalise a single raw claim dict.

    Returns a cleaned dict if the claim is usable, or None if it should
    be skipped. Never raises.

    Enforces:
    - Must be a dict
    - Must have a non-empty claim_text or claim string
    - Confidence clamped to [0.0, 1.0]
    - Keywords coerced to list[str]
    - Conditions coerced to dict
    """
    if not isinstance(claim, dict):
        logger.debug(f"[validate_claim] Non-dict claim skipped: {type(claim)}")
        return None

    # Accept both "claim_text" (new structured) and "claim" (legacy)
    text = (
        claim.get("claim_text")
        or claim.get("claim")
        or ""
    )
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()

    if len(text) < _MIN_CLAIM_LENGTH:
        logger.debug(f"[validate_claim] Claim too short ({len(text)} chars), skipped.")
        return None

    # Normalise confidence
    raw_conf = claim.get("confidence", 1.0)
    try:
        conf = float(raw_conf)
        conf = max(_CONFIDENCE_MIN, min(_CONFIDENCE_MAX, conf))
    except (TypeError, ValueError):
        conf = 1.0

    # Normalise keywords
    raw_kw = claim.get("keywords", [])
    if isinstance(raw_kw, list):
        keywords = [str(k) for k in raw_kw if k]
    elif isinstance(raw_kw, str):
        keywords = [raw_kw] if raw_kw else []
    else:
        keywords = []

    # Normalise conditions (structured claims)
    raw_cond = claim.get("conditions", {})
    if isinstance(raw_cond, dict):
        conditions = {str(k): str(v) for k, v in raw_cond.items() if v}
    else:
        conditions = {}

    # Build the normalized output — carry through all optional structured fields
    normalized: dict = {
        "claim": text,          # legacy key — used by reader.py
        "claim_text": text,     # structured key
        "confidence": conf,
        "keywords": keywords,
    }

    # Optional structured fields — keep if present and non-empty
    for field in ("subject", "predicate", "object", "metric", "direction", "evidence_span"):
        val = claim.get(field)
        if val and isinstance(val, str) and val.strip():
            normalized[field] = val.strip()

    if conditions:
        normalized["conditions"] = conditions

    return normalized


def normalize_claim_output(raw: str | None, context: str = "claims") -> list[dict]:
    """
    Normalise LLM output that should contain a list of claims.

    Handles the two forms LLMs return:
      - {"claims": [...]}          — standard dict wrapper
      - [{...}, {...}]             — raw list (common failure mode)
      - {"claim": "..."}          — single claim as top-level dict

    Returns a (possibly empty) list of validated claim dicts.
    Never raises.
    """
    parsed = safe_json_parse(raw, context=context)

    if parsed is None:
        return []

    raw_claims: list = []

    if isinstance(parsed, list):
        # LLM returned a raw list of claims directly
        raw_claims = parsed
    elif isinstance(parsed, dict):
        # Standard wrapper: {"claims": [...]}
        if "claims" in parsed and isinstance(parsed["claims"], list):
            raw_claims = parsed["claims"]
        # Single claim as top-level dict
        elif "claim" in parsed or "claim_text" in parsed:
            raw_claims = [parsed]
        else:
            # Try every key that holds a list
            for val in parsed.values():
                if isinstance(val, list) and val:
                    raw_claims = val
                    break

    validated = []
    for item in raw_claims:
        clean = validate_claim(item)
        if clean is not None:
            validated.append(clean)

    if not validated and raw_claims:
        logger.debug(
            f"[normalize_claim_output:{context}] "
            f"{len(raw_claims)} raw claims found but all failed validation."
        )

    return validated


# ─── Generic Output Normalization ─────────────────────────────────────────────

def normalize_llm_output(
    raw: str | None,
    expected_keys: list[str] | None = None,
    context: str = "",
    fallback: dict | None = None,
) -> dict:
    """
    Normalise LLM output that should return a dict.

    Args:
        raw:           Raw LLM string response.
        expected_keys: If provided, warn when keys are missing.
        context:       Label for log messages.
        fallback:      Dict to return if parsing fails entirely.

    Returns:
        Parsed dict, or `fallback` (default: {}) if parsing fails.
    """
    if fallback is None:
        fallback = {}

    parsed = safe_json_parse(raw, context=context)

    if parsed is None:
        logger.warning(
            f"[normalize_llm_output:{context}] Parse returned None. "
            f"Using fallback. Raw snippet: {(raw or '')[:200]!r}"
        )
        return fallback

    if isinstance(parsed, list):
        # Wrap a raw list in the fallback structure if we know the expected key
        if expected_keys:
            first_list_key = expected_keys[0]
            logger.debug(
                f"[normalize_llm_output:{context}] Got list; "
                f"wrapping as {{'{first_list_key}': ...}}"
            )
            return {first_list_key: parsed}
        # Otherwise treat as a dict of index→item (rare edge case)
        return {str(i): v for i, v in enumerate(parsed)}

    if not isinstance(parsed, dict):
        logger.warning(
            f"[normalize_llm_output:{context}] Unexpected type {type(parsed)}. "
            f"Using fallback."
        )
        return fallback

    if expected_keys:
        missing = [k for k in expected_keys if k not in parsed]
        if missing:
            logger.debug(
                f"[normalize_llm_output:{context}] "
                f"Expected keys missing: {missing}"
            )

    return parsed


# ─── Timing helper (used by llm.py) ──────────────────────────────────────────

class LLMCallTimer:
    """Context manager that times an LLM call and logs the result."""

    def __init__(self, provider: str, context: str = ""):
        self.provider = provider
        self.context = context
        self._start: float = 0.0

    def __enter__(self) -> "LLMCallTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        elapsed = time.perf_counter() - self._start
        tag = f"[{self.provider}]" + (f"[{self.context}]" if self.context else "")
        if exc_type is None:
            logger.debug(f"{tag} LLM call completed in {elapsed:.2f}s")
        else:
            logger.debug(f"{tag} LLM call failed after {elapsed:.2f}s: {exc_val}")
        return False   # do not suppress exceptions
