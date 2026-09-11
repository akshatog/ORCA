import base64
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.voice import normalize_language_code, speak, transcribe


def test_normalize_language_code():
    assert normalize_language_code("hi") == "hi-IN"
    assert normalize_language_code("mr") == "mr-IN"
    assert normalize_language_code("ta") == "ta-IN"
    assert normalize_language_code("te") == "te-IN"
    assert normalize_language_code("bn") == "bn-IN"
    assert normalize_language_code("ml") == "ml-IN"
    assert normalize_language_code("hi-IN") == "hi-IN"


def test_voice_missing_key_raises_value_error():
    with patch.dict("os.environ", {"SARVAM_API_KEY": ""}):
        with pytest.raises(ValueError, match="SARVAM_API_KEY not configured"):
            transcribe(b"fake audio bytes", "hi-IN")

        with pytest.raises(ValueError, match="SARVAM_API_KEY not configured"):
            speak("नमस्ते", "hi-IN")


def test_transcribe_and_speak_with_mock_client():
    mock_stt_resp = MagicMock()
    mock_stt_resp.status_code = 200
    mock_stt_resp.json.return_value = {"transcript": "क्या मैं आज मछली पकड़ने जा सकता हूँ?"}

    fake_wav_bytes = b"RIFF....WAVEfmt ...."
    mock_tts_resp = MagicMock()
    mock_tts_resp.status_code = 200
    mock_tts_resp.json.return_value = {"audios": [base64.b64encode(fake_wav_bytes).decode("ascii")]}

    mock_client = MagicMock()
    mock_client.post.side_effect = [mock_stt_resp, mock_tts_resp]

    with patch.dict("os.environ", {"SARVAM_API_KEY": "fake-sarvam-key"}):
        # 1. Transcribe
        txt = transcribe(b"audio_bytes", "hi-IN", client=mock_client)
        assert txt == "क्या मैं आज मछली पकड़ने जा सकता हूँ?"

        # 2. Speak
        audio = speak("हाँ, आज मौसम ठीक है।", "hi-IN", client=mock_client)
        assert audio == fake_wav_bytes


def test_voice_api_endpoints_browser_fallback_when_no_key():
    client = TestClient(app)
    with patch.dict("os.environ", {"SARVAM_API_KEY": ""}):
        # STT endpoint
        resp_stt = client.post(
            "/voice/transcribe",
            files={"file": ("test.wav", b"fake audio data", "audio/wav")},
            data={"language": "hi-IN"},
        )
        assert resp_stt.status_code == 503
        assert resp_stt.json()["detail"]["browser_fallback"] is True

        # TTS endpoint
        resp_tts = client.post(
            "/voice/speak",
            json={"text": "Hello fisher", "language": "en-IN"},
        )
        assert resp_tts.status_code == 503
        assert resp_tts.json()["detail"]["browser_fallback"] is True
