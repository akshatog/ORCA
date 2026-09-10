"""Standard mock fixtures for weather, advisories, PFZ, and cyclones.
All items are wrapped in Evidence_v2 or AdvisoryConstraint.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from app.schemas_v2 import Evidence, AdvisoryConstraint, make_evidence

NOW = datetime.now(timezone.utc)

# Standard marine weather fixtures for Mumbai / Konkan coast
WEATHER_FIXTURES: List[Evidence] = [
    make_evidence(
        metric="wave_height",
        value=1.4,
        unit="m",
        source="Open-Meteo",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=6),
        confidence=0.90,
        authority_level="external_forecast",
        mode="DEMO",
    ),
    make_evidence(
        metric="wind_speed",
        value=22.0,
        unit="kmph",
        source="Open-Meteo",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=6),
        confidence=0.88,
        authority_level="external_forecast",
        mode="DEMO",
    ),
    make_evidence(
        metric="wind_gusts",
        value=32.0,
        unit="kmph",
        source="Open-Meteo",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=6),
        confidence=0.85,
        authority_level="external_forecast",
        mode="DEMO",
    ),
    make_evidence(
        metric="visibility",
        value=9.5,
        unit="km",
        source="Open-Meteo",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=6),
        confidence=0.92,
        authority_level="external_forecast",
        mode="DEMO",
    ),
    make_evidence(
        metric="sea_surface_temp",
        value=28.4,
        unit="C",
        source="INCOIS",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=12),
        confidence=0.94,
        authority_level="official_forecast",
        mode="DEMO",
    ),
]

# Official advisories (AdvisoryConstraint objects)
ADVISORY_FIXTURES: List[AdvisoryConstraint] = [
    AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO",
        named_region="North Maharashtra Coast",
        severity="HIGH",
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=24),
        source_text="Squally weather with wind speeds reaching 45-55 kmph gusting to 65 kmph likely over North Maharashtra coast. Fishermen are advised not to venture into deep sea.",
        source_reference="IMD-MUM-BULLETIN-20260910",
        confidence=0.94,
    ),
    AdvisoryConstraint(
        authority="INCOIS",
        constraint_type="CAUTION",
        named_region="South Gujarat Coast",
        severity="MODERATE",
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=18),
        source_text="High swell waves in the range of 2.0 - 2.5 meters are forecasted during 17:30 hours on 10-09-2026 to 23:30 hours on 11-09-2026.",
        source_reference="INCOIS-SWELL-SURGE-0910",
        confidence=0.91,
    ),
]

# Potential Fishing Zone (PFZ) fixtures
PFZ_FIXTURES: List[Evidence] = [
    make_evidence(
        metric="pfz_zone",
        value={
            "zone_id": "PFZ-MH-01",
            "name": "Off Sassoon Dock - Shallow Ridge",
            "potential": "HIGH",
            "bearing_deg": 245,
            "distance_km": 18.5,
            "target_species": ["Mackerel", "Sardinella"],
            "coordinates": {"lat": 18.82, "lon": 72.68},
        },
        source="INCOIS",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=24),
        confidence=0.92,
        authority_level="official_forecast",
        mode="DEMO",
    ),
    make_evidence(
        metric="pfz_zone",
        value={
            "zone_id": "PFZ-MH-02",
            "name": "Alibaug Outer Trench",
            "potential": "MEDIUM",
            "bearing_deg": 210,
            "distance_km": 28.0,
            "target_species": ["Pomfret", "Ribbonfish"],
            "coordinates": {"lat": 18.65, "lon": 72.72},
        },
        source="INCOIS",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=24),
        confidence=0.88,
        authority_level="official_forecast",
        mode="DEMO",
    ),
]

# GDACS Cyclone alerts
CYCLONE_FIXTURES: List[Evidence] = [
    make_evidence(
        metric="cyclone_alert",
        value={
            "system_name": "Tropical Depression ARB-02",
            "alert_level": "green",
            "center_lat": 16.5,
            "center_lon": 68.2,
            "distance_km": 420.0,
            "wind_speed_kmh": 45.0,
        },
        source="GDACS",
        observed_at=NOW,
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=12),
        confidence=0.95,
        authority_level="official_advisory",
        mode="DEMO",
    ),
]
