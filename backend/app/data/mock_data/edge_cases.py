"""Edge cases explicitly modeled from docs/09_testing_and_edge_cases.md.

Every case outputs valid Evidence_v2 objects to exercise safety, conflict,
and fallback logic across the ORCA 2.0 pipeline.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from app.schemas_v2 import Evidence, AdvisoryConstraint, make_evidence

NOW = datetime.now(timezone.utc)

# 1. Low-confidence advisory (< 0.70) -> triggers INSUFFICIENT_EVIDENCE
CASE_1_LOW_CONFIDENCE = make_evidence(
    metric="advisory_constraint",
    value={
        "authority": "IMD_SCRAPED_BULLETIN",
        "constraint_type": "NO_GO",
        "named_region": "Western Offshore Region",
        "confidence": 0.54,
        "note": "Garbled text in bulletin, entity resolution uncertain",
    },
    source="IMD_SCRAPER",
    observed_at=NOW,
    confidence=0.54,  # Below 0.70 threshold
    authority_level="official_advisory",
    mode="DEMO",
)

# 2. Conflicting sources (disagreement on wave height)
CASE_2_CONFLICT_A = make_evidence(
    metric="wave_height",
    value=1.3,
    unit="m",
    source="Open-Meteo",
    observed_at=NOW,
    confidence=0.88,
    authority_level="external_forecast",
    mode="DEMO",
)

CASE_2_CONFLICT_B = make_evidence(
    metric="wave_height",
    value=2.8,
    unit="m",
    source="StormGlass",
    observed_at=NOW,
    confidence=0.82,
    authority_level="external_forecast",
    mode="DEMO",
)

# 3. Expired validity window -> STALE handling
CASE_3_EXPIRED_WINDOW = make_evidence(
    metric="wave_height",
    value=1.1,
    unit="m",
    source="Open-Meteo",
    observed_at=NOW - timedelta(days=2),
    retrieved_at=NOW - timedelta(days=2),
    valid_from=NOW - timedelta(days=2),
    valid_until=NOW - timedelta(hours=8),  # In the past
    confidence=0.65,
    authority_level="external_forecast",
    mode="STALE",
)

# 4. Missing optional fields (e.g. no geometry, no unit) -> graceful degradation
CASE_4_MISSING_OPTIONAL_FIELDS = make_evidence(
    metric="custom_warning",
    value="Unmarked floating debris reported near harbour entrance",
    unit=None,
    geometry=None,
    source="Coastal_Security",
    observed_at=NOW,
    confidence=0.75,
    authority_level="heuristic",
    mode="DEMO",
)

# 5. Network failure fallback -> CACHED mode with stale/valid cached timestamp
CASE_5_NETWORK_FAILURE_CACHED = make_evidence(
    metric="wind_speed",
    value=21.0,
    unit="kmph",
    source="Open-Meteo",
    observed_at=NOW - timedelta(hours=3),
    retrieved_at=NOW,
    valid_from=NOW - timedelta(hours=3),
    valid_until=NOW + timedelta(hours=1),
    confidence=0.78,
    authority_level="external_forecast",
    mode="CACHED",
)

# 6. Official NO_GO advisory with mild local readings -> floor must override weighted score
CASE_6_OFFICIAL_NO_GO_MILD_LOCAL = make_evidence(
    metric="official_advisory",
    value={
        "authority": "IMD",
        "constraint_type": "NO_GO",
        "named_region": "Konkan Coast",
        "statement": "Total fishing suspension due to active security operation / upcoming swell surge",
    },
    source="IMD",
    observed_at=NOW,
    confidence=0.98,
    authority_level="official_advisory",
    mode="DEMO",
)

# 7. Cyclone override -> GDACS orange/red alert overrides local calm conditions
CASE_7_CYCLONE_ORANGE_ALERT = make_evidence(
    metric="cyclone_alert",
    value={
        "system_name": "Severe Cyclonic Storm SHAKTI",
        "alert_level": "orange",
        "distance_km": 180.0,
        "max_wind_kmh": 110.0,
        "direction": "NE towards Maharashtra coast",
    },
    source="GDACS",
    observed_at=NOW,
    confidence=0.96,
    authority_level="official_advisory",
    mode="DEMO",
)

# 8. Ambiguous intent classification -> needs clarification
CASE_8_AMBIGUOUS_INTENT = make_evidence(
    metric="intent_classification",
    value={
        "query": "the sea water looks deep blue today",
        "operational_prob": 0.51,
        "analytical_prob": 0.49,
        "recommendation": "PROMPT_USER_FOR_CLARIFICATION",
    },
    source="IntentClassifier",
    observed_at=NOW,
    confidence=0.51,
    authority_level="heuristic",
    mode="DEMO",
)

# Central mapping for all edge cases (dictionary and list)
ALL_CASES: Dict[str, Evidence] = {
    "case_1_low_confidence_advisory": CASE_1_LOW_CONFIDENCE,
    "case_2_conflict_disagreeing_source": CASE_2_CONFLICT_B,
    "case_3_expired_validity_window": CASE_3_EXPIRED_WINDOW,
    "case_4_missing_optional_fields": CASE_4_MISSING_OPTIONAL_FIELDS,
    "case_5_network_failure_cached": CASE_5_NETWORK_FAILURE_CACHED,
    "case_6_official_no_go_mild_local": CASE_6_OFFICIAL_NO_GO_MILD_LOCAL,
    "case_7_cyclone_orange_alert": CASE_7_CYCLONE_ORANGE_ALERT,
    "case_8_ambiguous_intent": CASE_8_AMBIGUOUS_INTENT,
}

ALL_CASES_LIST: List[Evidence] = list(ALL_CASES.values())
