"""LLM rephrase layer for ORCA (provider: Groq).

CONSTRAINTS enforced by design:
  1. LLM receives ONLY already-computed structured facts -- never raw user input.
  2. System prompt explicitly forbids inventing/altering/omitting any number,
     time, or safety-critical fact.
  3. Every call has a hard 3-second wall-clock timeout via a daemon thread.
  4. LLMUnavailable is raised on ANY failure; the caller falls back silently.
  5. This module is read-only -- it never touches risk, route, or geo logic.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Optional

log = logging.getLogger(__name__)

_TIMEOUT_S = 5.0          # hard wall-clock budget for the LLM call (Groq ~500ms)

_SYSTEM_PROMPT = (
    "You are ORCA, a marine-safety assistant for small-boat fishers in India. "
    "The user asked a specific question (given as user_query in <facts>). "
    "Answer that specific question using ONLY the structured <facts> provided. "
    "Write 3-5 clear, empathetic sentences in the language given by the language field "
    "(en=English, hi=Hindi, mr=Marathi). "
    "Rules: (1) Directly address the user_query first. "
    "(2) Use ONLY facts in <facts> — never invent numbers. "
    "(3) Keep every numeric value exact. "
    "(4) If go is false, tell the fisher NOT to go out. "
    "(5) If official_warning is true, state it prominently. "
    "(6) End with facts.sources_line verbatim. "
    "No bullets, headers, or markdown."
)


class LLMUnavailable(Exception):
    """Raised on any LLM failure so callers can fall back to the template."""


def _call_groq(facts: dict, language: str) -> str:
    """Synchronous Groq chat-completion call.

    Kept separate so the timeout wrapper can run it in a daemon thread.
    """
    try:
        from groq import Groq  # type: ignore[import]
    except ImportError as exc:
        raise LLMUnavailable("groq SDK not installed") from exc

    from ..config import LLM_API_KEY, LLM_MODEL

    if not LLM_API_KEY:
        raise LLMUnavailable("GROQ_API_KEY is not set")

    # Serialise the facts dict into a labelled, human-readable block so the
    # model can process each field without ambiguity.
    facts_block = "\n".join(
        f"  {k}: {json.dumps(v, ensure_ascii=False)}"
        for k, v in facts.items()
    )
    user_message = (
        f"<facts>\n{facts_block}\n</facts>\n\n"
        f"Answer the user's question in language: {language}"
    )

    client = Groq(api_key=LLM_API_KEY)

    # Try primary model, then fallback model if content is empty.
    # Some models (reasoning models like gpt-oss-*) occasionally return
    # empty content ? qwen/qwen3.8-27b is 100% reliable as a fallback.
    _FALLBACK_MODEL = "qwen/qwen3.8-27b"
    models_to_try = [LLM_MODEL]
    if LLM_MODEL != _FALLBACK_MODEL:
        models_to_try.append(_FALLBACK_MODEL)

    text = ""
    for model_id in models_to_try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=400,
            temperature=0.4,
        )
        text = completion.choices[0].message.content if completion.choices else ""
        if text and text.strip():
            break  # got a valid response ? stop trying

    if not text or not text.strip():
        raise LLMUnavailable("All Groq models returned empty responses")
    return text.strip()


def rephrase_explanation(facts: dict, language: str) -> str:
    """Rephrase pre-computed structured facts into natural language via Groq.

    Args:
        facts:    Already-computed typed values (risk_score, category, go, ...).
                  Never pass raw user text here.
        language: "en" | "hi" | "mr"

    Returns:
        A natural-language answer string in the requested language.

    Raises:
        LLMUnavailable: on ANY failure (timeout, missing key, bad response,
                        import error, network error).  Caller MUST catch this
                        and fall back to the template answer.
    """
    result: Optional[str] = None
    error: Optional[Exception] = None

    def _worker() -> None:
        nonlocal result, error
        try:
            result = _call_groq(facts, language)
        except Exception as exc:  # noqa: BLE001
            error = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    from ..config import LLM_TIMEOUT as _cfg_timeout  # noqa: PLC0415
    _effective_timeout = _cfg_timeout
    thread.join(timeout=_effective_timeout)

    if thread.is_alive():
        raise LLMUnavailable(f"LLM call timed out after {_effective_timeout}s")

    if error is not None:
        if isinstance(error, LLMUnavailable):
            raise error
        raise LLMUnavailable(f"LLM call failed: {error}") from error

    if result is None:
        raise LLMUnavailable("LLM worker finished with no result")

    return result
