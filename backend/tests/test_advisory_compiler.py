import pytest
from unittest.mock import patch

from app.services.advisory_compiler import compile_advisory
from app.schemas_v2 import AdvisoryConstraint


REAL_IMD_BULLETIN = (
    "INDIA METEOROLOGICAL DEPARTMENT. FISHERMEN WARNING FOR NORTH MAHARASHTRA COAST: "
    "Squally weather with wind speed reaching 45-55 kmph gusting to 65 kmph likely to prevail. "
    "Sea conditions will be rough to very rough. Fishermen are advised not to venture into sea "
    "during next 24 hours."
)

GARBLED_BULLETIN = "!!!###%%% xqzwty 99824 ??? ~~~~ / // ///"


def test_compile_advisory_real_imd_bulletin():
    constraints = compile_advisory(REAL_IMD_BULLETIN, source_reference="IMD-2026-TEST")
    assert len(constraints) >= 1
    c = constraints[0]
    assert isinstance(c, AdvisoryConstraint)
    assert c.constraint_type in ("NO_GO", "CAUTION")
    assert c.confidence >= 0.70
    assert "Maharashtra" in c.named_region or "Coast" in c.named_region


def test_compile_advisory_garbled_text_yields_low_confidence():
    constraints = compile_advisory(GARBLED_BULLETIN, source_reference="GARBLED-TEST")
    # If returned, must have confidence < 0.70 to trigger INSUFFICIENT_EVIDENCE
    if constraints:
        assert constraints[0].confidence < 0.70, (
            f"Expected confidence < 0.70 for garbled text, got {constraints[0].confidence}"
        )


def test_compile_advisory_empty_string():
    assert compile_advisory("") == []
    assert compile_advisory("   ") == []


def test_compile_advisory_llm_down_heuristic_fallback():
    with patch("app.services.advisory_compiler.complete_chat", side_effect=Exception("API connection refused")):
        # Real text should still parse via heuristic fallback
        constraints = compile_advisory(REAL_IMD_BULLETIN, source_reference="FALLBACK-TEST")
        assert len(constraints) >= 1
        assert constraints[0].constraint_type == "NO_GO"
        assert constraints[0].confidence >= 0.70

        # Garbled text should produce confidence < 0.70
        garbled_res = compile_advisory(GARBLED_BULLETIN, source_reference="GARBLED-FALLBACK")
        assert len(garbled_res) >= 1
        assert garbled_res[0].confidence < 0.70
