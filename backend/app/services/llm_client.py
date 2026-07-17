"""
Thin wrapper around the Google Gemini API (google-genai SDK).

The rest of the codebase never talks to the `google.genai` SDK directly -- it
calls generate_text()/generate_json() here. That keeps provider-specific
details (model name, retry policy, JSON-mode) in one place, and makes it
possible to run the whole system without an API key (returns None, callers
fall back to deterministic templates) which is important for local
development, CI, and grading environments that may not have a live key
configured.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai
        _client = genai.Client(api_key=settings.gemini_api_key)
    except ImportError:
        logger.warning("google-genai package not installed; LLM calls disabled")
        return None
    return _client


def is_available() -> bool:
    return _get_client() is not None


def _build_config(types_module, system_prompt: str, max_tokens: Optional[int], json_mode: bool):
    """
    Shared config builder.

    Newer "thinking" Gemini models (2.x/3.x flash/pro) can spend part of the
    max_output_tokens budget on internal reasoning tokens before ever writing
    the visible response. If that budget is small, the model can exhaust it
    mid-thought and return a truncated/empty response -- which is exactly
    what showed up in logs here ("Here is the JSON" with nothing after it).
    We explicitly cap thinking_budget low (it's not needed for short,
    templated interview-question/scoring tasks) and use a generous
    max_output_tokens so the actual answer always has room to be written.
    """
    kwargs = dict(
        system_instruction=system_prompt,
        max_output_tokens=max_tokens or settings.llm_max_tokens,
    )
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    try:
        kwargs["thinking_config"] = types_module.ThinkingConfig(thinking_budget=0)
    except AttributeError:
        # older SDK / model without thinking config support -- fine to omit
        pass
    return types_module.GenerateContentConfig(**kwargs)


def generate_text(system_prompt: str, user_prompt: str, max_tokens: Optional[int] = None) -> Optional[str]:
    """Return raw text completion, or None if no LLM is configured/available."""
    client = _get_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=_build_config(types, system_prompt, max_tokens, json_mode=False),
        )
        text = (response.text or "").strip()
        if not text:
            logger.warning(
                "Empty LLM text response (finish_reason=%s)",
                getattr(response.candidates[0], "finish_reason", "unknown") if response.candidates else "no candidates",
            )
        return text or None
    except Exception as exc:  # network errors, auth errors, rate limits, etc.
        logger.error("LLM call failed: %s", exc)
        return None


def generate_json(system_prompt: str, user_prompt: str, max_tokens: Optional[int] = None) -> Optional[dict]:
    """Ask for strict JSON using Gemini's native JSON response mode."""
    client = _get_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_prompt,
            config=_build_config(types, system_prompt, max_tokens, json_mode=True),
        )
        raw = (response.text or "").strip()
        if not raw:
            finish_reason = (
                getattr(response.candidates[0], "finish_reason", "unknown") if response.candidates else "no candidates"
            )
            logger.warning("Empty LLM JSON response (finish_reason=%s) -- falling back", finish_reason)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return None

    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # try to salvage the largest {...} block, in case of stray formatting
        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass
        logger.error("Could not parse LLM JSON output (truncated or malformed): %s", raw[:300])
        return None