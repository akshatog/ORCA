"""ORCA 2.0 API-facing schemas (frozen contracts).

Defines Evidence, AdvisoryConstraint, DecisionState, AlertEvent, ORCAState,
the make_evidence factory, and converter bridges between schemas.py and schemas_v2.py.
See docs/02_schemas.md for the authoritative frozen schema specification.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from . import schemas as old_schemas


# --------------------------------------------------------------------------
# Evidence — universal wrapper for all retrieved or derived data
# --------------------------------------------------------------------------
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


Evidence_v2 = Evidence


def make_evidence(**kwargs) -> Evidence:
    """Factory — fills retrieved_at, observed_at, authority_level, and mode automatically if omitted."""
    kwargs.setdefault("retrieved_at", datetime.now(timezone.utc))
    if "observed_at" not in kwargs:
        kwargs["observed_at"] = kwargs["retrieved_at"]
    kwargs.setdefault("authority_level", "external_forecast")
    kwargs.setdefault("mode", "DEMO")
    return Evidence(**kwargs)


# --------------------------------------------------------------------------
# AdvisoryConstraint — direct output of the Advisory Compiler
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# DecisionState — unified decision payload returned by /plan
# --------------------------------------------------------------------------
class DecisionState(BaseModel):
    request_id: Optional[str] = None
    status: Literal["SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE"]
    risk_score: float = Field(ge=0.0, le=100.0) # 0-100
    reasons: List[str]                          # human-readable, each tied to specific Evidence
    active_advisories: List[AdvisoryConstraint] = Field(default_factory=list)
    trip_window: Optional[dict] = None          # {"start": ..., "end": ...}
    route: Optional[dict] = None                # {"safe_port": ..., "distance_km": ...}
    trip_economics: Optional[dict] = None       # {"cost": ..., "revenue": ..., "value": ..., "basis": [...]}
    language: str
    explanation: str                            # LLM-generated narrative — never authoritative
    generated_at: datetime


# --------------------------------------------------------------------------
# AlertEvent — voyage monitor alert when conditions deteriorate
# --------------------------------------------------------------------------
class AlertEvent(BaseModel):
    voyage_id: str
    previous_status: str
    new_status: str
    reason: str
    safe_port: dict                             # {"name": ..., "lat": ..., "lon": ..., "distance_km": ...}
    triggered_at: datetime


# --------------------------------------------------------------------------
# ORCAState — central state passed between LangGraph nodes
# --------------------------------------------------------------------------
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
# Converters (Old schemas.py -> New schemas_v2.py)
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
    measurement: old_schemas.Measurement,
    metric: str,
    default_source: str = "DEMO",
    authority_level: Literal["official_advisory", "official_forecast", "external_forecast", "derived", "heuristic"] = "external_forecast",
) -> Optional[Evidence]:
    """Convert an old Measurement schema instance into an Evidence_v2 instance."""
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


def agent_result_to_evidence_list(result: old_schemas.AgentResult) -> List[Evidence]:
    """Extract all measurements from an old AgentResult into Evidence_v2 objects."""
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
    risk: old_schemas.RiskAssessment,
    language: str = "en",
    explanation: str = "",
    advisories: Optional[List[AdvisoryConstraint]] = None,
    route: Optional[dict] = None,
    trip_economics: Optional[dict] = None,
) -> DecisionState:
    """Map old RiskAssessment to new DecisionState."""
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
