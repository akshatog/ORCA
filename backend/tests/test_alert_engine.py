from datetime import datetime, timezone
import pytest

from app.data.voyage_store import (
    clear_voyages,
    get_voyage,
    start_voyage,
)
from app.schemas_v2 import AdvisoryConstraint, DecisionState, make_evidence
from app.services.alert_engine import on_evidence_change, trigger_manual_alert


@pytest.fixture(autouse=True)
def clean_store():
    clear_voyages()
    yield
    clear_voyages()


def test_safe_voyage_with_severe_advisory_fires_alert():
    now = datetime.now(timezone.utc)
    # Start a SAFE voyage off Mumbai coast
    initial_decision = DecisionState(
        status="SAFE",
        risk_score=18.0,
        reasons=["Calm sea state"],
        language="en",
        explanation="Conditions favorable.",
        generated_at=now,
    )
    v = start_voyage(
        location={"name": "Offshore Mumbai", "lat": 18.95, "lon": 72.70},
        initial_decision=initial_decision,
        voyage_id="v-mumbai-safe",
    )
    assert v.status == "ACTIVE"

    # Inject severe advisory
    severe_adv = AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="Maharashtra Coast",
        severity="SEVERE",
        valid_from=now,
        valid_until=now,
        source_text="Squally weather with wind speed reaching 65 kmph. Fishermen advised not to venture.",
        source_reference="IMD-MUMBAI-BULLETIN-1",
        confidence=0.95,
    )

    alerts = on_evidence_change(new_advisories=[severe_adv])
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.voyage_id == "v-mumbai-safe"
    assert alert.previous_status == "SAFE"
    assert alert.new_status == "UNSAFE"
    assert "Official Severe Advisory" in alert.reason
    assert alert.safe_port["name"] == "Mumbai"
    assert alert.safe_port["distance_km"] > 0
    assert "lat" in alert.safe_port and "lon" in alert.safe_port

    # Verify voyage in store updated
    updated_v = get_voyage("v-mumbai-safe")
    assert updated_v.last_decision.status == "UNSAFE"
    assert updated_v.last_decision.risk_score >= 90.0


def test_safe_voyage_with_danger_wave_evidence():
    now = datetime.now(timezone.utc)
    initial_decision = DecisionState(
        status="SAFE",
        risk_score=20.0,
        reasons=["Mild sea state"],
        language="en",
        explanation="Safe to sail.",
        generated_at=now,
    )
    start_voyage(
        location={"name": "Offshore Kochi", "lat": 9.90, "lon": 76.15},
        initial_decision=initial_decision,
        voyage_id="v-kochi-1",
    )

    # Inject 4.5m wave height evidence
    wave_ev = make_evidence(
        metric="wave_height",
        value=4.5,
        unit="m",
        source="INCOIS",
        confidence=0.95,
    )

    alerts = on_evidence_change(new_evidence=[wave_ev])
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.voyage_id == "v-kochi-1"
    assert alert.previous_status == "SAFE"
    assert alert.new_status == "UNSAFE"
    assert "exceeds danger threshold" in alert.reason
    assert alert.safe_port["name"] == "Kochi"


def test_no_active_voyages_returns_empty():
    now = datetime.now(timezone.utc)
    adv = AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="All Coasts",
        severity="SEVERE",
        valid_from=now,
        valid_until=now,
        source_text="Severe cyclone warning.",
        source_reference="IMD-CYCLONE-1",
        confidence=0.99,
    )
    alerts = on_evidence_change(new_advisories=[adv])
    assert alerts == []


def test_already_unsafe_voyage_does_not_fire_duplicate_alert():
    now = datetime.now(timezone.utc)
    initial_decision = DecisionState(
        status="UNSAFE",
        risk_score=95.0,
        reasons=["Previous cyclone alert"],
        language="en",
        explanation="Stay in port.",
        generated_at=now,
    )
    start_voyage(
        location={"name": "Offshore Ratnagiri", "lat": 16.99, "lon": 73.20},
        initial_decision=initial_decision,
        voyage_id="v-ratnagiri-unsafe",
    )

    severe_adv = AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="Konkan Coast",
        severity="SEVERE",
        valid_from=now,
        valid_until=now,
        source_text="Another severe warning.",
        source_reference="IMD-BULLETIN-2",
        confidence=0.95,
    )

    alerts = on_evidence_change(new_advisories=[severe_adv])
    assert len(alerts) == 0  # No deterioration, already UNSAFE
