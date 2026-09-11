"""Typed contracts shared by every ORCA agent.

Rule: agents never return prose. They return these structures, each carrying
provenance (value + unit + source + timestamp + confidence). The Explanation
agent is the only component allowed to turn them into sentences.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "mr", "ta", "te", "bn", "ml", "gu", "kn", "or"]
DataMode = Literal["LIVE", "DEMO", "CACHE"]
RiskCategory = Literal["LOW", "MODERATE", "HIGH", "EXTREME"]


class Provenance(BaseModel):
    """Attached to every factual number ORCA shows a user."""

    source: str
    timestamp: str
    mode: DataMode = "DEMO"
    confidence: Optional[float] = None
    note: Optional[str] = None


class Measurement(BaseModel):
    """A single traceable value."""

    value: Optional[float] = None
    unit: str = ""
    label: str = ""
    provenance: Provenance

    @property
    def known(self) -> bool:
        return self.value is not None


class Location(BaseModel):
    name: str = ""
    latitude: float
    longitude: float
    state: Optional[str] = None


class Intent(BaseModel):
    intent: str = "fishing_safety"
    activity: str = "fishing"
    location: Optional[Location] = None
    location_text: str = ""
    date: Optional[str] = None
    time: Optional[str] = None
    language: Language = "en"
    raw_query: str = ""
    needs: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Uniform envelope returned by every specialist agent."""

    agent: str
    ok: bool = True
    location: Optional[Location] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    measurements: Dict[str, Measurement] = Field(default_factory=dict)
    risk: Optional[float] = None          # 0..1 sub-risk for the risk engine
    unavailable: List[str] = Field(default_factory=list)
    source: str = "DEMO"
    timestamp: str = ""
    confidence: Optional[float] = None
    mode: DataMode = "DEMO"
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class RiskFactor(BaseModel):
    key: str
    label: str
    factor: float          # 0..1 normalised severity
    weight: float          # configured weight
    contribution: float    # points added to the 0-100 score
    detail: str = ""


class RiskAssessment(BaseModel):
    score: int
    category: RiskCategory
    factors: List[RiskFactor]
    overrides: List[str] = Field(default_factory=list)
    official_warning: bool = False
    go: bool = False
    headline: str = ""
    advice: str = ""
    window: Optional[str] = None          # e.g. "conditions improve after 11:00"
    sources: List[str] = Field(default_factory=list)
    generated_at: str = ""
    mode: DataMode = "DEMO"


class PFZZone(BaseModel):
    rank: int
    latitude: float
    longitude: float
    distance_km: float
    bearing: str = ""
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    wave_height_m: Optional[float] = None
    confidence: float = 0.0
    rationale: str = ""
    source: str = "DEMO"
    timestamp: str = ""


class RouteLeg(BaseModel):
    latitude: float
    longitude: float


class WaypointCondition(BaseModel):
    lat: float
    lon: float
    distance_from_start_km: float
    wave_m: float
    wind_kmh: float
    risk_factor: float          # 0-1
    risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]


class RouteOption(BaseModel):
    name: str
    kind: Literal["safest", "shortest", "alternate"]
    legs: List[RouteLeg]
    distance_km: float
    eta_minutes: int
    risk_score: int
    risk_category: RiskCategory
    penalties: Dict[str, float] = Field(default_factory=dict)
    recommended: bool = False
    notes: str = ""
    waypoint_conditions: List[WaypointCondition] = Field(default_factory=list)
    path_risk_score: Optional[float] = None


class GeofenceAlert(BaseModel):
    zone_name: str
    zone_type: str
    distance_km: float
    inside: bool
    severity: Literal["info", "warning", "critical"]
    message: str


class EvidenceRow(BaseModel):
    """One row of the 'why did you say that' table."""

    label: str
    value: str
    source: str
    timestamp: str
    confidence: Optional[float] = None
    mode: DataMode = "DEMO"


class ChatRequest(BaseModel):
    message: str
    language: Optional[Language] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    session_id: str = "default"


class AgentTrace(BaseModel):
    """What ran, in what order, how long it took â€” drives the demo animation."""

    agent: str
    status: Literal["ok", "skipped", "failed", "degraded"]
    latency_ms: int
    summary: str = ""
    source: str = ""
    mode: DataMode = "DEMO"


class ChatResponse(BaseModel):
    session_id: str
    language: Language
    answer: str
    intent: Intent
    risk: Optional[RiskAssessment] = None
    pfz: List[PFZZone] = Field(default_factory=list)
    routes: List[RouteOption] = Field(default_factory=list)
    geofence: List[GeofenceAlert] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[EvidenceRow] = Field(default_factory=list)
    trace: List[AgentTrace] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    mode: DataMode = "DEMO"
    disclaimer: str = ""
    explanation_source: Literal["llm", "template"] = "template"
    elapsed_ms: int = 0


# ==========================================================================
# ORCA 2.0 API-facing schemas — consolidated from schemas_v2.py (ARCH-001)
# ==========================================================================
# Previously in backend/app/schemas_v2.py. These are the ORCA 2.0 contracts
# powering /plan, /trace, /voyages, /alerts and the LangGraph pipeline. Merged
# here so there is a single canonical schema module. The v1 "why-table" row
# type was renamed to EvidenceRow (above) so the ORCA 2.0 Evidence wrapper can
# own the canonical `Evidence` name. See docs/DECISIONS.md (2026-09-11).


class Evidence(BaseModel):
    """Every piece of retrieved data — weather, PFZ, advisory, geometry —
    gets wrapped in this before anything else touches it."""
    metric: str                                # e.g. "wave_height", "advisory_no_go"
    value: Union[float, str, dict, list, int]  # numeric reading, or structured payload
    unit: Optional[str] = None                 # e.g. "m", "kmph" — None for non-numeric
    source: str                                # e.g. "Open-Meteo", "IMD", "INCOIS", "StormGlass", "GDACS"
    observed_at: datetime                      # when the underlying reading was taken
    retrieved_at: datetime                     # when ORCA fetched it
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    geometry: Optional[dict] = None            # GeoJSON, when spatially scoped
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0–1.0
    authority_level: Literal[
        "official_advisory", "official_forecast", "external_forecast",
        "derived", "heuristic"
    ]
    mode: Literal["LIVE", "CACHED", "STALE", "DEMO"]
    conflict_status: Optional[Literal["selected", "overridden"]] = None
    conflict_reason: Optional[str] = None


# deprecated: use Evidence
Evidence_v2 = Evidence


def make_evidence(**kwargs) -> Evidence:
    """Factory — fills retrieved_at, observed_at, authority_level, and mode automatically if omitted."""
    kwargs.setdefault("retrieved_at", datetime.now(timezone.utc))
    if "observed_at" not in kwargs:
        kwargs["observed_at"] = kwargs["retrieved_at"]
    kwargs.setdefault("authority_level", "external_forecast")
    kwargs.setdefault("mode", "DEMO")
    return Evidence(**kwargs)


class AdvisoryConstraint(BaseModel):
    """Direct output of the Advisory Compiler."""
    authority: str                             # e.g. "IMD", "INCOIS", "SACHET"
    constraint_type: Literal["NO_GO", "CAUTION", "PORT_WARNING"]
    named_region: str                          # e.g. "North Maharashtra coast"
    geometry: Optional[dict] = None            # resolved polygon, once region→geometry runs
    severity: Literal["LOW", "MODERATE", "HIGH", "SEVERE"]
    valid_from: datetime
    valid_until: datetime
    source_text: str                           # original bulletin excerpt this was derived from
    source_reference: str                      # which archived bulletin it's adapted from
    confidence: float = Field(ge=0.0, le=1.0)  # LLM parse confidence
    localized_summaries: Dict[str, str] = Field(default_factory=dict)  # translations e.g. {"ta": ..., "hi": ...}


class DecisionState(BaseModel):
    request_id: Optional[str] = None
    status: Literal["SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE"]
    risk_score: float = Field(ge=0.0, le=100.0)  # 0-100
    reasons: List[str]                          # human-readable, each tied to specific Evidence
    active_advisories: List[AdvisoryConstraint] = Field(default_factory=list)
    trip_window: Optional[dict] = None          # {"start": ..., "end": ...}
    route: Optional[dict] = None                # {"safe_port": ..., "distance_km": ...}
    trip_economics: Optional[dict] = None       # {"cost": ..., "revenue": ..., "value": ..., "basis": [...]}
    language: str
    explanation: str                            # LLM-generated narrative — never authoritative
    generated_at: datetime


class AlertEvent(BaseModel):
    voyage_id: str
    previous_status: str
    new_status: str
    reason: str
    safe_port: dict                             # {"name": ..., "lat": ..., "lon": ..., "distance_km": ...}
    triggered_at: datetime


class ORCAState(BaseModel):
    """The single object LangGraph nodes read from and write to."""
    request_id: str
    intent: Literal["operational", "analytical"]
    raw_query: str
    language: str
    location: Optional[dict] = None
    evidence: List[Evidence] = Field(default_factory=list)
    advisories: List[AdvisoryConstraint] = Field(default_factory=list)
    conflict_log: List[dict] = Field(default_factory=list)
    decision: Optional[DecisionState] = None
    trace: List[dict] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Converters (v1 schemas -> v2 schemas)
# --------------------------------------------------------------------------
def _parse_datetime(dt_val: Any) -> datetime:
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str) and dt_val:
        try:
            return datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)


def measurement_to_evidence(
    measurement: Measurement,
    metric: str,
    default_source: str = "DEMO",
    authority_level: Literal["official_advisory", "official_forecast", "external_forecast", "derived", "heuristic"] = "external_forecast",
) -> Optional[Evidence]:
    """Convert a Measurement instance into an Evidence instance."""
    if measurement.value is None:
        return None

    prov = measurement.provenance
    mode_map: Dict[str, Literal["LIVE", "CACHED", "STALE", "DEMO"]] = {
        "LIVE": "LIVE",
        "DEMO": "DEMO",
        "CACHE": "CACHED",
        "CACHED": "CACHED",
        "STALE": "STALE",
    }
    mode = mode_map.get(str(prov.mode).upper(), "DEMO")
    conf = prov.confidence if prov.confidence is not None else 0.85
    conf = max(0.0, min(1.0, float(conf)))

    dt = _parse_datetime(prov.timestamp)

    return Evidence(
        metric=metric,
        value=measurement.value,
        unit=measurement.unit or None,
        source=prov.source or default_source,
        observed_at=dt,
        retrieved_at=dt,
        confidence=conf,
        authority_level=authority_level,
        mode=mode,
    )


def agent_result_to_evidence_list(result: AgentResult) -> List[Evidence]:
    """Extract all measurements from an AgentResult into Evidence objects."""
    evidences: List[Evidence] = []
    default_source = result.source or "DEMO"

    auth_level: Literal["official_advisory", "official_forecast", "external_forecast", "derived", "heuristic"] = (
        "official_forecast" if result.source in ("IMD", "INCOIS") else "external_forecast"
    )

    for metric_name, measurement in result.measurements.items():
        ev = measurement_to_evidence(
            measurement,
            metric=metric_name,
            default_source=default_source,
            authority_level=auth_level,
        )
        if ev is not None:
            evidences.append(ev)

    return evidences


def risk_assessment_to_decision_state(
    risk: RiskAssessment,
    language: str = "en",
    explanation: str = "",
    advisories: Optional[List[AdvisoryConstraint]] = None,
    route: Optional[dict] = None,
    trip_economics: Optional[dict] = None,
) -> DecisionState:
    """Map a RiskAssessment to a DecisionState."""
    status_map: Dict[str, Literal["SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE"]] = {
        "LOW": "SAFE",
        "MODERATE": "CAUTION",
        "HIGH": "UNSAFE",
        "EXTREME": "UNSAFE",
    }
    status = status_map.get(risk.category, "UNSAFE")
    if not risk.factors and not risk.overrides:
        status = "INSUFFICIENT_EVIDENCE"

    reasons: List[str] = []
    if risk.headline:
        reasons.append(risk.headline)
    for override in risk.overrides:
        reasons.append(f"Override: {override}")
    for factor in risk.factors:
        if factor.contribution > 5.0:
            reasons.append(f"{factor.label}: {factor.detail} (impact +{factor.contribution:.0f})")

    gen_at = _parse_datetime(risk.generated_at)

    trip_win = None
    if risk.window:
        trip_win = {"window_text": risk.window}

    return DecisionState(
        status=status,
        risk_score=float(risk.score),
        reasons=reasons,
        active_advisories=advisories or [],
        trip_window=trip_win,
        route=route,
        trip_economics=trip_economics,
        language=language,
        explanation=explanation or risk.advice or risk.headline,
        generated_at=gen_at,
    )

