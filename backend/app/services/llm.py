"""Multi-provider LLM abstraction layer for ORCA 2.0.

Fallback Chain:
    Groq (Primary) -> Cerebras (Fallback 1) -> Gemini Flash (Fallback 2) -> Template Engine (Safety Net)

CONSTRAINTS enforced by design:
  1. The LLM NEVER computes risk scores, GIS math, or authoritative safety decisions.
  2. The LLM only plans, translates, rephrases structured facts, or compiles narrative text.
  3. Every provider call is strictly bounded by wall-clock timeout.
  4. If any provider fails (quota, network, 4xx/5xx), execution falls back silently to the next.
  5. If all LLMs fail, the deterministic template engine guarantees zero crashes.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import httpx

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 6.0

_SYSTEM_PROMPT = (
    "You are ORCA, a marine-safety assistant for small-boat fishers in India. "
    "The user asked a specific question (given as user_query in <facts>). "
    "Answer that specific question using ONLY the structured <facts> provided. "
    "Write 3-5 clear, empathetic sentences in the language given by the language field "
    "(en=English, hi=Hindi, mr=Marathi, ta=Tamil, te=Telugu, bn=Bengali, ml=Malayalam). "
    "Rules: (1) Directly address the user_query first. "
    "(2) Use ONLY facts in <facts> — never invent numbers. "
    "(3) Keep every numeric value exact. "
    "(4) If go is false, tell the fisher NOT to go out. "
    "(5) If official_warning is true, state it prominently. "
    "(6) End with facts.sources_line verbatim. "
    "No bullets, headers, or markdown."
)


class LLMUnavailable(Exception):
    """Raised when all configured LLM providers fail and no template is requested."""


def _call_groq(
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = _DEFAULT_TIMEOUT_S,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    """Call Groq API using OpenAI-compatible endpoint."""
    if not api_key:
        raise LLMUnavailable("GROQ_API_KEY is not set")

    # Try supported fast models on Groq
    candidate_models = [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
    ]

    for model in candidate_models:
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content.strip()
            log.debug("Groq model %s returned status %s: %s", model, resp.status_code, resp.text[:100])
        except Exception as exc:
            log.debug("Groq model %s failed: %s", model, exc)

    raise LLMUnavailable("Groq models failed or returned empty content")


def _call_cerebras(
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = _DEFAULT_TIMEOUT_S,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    """Call Cerebras API using OpenAI-compatible endpoint."""
    if not api_key:
        raise LLMUnavailable("CEREBRAS_API_KEY is not set")

    candidate_models = [
        "qwen-3.8-27b",
        "gpt-oss-120b",
        "llama3.1-70b",
    ]

    for model in candidate_models:
        try:
            resp = httpx.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content and content.strip():
                        return content.strip()
            log.debug("Cerebras model %s returned status %s: %s", model, resp.status_code, resp.text[:100])
        except Exception as exc:
            log.debug("Cerebras model %s failed: %s", model, exc)

    raise LLMUnavailable("Cerebras models failed or returned empty content")


def _call_gemini(
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = _DEFAULT_TIMEOUT_S,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    """Call Google Gemini Flash API via generateContent endpoint."""
    if not api_key:
        raise LLMUnavailable("GEMINI_API_KEY is not set")

    candidate_models = [
        "gemini-flash-latest",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    # Convert OpenAI-style messages to Gemini contents + system instruction
    contents: List[Dict[str, Any]] = []
    system_instruction: Optional[Dict[str, Any]] = None

    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    if not contents and system_instruction:
        contents.append({"role": "user", "parts": [{"text": "Please proceed according to the instructions."}]})

    for model in candidate_models:
        try:
            payload: Dict[str, Any] = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max(max_tokens, 200),
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }
            if system_instruction:
                payload["systemInstruction"] = system_instruction

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            resp = httpx.post(url, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text_parts = [p.get("text", "") for p in parts if "text" in p]
                    text = "".join(text_parts).strip()
                    if text:
                        return text
            log.debug("Gemini model %s returned status %s: %s", model, resp.status_code, resp.text[:100])
        except Exception as exc:
            log.debug("Gemini model %s failed: %s", model, exc)

    raise LLMUnavailable("Gemini models failed or returned empty content")


def complete_chat(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 500,
    timeout: float = _DEFAULT_TIMEOUT_S,
    fallback_to_template: bool = True,
) -> Tuple[str, str]:
    """Execute chat completion with automatic fallback:
    Groq -> Cerebras -> Gemini -> Template.

    Returns:
        (response_text, provider_used) e.g. ("Conditions safe...", "groq")
    """
    full_messages: List[Dict[str, str]] = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 1. Try Groq
    if groq_key:
        try:
            text = _call_groq(full_messages, groq_key, timeout=timeout, temperature=temperature, max_tokens=max_tokens)
            return text, "groq"
        except Exception as e:
            log.info("Groq provider failed, cascading to Cerebras: %s", e)

    # 2. Try Cerebras
    if cerebras_key:
        try:
            text = _call_cerebras(full_messages, cerebras_key, timeout=timeout, temperature=temperature, max_tokens=max_tokens)
            return text, "cerebras"
        except Exception as e:
            log.info("Cerebras provider failed, cascading to Gemini: %s", e)

    # 3. Try Gemini
    if gemini_key:
        try:
            text = _call_gemini(full_messages, gemini_key, timeout=timeout, temperature=temperature, max_tokens=max_tokens)
            return text, "gemini"
        except Exception as e:
            log.info("Gemini provider failed: %s", e)

    # 4. Fallback to template engine if allowed
    if fallback_to_template:
        template_resp = (
            "Marine advisory summary: Operations must proceed with caution. "
            "Refer to official IMD/INCOIS forecasts for latest warnings."
        )
        return template_resp, "template"

    raise LLMUnavailable("All LLM providers (Groq, Cerebras, Gemini) failed")


def rephrase_explanation(facts: Dict[str, Any], language: str = "en") -> str:
    """Rephrase pre-computed structured facts into natural language via LLM chain.

    If all providers are down or timeout, returns a clean deterministic template answer.
    """
    facts_block = "\n".join(
        f"  {k}: {json.dumps(v, ensure_ascii=False)}"
        for k, v in facts.items()
    )
    user_message = (
        f"<facts>\n{facts_block}\n</facts>\n\n"
        f"Answer the user's question in language: {language}"
    )

    messages = [{"role": "user", "content": user_message}]

    try:
        text, provider = complete_chat(
            messages,
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=400,
            fallback_to_template=True,
        )
        if provider == "template":
            # Generate facts-based template fallback
            go_status = "SAFE TO GO" if facts.get("go") else "UNSAFE — DO NOT VENTURE OUT"
            wave = facts.get("wave_height_m", "N/A")
            wind = facts.get("wind_speed_kmh", "N/A")
            srcs = facts.get("sources_line", "")
            return f"Conditions: {go_status}. Wave height: {wave} m, Wind: {wind} km/h. {srcs}"
        return text
    except Exception as exc:
        raise LLMUnavailable(f"Rephrase failed: {exc}") from exc
