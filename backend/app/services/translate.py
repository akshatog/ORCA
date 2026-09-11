"""Machine translation service for ORCA 2.0 using Sarvam Mayura.

Supports translation between English and Indian regional languages (Tamil, Telugu,
Bengali, Malayalam, Hindi, Marathi, Gujarati, Kannada, Odia).

Used for:
- Live query / response translation.
- Advisory translation (TASK-4.9): translating official bulletin excerpts
  into localized summaries across all coastal languages.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Sequence

import httpx

from ..schemas import AdvisoryConstraint
from .voice import LANG_MAP, get_sarvam_key, normalize_language_code

log = logging.getLogger(__name__)

SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"

# Heuristic translations for emergency bulletin phrases when offline or API key is unset
OFFLINE_PHRASE_FALLBACKS: Dict[str, Dict[str, str]] = {
    "ta": {
        "Fishermen are advised not to venture into sea": "மீனவர்கள் கடலுக்கு செல்ல வேண்டாம் என்று அறிவுறுத்தப்படுகிறார்கள்",
        "Squally weather with wind speed reaching": "சூறாவளி காற்று வீசக்கூடும்",
        "High swell waves": "உயர்ந்த அலைகள் எழக்கூடும்",
        "Safe to sail": "பயணம் செய்ய பாதுகாப்பானது",
    },
    "te": {
        "Fishermen are advised not to venture into sea": "మత్స్యకారులు సముద్రంలోకి వెళ్లవద్దని సూచించబడింది",
        "Squally weather with wind speed reaching": "ఈదురు గాలులు వీచే అవకాశం ఉంది",
        "High swell waves": "ఎత్తైన అలలు వచ్చే అవకాశం ఉంది",
        "Safe to sail": "ప్రయాణానికి సురక్షితం",
    },
    "bn": {
        "Fishermen are advised not to venture into sea": "মৎস্যজীবীদের সমুদ্রে না যাওয়ার পরামর্শ দেওয়া হচ্ছে",
        "Squally weather with wind speed reaching": "দমকা হাওয়া সহ দুর্যোগপূর্ণ আবহাওয়া",
        "High swell waves": "উঁচু ঢেউয়ের আশঙ্কা",
        "Safe to sail": "যাত্রার জন্য নিরাপদ",
    },
    "ml": {
        "Fishermen are advised not to venture into sea": "മത്സ്യത്തൊഴിലാളികൾ കടലിൽ പോകരുതെന്ന് മുന്നറിയിപ്പ്",
        "Squally weather with wind speed reaching": "ശക്തമായ കാറ്റിന് സാധ്യത",
        "High swell waves": "ഉയർന്ന തിരമാലകൾക്ക് സാധ്യത",
        "Safe to sail": "യാത്ര സുരക്ഷിതമാണ്",
    },
    "hi": {
        "Fishermen are advised not to venture into sea": "मछुआरों को समुद्र में न जाने की सलाह दी जाती है",
        "Squally weather with wind speed reaching": "तूफानी मौसम और तेज हवाएं चलने की संभावना",
        "High swell waves": "ऊंची लहरें उठने की संभावना",
        "Safe to sail": "यात्रा सुरक्षित है",
    },
    "mr": {
        "Fishermen are advised not to venture into sea": "मासेमारांना समुद्रात न जाण्याचा सल्ला देण्यात आला आहे",
        "Squally weather with wind speed reaching": "वादळी हवामान आणि सोसाट्याचा वारा वाहण्याची शक्यता",
        "High swell waves": "उंच लाटा उसळण्याची शक्यता",
        "Safe to sail": "प्रवास सुरक्षित आहे",
    },
}


def translate(
    text: str,
    from_lang: str = "en",
    to_lang: str = "hi",
    client: Optional[httpx.Client] = None,
) -> str:
    """Translate text using Sarvam Mayura model.

    Falls back smoothly to offline phrasebook or original text if key is unset.
    """
    if not text or not text.strip():
        return ""

    src_short = from_lang.lower().split("-")[0]
    tgt_short = to_lang.lower().split("-")[0]

    if src_short == tgt_short:
        return text

    key = get_sarvam_key()
    if not key:
        # Check offline fallbacks
        fallbacks = OFFLINE_PHRASE_FALLBACKS.get(tgt_short, {})
        for eng, trans in fallbacks.items():
            if eng.lower() in text.lower():
                return trans
        return text  # Graceful fallback: return original text

    src_code = normalize_language_code(src_short)
    tgt_code = normalize_language_code(tgt_short)

    payload = {
        "input": text[:1000],
        "source_language_code": src_code,
        "target_language_code": tgt_code,
        "speaker_gender": "Male",
        "mode": "formal",
        "model": "mayura:v1",
        "enable_preprocessing": True,
    }
    headers = {
        "api-subscription-key": key,
        "Content-Type": "application/json",
    }

    try:
        http_client = client or httpx.Client(timeout=8.0)
        resp = http_client.post(SARVAM_TRANSLATE_URL, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("translated_text", text).strip()
        else:
            log.warning("Sarvam Translate returned %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.warning("Sarvam Translate request failed: %s", e)

    # Fallback to phrasebook if available
    fallbacks = OFFLINE_PHRASE_FALLBACKS.get(tgt_short, {})
    for eng, trans in fallbacks.items():
        if eng.lower() in text.lower():
            return trans
    return text


def translate_advisory(
    advisory: AdvisoryConstraint,
    target_languages: Sequence[str] = ("ta", "te", "bn", "ml", "hi", "mr"),
    client: Optional[httpx.Client] = None,
) -> AdvisoryConstraint:
    """Translate an advisory's source_text across priority languages.

    Populates advisory.localized_summaries: Dict[str, str].
    """
    summaries: Dict[str, str] = dict(advisory.localized_summaries or {})
    src_text = advisory.source_text

    for lang in target_languages:
        if lang not in summaries:
            try:
                summaries[lang] = translate(src_text, from_lang="en", to_lang=lang, client=client)
            except Exception:
                summaries[lang] = src_text

    advisory.localized_summaries = summaries
    return advisory
