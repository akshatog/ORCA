# ORCA — Tasks & Assignments

**Solo builder mode.** Akshay builds backend + migration with AI agents.
Teammates join later for frontend polish, data sources, and voice.

---

## Phase 0 — Foundation

### TASK-0.1 — Config YAML files
Extract `RiskConfig` + trip economics from `config.py` into `config/risk_thresholds.yaml`
and `config/trip_economics.yaml`. Load at startup, fall back to hardcoded defaults.
**Verify:** Backend boots, `RISK.weights` prints correctly.

### TASK-0.2 — ORCA 2.0 schemas (`schemas_v2.py`)
`Evidence_v2`, `AdvisoryConstraint`, `DecisionState`, `AlertEvent`, `ORCAState`,
`make_evidence()` factory, old→new converters. Keep `schemas.py` untouched.
**Verify:** All models import. 3 unit tests per model.

### TASK-0.3 — Centralized mock data
`data/mock_data/` with weather, advisory, PFZ, cyclone fixtures + all 7 edge
cases from `09_testing_and_edge_cases.md`. Output `Evidence_v2` objects.
**Verify:** `ALL_CASES` has 7+ entries, each valid `Evidence_v2`.

### TASK-0.4 — Update `DECISIONS.md`
Log all foundation decisions.

---

## Phase 1 — LLM Layer

### TASK-1.1 — Multi-provider LLM with fallback chain
**Fallback order:** Groq (`llama-3.3-70b`) → Cerebras (`llama-3.1-70b`) → Gemini Flash 2.0 → Template engine (always works)
All three use OpenAI-compatible APIs — same code, different base URL + model name.
Env vars: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`
**Verify:** Kill keys one by one → each fallback activates. All keys dead → template response, no crash.

### TASK-1.2 — Advisory Compiler
`services/advisory_compiler.py`: `compile_advisory(text) → list[AdvisoryConstraint]`.
Confidence < 0.70 → `INSUFFICIENT_EVIDENCE`. LLM down → empty list, no crash.
**Verify:** Real IMD bulletin → valid parse. Garbled text → low confidence.

---

## Phase 2 — Core Pipeline (LangGraph)

### TASK-2.1 — LangGraph graph
`graph/` package: `state.py`, `nodes.py`, `graph.py`. Wrap each existing agent
as a LangGraph node. Topology:
```
intent → [weather, ocean, pfz, cyclone, gis] → evidence_store → conflict_resolver → constraint_engine → route → explanation
```
**Verify:** Graph prints ASCII topology. One mock run → valid `ORCAState`.

### TASK-2.2 — `POST /plan` endpoint
Accepts `{location, intent_text, language}` → invokes graph → returns `DecisionState`.
Stores `ORCAState` in memory by `request_id`.
**Verify:** curl POST → valid `DecisionState` JSON.

### TASK-2.3 — `GET /trace/{request_id}`
Returns `ORCAState.trace`. 404 if not found.
**Verify:** POST then GET → trace contains all node names.

### TASK-2.4 — Keep `/api/chat` working
No changes to `planner.py`. Verify existing frontend works after all Phase 2 changes.
**Verify:** Frontend chat responds, all tabs render.

### TASK-2.5 — Route waypoint risk scoring (path-integrated risk)
After A* returns route candidates, sample conditions at evenly-spaced waypoints
(~5 per route, every ~10km for a 40km route). Compute `path_risk_score`:
```
score = 0.7 × avg(waypoint_factors) + 0.3 × max(waypoint_factors)
```
The `max_spike` term penalises routes that pass through storm bands.
Re-rank routes by `path_risk_score`. Attach `waypoint_conditions[]` to each `RouteOption`.
Weights live in `config/risk_thresholds.yaml`.

**Files:**
- [MODIFY] `backend/app/services/route_optimizer.py` — add `score_route_path()`
- [MODIFY] `backend/app/schemas.py` — add `WaypointCondition`, add fields to `RouteOption`
- [MODIFY] route agent/graph node — call scorer after A*

**Schema addition:**
```python
class WaypointCondition(BaseModel):
    lat: float
    lon: float
    distance_from_start_km: float
    wave_m: float
    wind_kmh: float
    risk_factor: float          # 0-1
    risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
```

**Verify:**
- Mock route through bad-weather cell vs route avoiding it → lower-risk route wins
- `waypoint_conditions` has ~5 entries per 40km route
- Frontend can render colored dots (🟢🟡🔴) on route line

---

## Phase 3 — Safety Engine & Alerts

### TASK-3.1 — Conflict Resolver
`services/conflict_resolver.py`. Authority hierarchy: `official_advisory >
official_forecast > external_forecast > derived > heuristic`.
**Verify:** IMD wave vs Open-Meteo wave → IMD wins, Open-Meteo overridden.

### TASK-3.2 — Voyage tracking store
`data/voyage_store.py`. `start_voyage()`, `get_active_voyages()`, `end_voyage()`,
`update_voyage_decision()`. In-memory dict.
**Verify:** Start → list → end → gone.

### TASK-3.3 — Alert engine (`on_evidence_change`)
`services/alert_engine.py`. Re-runs constraint engine for affected voyages.
`AlertEvent` includes safe-port recommendation from `geo.py`.
**Verify:** SAFE voyage + severe advisory → `AlertEvent` fires with valid port.

### TASK-3.4 — Voyage/alert API
`api/voyages.py`. `POST /voyages/start`, `GET /voyages/active`,
`POST /voyages/{id}/end`, `POST /alerts/trigger`.
**Verify:** Full flow: start → trigger → alert → end.

---

## Phase 4 — Data Layer

### TASK-4.1 — GDACS cyclone feed — **15 min refresh**
`fetch_gdacs()` in `live_client.py`. Parse `gdacs.org/xml/rss.xml`. Filter Indian
Ocean. TTL 15 min (cyclones intensify fast). On change → `on_evidence_change()`.
**Verify:** Returns parsed entries or empty list.

### TASK-4.2 — StormGlass adapter — **2 hr refresh**
`data/stormglass_client.py`. Tide + current. Cache per 0.1° region. Only fetch
for ports with active voyages (quota: 50 req/day → ~24-60 real calls/day). Graceful
fallback without key.
**Verify:** With key → data. Without → fallback, no crash.

### TASK-4.3 — IMD Advisory Scraper — **1 hr refresh**
`data/advisory_scraper.py`. `BeautifulSoup` for HTML links, `pdfplumber` for PDF text.
SHA-256 hash → only re-process if content changed. On new advisory → Advisory Compiler.
**Deps:** `pdfplumber`, `beautifulsoup4`, `lxml`
**Verify:** Real IMD URL → valid `AdvisoryConstraint` output.

### TASK-4.4 — INCOIS PFZ Scraper — **6 hr refresh**
Add to `advisory_scraper.py`. Scrape `incois.gov.in/portal/advisories/`.
TTL 6hr — PFZ is satellite-derived, updates 1-2x/day.
**Verify:** PFZ coordinates extracted from test bulletin.

### TASK-4.5 — Tiered Scheduler
`data/scheduler.py`. APScheduler jobs:
```python
fetch_gdacs_and_alert   → every 15 min
fetch_open_meteo_cache  → every 30 min
fetch_imd_advisory      → every 1 hr
fetch_stormglass_cache  → every 2 hr
fetch_incois_pfz        → every 6 hr
```
All jobs run once at startup to warm the cache. Each job calls `on_evidence_change()`
if data changed.
**Dep:** `apscheduler`
**Verify:** Start server → all 5 jobs logged at startup. 15 min → GDACS runs again.

### TASK-4.6 — Source Registry
`data/source_registry.py`. Capability → `{source_name, fetch_fn, priority, is_live,
refresh_interval_s}`. Agents query registry instead of hardcoding client imports.
**Verify:** `get_sources('weather')` returns ordered source list.

### TASK-4.7 — Sarvam Voice Integration
**Files:** `services/voice.py`, `api/voice.py`
- `transcribe(audio_bytes, language_hint) → str` — Saaras STT (22 Indian languages)
- `speak(text, language_code, voice_id) → bytes` — Bulbul TTS (11 languages)
- `POST /voice/transcribe` — audio blob → transcript
- `POST /voice/speak` — text + language → audio stream
- Fallback: if Sarvam down → return error, frontend uses browser fallback

**Env var:** `SARVAM_API_KEY`
**Verify:** Hindi audio clip → Hindi transcript. Hindi text → audio bytes.

### TASK-4.8 — Extend Language Support (text layer)
- Extend `Language` type in `schemas.py`: add `"ta" | "te" | "bn" | "ml" | "gu" | "kn" | "or"`
- Add string tables for TA, TE, BN, ML to `services/i18n.py`
- Intent agent: detect language by Unicode script range (no LLM needed):
  - Tamil U+0B80–U+0BFF, Telugu U+0C00–U+0C7F, Bengali U+0980–U+09FF, Malayalam U+0D00–U+0D7F
- `services/translate.py`: `translate(text, from_lang, to_lang) → str` using Sarvam Mayura

**Verify:** Tamil-script query → `language="ta"` detected → Tamil response.

### TASK-4.9 — Advisory Translation
After Advisory Compiler, translate `source_text` to all priority languages using
Sarvam Translate. Store as `localized_summaries: dict[str, str]` on `AdvisoryConstraint`.
**Verify:** Compiled advisory has Tamil text in `localized_summaries["ta"]`.

---

## Phase 5 — Frontend: Minimal Wiring

### TASK-5.1 — New TypeScript types
Add to `types.ts`: `Evidence_v2`, `AdvisoryConstraint`, `DecisionState`, `AlertEvent`,
`ORCAState`, `TraceEntry`, `WaypointCondition`.
**Verify:** `npx tsc --noEmit` passes.

### TASK-5.2 — New API functions
Add to `api.ts`: `fetchPlan()`, `fetchTrace()`, `startVoyage()`, `endVoyage()`,
`triggerAlert()`, `transcribeVoice()`, `speakText()`.
**Verify:** Call from browser console → valid response.

---

## Phase 6 — Testing

| Task | File | Coverage |
|---|---|---|
| TASK-6.1 | `tests/test_schemas_v2.py` | 3 per model: valid, missing required, out-of-range |
| TASK-6.2 | `tests/test_risk_engine.py` | Floors, advisory override, cyclone floor, wave danger |
| TASK-6.3 | `tests/test_advisory_compiler.py` | Real bulletin, garbled, LLM down |
| TASK-6.4 | `tests/test_conflict_resolver.py` | Authority hierarchy, expired evidence |
| TASK-6.5 | `tests/test_alert_engine.py` | SAFE → alert, non-overlapping voyage → no alert |
| TASK-6.6 | `tests/test_route_waypoint.py` | Storm-band route demoted vs clear route |
| TASK-6.7 | `tests/test_scheduler.py` | All 5 jobs registered, run without exception |
| TASK-6.8 | `tests/test_i18n.py` | Tamil → `"ta"`, Telugu → `"te"`, fallback → `"en"` |

---

## Phase 7 — Docs & Polish

### TASK-7.1 — Update all docs to reflect final state
### TASK-7.2 — Comprehensive smoke test (`backend/smoke_test.py`)
### TASK-7.3 — Update `AGENT.md`

---

## Phase 8 — Full Frontend Build

| Task | Description |
|---|---|
| TASK-8.1 | Evidence Provenance Panel — source, authority, mode badge, confidence |
| TASK-8.2 | Conflict Resolution Log — who won, who was overridden, why |
| TASK-8.3 | Decision Pipeline Visualization — LangGraph animated node flow |
| TASK-8.4 | Voyage Tracker — start/stop, status badge, region on map |
| TASK-8.5 | Alert Banner — slides in on alert, old/new status, safe port, navigate button |
| TASK-8.6 | Wire Research Web to new endpoints |
| TASK-8.7 | Wire Fisherman App to voyage/alert system |
| TASK-8.8 | Language switcher upgrade — TA, TE, BN, ML added, persist in localStorage |
| TASK-8.9 | PWA service worker + IndexedDB offline decision cache |
| TASK-8.10 | PWA manifest.json — home screen install, standalone mode |
| TASK-8.11 | Voice UI — mic button → Sarvam STT, TTS response playback, language-aware |
| TASK-8.12 | Route waypoint dots — colored 🟢🟡🔴 dots on route line per WaypointCondition |
| TASK-8.13 | Frontend build + full integration test |

---

## Update discipline

After every task:
1. Append one line to `docs/PROGRESS.md`
2. Commit with task ID: `git commit -m "TASK-X.Y: what was done"`
3. Run the task's verification step before marking done
