from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.schemas import (
    Evidence,
    make_evidence,
    AdvisoryConstraint,
    DecisionState,
    AlertEvent,
    ORCAState,
    measurement_to_evidence,
    agent_result_to_evidence_list,
    risk_assessment_to_decision_state,
)
from app import schemas as old_schemas


# ============================================================================
# Evidence Tests (3 tests: valid, missing field, out-of-range)
# ============================================================================
def test_evidence_valid():
    now = datetime.now(timezone.utc)
    ev = Evidence(
        metric="wave_height",
        value=1.8,
        unit="m",
        source="Open-Meteo",
        observed_at=now,
        retrieved_at=now,
        confidence=0.92,
        authority_level="external_forecast",
        mode="LIVE",
    )
    assert ev.metric == "wave_height"
    assert ev.value == 1.8
    assert ev.confidence == 0.92
    assert ev.mode == "LIVE"

    # Test make_evidence factory
    ev2 = make_evidence(
        metric="wind_speed",
        value=24.0,
        unit="kmph",
        source="IMD",
        confidence=0.85,
        authority_level="official_forecast",
        mode="DEMO",
    )
    assert ev2.metric == "wind_speed"
    assert ev2.retrieved_at is not None
    assert ev2.observed_at is not None


def test_evidence_missing_field():
    # missing source, confidence, authority_level, mode
    with pytest.raises(ValidationError):
        Evidence(
            metric="wave_height",
            value=2.0,
            observed_at=datetime.now(timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
        )


def test_evidence_out_of_range():
    now = datetime.now(timezone.utc)
    # confidence > 1.0
    with pytest.raises(ValidationError):
        Evidence(
            metric="wave_height",
            value=2.0,
            source="IMD",
            observed_at=now,
            retrieved_at=now,
            confidence=1.2,
            authority_level="official_advisory",
            mode="LIVE",
        )
    # confidence < 0.0
    with pytest.raises(ValidationError):
        Evidence(
            metric="wave_height",
            value=2.0,
            source="IMD",
            observed_at=now,
            retrieved_at=now,
            confidence=-0.1,
            authority_level="official_advisory",
            mode="LIVE",
        )
    # invalid authority_level literal
    with pytest.raises(ValidationError):
        Evidence(
            metric="wave_height",
            value=2.0,
            source="IMD",
            observed_at=now,
            retrieved_at=now,
            confidence=0.5,
            authority_level="invalid_authority",  # type: ignore
            mode="LIVE",
        )


# ============================================================================
# AdvisoryConstraint Tests (3 tests: valid, missing field, out-of-range)
# ============================================================================
def test_advisory_constraint_valid():
    now = datetime.now(timezone.utc)
    adv = AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="North Maharashtra coast",
        severity="SEVERE",
        valid_from=now,
        valid_until=now + timedelta(hours=24),
        source_text="Squally weather with wind speed reaching 45-55 kmph. Fishermen advised not to venture.",
        source_reference="IMD-MUM-20260910-01",
        confidence=0.95,
    )
    assert adv.authority == "IMD"
    assert adv.constraint_type == "NO_GO"
    assert adv.severity == "SEVERE"
    assert adv.confidence == 0.95


def test_advisory_constraint_missing_field():
    # missing source_text, source_reference, confidence
    with pytest.raises(ValidationError):
        AdvisoryConstraint(
            authority="IMD",
            constraint_type="NO_GO",
            named_region="Goa coast",
            severity="HIGH",
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=12),
        )


def test_advisory_constraint_out_of_range():
    now = datetime.now(timezone.utc)
    # confidence > 1.0
    with pytest.raises(ValidationError):
        AdvisoryConstraint(
            authority="IMD",
            constraint_type="NO_GO",
            named_region="Goa coast",
            severity="HIGH",
            valid_from=now,
            valid_until=now + timedelta(hours=12),
            source_text="Advisory text",
            source_reference="REF-01",
            confidence=1.5,
        )
    # invalid constraint_type
    with pytest.raises(ValidationError):
        AdvisoryConstraint(
            authority="IMD",
            constraint_type="SAFE_LAUNCH",  # invalid
            named_region="Goa coast",
            severity="HIGH",
            valid_from=now,
            valid_until=now + timedelta(hours=12),
            source_text="Advisory text",
            source_reference="REF-01",
            confidence=0.8,
        )


# ============================================================================
# DecisionState Tests (3 tests: valid, missing field, out-of-range)
# ============================================================================
def test_decision_state_valid():
    now = datetime.now(timezone.utc)
    dec = DecisionState(
        status="SAFE",
        risk_score=18.5,
        reasons=["Calm seas, wave height 0.8m", "No active official warnings"],
        language="en",
        explanation="Conditions are favorable for small craft fishing.",
        generated_at=now,
    )
    assert dec.status == "SAFE"
    assert dec.risk_score == 18.5
    assert len(dec.reasons) == 2


def test_decision_state_missing_field():
    # missing reasons, explanation, generated_at
    with pytest.raises(ValidationError):
        DecisionState(
            status="SAFE",
            risk_score=20.0,
            language="en",
        )


def test_decision_state_out_of_range():
    now = datetime.now(timezone.utc)
    # risk_score > 100
    with pytest.raises(ValidationError):
        DecisionState(
            status="UNSAFE",
            risk_score=105.0,
            reasons=["Extreme storm"],
            language="en",
            explanation="Do not go",
            generated_at=now,
        )
    # invalid status
    with pytest.raises(ValidationError):
        DecisionState(
            status="UNCERTAIN",  # invalid
            risk_score=50.0,
            reasons=["Uncertain weather"],
            language="en",
            explanation="Be careful",
            generated_at=now,
        )


# ============================================================================
# AlertEvent Tests (3 tests: valid, missing field, invalid types)
# ============================================================================
def test_alert_event_valid():
    now = datetime.now(timezone.utc)
    alert = AlertEvent(
        voyage_id="voyage_101",
        previous_status="SAFE",
        new_status="UNSAFE",
        reason="Sudden swell surge detected by IMD bulletin",
        safe_port={"name": "Sassoon Dock", "lat": 18.91, "lon": 72.82, "distance_km": 8.4},
        triggered_at=now,
    )
    assert alert.voyage_id == "voyage_101"
    assert alert.new_status == "UNSAFE"
    assert alert.safe_port["name"] == "Sassoon Dock"


def test_alert_event_missing_field():
    # missing safe_port and triggered_at
    with pytest.raises(ValidationError):
        AlertEvent(
            voyage_id="voyage_102",
            previous_status="SAFE",
            new_status="CAUTION",
            reason="High wind approaching",
        )


def test_alert_event_invalid_types():
    # safe_port not a dict
    with pytest.raises(ValidationError):
        AlertEvent(
            voyage_id="voyage_103",
            previous_status="SAFE",
            new_status="UNSAFE",
            reason="Storm alert",
            safe_port="Sassoon Dock",  # should be a dict
            triggered_at=datetime.now(timezone.utc),
        )


# ============================================================================
# ORCAState Tests (3 tests: valid, missing field, out-of-range)
# ============================================================================
def test_orca_state_valid():
    state = ORCAState(
        request_id="req-999",
        intent="operational",
        raw_query="Can I go fishing tomorrow morning?",
        language="en",
        location={"name": "Mumbai", "lat": 18.93, "lon": 72.83},
    )
    assert state.request_id == "req-999"
    assert state.intent == "operational"
    assert state.evidence == []


def test_orca_state_missing_field():
    # missing request_id, intent, raw_query, language
    with pytest.raises(ValidationError):
        ORCAState(location={"name": "Mumbai"})


def test_orca_state_out_of_range():
    # invalid intent literal (not "operational" or "analytical")
    with pytest.raises(ValidationError):
        ORCAState(
            request_id="req-1000",
            intent="commercial_shipping",  # invalid
            raw_query="Weather query",
            language="en",
        )


# ============================================================================
# Converters Tests
# ============================================================================
def test_converters_from_old_schemas():
    old_m = old_schemas.Measurement(
        value=1.5,
        unit="m",
        label="wave_height",
        provenance=old_schemas.Provenance(
            source="Open-Meteo",
            timestamp="2026-09-10T12:00:00Z",
            mode="LIVE",
            confidence=0.9,
        ),
    )
    ev = measurement_to_evidence(old_m, metric="wave_height")
    assert ev is not None
    assert ev.metric == "wave_height"
    assert ev.value == 1.5
    assert ev.mode == "LIVE"
    assert ev.source == "Open-Meteo"

    old_res = old_schemas.AgentResult(
        agent="weather",
        source="IMD",
        measurements={"wave_height": old_m},
    )
    ev_list = agent_result_to_evidence_list(old_res)
    assert len(ev_list) == 1
    assert ev_list[0].metric == "wave_height"

    old_risk = old_schemas.RiskAssessment(
        score=75,
        category="HIGH",
        factors=[
            old_schemas.RiskFactor(key="wave", label="Wave Height", factor=0.75, weight=0.25, contribution=18.75, detail="Rough seas")
        ],
        overrides=["Fishermen advisory active"],
        headline="High risk: Rough seas and warning active",
        generated_at="2026-09-10T12:00:00Z",
    )
    dec = risk_assessment_to_decision_state(old_risk, language="en")
    assert dec.status == "UNSAFE"
    assert dec.risk_score == 75.0
    assert len(dec.reasons) > 0
