"""LangGraph node implementations for the ORCA 2.0 pipeline.

Nodes wrap existing battle-tested agents and enforce:
  1. Universal Evidence_v2 contract.
  2. Authority/Conflict Resolution policy.
  3. Deterministic Safety Floors in the Constraint Engine.
  4. Separate Trip Economics computation.
  5. Multilingual LLM narrative explanation.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from ..agents import (
    cyclone_agent,
    gis_agent,
    intent_agent,
    ocean_agent,
    pfz_agent,
    risk_agent,
    route_agent,
    weather_agent,
)
from ..config import RISK, TRIP_ECONOMICS, ROUTE_SCORING, get_data_mode
from ..data.geo import DEFAULT_PORT
from ..schemas import Location
from ..schemas_v2 import (
    AdvisoryConstraint,
    DecisionState,
    Evidence,
    agent_result_to_evidence_list,
    make_evidence,
)
from ..services import risk_engine
from ..services.llm import complete_chat

log = logging.getLogger(__name__)

AUTHORITY_RANKS = {
    "official_advisory": 5,
    "official_forecast": 4,
    "external_forecast": 3,
    "derived": 2,
    "heuristic": 1,
}


def _trace_entry(agent: str, status: str, latency_ms: int, summary: str) -> dict:
    return {
        "agent": agent,
        "node_name": agent,
        "status": status,
        "latency_ms": latency_ms,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _get_location_obj(state) -> Location:
    loc = state.location or DEFAULT_PORT
    return Location(
        name=loc.get("name", DEFAULT_PORT["name"]),
        latitude=loc.get("lat", DEFAULT_PORT["lat"]),
        longitude=loc.get("lon", DEFAULT_PORT["lon"]),
        state=loc.get("state", DEFAULT_PORT["state"]),
    )


# --------------------------------------------------------------------------
# Node 1: Intent Node
# --------------------------------------------------------------------------
def intent_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    location_dict = state.location or {}
    lat = location_dict.get("lat") or location_dict.get("latitude")
    lon = location_dict.get("lon") or location_dict.get("longitude")
    loc_name = location_dict.get("name", "")

    intent_res = intent_agent.run(
        state.raw_query,
        language=state.language,
        latitude=lat,
        longitude=lon,
        location_name=loc_name,
    )
    data = intent_res.data or {}
    
    loc = data.get("location")
    if not loc:
        resolved_loc = {
            "name": DEFAULT_PORT["name"],
            "lat": DEFAULT_PORT["lat"],
            "lon": DEFAULT_PORT["lon"],
            "state": DEFAULT_PORT["state"],
        }
    else:
        resolved_loc = {
            "name": loc.get("name", DEFAULT_PORT["name"]),
            "lat": loc.get("latitude", DEFAULT_PORT["lat"]),
            "lon": loc.get("longitude", DEFAULT_PORT["lon"]),
            "state": loc.get("state", DEFAULT_PORT["state"]),
        }

    raw_intent = str(data.get("intent", "operational")).lower()
    intent_type = "analytical" if "analysis" in raw_intent or "overview" in raw_intent else "operational"

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "location": resolved_loc,
        "intent": intent_type,
        "trace": [_trace_entry("intent", "ok", latency, f"Intent: {intent_type} @ {resolved_loc['name']}")],
    }


# --------------------------------------------------------------------------
# Parallel Specialist Nodes: Weather, Ocean, PFZ, Cyclone, GIS
# --------------------------------------------------------------------------
def weather_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)
    res = weather_agent.run(loc, when)
    evidences = agent_result_to_evidence_list(res)
    latency = int((time.perf_counter() - start) * 1000)
    return {
        "evidence": evidences,
        "trace": [_trace_entry("weather", "ok" if res.ok else "failed", latency, f"{len(evidences)} weather metrics retrieved")],
    }


def ocean_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)
    res = ocean_agent.run(loc, when)
    evidences = agent_result_to_evidence_list(res)
    latency = int((time.perf_counter() - start) * 1000)
    return {
        "evidence": evidences,
        "trace": [_trace_entry("ocean", "ok" if res.ok else "failed", latency, f"{len(evidences)} ocean metrics retrieved")],
    }


def pfz_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)
    res = pfz_agent.run(loc, when)
    evidences = agent_result_to_evidence_list(res)
    
    zones = res.data.get("zones", [])
    now = datetime.now(timezone.utc)
    for z in zones:
        evidences.append(
            make_evidence(
                metric="pfz_zone",
                value=z,
                source="INCOIS",
                confidence=0.92,
                authority_level="official_forecast",
                mode=get_data_mode(),
                observed_at=now,
            )
        )

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "evidence": evidences,
        "trace": [_trace_entry("pfz", "ok" if res.ok else "failed", latency, f"{len(zones)} PFZ zones discovered")],
    }


def cyclone_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)
    res = cyclone_agent.run(loc, when)
    evidences = agent_result_to_evidence_list(res)
    
    advisories = []
    if res.data.get("active"):
        headline = res.data.get("headline", "Severe weather warning")
        adv = AdvisoryConstraint(
            authority="IMD",
            constraint_type="NO_GO",
            named_region=loc.name or "Coastal Waters",
            severity="SEVERE",
            valid_from=when,
            valid_until=when,
            source_text=headline,
            source_reference="IMD-CYCLONE-ALERT",
            confidence=0.95,
        )
        advisories.append(adv)

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "evidence": evidences,
        "advisories": advisories,
        "trace": [_trace_entry("cyclone", "ok" if res.ok else "failed", latency, res.data.get("headline", "No warning"))],
    }


def gis_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)
    res = gis_agent.run(loc, when)
    # agent_result_to_evidence_list only converts measurements{}; GIS agent has
    # none, so we must explicitly store the GIS scalars as Evidence records so
    # constraint_engine_node can pass them to risk_engine.assess().
    evidences = agent_result_to_evidence_list(res)
    now = datetime.now(timezone.utc)
    gis_fields = {
        "distance_from_shore_km": (res.data.get("distance_from_shore_km"), "km"),
        "nearest_zone_km": (res.data.get("nearest_zone_km"), "km"),
        "inside_restricted_zone": (bool(res.data.get("inside_restricted_zone", False)), "bool"),
    }
    for metric, (value, unit) in gis_fields.items():
        if value is not None:
            evidences.append(
                make_evidence(
                    metric=metric,
                    value=value,
                    unit=unit,
                    source="ORCA_GIS",
                    confidence=0.90,
                    authority_level="derived",
                    mode=get_data_mode(),
                    observed_at=now,
                )
            )
    latency = int((time.perf_counter() - start) * 1000)
    return {
        "evidence": evidences,
        "trace": [_trace_entry("gis", "ok" if res.ok else "failed", latency, f"Distance offshore: {res.data.get('distance_from_shore_km')} km")],
    }


# --------------------------------------------------------------------------
# Node 3: Evidence Store Node
# --------------------------------------------------------------------------
def evidence_store_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    latency = int((time.perf_counter() - start) * 1000)
    return {
        "trace": [_trace_entry("evidence_store", "ok", latency, f"Stored {len(state.evidence)} evidence records")],
    }


# --------------------------------------------------------------------------
# Node 4: Conflict Resolver Node
# --------------------------------------------------------------------------
def conflict_resolver_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    from ..services.conflict_resolver import resolve_conflicts
    reconciled_evidences, new_conflicts = resolve_conflicts(state.evidence)
    latency = int((time.perf_counter() - start) * 1000)
    return {
        "conflict_log": new_conflicts,
        "trace": [_trace_entry("conflict_resolver", "ok", latency, f"Resolved {len(new_conflicts)} metric conflict(s)")],
    }


# --------------------------------------------------------------------------
# Node 5: Constraint Engine Node (Risk + Deterministic Floors)
# --------------------------------------------------------------------------
def _build_cyclone_alerts_for_risk_engine(advisories: Sequence[AdvisoryConstraint]) -> List[Dict]:
    """Convert v2 AdvisoryConstraint objects into the dict format risk_engine._alert_factor() expects."""
    alerts = []
    severity_map = {"SEVERE": "severe", "HIGH": "high", "MODERATE": "moderate", "LOW": "low"}
    for adv in advisories:
        alerts.append({
            "severity": severity_map.get(adv.severity, "moderate"),
            "official": True,  # all v2 AdvisoryConstraints come from official sources
            "headline": adv.source_text or f"{adv.authority} {adv.constraint_type}",
            "source": adv.authority,
            "type": "fishermen_warning" if adv.constraint_type == "CAUTION" else "no_go_advisory",
        })
    return alerts


def constraint_engine_node(state) -> Dict[str, Any]:
    """Compute risk score using the canonical risk_engine.assess() — same model as the v1 chat path.

    This replaces the earlier inline simplified formula (which only used wave + wind and
    hardcoded ocean/weather/cyclone weights) with the full calibrated breakpoint-curve model,
    ensuring /plan and /api/chat produce consistent scores for identical conditions.
    The deterministic safety floors in risk_engine.assess() are preserved unchanged.
    """
    start = time.perf_counter()
    now = datetime.now(timezone.utc)

    # Build a flat metric → value lookup from all collected evidence.
    # Metric names match what each specialist agent stores in its measurements{}:
    #   weather_node  → wave_height (ocean agent), wind_speed, rain_probability, visibility
    #   ocean_node    → wave_height, wave_period, sst  (note: no current — ocean agent omits it)
    #   gis_node      → distance_from_shore_km, nearest_zone_km, inside_restricted_zone  (explicit)
    ev_map: Dict[str, Any] = {e.metric: e.value for e in state.evidence}

    # --- pull the inputs risk_engine.assess() needs ---
    wave_height_m: Optional[float] = (
        float(ev_map["wave_height"]) if "wave_height" in ev_map else None
    )
    wave_period_s: Optional[float] = (
        float(ev_map["wave_period"]) if "wave_period" in ev_map else None
    )
    wind_speed_kmh: Optional[float] = (
        float(ev_map["wind_speed"]) if "wind_speed" in ev_map else None
    )
    rain_probability_pct: Optional[float] = (
        float(ev_map["rain_probability"]) if "rain_probability" in ev_map else None
    )
    lightning: bool = bool(ev_map.get("lightning", False))
    visibility_km: Optional[float] = (
        float(ev_map["visibility"]) if "visibility" in ev_map else None
    )
    # sea_state label and current: ocean agent omits measurements for these but
    # stores them in data{}. They are not in evidence; pass None and the engine
    # uses its documented defaults (sea_state="moderate", current=0 → low contribution).
    sea_state_label: Optional[str] = None
    current_speed_ms: Optional[float] = None

    # GIS — explicitly stored by gis_node above
    distance_from_shore_km: Optional[float] = (
        float(ev_map["distance_from_shore_km"]) if "distance_from_shore_km" in ev_map else None
    )
    nearest_zone_km: Optional[float] = (
        float(ev_map["nearest_zone_km"]) if "nearest_zone_km" in ev_map else None
    )
    inside_zone: bool = bool(ev_map.get("inside_restricted_zone", False))

    # Cyclone / official advisories — convert AdvisoryConstraints to the alert-dict format
    cyclone_alerts = _build_cyclone_alerts_for_risk_engine(state.advisories)

    # Collect unique source strings for the RiskAssessment.sources list
    sources = list(dict.fromkeys(e.source for e in state.evidence if e.source))

    # Delegate to the canonical risk engine (full breakpoint-curve model + deterministic floors)
    assessment = risk_engine.assess(
        wave_height_m=wave_height_m,
        wave_period_s=wave_period_s,
        wind_speed_kmh=wind_speed_kmh,
        rain_probability_pct=rain_probability_pct,
        lightning=lightning,
        visibility_km=visibility_km,
        sea_state_label=sea_state_label,
        current_speed_ms=current_speed_ms,
        alerts=cyclone_alerts,
        distance_from_shore_km=distance_from_shore_km,
        nearest_zone_km=nearest_zone_km,
        inside_zone=inside_zone,
        sources=sources,
        mode=get_data_mode(),
        generated_at=now.isoformat(),
    )

    score = float(assessment.score)
    official_no_go = assessment.official_warning

    # Build human-readable reasons from the engine's factor breakdown + overrides
    reasons: List[str] = []
    for factor in assessment.factors:
        if factor.contribution >= 5.0:  # only report factors that meaningfully contribute
            reasons.append(f"{factor.label}: {factor.detail} (impact +{factor.contribution:.0f})")
    for override in assessment.overrides:
        reasons.append(f"Safety Override: {override}")
    if not reasons:
        wave_str = f"{wave_height_m:.1f}m" if wave_height_m is not None else "unknown"
        wind_str = f"{wind_speed_kmh:.0f} km/h" if wind_speed_kmh is not None else "unknown"
        reasons.append(f"Marine conditions assessed: Wave {wave_str}, Wind {wind_str}")

    # Determine operational status from the engine's category + low-confidence advisory check
    has_low_conf_advisory = any(adv.confidence < 0.70 for adv in state.advisories)
    cat = assessment.category  # "LOW" | "MODERATE" | "HIGH" | "EXTREME"

    if has_low_conf_advisory and not official_no_go and score < 70:
        status = "INSUFFICIENT_EVIDENCE"
        reasons.append("Uncertain advisory parse: Confidence < 0.70 requires operator verification")
    elif cat in ("HIGH", "EXTREME") or official_no_go:
        status = "UNSAFE"
    elif cat == "MODERATE":
        status = "CAUTION"
    else:
        status = "SAFE"

    decision = DecisionState(
        status=status,
        risk_score=round(score, 1),
        reasons=reasons,
        active_advisories=state.advisories,
        language=state.language,
        explanation="",
        generated_at=now,
    )

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "decision": decision,
        "trace": [_trace_entry("constraint_engine", "ok", latency, f"Status: {status} (Score {score:.1f})")],
    }


# --------------------------------------------------------------------------
# Node 6: Route & Economics Node
# --------------------------------------------------------------------------
def _pfz_potential_from_chlorophyll(chl: Optional[float]) -> str:
    """Map chlorophyll concentration (mg/m³) to a PFZ catch-potential label.

    Thresholds calibrated to the INCOIS chlorophyll-front methodology:
      ≥ 1.20 → HIGH   (strong nutrient upwelling, dense forage aggregation)
      ≥ 0.60 → MEDIUM (moderate front, typical catch)
      < 0.60 → LOW    (weak signal, opportunistic fishing only)
    Falls back to MEDIUM (not HIGH) when chlorophyll is unavailable — avoids
    over-optimistic economics when data is missing.
    """
    if chl is None:
        return "MEDIUM"
    if chl >= 1.20:
        return "HIGH"
    if chl >= 0.60:
        return "MEDIUM"
    return "LOW"


def route_node(state) -> Dict[str, Any]:
    """Select the best PFZ target from evidence, plan a route, and compute trip economics.

    Fixes BE-001: reads latitude/longitude from the PFZ zone dict (the actual keys
    emitted by pfz_agent/demo_store) instead of the non-existent 'coordinates' key.
    Potential is derived from the zone's chlorophyll concentration.
    """
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)

    # Collect all PFZ zone evidence records (each .value is a PFZZone.model_dump() dict)
    pfz_evs = [
        e for e in state.evidence
        if e.metric == "pfz_zone" and isinstance(e.value, dict)
    ]

    target_dest: tuple
    target_potential: str
    destination_name: str

    if pfz_evs:
        # Pick the highest-confidence zone; fall back to first if confidence is absent/equal.
        best_ev = max(pfz_evs, key=lambda e: float(e.confidence or 0))
        z = best_ev.value

        # Read the actual coordinate keys from PFZZone.model_dump()
        z_lat = z.get("latitude")
        z_lon = z.get("longitude")

        if z_lat is not None and z_lon is not None:
            target_dest = (float(z_lat), float(z_lon))
        else:
            # PFZ record is present but coordinates missing — log a warning and use a
            # safe 0.15° seaward offset so the route is at least valid.
            log.warning(
                "route_node: pfz_zone evidence missing latitude/longitude keys — "
                "falling back to offset target. Zone keys: %s", list(z.keys())
            )
            target_dest = (loc.latitude + 0.15, loc.longitude + 0.15)

        target_potential = _pfz_potential_from_chlorophyll(z.get("chlorophyll_mg_m3"))
        zone_rank = z.get("rank", "?")
        destination_name = f"PFZ #{zone_rank} (rank-{zone_rank})"
    else:
        # No PFZ evidence at all — route to open water seaward of the port.
        # This can happen if all candidate zones were filtered out by the safety
        # filter in pfz_agent (e.g. all inside restricted areas).
        log.info("route_node: no pfz_zone evidence found — routing to seaward offset")
        target_dest = (loc.latitude + 0.15, loc.longitude + 0.15)
        target_potential = "MEDIUM"  # conservative default — not HIGH
        destination_name = "Open Water (no PFZ identified)"

    route_res = route_agent.run(
        loc,
        when,
        destination=target_dest,
        destination_name=destination_name,
    )

    distance_km = 32.0
    routes_list = route_res.data.get("options", [])
    if routes_list:
        distance_km = float(routes_list[0].get("distance_km", 32.0))

    fuel_rate = TRIP_ECONOMICS.fuel_rate_l_per_km
    fuel_price = TRIP_ECONOMICS.fuel_price_per_l
    fixed_prov = TRIP_ECONOMICS.fixed_provisions_estimate
    mkt_price = TRIP_ECONOMICS.avg_market_price_per_kg

    trip_cost = (distance_km * 2 * fuel_rate * fuel_price) + fixed_prov
    catch_kg = TRIP_ECONOMICS.catch_potential_kg.get(target_potential, 80.0)
    trip_revenue = catch_kg * mkt_price
    trip_value = trip_revenue - trip_cost

    economics = {
        "distance_km": round(distance_km, 1),
        "fuel_cost_inr": round(distance_km * 2 * fuel_rate * fuel_price, 0),
        "fixed_provisions_inr": fixed_prov,
        "total_cost_inr": round(trip_cost, 0),
        "estimated_catch_kg": catch_kg,
        "estimated_revenue_inr": round(trip_revenue, 0),
        "net_trip_value_inr": round(trip_value, 0),
        "basis": [
            f"Round-trip distance: {distance_km * 2:.1f} km @ {fuel_rate} L/km",
            f"Fuel: ₹{fuel_price}/L diesel benchmark",
            f"Catch estimate: {catch_kg}kg based on {target_potential} PFZ advisory potential",
            f"Landing center market price: ₹{mkt_price}/kg average",
        ],
    }

    route_payload = {
        "safe_port": {"name": loc.name or DEFAULT_PORT["name"], "lat": loc.latitude, "lon": loc.longitude},
        "distance_km": distance_km,
        "options": routes_list,
    }

    decision = state.decision
    if decision:
        decision = decision.model_copy(update={"route": route_payload, "trip_economics": economics})

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "decision": decision,
        "trace": [_trace_entry("route", "ok", latency, f"Route: {distance_km}km, Trip value: ₹{trip_value:,.0f}")],
    }


# --------------------------------------------------------------------------
# Node 7: Explanation Node
# --------------------------------------------------------------------------
def explanation_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    decision = state.decision

    if not decision:
        return {"trace": []}

    facts = {
        "user_query": state.raw_query,
        "status": decision.status,
        "risk_score": decision.risk_score,
        "reasons": decision.reasons,
        "location": state.location.get("name") if state.location else "Coast",
        "trip_economics": decision.trip_economics,
        "go": decision.status == "SAFE",
    }

    system_prompt = (
        "You are ORCA 2.0 marine safety advisor for fishers in India. "
        "Provide a clear, respectful, authoritative 2-3 sentence summary of whether it is safe "
        f"to venture out, and the economic potential. Language: {state.language}."
    )
    user_prompt = f"Decision Facts:\n{facts}"

    explanation_text, provider = complete_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
        max_tokens=300,
        fallback_to_template=True,
    )

    if provider == "template":
        explanation_text = (
            f"ORCA Safety Advisory: Conditions are assessed as {decision.status} "
            f"(Risk score {decision.risk_score}/100). "
            f"Primary reason: {decision.reasons[0] if decision.reasons else 'Normal sea conditions'}."
        )

    updated_decision = decision.model_copy(update={"explanation": explanation_text})

    latency = int((time.perf_counter() - start) * 1000)
    return {
        "decision": updated_decision,
        "trace": [_trace_entry("explanation", "ok", latency, f"Generated summary via {provider}")],
    }
