"""Alert engine for ORCA 2.0 active voyage monitoring.

Monitors incoming real-time evidence and official advisories against active voyages.
When marine conditions deteriorate (e.g. SAFE -> CAUTION or SAFE -> UNSAFE),
it calculates the nearest safe harbour and fires an AlertEvent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from ..config import RISK
from ..data.geo import haversine_km, nearest_port
from ..data.voyage_store import Voyage, get_active_voyages, get_voyage, update_voyage_decision
from ..schemas_v2 import AdvisoryConstraint, AlertEvent, DecisionState, Evidence

log = logging.getLogger(__name__)

# Severity hierarchy for status transitions
STATUS_RANK = {
    "SAFE": 0,
    "INSUFFICIENT_EVIDENCE": 1,
    "CAUTION": 2,
    "UNSAFE": 3,
}


def _evaluate_voyage_conditions(
    voyage: Voyage,
    evidences: Sequence[Evidence],
    advisories: Sequence[AdvisoryConstraint],
) -> tuple[str, float, List[str], Optional[str]]:
    """Evaluate new status and risk score for a single voyage.

    Returns: (new_status, risk_score, reasons, primary_deterioration_reason)
    """
    now = datetime.now(timezone.utc)
    ev_map = {e.metric: e.value for e in evidences}

    wave = float(ev_map.get("wave_height", 1.2)) if "wave_height" in ev_map else 1.2
    wind = float(ev_map.get("wind_speed", 20.0)) if "wind_speed" in ev_map else 20.0
    restricted = bool(ev_map.get("inside_restricted_zone", False))

    weights = RISK.weights
    norm_wave = min(1.0, wave / 4.0)
    norm_wind = min(1.0, wind / 60.0)
    norm_gis = 1.0 if restricted else 0.1
    norm_ocean = 0.2
    norm_weather = 0.15
    norm_cyclone = 0.0

    raw_score = (
        norm_wave * weights.get("wave", 0.25)
        + norm_wind * weights.get("wind", 0.20)
        + norm_gis * weights.get("gis", 0.10)
        + norm_ocean * weights.get("ocean", 0.10)
        + norm_weather * weights.get("weather", 0.10)
        + norm_cyclone * weights.get("cyclone", 0.25)
    ) * 100.0

    score = raw_score
    reasons: List[str] = []
    primary_reason: Optional[str] = None
    official_no_go = False

    # 1. Check advisories
    for adv in advisories:
        if adv.constraint_type == "NO_GO" or adv.severity in ("SEVERE", "HIGH"):
            official_no_go = True
            score = max(score, float(RISK.severe_warning_floor))
            reason_text = f"Official Severe Advisory ({adv.authority}): {adv.source_text}"
            reasons.append(reason_text)
            if not primary_reason:
                primary_reason = reason_text
        elif adv.constraint_type == "CAUTION" or adv.severity == "MODERATE":
            score = max(score, float(RISK.fishermen_warning_floor))
            reason_text = f"Caution Bulletin ({adv.authority}): {adv.source_text}"
            reasons.append(reason_text)
            if not primary_reason:
                primary_reason = reason_text

    # 2. Check deterministic safety thresholds
    if wave >= RISK.wave_danger_m:
        score = max(score, float(RISK.wave_danger_floor))
        reason_text = f"Wave height {wave:.1f}m exceeds danger threshold ({RISK.wave_danger_m}m)"
        reasons.append(reason_text)
        if not primary_reason:
            primary_reason = reason_text

    if wind >= RISK.wind_danger_kmh:
        score = max(score, float(RISK.wind_danger_floor))
        reason_text = f"Wind speed {wind:.0f} km/h reaches gale force ({RISK.wind_danger_kmh} km/h)"
        reasons.append(reason_text)
        if not primary_reason:
            primary_reason = reason_text

    if restricted:
        score = max(score, float(RISK.restricted_zone_floor))
        reason_text = "Vessel in vicinity of restricted maritime zone"
        reasons.append(reason_text)
        if not primary_reason:
            primary_reason = reason_text

    cat = RISK.categorise(score)
    if cat in ("HIGH", "EXTREME") or official_no_go or score >= 75.0:
        new_status = "UNSAFE"
    elif cat == "MODERATE" or score >= 45.0:
        new_status = "CAUTION"
    else:
        new_status = "SAFE"

    if not primary_reason:
        primary_reason = reasons[0] if reasons else f"Risk score increased to {score:.0f}"

    return new_status, round(score, 1), reasons, primary_reason


def on_evidence_change(
    new_evidence: Optional[Sequence[Union[Evidence, AdvisoryConstraint]]] = None,
    new_advisories: Optional[Sequence[AdvisoryConstraint]] = None,
) -> List[AlertEvent]:
    """Re-evaluate risk and safety constraints for all active voyages.

    If conditions degrade (e.g. SAFE -> CAUTION or SAFE -> UNSAFE), produces an AlertEvent
    with the nearest safe emergency port and updates the voyage's DecisionState.
    """
    evidences: List[Evidence] = []
    advisories: List[AdvisoryConstraint] = list(new_advisories or [])

    if new_evidence:
        for item in new_evidence:
            if isinstance(item, AdvisoryConstraint):
                advisories.append(item)
            elif isinstance(item, Evidence):
                evidences.append(item)

    active_voyages = get_active_voyages()
    if not active_voyages:
        log.debug("No active voyages to evaluate for evidence change.")
        return []

    alerts: List[AlertEvent] = []
    now = datetime.now(timezone.utc)

    for voyage in active_voyages:
        prev_status = voyage.last_decision.status if voyage.last_decision else "SAFE"
        new_status, score, reasons, primary_reason = _evaluate_voyage_conditions(
            voyage, evidences, advisories
        )

        prev_rank = STATUS_RANK.get(prev_status, 0)
        new_rank = STATUS_RANK.get(new_status, 0)

        # Trigger alert if conditions deteriorated
        if new_rank > prev_rank:
            lat = float(voyage.location.get("lat", 18.92))
            lon = float(voyage.location.get("lon", 72.83))
            port = nearest_port(lat, lon)
            dist_km = round(haversine_km((lat, lon), (port["lat"], port["lon"])), 1)

            safe_port = {
                "name": port["name"],
                "lat": port["lat"],
                "lon": port["lon"],
                "distance_km": dist_km,
            }

            alert = AlertEvent(
                voyage_id=voyage.voyage_id,
                previous_status=prev_status,
                new_status=new_status,
                reason=primary_reason or "Marine conditions degraded",
                safe_port=safe_port,
                triggered_at=now,
            )
            alerts.append(alert)

            # Update voyage state with updated decision
            lang = voyage.last_decision.language if voyage.last_decision else "en"
            updated_decision = DecisionState(
                status=new_status,  # type: ignore[arg-type]
                risk_score=score,
                reasons=reasons,
                active_advisories=advisories,
                language=lang,
                explanation=f"ALERT: {primary_reason}. Recommend immediate return to {safe_port['name']} ({dist_km} km).",
                generated_at=now,
                route={"safe_port": safe_port["name"], "distance_km": dist_km},
            )
            update_voyage_decision(voyage.voyage_id, updated_decision)
            log.warning(
                "Alert fired for voyage %s: %s -> %s (Reason: %s)",
                voyage.voyage_id,
                prev_status,
                new_status,
                primary_reason,
            )

    return alerts


def trigger_manual_alert(
    voyage_id: Optional[str] = None,
    advisory: Optional[AdvisoryConstraint] = None,
    headline: str = "Severe weather warning issued",
    severity: str = "SEVERE",
) -> List[AlertEvent]:
    """Helper to trigger an alert manually (e.g. from an API call or simulation)."""
    adv = advisory or AdvisoryConstraint(
        authority="IMD",
        constraint_type="NO_GO" if severity in ("SEVERE", "HIGH") else "CAUTION",
        named_region="Coastal Waters",
        severity=severity,  # type: ignore[arg-type]
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc),
        source_text=headline,
        source_reference="MANUAL-ALERT-TRIGGER",
        confidence=1.0,
    )

    if voyage_id:
        voyage = get_voyage(voyage_id)
        if not voyage or voyage.status != "ACTIVE":
            return []
        return on_evidence_change(new_advisories=[adv])
    else:
        return on_evidence_change(new_advisories=[adv])
