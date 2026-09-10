from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch

from app.schemas_v2 import AdvisoryConstraint
from app.services.advisory_compiler import compile_advisory
from app.services.i18n import detect_language, t
from app.services.translate import translate, translate_advisory


def test_detect_language_all_indian_scripts():
    # Tamil
    assert detect_language("நாளை காலை மீன்பிடிக்க செல்லலாமா?") == "ta"

    # Telugu
    assert detect_language("రేపు ఉదయం చేపల వేటకు వెళ్లవచ్చా?") == "te"

    # Bengali
    assert detect_language("কাল সকালে কি মাছ ধরতে যাওয়া নিরাপদ?") == "bn"

    # Malayalam
    assert detect_language("നാളെ രാവിലെ മീൻപിടിക്കാൻ പോകുന്നത് സുരക്ഷിതമാണോ?") == "ml"

    # Marathi vs Hindi (both Devanagari)
    assert detect_language("उद्या सकाळी ६ वाजता मासेमारी सुरक्षित आहे का?") == "mr"
    assert detect_language("क्या कल सुबह मछली पकड़ने जाना सुरक्षित है?") == "hi"

    # English default
    assert detect_language("Is it safe to go fishing tomorrow morning?") == "en"


def test_phrasebook_regional_translations():
    # Test verdict_low across languages
    assert t("verdict_low", "ta") == "சூழ்நிலைகள் பாதுகாப்பாக உள்ளன"
    assert t("verdict_low", "te") == "పరిస్థితులు సురక్షితంగా ఉన్నాయి"
    assert t("verdict_low", "bn") == "পরিস্থিতি অনুকূল ও নিরাপদ"
    assert t("verdict_low", "ml") == "സാഹചര്യങ്ങൾ സുരക്ഷിതമാണ്"
    assert t("verdict_low", "en") == "Conditions look safe"


def test_translate_offline_fallbacks_and_mock():
    # Offline fallback
    with patch.dict("os.environ", {"SARVAM_API_KEY": ""}):
        res_ta = translate("Fishermen are advised not to venture into sea", "en", "ta")
        assert "மீனவர்கள் கடலுக்கு செல்ல வேண்டாம்" in res_ta

    # Mock Sarvam API call
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"translated_text": "வானிலை சீராக உள்ளது"}

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp

    with patch.dict("os.environ", {"SARVAM_API_KEY": "fake-key"}):
        res = translate("Weather is clear", "en", "ta", client=mock_client)
        assert res == "வானிலை சீராக உள்ளது"


def test_translate_advisory_populates_localized_summaries():
    now = datetime.now(timezone.utc)
    adv = AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="Tamil Nadu coast",
        severity="SEVERE",
        valid_from=now,
        valid_until=now,
        source_text="Fishermen are advised not to venture into sea due to high swell waves.",
        source_reference="IMD-TN-01",
        confidence=0.95,
    )

    with patch.dict("os.environ", {"SARVAM_API_KEY": ""}):
        updated = translate_advisory(adv, target_languages=["ta", "te", "bn", "ml", "hi", "mr"])
        assert "ta" in updated.localized_summaries
        assert "te" in updated.localized_summaries
        assert "bn" in updated.localized_summaries
        assert "ml" in updated.localized_summaries
        assert len(updated.localized_summaries["ta"]) > 0


def test_compile_advisory_includes_localized_summaries():
    bulletin = "Fishermen are advised not to venture into deep sea areas along Maharashtra coast due to squally weather."
    with patch.dict("os.environ", {"SARVAM_API_KEY": ""}):
        advisories = compile_advisory(bulletin, source_reference="TEST-IMD")
        assert len(advisories) >= 1
        adv = advisories[0]
        assert hasattr(adv, "localized_summaries")
        assert "ta" in adv.localized_summaries
