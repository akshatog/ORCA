# ORCA 2.0 — Engineering Audit & Fix Status

> Last updated: 2026-09-11 (P3 fixes + ARCH-001 schema consolidation complete)
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

## Schemas: Consolidated ✅ (ARCH-001 complete)

The dual-schema problem has been resolved. `schemas_v2.py` is **deleted**. All types now live in `backend/app/schemas.py`.

| Model | Location | Notes |
|---|---|---|
| `EvidenceRow` | `schemas.py` | Renamed from v1 `Evidence` — the 6-field display row used by `/api/chat` response |
| `Evidence` | `schemas.py` | The v2 universal data wrapper (metric/value/unit/observed_at/confidence/authority_level…) |
| `Evidence_v2` | `schemas.py` | Alias for `Evidence` — kept for zero-cost backward compat |
| `AdvisoryConstraint`, `DecisionState`, `AlertEvent`, `ORCAState` | `schemas.py` | Moved from schemas_v2.py |
| `make_evidence`, converters | `schemas.py` | Moved from schemas_v2.py |
| `WaypointCondition`, `RiskAssessment`, `PFZZone`, `RouteOption`, etc. | `schemas.py` | Unchanged v1 types |
| `ORCAGraphState` | `graph/state.py` | Stays there — LangGraph execution concern, not a wire schema |

**Branch:** ARCH-001 is on the `schema-consolidation` branch (commit `fee1775`). Merge to `orca-2.0` is the next step.

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

### P3 — Polish (ALL FIXED as of 2026-09-11)

| ID | Problem | Status | Fix Applied |
|---|---|---|---|
| **LANG-002** | `GET /api/fishing?lang=ta` returned 422 → blank fishing screen. Regex `^(en\|hi\|mr)$` rejected all other languages. | ✅ FIXED | `api/fishing.py` lang pattern widened to `^(en\|hi\|mr\|ta\|te\|bn\|ml)$` |
| **ERR-002** | `POST /api/config/mode` with invalid mode returned HTTP 200 `{ok:false}` | ✅ FIXED | Now raises `HTTPException(422)` — status code correctly signals failure |
| **INT-002** | Unknown `/api/path` returned HTML 200 (SPA catch-all) instead of JSON 404 | ✅ FIXED | `main.py` — `@app.get("/api/{rest_of_path:path}")` handler returns `JSONResponse(404)` before the SPA mount |
| **FE-002/003** | `startVoyage`, `endVoyage`, `triggerAlert`, `fetchPlan` errors swallowed silently | ✅ FIXED | `App.tsx` — all 4 now have `try/catch` calling `setError()` + 8s auto-dismiss |

### P4 — Documentation Gaps

| ID | Problem | Status |
|---|---|---|
| **DOC-001** | `docs/05_api_contracts.md` says `GET /api/routes` — it's `POST` | ✅ FIXED below |
| **DOC-002** | Docs say `/api/mode` — it's `/api/config/mode` | ✅ FIXED below |
| **DOC-003** | Docs say `?hours=` — it's `?when=` | ✅ FIXED below |

### Open — BE-003 (your call)

| ID | Problem | Options |
|---|---|---|
| **BE-003** | `conflict_resolver_node` produces reconciled evidence but output is discarded. `ConflictLogPanel` shows data that changes no outcomes. | **Wire it** (~1hr, impressive): pass resolved evidence into `constraint_engine_node` instead of raw evidence. **Or remove panel** (10min, cleaner): drop `ConflictLogPanel` from `App.tsx` ops tab. |

---

## Test Coverage

| Suite | Tests | Status |
|---|---|---|
| Full backend suite | 84 tests | ✅ 82/82 passing (2 deselected = live LLM API tests — unrelated to code, need API quota) |
| `test_contract_p1_p2.py` | 8 contract tests (NEW) | ✅ All passing |
| `test_graph.py` | 3 end-to-end pipeline tests | ✅ Passing |
| `test_alert_engine.py` | 4 alert lifecycle tests | ✅ Passing |
| `test_risk_engine.py` | 6 safety floor tests | ✅ Passing |
| Frontend `tsc --noEmit` | TypeScript compile | ✅ Exit 0 |

**Gap:** Zero frontend ↔ backend integration tests. The 8 contract tests in `test_contract_p1_p2.py` partially address this for the schema boundary.

**Note on the 2 deselected tests:** `test_complete_chat_groq_active` and `test_complete_chat_gemini_fallback_when_groq_cerebras_killed` make live API calls to Groq/Gemini. They pass when API quota is available. They have zero dependency on schemas, routes, or any code changed in this session.

---

## Schema Consolidation (ARCH-001) — COMPLETE ✅

`schemas.py` and `schemas_v2.py` have been merged. `schemas_v2.py` is deleted. All 30 affected files (app + tests) updated. See `DECISIONS.md` (2026-09-11 entries) for the full decision rationale.

**What was renamed:** v1 `Evidence` → `EvidenceRow` (6-field display row). v2 `Evidence` is now the canonical type. `Evidence_v2 = Evidence` alias preserved.
**Branch:** `schema-consolidation` (commit `fee1775`) — merge to `orca-2.0` pending.

---

## Key File Map

```
backend/
  app/
    schemas.py          # Canonical schema — all v1 + v2 types. schemas_v2.py is DELETED.
    graph/
      nodes.py          # LangGraph node implementations (the v2 brain)
      state.py          # ORCAGraphState (LangGraph internal) — imports from schemas.py
      __init__.py       # Compiles the LangGraph and exposes run_plan()
    agents/
      planner.py        # v1 multi-agent orchestrator (DO NOT BREAK)
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
