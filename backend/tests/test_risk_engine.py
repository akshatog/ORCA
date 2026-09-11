import pytest
from app.config import RISK
from app.services.risk_engine import assess


def test_calm_conditions_low_risk():
    res = assess(
        wave_height_m=0.8,
        wave_period_s=6.0,
        wind_speed_kmh=12.0,
        rain_probability_pct=5.0,
        lightning=False,
        visibility_km=12.0,
        sea_state_label="slight",
        current_speed_ms=0.3,
        alerts=[],
        distance_from_shore_km=5.0,
        nearest_zone_km=25.0,
        inside_zone=False,
        sources=["DEMO"],
    )
    assert res.score <= 25
    assert res.category == "LOW"
    assert res.go is True
    assert res.official_warning is False


def test_deterministic_floor_severe_warning():
    res = assess(
        wave_height_m=0.8,
        wave_period_s=6.0,
        wind_speed_kmh=12.0,
        rain_probability_pct=5.0,
        lightning=False,
        visibility_km=12.0,
        sea_state_label="slight",
        current_speed_ms=0.3,
        alerts=[{"severity": "severe", "headline": "Cyclone warning", "official": True, "source": "IMD"}],
        distance_from_shore_km=5.0,
        nearest_zone_km=25.0,
        inside_zone=False,
        sources=["IMD"],
    )
    assert res.score >= RISK.severe_warning_floor  # >= 92
    assert res.category == "EXTREME"
    assert res.go is False
    assert res.official_warning is True
    assert any("Official severe warning" in o for o in res.overrides)


def test_deterministic_floor_fishermen_warning():
    res = assess(
        wave_height_m=1.0,
        wave_period_s=6.0,
        wind_speed_kmh=15.0,
        rain_probability_pct=10.0,
        lightning=False,
        visibility_km=10.0,
        sea_state_label="moderate",
        current_speed_ms=0.4,
        alerts=[{"type": "fishermen_warning", "severity": "moderate", "headline": "Fishermen warning", "official": True, "source": "IMD"}],
        distance_from_shore_km=5.0,
        nearest_zone_km=25.0,
        inside_zone=False,
        sources=["IMD"],
    )
    assert res.score >= RISK.fishermen_warning_floor  # >= 70
    assert res.go is False
    assert res.official_warning is True


def test_deterministic_floor_wave_danger():
    res = assess(
        wave_height_m=4.5,  # Exceeds small craft danger threshold (4.0m)
        wave_period_s=9.0,
        wind_speed_kmh=20.0,
        rain_probability_pct=10.0,
        lightning=False,
        visibility_km=10.0,
        sea_state_label="rough",
        current_speed_ms=0.4,
        alerts=[],
        distance_from_shore_km=10.0,
        nearest_zone_km=20.0,
        inside_zone=False,
        sources=["DEMO"],
    )
    assert res.score >= RISK.wave_danger_floor  # >= 85
    assert any("Wave height" in o and "exceeds" in o for o in res.overrides)


def test_deterministic_floor_wind_gale():
    res = assess(
        wave_height_m=1.5,
        wave_period_s=6.0,
        wind_speed_kmh=68.0,  # Exceeds gale force threshold (62 km/h)
        rain_probability_pct=20.0,
        lightning=False,
        visibility_km=8.0,
        sea_state_label="moderate",
        current_speed_ms=0.4,
        alerts=[],
        distance_from_shore_km=10.0,
        nearest_zone_km=20.0,
        inside_zone=False,
        sources=["DEMO"],
    )
    assert res.score >= RISK.wind_danger_floor  # >= 85
    assert any("gale force" in o for o in res.overrides)


def test_deterministic_floor_inside_restricted_zone():
    res = assess(
        wave_height_m=0.8,
        wave_period_s=6.0,
        wind_speed_kmh=12.0,
        rain_probability_pct=5.0,
        lightning=False,
        visibility_km=12.0,
        sea_state_label="slight",
        current_speed_ms=0.3,
        alerts=[],
        distance_from_shore_km=5.0,
        nearest_zone_km=0.0,
        inside_zone=True,  # Inside naval/security zone
        sources=["DEMO"],
    )
    assert res.score >= RISK.restricted_zone_floor  # >= 60
    assert any("restricted maritime zone" in o for o in res.overrides)
