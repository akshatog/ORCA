# ORCA — Schemas

## Dual-schema strategy

The codebase maintains **two** schema files:

1. **`backend/app/schemas.py`** — the original internal schemas used by the existing
   agents, API routes, and frontend. These are NOT being deleted. The existing
   `ChatResponse`, `RiskAssessment`, `AgentResult`, etc. continue to power the
   old `/api/chat` endpoint and all 17 frontend components.

2. **`backend/app/schemas_v2.py`** — the ORCA 2.0 API-facing schemas defined below.
   These power the new `/plan`, `/trace`, `/voyages`, `/alerts` endpoints and the
   LangGraph state graph.

Converter functions in `schemas_v2.py` bridge old → new. When both paths stabilize,
a cleanup pass can consolidate to one schema set.

---

## ORCA 2.0 schemas (schemas_v2.py)

These are frozen. If a change is genuinely needed, log it in `DECISIONS.md`
with a reason before changing this file.

```python
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class Evidence(BaseModel):
    """Every piece of retrieved data — weather, PFZ, advisory, geometry —
    gets wrapped in this before anything else touches it."""
    metric: str                      # e.g. "wave_height", "advisory_no_go"
    value: float | str | dict        # numeric reading, or structured payload
    unit: Optional[str] = None       # e.g. "m", "kmph" — None for non-numeric
    source: str                      # e.g. "Open-Meteo", "IMD", "INCOIS", "StormGlass", "GDACS"
    observed_at: datetime            # when the underlying reading was taken
    retrieved_at: datetime           # when ORCA fetched it
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    geometry: Optional[dict] = None  # GeoJSON, when spatially scoped
    confidence: float                # 0.0–1.0
    authority_level: Literal[
        "official_advisory", "official_forecast", "external_forecast",
        "derived", "heuristic"
    ]
    mode: Literal["LIVE", "CACHED", "STALE", "DEMO"]
    conflict_status: Optional[Literal["selected", "overridden"]] = None
    conflict_reason: Optional[str] = None


def make_evidence(**kwargs) -> Evidence:
    """Factory — fills retrieved_at automatically."""
    kwargs.setdefault("retrieved_at", datetime.utcnow())
    return Evidence(**kwargs)


class AdvisoryConstraint(BaseModel):
    """Direct output of the Advisory Compiler."""
    authority: str                   # e.g. "IMD", "INCOIS", "SACHET"
    constraint_type: Literal["NO_GO", "CAUTION", "PORT_WARNING"]
    named_region: str                # e.g. "North Maharashtra coast"
    geometry: Optional[dict] = None  # resolved polygon, once region→geometry runs
    severity: Literal["LOW", "MODERATE", "HIGH", "SEVERE"]
    valid_from: datetime
    valid_until: datetime
    source_text: str                 # original bulletin excerpt this was derived from
    source_reference: str            # which archived bulletin it's adapted from
    confidence: float                # LLM parse confidence — see 04 for the 0.7 rule


class DecisionState(BaseModel):
    status: Literal["SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE"]
    risk_score: float                 # 0-100
    reasons: list[str]                 # human-readable, each tied to specific Evidence
    active_advisories: list[AdvisoryConstraint] = []
    trip_window: Optional[dict] = None       # {"start": ..., "end": ...}
    route: Optional[dict] = None             # {"safe_port": ..., "distance_km": ...}
    trip_economics: Optional[dict] = None    # {"cost": ..., "revenue": ..., "value": ..., "basis": [...]}
    language: str
    explanation: str                  # LLM-generated narrative — never authoritative
    generated_at: datetime


class AlertEvent(BaseModel):
    voyage_id: str
    previous_status: str
    new_status: str
    reason: str
    safe_port: dict                   # {"name": ..., "lat": ..., "lon": ..., "distance_km": ...}
    triggered_at: datetime


class ORCAState(BaseModel):
    """The single object LangGraph nodes read from and write to."""
    request_id: str
    intent: Literal["operational", "analytical"]
    raw_query: str
    language: str
    location: Optional[dict] = None
    evidence: list[Evidence] = []
    advisories: list[AdvisoryConstraint] = []
    conflict_log: list[dict] = []
    decision: Optional[DecisionState] = None
    trace: list[dict] = []
```

## Rules for every schema

- No fields beyond what's listed here without a `DECISIONS.md` entry.
- Every module that computes a derived value wraps its output as an `Evidence`
  with `authority_level: "derived"` and lists which input Evidence items it used.
- `mode` is never silently upgraded — a `CACHED` value only becomes `STALE`
  when `valid_until` passes; it is never presented as `LIVE` after the fact.

## Old schemas (schemas.py) — still in use

The following types remain in `schemas.py` and are used by the existing frontend:

- `Provenance`, `Measurement`, `Location`, `Intent` — internal agent types
- `AgentResult` — uniform agent return envelope
- `RiskFactor`, `RiskAssessment` — risk engine output
- `PFZZone`, `RouteLeg`, `RouteOption`, `GeofenceAlert` — domain types
- `Evidence` (old) — simpler 6-field version for the "why" table
- `ChatRequest`, `ChatResponse` — the old `/api/chat` contract
- `AgentTrace` — agent execution trace for demo animation

**Do not delete or modify these.** They are used by the old API path.

## Test requirement

3 tests per model: valid construction, missing required field, an
out-of-range value (e.g. `confidence` outside 0.0–1.0). Nothing more —
these are schemas, not logic.
