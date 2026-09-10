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
from typing import Any, Dict, List, Optional

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
    evidences = agent_result_to_evidence_list(res)
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
def constraint_engine_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    now = datetime.now(timezone.utc)

    # Extract readings
    ev_map: Dict[str, Any] = {e.metric: e.value for e in state.evidence}

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

    reasons: List[str] = [
        f"Base marine condition: Wave {wave:.1f}m, Wind {wind:.0f} km/h",
    ]

    score = raw_score
    official_no_go = False

    for adv in state.advisories:
        if adv.constraint_type == "NO_GO":
            official_no_go = True
            score = max(score, float(RISK.severe_warning_floor))
            reasons.append(f"Official Warning ({adv.authority}): {adv.source_text}")
        elif adv.constraint_type == "CAUTION":
            score = max(score, float(RISK.fishermen_warning_floor))
            reasons.append(f"Caution Bulletin ({adv.authority}): {adv.source_text}")

    if wave >= RISK.wave_danger_m:
        score = max(score, float(RISK.wave_danger_floor))
        reasons.append(f"Safety Floor: Wave height {wave:.1f}m exceeds danger threshold ({RISK.wave_danger_m}m)")

    if wind >= RISK.wind_danger_kmh:
        score = max(score, float(RISK.wind_danger_floor))
        reasons.append(f"Safety Floor: Wind speed {wind:.0f} km/h reaches gale force ({RISK.wind_danger_kmh} km/h)")

    if restricted:
        score = max(score, float(RISK.restricted_zone_floor))
        reasons.append("Safety Floor: Vessel in vicinity of restricted zone")

    has_low_conf_advisory = any(adv.confidence < 0.70 for adv in state.advisories)

    cat = RISK.categorise(score)
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
def route_node(state) -> Dict[str, Any]:
    start = time.perf_counter()
    loc = _get_location_obj(state)
    when = datetime.now(timezone.utc)

    pfz_evs = [e for e in state.evidence if e.metric == "pfz_zone" and isinstance(e.value, dict)]
    target_potential = "HIGH"

    if pfz_evs:
        z = pfz_evs[0].value
        coords = z.get("coordinates", {})
        target_dest = (coords.get("lat", loc.latitude + 0.15), coords.get("lon", loc.longitude + 0.15))
        target_potential = z.get("potential", "HIGH")
    else:
        target_dest = (loc.latitude + 0.15, loc.longitude + 0.15)

    route_res = route_agent.run(
        loc,
        when,
        destination=target_dest,
        destination_name="Optimal PFZ Target",
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
