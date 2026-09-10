"""Sarvam AI Voice Integration for ORCA 2.0.

Provides:
- Saaras STT: Speech-to-Text across 22 Indian languages.
- Bulbul TTS: Natural Indian accent Text-to-Speech across 11 languages.
- Graceful fallbacks when SARVAM_API_KEY is unset or service is unavailable.
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

import httpx

log = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Standard mapping from short language codes to Sarvam regional locale tags
LANG_MAP = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "ml": "ml-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "or": "od-IN",
    "en": "en-IN",
}


def get_sarvam_key() -> str:
    return os.getenv("SARVAM_API_KEY", "").strip()


def normalize_language_code(code: str) -> str:
    cleaned = (code or "hi").strip().lower().split("-")[0]
    return LANG_MAP.get(cleaned, code if "-" in code else f"{cleaned}-IN")


def transcribe(
    audio_bytes: bytes,
    language_hint: str = "hi-IN",
    client: Optional[httpx.Client] = None,
) -> str:
    """Transcribe Indian audio speech using Sarvam Saaras model.

    Returns transcript string or raises error for caller fallback.
    """
    key = get_sarvam_key()
    if not key:
        raise ValueError("SARVAM_API_KEY not configured. Use browser Web Speech fallback.")

    if not audio_bytes:
        return ""

    locale = normalize_language_code(language_hint)
    headers = {"api-subscription-key": key}
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"model": "saaras:v1", "language_code": locale}

    http_client = client or httpx.Client(timeout=12.0)
    resp = http_client.post(SARVAM_STT_URL, headers=headers, files=files, data=data)
    if resp.status_code == 200:
        result = resp.json()
        return result.get("transcript", "").strip()
    else:
        log.error("Sarvam STT failed (status %d): %s", resp.status_code, resp.text[:200])
        raise RuntimeError(f"Sarvam STT failed with status {resp.status_code}")


def speak(
    text: str,
    language_code: str = "hi-IN",
    voice_id: str = "meera",
    client: Optional[httpx.Client] = None,
) -> bytes:
    """Synthesize speech using Sarvam Bulbul TTS.

    Returns raw audio bytes (WAV format).
    """
    key = get_sarvam_key()
    if not key:
        raise ValueError("SARVAM_API_KEY not configured. Use browser SpeechSynthesis fallback.")

    if not text or not text.strip():
        return b""

    locale = normalize_language_code(language_code)
    headers = {
        "api-subscription-key": key,
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": [text[:500]],  # Bulbul standard segment length limit
        "target_language_code": locale,
        "speaker": voice_id or "meera",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 16000,
        "enable_preprocessing": True,
        "model": "bulbul:v1",
    }

    http_client = client or httpx.Client(timeout=12.0)
    resp = http_client.post(SARVAM_TTS_URL, headers=headers, json=payload)
    if resp.status_code == 200:
        result = resp.json()
        audios = result.get("audios", [])
        if audios and audios[0]:
            return base64.b64decode(audios[0])
        raise ValueError("No audio content returned from Sarvam TTS")
    else:
        log.error("Sarvam TTS failed (status %d): %s", resp.status_code, resp.text[:200])
        raise RuntimeError(f"Sarvam TTS failed with status {resp.status_code}")
