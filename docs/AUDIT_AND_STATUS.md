# ORCA 2.0 — Engineering Audit & Fix Status

> Last updated: 2026-09-11
> Source: Full automated audit (ORCA_AUDIT/ directory) + manual verification against live code.
> **Read this before touching anything.** It tells you what was broken, what is now fixed, and what the known gaps are.

---

## Background: Two Pipelines

ORCA 2.0 has **two parallel request paths**. This is intentional — v1 is the live demo path, v2 is the upgrade layer.

| Path | Entry Point | Description |
|---|---|---|
| **v1** | `POST /api/chat` | LangChain multi-agent planner (`agents/planner.py`). Powers Chat, Forecast, Fishing, System pages. Battle-tested, demo-ready. |
| **v2** | `POST /api/plan` | LangGraph pipeline (`graph/nodes.py`). Powers Plan, Voyages, Alerts, Voice. Newer, had more bugs. |

Both paths call the same specialist agents (`weather_agent`, `ocean_agent`, `pfz_agent`, `gis_agent`, `cyclone_agent`) and use the **same `risk_engine.py`** (the safety core — never change this).

### Do NOT touch
- `risk_engine.py` — deterministic safety floors. Legally correct. Never override.
- `demo_store.py` — the 5 seeded demo scenarios (Mumbai=rough, Goa=calm, Paradip=cyclone, Kochi=moderate, Digha=rough). Live demo depends on exact values.
- `agents/planner.py` — the v1 chat pipeline. It works. Leave it alone.
- All existing `/api/*` alias routes — smoke tests use them.

---

## Schemas: The Core Problem

The project has **two schema files** which drifted apart:

| File | Used by | Notes |
|---|---|---|
| `backend/app/schemas.py` | v1 pipeline, all specialist agents, `PFZZone`, `WaypointCondition`, `RiskAssessment`, `RouteOption` | The original, battle-tested schema |
| `backend/app/schemas_v2.py` | v2 LangGraph pipeline, voyages, alerts, DecisionState | Added for ORCA 2.0 — overlaps with schemas.py |

**This dual-schema situation was the root cause of most audit bugs.** A schema consolidation is planned (see below).

---

## Audit Findings — Full Inventory

### P1 — Were Crashing / Blocking (ALL FIXED as of 2026-09-11)

| ID | Problem | Status | Fix Applied |
|---|---|---|---|
| **API-001** | `MarineMap.tsx` read `wp.latitude/longitude/wave_height_m/segment_risk` but backend emitted `lat/lon/wave_m/risk_factor` → `undefined.toFixed()` crash on map | ✅ FIXED | `types.ts::WaypointCondition` + `MarineMap.tsx` lines 343-378 aligned to backend fields with `?.` guards |
| **INT-001** | `api.ts` called `/plan`, `/voyages/start` at root; Vite proxy only forwarded `/api/*` → all v2 calls returned HTML 200 (silent failure) | ✅ FIXED | Vite proxy now covers `/plan`, `/trace`, `/state`, `/voyages`, `/alerts`, `/voice`; `api.ts` standardized to `${BASE}/...`; `/api` aliases added in `plan.py` |

### P2 — V2 Pipeline Correctness (ALL FIXED as of 2026-09-11)

| ID | Problem | Status | Fix Applied |
|---|---|---|---|
| **BE-001** | `route_node` read `z.get("coordinates", {})` which was always empty — route always went to `loc+0.15°` regardless of actual PFZ location | ✅ FIXED | Now reads `z["latitude"]`/`z["longitude"]`; picks highest-confidence zone; derives potential from chlorophyll via `_pfz_potential_from_chlorophyll()` |
| **DUP-001** | Three separate risk formulas: `risk_engine.assess()` (v1), `constraint_engine_node` inline (v2 plan), `_evaluate_voyage_conditions` inline (alert engine) — all produced different scores for identical conditions | ✅ FIXED | `constraint_engine_node` now delegates to `risk_engine.assess()`. Alert engine retains its own copy (acceptable — it runs in real-time monitoring context, not decision context) |
| **BE-002** | v2 risk scoring only used wave + wind; ignored rain, visibility, sea state, current, offshore distance | ✅ FIXED | Automatic after DUP-001 — `risk_engine.assess()` uses all factors |
| **GIS evidence gap** | `gis_node` called `agent_result_to_evidence_list()` but GIS agent has no `measurements{}` dict → zero GIS evidence in `state.evidence` → `inside_restricted_zone` always False in v2 | ✅ FIXED | `gis_node` now explicitly stores `distance_from_shore_km`, `nearest_zone_km`, `inside_restricted_zone` as Evidence records |

### P3 — Polish (NOT YET DONE)

| ID | Problem | Priority | Notes |
|---|---|---|---|
| **LANG-002** | `GET /api/fishing?lang=ta` returns 422 → blank fishing screen. Regex only allows `en\|hi\|mr`. | Medium | Fix: widen regex in `api/fishing.py` to all 10 Language values |
| **BE-003** | `conflict_resolver_node` runs but discards reconciled evidence. ConflictLogPanel shows data that changes no outcomes. | Medium | Wire it or drop the panel — 1hr vs 10min |
| **ERR-002** | `POST /api/config/mode` with invalid mode returns HTTP 200 `{ok:false}` instead of 422 | Low | Fix in `api/routes.py::switch_mode` |
| **FE-002/003** | Voyage start/end/alert errors swallowed with `console.warn` → silent UI failures | Medium | Add try/catch → error toast in `App.tsx` |
| **INT-002** | Unknown `/api/path` returns HTML 200 (SPA catch-all fires) instead of JSON 404 | Low | Add `@app.exception_handler` or ordered catch-all in `main.py` |

### P4 — Documentation Gaps (NOT YET DONE)

| ID | Problem |
|---|---|
| **DOC-001** | `docs/05_api_contracts.md` says `GET /api/routes` — it's `POST` |
| **DOC-002** | Docs say `/api/mode` — it's `/api/config/mode` |
| **DOC-003** | Docs say `?hours=` — it's `?when=` |

---

## Test Coverage

| Suite | Tests | Status |
|---|---|---|
| Full backend suite | 84 tests | ✅ 84/84 passing |
| `test_contract_p1_p2.py` | 8 contract tests (NEW) | ✅ All passing |
| `test_graph.py` | 3 end-to-end pipeline tests | ✅ Passing |
| `test_alert_engine.py` | 4 alert lifecycle tests | ✅ Passing |
| `test_risk_engine.py` | 6 safety floor tests | ✅ Passing |
| Frontend `tsc --noEmit` | TypeScript compile | ✅ Exit 0 |

**Gap:** Zero frontend ↔ backend integration tests. The 8 new contract tests in `test_contract_p1_p2.py` partially address this for the schema boundary.

---

## Planned: Schema Consolidation (ARCH-001)

The next major task is merging `schemas.py` + `schemas_v2.py` into one canonical schema.

**Decision:** Fix specific contract breaks now (P1/P2 above). Do full schema merge as a separate task after P1/P2 are stable and tested.

**Scope of merge:**
- One `WaypointCondition` (currently exists in both with different fields)
- One risk model output type (currently `RiskAssessment` in v1, `DecisionState` in v2)
- One evidence type (currently `Evidence` in schemas.py, `Evidence` in schemas_v2.py — confusingly both named the same)
- All v2 types (`DecisionState`, `ORCAState`, `AdvisoryConstraint`, `AlertEvent`, `Voyage`) stay, v1 types that overlap get removed or aliased
- Both pipelines consume the merged schema

**Files affected by merge:**
- `backend/app/schemas.py` — kept, extended with v2 types
- `backend/app/schemas_v2.py` — consolidated into schemas.py, then deleted
- `backend/app/graph/nodes.py` — update imports
- `backend/app/graph/__init__.py` — update imports
- `backend/app/api/plan.py` — update imports
- `backend/app/api/voyages.py` — update imports
- `backend/app/api/alerts.py` — update imports
- `backend/app/services/alert_engine.py` — update imports
- `backend/app/services/conflict_resolver.py` — update imports
- `backend/app/agents/planner.py` — update imports (v1 path must continue to work)
- All test files that import from schemas_v2
- `frontend/src/types.ts` — sync any field-name changes

**Risk:** HIGH. Both pipelines depend on these schemas. Must have comprehensive tests running before and after, and must verify both `/api/chat` and `/api/plan` produce correct output post-merge.

---

## Key File Map

```
backend/
  app/
    schemas.py          # v1 Pydantic models (Location, PFZZone, WaypointCondition, RiskAssessment...)
    schemas_v2.py       # v2 Pydantic models (Evidence, DecisionState, ORCAState, AdvisoryConstraint...)
    graph/
      nodes.py          # LangGraph node implementations (the v2 brain)
      __init__.py       # Compiles the LangGraph and exposes run_plan()
    agents/
      planner.py        # v1 multi-agent orchestrator
      risk_agent.py     # Calls risk_engine.assess()
      pfz_agent.py      # PFZ zone finder (uses schemas.PFZZone)
      [others]          # weather, ocean, gis, cyclone, route, intent
    services/
      risk_engine.py    # THE SAFETY CORE. Do not change safety floors.
      alert_engine.py   # Voyage monitoring and alert firing
      conflict_resolver.py  # Evidence conflict detection (currently decorative in v2)
    api/
      plan.py           # POST /plan (+ /api/plan alias)
      voyages.py        # POST /voyages/start, /end, GET /active
      alerts.py         # POST /alerts/trigger
      voice.py          # POST /voice/transcribe, /speak
      chat.py           # POST /api/chat (v1 entry point)
      fishing.py        # GET /api/fishing
    data/
      demo_store.py     # Seeded scenarios. Do not change values.
      geo.py            # RESTRICTED_ZONES, port list, haversine, bearing utils
    config/
      risk_thresholds.yaml  # All safety floor values

frontend/
  src/
    types.ts            # All TypeScript interfaces (must match backend wire shapes)
    api.ts              # All fetch calls (uses BASE = "/api")
    components/
      MarineMap.tsx     # Leaflet map — renders waypoint risk dots
      ConflictLogPanel.tsx  # Shows conflict resolver output (currently decorative)
    pages/              # Plan, Voyages, Fishing, System pages
  vite.config.ts        # Dev proxy config (must cover all v2 routes)

tests/                  # All pytest tests
  test_contract_p1_p2.py  # NEW — contract regression guards
  test_risk_engine.py     # Safety floor tests — must always pass
  test_graph.py           # End-to-end pipeline smoke test
```
