"""Advisory Compiler for ORCA 2.0.

Compiles unstructured marine weather and safety bulletins (IMD, INCOIS, SACHET)
into structured AdvisoryConstraint objects.

Rule:
    Confidence < 0.70 -> flags low confidence / triggers INSUFFICIENT_EVIDENCE downstream.
    LLM down -> returns empty list or deterministic heuristic without crashing.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from ..schemas_v2 import AdvisoryConstraint
from .llm import complete_chat

log = logging.getLogger(__name__)

_COMPILER_SYSTEM_PROMPT = """You are the ORCA 2.0 Maritime Advisory Compiler.
Your job is to parse official government marine bulletins (IMD, INCOIS, SACHET, Coast Guard)
into structured safety constraints for Indian coastal waters.

Extract an array of JSON objects matching this schema:
[
  {
    "authority": "IMD" | "INCOIS" | "SACHET" | "COAST_GUARD" | "UNKNOWN",
    "constraint_type": "NO_GO" | "CAUTION" | "PORT_WARNING",
    "named_region": "Name of coastal region/state (e.g. North Maharashtra coast)",
    "severity": "LOW" | "MODERATE" | "HIGH" | "SEVERE",
    "valid_hours": 24,
    "source_text": "Exact excerpt from bulletin describing the condition or restriction",
    "confidence": 0.0 to 1.0
  }
]

CRITICAL RULES FOR CONFIDENCE:
- If the bulletin is clear, official, names specific coastal regions and hazards -> confidence >= 0.85.
- If the bulletin text is garbled, ambiguous, missing coastal location, or gibberish -> confidence MUST BE < 0.70 (e.g. 0.30 - 0.50).
- If the text has no safety restrictions or advisories -> return empty array [].
- Respond ONLY with valid JSON array, no conversational filler or markdown formatting outside the JSON block.
"""


def _clean_json_str(raw: str) -> str:
    """Extract raw JSON substring from LLM response."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


def compile_advisory(
    bulletin_text: str,
    source_reference: str = "OFFICIAL_BULLETIN",
    authority_hint: str = "IMD",
) -> List[AdvisoryConstraint]:
    """Compile raw bulletin text into a list of AdvisoryConstraint objects.

    Args:
        bulletin_text: Raw text of the advisory / bulletin.
        source_reference: Reference ID or bulletin number.
        authority_hint: Default authority name if not detectable.

    Returns:
        List of parsed AdvisoryConstraint objects. If text is invalid or LLM
        fails, returns an empty list or low-confidence fallback without crashing.
    """
    if not bulletin_text or not bulletin_text.strip():
        return []

    now = datetime.now(timezone.utc)
    user_prompt = f"Parse the following bulletin text into structured constraints:\n\n{bulletin_text.strip()}"
    messages = [{"role": "user", "content": user_prompt}]

    try:
        raw_resp, provider = complete_chat(
            messages,
            system_prompt=_COMPILER_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=600,
            timeout=8.0,
            fallback_to_template=False,
        )
    except Exception as exc:
        log.warning("Advisory compiler LLM call failed: %s. Using heuristic fallback.", exc)
        return _heuristic_fallback(bulletin_text, source_reference, authority_hint, now)

    clean_json = _clean_json_str(raw_resp)
    try:
        parsed = json.loads(clean_json)
        if isinstance(parsed, dict) and "constraints" in parsed:
            parsed = parsed["constraints"]
        if not isinstance(parsed, list):
            parsed = [parsed]
    except Exception as parse_err:
        log.warning("Failed to parse compiler JSON: %s. Raw was: %s", parse_err, raw_resp[:150])
        return _heuristic_fallback(bulletin_text, source_reference, authority_hint, now)

    constraints: List[AdvisoryConstraint] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            auth = item.get("authority") or authority_hint
            if auth not in ("IMD", "INCOIS", "SACHET", "COAST_GUARD"):
                auth = "IMD"

            ctype = str(item.get("constraint_type", "CAUTION")).upper()
            if ctype not in ("NO_GO", "CAUTION", "PORT_WARNING"):
                ctype = "CAUTION"

            severity = str(item.get("severity", "MODERATE")).upper()
            if severity not in ("LOW", "MODERATE", "HIGH", "SEVERE"):
                severity = "MODERATE"

            valid_hrs = int(item.get("valid_hours", 24))
            conf = float(item.get("confidence", 0.75))
            conf = max(0.0, min(1.0, conf))

            region = str(item.get("named_region", "Coastal Waters")).strip() or "Coastal Waters"
            src_text = str(item.get("source_text", bulletin_text[:200])).strip()

            c = AdvisoryConstraint(
                authority=auth,
                constraint_type=ctype,  # type: ignore
                named_region=region,
                severity=severity,      # type: ignore
                valid_from=now,
                valid_until=now + timedelta(hours=max(1, valid_hrs)),
                source_text=src_text,
                source_reference=source_reference,
                confidence=conf,
            )
            constraints.append(c)
        except Exception as item_err:
            log.debug("Skipping malformed advisory item %s: %s", item, item_err)

    return _localize_advisories(constraints)


def _localize_advisories(constraints: List[AdvisoryConstraint]) -> List[AdvisoryConstraint]:
    try:
        from .translate import translate_advisory
        for c in constraints:
            translate_advisory(c)
    except Exception as e:
        log.debug("Advisory localization skipped: %s", e)
    return constraints


def _heuristic_fallback(
    text: str,
    source_reference: str,
    authority: str,
    now: datetime,
) -> List[AdvisoryConstraint]:
    """Rule-based fallback when LLM is unavailable."""
    lower = text.lower()
    
    # Check for garbled / nonsense text
    alphanumeric = sum(1 for c in text if c.isalnum() or c.isspace())
    if len(text) < 15 or (alphanumeric / max(1, len(text)) < 0.6):
        # Garbled text -> return low confidence advisory (< 0.70)
        return [
            AdvisoryConstraint(
                authority=authority,
                constraint_type="CAUTION",
                named_region="Unknown Region",
                severity="MODERATE",
                valid_from=now,
                valid_until=now + timedelta(hours=12),
                source_text=text[:100],
                source_reference=source_reference,
                confidence=0.35,  # Below 0.70 -> triggers INSUFFICIENT_EVIDENCE
            )
        ]

    # Rule matching for real bulletins
    is_no_go = any(k in lower for k in [
        "advised not to venture",
        "do not venture",
        "suspend all fishing",
        "total suspension",
        "rough to very rough",
        "gale warning",
        "cyclonic storm",
    ])
    
    is_caution = any(k in lower for k in [
        "squally weather",
        "strong winds",
        "high swell",
        "rough sea",
        "caution",
        "vigilance",
    ])

    if not is_no_go and not is_caution:
        return []

    ctype = "NO_GO" if is_no_go else "CAUTION"
    sev = "SEVERE" if is_no_go else "MODERATE"

    # Region extraction heuristic
    region = "Indian Coastal Waters"
    for r in ["North Maharashtra", "South Maharashtra", "Goa", "Gujarat", "Kerala", "Tamil Nadu", "Odisha", "West Bengal", "Konkan"]:
        if r.lower() in lower:
            region = f"{r} coast"
            break

    return _localize_advisories([
        AdvisoryConstraint(
            authority=authority,
            constraint_type=ctype,  # type: ignore
            named_region=region,
            severity=sev,           # type: ignore
            valid_from=now,
            valid_until=now + timedelta(hours=24),
            source_text=text[:250],
            source_reference=source_reference,
            confidence=0.85,
        )
    ])
