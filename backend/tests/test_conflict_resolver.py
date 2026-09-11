from datetime import datetime, timezone
import pytest

from app.schemas import make_evidence
from app.services.conflict_resolver import resolve_conflicts, get_selected_evidence

NOW = datetime.now(timezone.utc)


def test_imd_wave_vs_open_meteo_wave_imd_wins():
    """Verify: IMD wave vs Open-Meteo wave -> IMD wins, Open-Meteo overridden."""
    ev_imd = make_evidence(
        metric="wave_height",
        value=2.8,
        unit="m",
        source="IMD",
        confidence=0.90,
        authority_level="official_forecast",
        mode="DEMO",
        observed_at=NOW,
    )
    ev_open_meteo = make_evidence(
        metric="wave_height",
        value=1.4,
        unit="m",
        source="Open-Meteo",
        confidence=0.92,
        authority_level="external_forecast",
        mode="DEMO",
        observed_at=NOW,
    )

    reconciled, log_entries = resolve_conflicts([ev_imd, ev_open_meteo])

    selected = [e for e in reconciled if e.conflict_status == "selected"]
    overridden = [e for e in reconciled if e.conflict_status == "overridden"]

    assert len(selected) == 1
    assert selected[0].source == "IMD"
    assert selected[0].value == 2.8

    assert len(overridden) == 1
    assert overridden[0].source == "Open-Meteo"
    assert overridden[0].value == 1.4
    assert "Overridden by IMD" in overridden[0].conflict_reason

    assert len(log_entries) == 1
    assert log_entries[0]["metric"] == "wave_height"
    assert log_entries[0]["winner"]["source"] == "IMD"


def test_official_advisory_dominates_forecast():
    ev_adv = make_evidence(
        metric="wind_speed",
        value=65.0,
        unit="kmph",
        source="IMD_CYCLONE_BULLETIN",
        confidence=0.95,
        authority_level="official_advisory",
        mode="DEMO",
        observed_at=NOW,
    )
    ev_forecast = make_evidence(
        metric="wind_speed",
        value=30.0,
        unit="kmph",
        source="INCOIS_FORECAST",
        confidence=0.96,
        authority_level="official_forecast",
        mode="DEMO",
        observed_at=NOW,
    )

    reconciled, log_entries = resolve_conflicts([ev_adv, ev_forecast])
    selected = get_selected_evidence(reconciled)

    assert len(selected) == 1
    assert selected[0].source == "IMD_CYCLONE_BULLETIN"
    assert selected[0].value == 65.0


def test_tie_breaking_by_confidence():
    # Both are external forecasts
    ev_sg = make_evidence(
        metric="sea_surface_temp",
        value=29.2,
        unit="C",
        source="StormGlass",
        confidence=0.88,
        authority_level="external_forecast",
        mode="DEMO",
        observed_at=NOW,
    )
    ev_om = make_evidence(
        metric="sea_surface_temp",
        value=28.1,
        unit="C",
        source="Open-Meteo",
        confidence=0.75,
        authority_level="external_forecast",
        mode="DEMO",
        observed_at=NOW,
    )

    reconciled, _ = resolve_conflicts([ev_sg, ev_om])
    selected = get_selected_evidence(reconciled)

    assert len(selected) == 1
    assert selected[0].source == "StormGlass"
    assert selected[0].value == 29.2
