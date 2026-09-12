"""Potential Fishing Zone agent.

WHAT PFZ MEANS (we say this on stage, because it is the single most likely
"gotcha" question): a PFZ is not a fish detector. INCOIS derives PFZ advisories
from sea-surface-temperature fronts and chlorophyll concentration — the physical
signature of nutrient upwelling where forage species, and therefore catch,
concentrate. ORCA reproduces that reasoning and ranks candidate zones. It never
claims to see fish.

LIVE mode: fetches real INCOIS TextData sector endpoints (SEC001–SEC008) via
           advisory_scraper.scrape_incois_pfz() and maps them to PFZZone objects.
DEMO mode: uses demo_store as before.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from ..data import demo_store
from ..data.geo import RESTRICTED_ZONES, point_in_polygon
from ..schemas import AgentResult, Location, PFZZone
from .base import live_enabled, timed


def _score(zone: dict) -> float:
    """Rank by front strength (chlorophyll) discounted by distance and sea state.

    When chlorophyll is None (INCOIS TextData does not provide it directly),
    fall back to distance-only scoring so live zones are still ranked sensibly.
    """
    chl = zone.get("chlorophyll_mg_m3") or 0.8  # conservative default if not provided
    distance = zone.get("distance_km") or 1.0
    wave = zone.get("wave_height_m") or 1.0
    return (chl * 1.6) - (distance / 45.0) - (wave * 0.25)


def _blocking_zone(lat: float, lon: float):
    """The restricted area containing this point, if any."""
    for zone in RESTRICTED_ZONES:
        if point_in_polygon((lat, lon), zone["polygon"]):
            return zone
    return None


def _incois_to_pfz_zone(raw: dict, rank: int, stamp: str) -> dict:
    """Convert an INCOIS scraper zone dict to the PFZZone-compatible format."""
    return {
        "zone_id": raw.get("zone_id", f"INCOIS-{rank:02d}"),
        "latitude": raw["latitude"],
        "longitude": raw["longitude"],
        "distance_km": raw.get("distance_km", 25.0),
        "bearing_deg": raw.get("bearing_deg"),
        "depth_m": raw.get("depth_m"),
        "wave_height_m": raw.get("wave_height_m"),
        "sst_c": raw.get("sst_c"),
        "chlorophyll_mg_m3": raw.get("chlorophyll_mg_m3"),
        "confidence": raw.get("confidence", 0.90),
        "source": raw.get("source", "INCOIS"),
        "source_type": raw.get("source_type", "official_bulletin"),
        "rank": rank,
        "timestamp": stamp,
    }


@timed
def run(location: Location, when: datetime, count: int = 3) -> AgentResult:
    stamp = when.isoformat(timespec="seconds")
    source = "DEMO"
    mode = "DEMO"
    raw: List[dict] = []

    if live_enabled():
        try:
            from ..data.advisory_scraper import scrape_incois_pfz
            live_zones = scrape_incois_pfz()
            if live_zones:
                raw = live_zones
                source = "INCOIS"
                mode = "LIVE"
        except Exception:
            pass

    # Fall back to demo store if live returned nothing
    if not raw:
        raw = demo_store.pfz_zones(
            location.latitude, location.longitude, location.name, when, count=count * 2
        )
        source = "DEMO"
        mode = "DEMO"

    # SAFETY FILTER: never recommend a fishing zone inside a restricted area.
    kept, excluded = [], []
    for z in raw:
        blocker = _blocking_zone(z["latitude"], z["longitude"])
        if blocker:
            excluded.append({
                "latitude": z["latitude"],
                "longitude": z["longitude"],
                "reason": blocker["name"],
                "zone_type": blocker["zone_type"],
            })
        else:
            kept.append(z)

    kept.sort(key=_score, reverse=True)
    kept = kept[:count]

    zones: List[PFZZone] = []
    for rank, z in enumerate(kept, start=1):
        formatted = _incois_to_pfz_zone(z, rank, stamp)
        zones.append(PFZZone(**{k: v for k, v in formatted.items() if k in PFZZone.model_fields}))

    return AgentResult(
        agent="pfz",
        ok=True,
        location=location,
        data={
            "zones": [z.model_dump() for z in zones],
            "excluded_zones": excluded,
            "excluded_count": len(excluded),
            "method": "SST front + chlorophyll concentration ranking (INCOIS methodology)",
            "safety_filter": "Candidate zones inside restricted maritime areas are removed.",
            "caveat": "Potential zone — indicates likelihood of fish aggregation, not a guarantee.",
        },
        source=source,
        timestamp=stamp,
        confidence=zones[0].confidence if zones else 0.0,
        mode=mode,  # type: ignore[arg-type]
    )
