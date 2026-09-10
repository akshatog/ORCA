"""Streaming chat endpoint — SSE agent-by-agent progress + final answer."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..agents import (cyclone_agent, explanation_agent, gis_agent,
                      intent_agent, ocean_agent, pfz_agent, risk_agent,
                      route_agent, weather_agent)
from ..agents.planner import _SESSIONS, _target_datetime, _trace, AGENT_SUMMARY
from ..config import get_data_mode
from ..schemas import (AgentTrace, ChatRequest, ChatResponse, Evidence,
                       GeofenceAlert, Intent, Location, PFZZone,
                       RiskAssessment, RouteOption)

router = APIRouter(prefix="/api", tags=["chat-stream"])


def _event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


AGENT_LABELS = {
    "intent":      "Intent Agent",
    "weather":     "Weather Agent",
    "ocean":       "Ocean Agent",
    "pfz":         "PFZ Agent",
    "cyclone":     "Cyclone Agent",
    "gis":         "GIS Agent",
    "risk":        "Risk Agent",
    "route":       "Route Agent",
    "explanation": "Explanation Agent",
}

THINKING_STEPS = {
    "intent":      "Parsing your question...",
    "specialists": "Gathering marine data concurrently...",
    "risk":        "Scoring the risk...",
    "route":       "Planning the safest route...",
    "explanation": "Composing the answer...",
}


def _stream(req: ChatRequest):
    started = time.perf_counter()

    # node 1: intent
    yield _event("thinking", {"step": THINKING_STEPS["intent"], "agent": "intent"})
    previous = _SESSIONS.get(req.session_id)
    intent_res = intent_agent.run(
        req.message, language=req.language, latitude=req.latitude,
        longitude=req.longitude, location_name=req.location_name,
        previous=previous,
    )
    intent = Intent(**intent_res.data)
    if intent.location is None:
        from ..data.geo import DEFAULT_PORT
        intent.location = Location(
            name=DEFAULT_PORT["name"], latitude=DEFAULT_PORT["lat"],
            longitude=DEFAULT_PORT["lon"], state=DEFAULT_PORT["state"],
        )
        intent.location_text = DEFAULT_PORT["name"]
    _SESSIONS[req.session_id] = intent

    try:
        summary = AGENT_SUMMARY["intent"](intent_res.data or {})
    except Exception:
        summary = ""
    yield _event("agent_done", {
        "agent": "intent", "label": AGENT_LABELS["intent"],
        "summary": summary, "status": "ok" if intent_res.ok else "failed",
    })

    location = intent.location
    from ..data.demo_store import IST, now_ist
    from datetime import datetime
    base = now_ist()
    try:
        y, m, d = (int(x) for x in (intent.date or base.date().isoformat()).split("-"))
        hh, mm = (int(x) for x in (intent.time or "06:00").split(":"))
        when = datetime(y, m, d, hh, mm, tzinfo=IST)
    except Exception:
        when = base
    needs = set(intent.needs)
    trace = [_trace(intent_res, "intent")]
    agents: dict = {}

    # node 2: parallel specialists
    yield _event("thinking", {"step": THINKING_STEPS["specialists"], "agent": "specialists"})
    job_map = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        if "weather" in needs:
            job_map["weather"] = pool.submit(weather_agent.run, location, when)
        if "ocean" in needs:
            job_map["ocean"] = pool.submit(ocean_agent.run, location, when)
        if "pfz" in needs:
            job_map["pfz"] = pool.submit(pfz_agent.run, location, when)
        if "cyclone" in needs:
            job_map["cyclone"] = pool.submit(cyclone_agent.run, location, when)
        if "gis" in needs:
            job_map["gis"] = pool.submit(gis_agent.run, location, when)

        for fut in as_completed(job_map.values()):
            name = next(n for n, f in job_map.items() if f is fut)
            res = fut.result()
            agents[name] = res
            trace.append(_trace(res, name))
            try:
                s = AGENT_SUMMARY.get(name, lambda d: "")(res.data or {})
            except Exception:
                s = ""
            yield _event("agent_done", {
                "agent": name, "label": AGENT_LABELS.get(name, name),
                "summary": s, "status": "ok" if res.ok else "failed",
            })

    def _d(k): return agents[k].data if k in agents and agents[k].ok else {}
    weather_d = _d("weather"); ocean_d = _d("ocean")
    cyclone_d = _d("cyclone"); gis_d = _d("gis")
    sources = [r.source for r in agents.values() if r.ok]
    mode = "LIVE" if any(r.mode == "LIVE" for r in agents.values()) else get_data_mode()
    if mode not in ("LIVE", "DEMO", "CACHE"):
        mode = "DEMO"

    # node 3: risk
    risk = None
    if "risk" in needs:
        yield _event("thinking", {"step": THINKING_STEPS["risk"], "agent": "risk"})
        risk_res = risk_agent.run(location, when, weather=weather_d, ocean=ocean_d,
                                  cyclone=cyclone_d, gis=gis_d, sources=sources, mode=mode)
        agents["risk"] = risk_res
        trace.append(_trace(risk_res, "risk"))
        if risk_res.ok:
            risk = RiskAssessment(**risk_res.data)
        try:
            s = AGENT_SUMMARY["risk"](risk_res.data or {})
        except Exception:
            s = ""
        yield _event("agent_done", {
            "agent": "risk", "label": AGENT_LABELS["risk"],
            "summary": s, "status": "ok" if risk_res.ok else "failed",
        })

    # node 4: pfz + route
    pfz_zones = []
    if "pfz" in agents and agents["pfz"].ok:
        pfz_zones = [PFZZone(**z) for z in agents["pfz"].data.get("zones", [])]

    routes = []
    if "route" in needs and pfz_zones:
        yield _event("thinking", {"step": THINKING_STEPS["route"], "agent": "route"})
        tgt = pfz_zones[0]
        route_res = route_agent.run(location, when,
                                    destination=(tgt.latitude, tgt.longitude),
                                    destination_name=f"PFZ #{tgt.rank}",
                                    ocean=ocean_d, weather=weather_d,
                                    risk=(risk.model_dump() if risk else {}))
        agents["route"] = route_res
        trace.append(_trace(route_res, "route"))
        if route_res.ok:
            routes = [RouteOption(**o) for o in route_res.data.get("options", [])]
        try:
            s = AGENT_SUMMARY["route"](route_res.data or {})
        except Exception:
            s = ""
        yield _event("agent_done", {
            "agent": "route", "label": AGENT_LABELS["route"],
            "summary": s, "status": "ok" if route_res.ok else "failed",
        })

    # node 5: explanation
    yield _event("thinking", {"step": THINKING_STEPS["explanation"], "agent": "explanation"})
    geofence = [GeofenceAlert(**a) for a in gis_d.get("geofence_alerts", [])]
    expl_res = explanation_agent.run(
        intent=intent, risk=risk, pfz=pfz_zones, routes=routes, geofence=geofence,
        weather=weather_d, ocean=ocean_d, cyclone=cyclone_d, gis=gis_d,
        agents=agents, mode=mode, when=when,
    )
    trace.append(_trace(expl_res, "explanation"))
    yield _event("agent_done", {
        "agent": "explanation", "label": AGENT_LABELS["explanation"],
        "summary": "Answer composed", "status": "ok",
    })

    # final response
    evidence = [Evidence(**e) for e in expl_res.data.get("evidence", [])]
    response = ChatResponse(
        session_id=req.session_id,
        language=intent.language,
        answer=expl_res.data.get("answer", ""),
        intent=intent, risk=risk, pfz=pfz_zones, routes=routes, geofence=geofence,
        alerts=cyclone_d.get("alerts", []),
        evidence=evidence, trace=trace,
        suggestions=expl_res.data.get("suggestions", []),
        mode=mode,
        disclaimer=expl_res.data.get("disclaimer", ""),
        explanation_source=expl_res.data.get("explanation_source", "template"),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
    yield _event("done", json.loads(response.model_dump_json()))


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """SSE: yields agent events one by one, then the full response."""
    return StreamingResponse(
        _stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
