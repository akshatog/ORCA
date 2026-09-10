"""Voice API endpoints using Sarvam AI.

POST /voice/transcribe: Audio binary -> transcript text
POST /voice/speak: Text + language code -> Audio WAV stream
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

from ..services.voice import normalize_language_code, speak, transcribe

log = logging.getLogger(__name__)

router = APIRouter(tags=["ORCA 2.0 Voice"])


class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text narrative to synthesize")
    language: str = Field(default="hi-IN", description="Language locale (e.g. hi-IN, mr-IN, ta-IN)")
    voice_id: Optional[str] = Field(default="aditya", description="Sarvam speaker voice ID")


class TranscribeResponse(BaseModel):
    transcript: str
    language: str
    engine: str = "sarvam_saaras"


@router.post("/voice/transcribe", response_model=TranscribeResponse)
@router.post("/api/voice/transcribe", response_model=TranscribeResponse, include_in_schema=False)
async def transcribe_endpoint(
    file: UploadFile = File(...),
    language: str = Form("hi-IN"),
) -> TranscribeResponse:
    """Transcribe uploaded audio clip to Indian language text."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    try:
        text = transcribe(audio_bytes, language_hint=language)
        return TranscribeResponse(
            transcript=text,
            language=normalize_language_code(language),
            engine="sarvam_saaras",
        )
    except ValueError as ve:
        raise HTTPException(status_code=503, detail={"error": str(ve), "browser_fallback": True})
    except Exception as e:
        log.warning("Voice transcription failed: %s", e)
        raise HTTPException(status_code=500, detail={"error": str(e), "browser_fallback": True})


@router.post("/voice/speak")
@router.post("/api/voice/speak", include_in_schema=False)
def speak_endpoint(req: SpeakRequest):
    """Synthesize text narrative to streaming WAV audio."""
    try:
        audio_bytes = speak(req.text, language_code=req.language, voice_id=req.voice_id or "aditya")
        return Response(content=audio_bytes, media_type="audio/wav")
    except ValueError as ve:
        raise HTTPException(status_code=503, detail={"error": str(ve), "browser_fallback": True})
    except Exception as e:
        log.warning("Voice synthesis failed: %s", e)
        raise HTTPException(status_code=500, detail={"error": str(e), "browser_fallback": True})
