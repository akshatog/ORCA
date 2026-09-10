import os
import pytest
from unittest.mock import patch
from app.config import _load_dotenv

_load_dotenv()

from app.services.llm import complete_chat, rephrase_explanation, LLMUnavailable


def test_complete_chat_groq_active(monkeypatch):
    # Ensure real or test Groq key is present
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        messages = [{"role": "user", "content": "Reply with 'TEST_OK'"}]
        text, provider = complete_chat(messages, max_tokens=10, timeout=10.0)
        assert provider == "groq"
        assert len(text) > 0


def test_complete_chat_gemini_fallback_when_groq_cerebras_killed(monkeypatch):
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        pytest.skip("GEMINI_API_KEY not set")

    # Kill Groq and Cerebras keys
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", gemini_key)

    messages = [{"role": "user", "content": "Reply with 'GEMINI_OK'"}]
    text, provider = complete_chat(messages, max_tokens=10, timeout=10.0)
    assert provider == "gemini"
    assert len(text) > 0


def test_complete_chat_template_fallback_when_all_keys_dead(monkeypatch):
    # Kill all keys
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    messages = [{"role": "user", "content": "Can I go fishing today?"}]
    text, provider = complete_chat(messages, fallback_to_template=True)
    assert provider == "template"
    assert "advisory" in text.lower() or "marine" in text.lower()


def test_complete_chat_raises_when_all_dead_and_no_template(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    messages = [{"role": "user", "content": "Can I go fishing today?"}]
    with pytest.raises(LLMUnavailable):
        complete_chat(messages, fallback_to_template=False)


def test_rephrase_explanation_fallback_when_all_keys_dead(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    facts = {
        "user_query": "Is it safe to go fishing?",
        "go": False,
        "wave_height_m": 3.8,
        "wind_speed_kmh": 45.0,
        "sources_line": "Sources: IMD, Open-Meteo",
    }
    result = rephrase_explanation(facts, language="en")
    assert isinstance(result, str)
    assert "UNSAFE" in result or "3.8" in result
