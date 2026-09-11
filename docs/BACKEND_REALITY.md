# ORCA Backend Reality Document

> **Read-only discovery pass — no code was modified to produce this document.**
> Generated: 2026-09-11. Cites exact paths throughout.

---

## 1. LangGraph Structure

### 1.1 Graph File Locations

- Graph definition: `backend/app/graph/graph.py`
- State schema: `backend/app/graph/state.py`
- Node implementations: `backend/app/graph/nodes.py`

### 1.2 Execution Topology

```
START ? intent
intent ? [weather, ocean, pfz, cyclone, gis]   ? parallel fan-out (5 workers)
[weather, ocean, pfz, cyclone, gis] ? evidence_store   ? fan-in
evidence_store ? conflict_resolver ? constraint_engine ? route ? explanation ? END
```

**No conditional branches exist.** All edges are deterministic. The `intent` field (`operational` vs `analytical`) is computed but does NOT currently route differently — all queries traverse the same node sequence.

### 1.3 Node Descriptions (in execution order)

| # | Node | Function | What it does |
|---|---|---|---|
| 1 | `intent` | `intent_node()` | Calls `intent_agent.run()` — parses query language, resolves location, classifies intent as `operational` or `analytical` |
| 2a | `weather` | `weather_node()` | Calls `weather_agent.run()` — returns wind_speed, rain_probability, visibility measurements |
| 2b | `ocean` | `ocean_node()` | Calls `ocean_agent.run()` — returns wave_height, wave_period, SST |
| 2c | `pfz` | `pfz_node()` | Calls `pfz_agent.run()` — returns PFZ zones; each zone also inserted as `Evidence(metric="pfz_zone")` |
| 2d | `cyclone` | `cyclone_node()` | Calls `cyclone_agent.run()` — if cyclone active, creates `AdvisoryConstraint(NO_GO, SEVERE)` |
| 2e | `gis` | `gis_node()` | Calls `gis_agent.run()` — inserts `distance_from_shore_km`, `nearest_zone_km`, `inside_restricted_zone` as Evidence records |
| 3 | `evidence_store` | `evidence_store_node()` | Pass-through — logs evidence count, no dedup/reduction |
| 4 | `conflict_resolver` | `conflict_resolver_node()` | Calls `services/conflict_resolver.py::resolve_conflicts()` — appends conflicts to `conflict_log`. Does NOT write reconciled evidence back (BE-003) |
| 5 | `constraint_engine` | `constraint_engine_node()` | Extracts named metrics from evidence dict; calls `risk_engine.assess()` full breakpoint-curve model; builds `DecisionState` |
| 6 | `route` | `route_node()` | Picks best PFZ zone by confidence; calls `route_agent.run()` for waypoints; computes trip economics (fuel, catch, revenue) |
| 7 | `explanation` | `explanation_node()` | Calls `services/llm.py::complete_chat()` for 2-3 sentence narrative in requested language; falls back to template string if LLM fails |

### 1.4 ORCAGraphState — Full Field List

```python
class ORCAGraphState(BaseModel):
    request_id: str
    intent: Literal["operational", "analytical"] = "operational"
    raw_query: str = ""
    language: str = "en"
    location: Optional[dict] = None
    evidence: Annotated[List[Evidence], operator.add]      # fan-in reducer
    advisories: Annotated[List[AdvisoryConstraint], operator.add]  # fan-in reducer
    conflict_log: Annotated[List[dict], operator.add]      # fan-in reducer
    decision: Optional[DecisionState] = None
    trace: Annotated[List[dict], operator.add]             # fan-in reducer
```

`operator.add` is the LangGraph fan-in mechanism: each parallel node returns a partial list, LangGraph merges them after all 5 specialists complete.

---

## 2. API Surface — Current Reality

All routers registered in `backend/app/main.py`.

### 2.1 Routing Conventions

- Most routes use `prefix="/api"` inside their router — registered at `/api/*` only.
- **Voice endpoints**: registered at BOTH `/voice/*` AND `/api/voice/*` (alias is `include_in_schema=False`).
- **Plan/Trace/Voyages**: registered at both `/plan` and `/api/plan` (same alias pattern).
- **Catch-all**: `GET /api/{rest_of_path:path}` ? JSON 404 (not HTML).

### 2.2 Complete Endpoint Inventory

#### Health & Config (`backend/app/main.py`, `backend/app/api/routes.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| GET | `/api/health` | — | `{status, version, data_mode, agents[]}` | `api.ts::health()` ? SystemPanel | ? Working |
| GET | `/api/config` | — | risk weights, thresholds, sources | `api.ts::config()` ? SystemPanel | ? Working |
| POST | `/api/config/mode` | `{mode: "LIVE"/"DEMO"}` | `{ok, data_mode, note}` | `api.ts::setMode()` ? App.tsx | ? Working |
| GET | `/api/scenarios` | — | 5 demo scenarios catalogue | **None** | ? No frontend consumer |

#### Chat (`backend/app/api/chat.py`, `backend/app/api/chat_stream.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| POST | `/api/chat` | `ChatRequest` | `ChatResponse` | `api.ts::ask()` ? MobileApp Ask tab | ? Working |
| POST | `/api/chat/stream` | `ChatRequest` | SSE stream: `thinking/agent_done` events + `done:ChatResponse` | `api.ts::askStream()` ? ChatPanel.tsx | ? Working |
| POST | `/api/chat/reset` | `?session_id=` | `{ok, session_id}` | `api.ts::resetSession()` — wired but not exposed in UI | ?? Available, not surfaced |

#### Fishing Outlook (`backend/app/api/fishing.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| GET | `/api/fishing` | `?lat&lon&radius_km&days&lang` | Full FishingOutlook dict | `api.ts::fishingOutlook()` ? MobileApp Today + FishingPanel | ? Working |

#### Forecast & Risk (`backend/app/api/forecast.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| GET | `/api/forecast` | `?lat&lon&when?` | `{location, weather AgentResult, ocean AgentResult}` | `api.ts::forecast()` ? SystemPanel | ? Working |
| GET | `/api/risk` | `?lat&lon&when?` | Full risk assessment + agent inputs | **None** | ? No frontend consumer |
| GET | `/api/risk/timeline` | `?lat&lon&hours` | `{points[{hour,score,category,wave,wind,warning}]}` | `api.ts::riskTimeline()` ? RiskTimeline | ? Working |
| GET | `/api/position` | `?lat&lon` | `PositionCheck` (status, geofence_alerts, distances) | `api.ts::checkPosition()` ? MarineMap drag | ? Working |

#### Alerts & Authority (`backend/app/api/alerts.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| GET | `/api/alerts` | `?lat&lon` | `{marine_alerts, geofence_alerts}` | **None** | ? No frontend consumer |
| GET | `/api/authority/dashboard` | — | `{summary{}, locations[]}` | `api.ts::authority()` ? AuthorityPanel | ? Working |
| POST | `/api/alerts/trigger` | `TriggerAlertRequest` | `{alerts: AlertEvent[]}` | `api.ts::triggerAlert()` ? VoyageTracker | ? Working |

#### Map Layers (`backend/app/api/map.py`, `backend/app/api/field.py`, `backend/app/api/routes.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| GET | `/api/map/zones` | — | GeoJSON restricted zones | `api.ts::zones()` ? MarineMap + MobileApp | ? Working |
| GET | `/api/map/ports` | — | GeoJSON port markers | **None** | ? No frontend consumer |
| GET | `/api/map/pfz` | `?lat&lon&count` | GeoJSON PFZ point features | **None** | ? No frontend consumer |
| GET | `/api/field` | `?min_lat&max_lat&min_lon&max_lon&nx&ny` | Grid `{wind_u,wind_v,cur_u,cur_v,sst,sea}` + land mask | `api.ts::flowField()` ? MarineMap animation | ? Working |
| POST | `/api/routes` | `{start_lat,start_lon,dest_lat,dest_lon,dest_name}` | Route options dict | **None** | ? No frontend consumer |

#### ORCA 2.0 Plan / Trace / Voyage (`backend/app/api/plan.py`, `backend/app/api/voyages.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| POST | `/plan` + `/api/plan` | `PlanRequest {query,location,language}` | `DecisionState` | `api.ts::fetchPlan()` ? App.tsx Ops tab | ? Working |
| GET | `/trace/{id}` + `/api/trace/{id}` | path param | `List[TraceEntry]` | `api.ts::fetchTrace()` ? DecisionPipelineVisualizer | ? Working |
| GET | `/state/{id}` + `/api/state/{id}` | path param | `ORCAState` | `api.ts::fetchState()` ? EvidenceProvenancePanel, ConflictLogPanel | ? Working |
| POST | `/voyages/start` + `/api/voyages/start` | `StartVoyageRequest` | `StartVoyageResponse` | `api.ts::startVoyage()` ? VoyageTracker | ? Working |
| GET | `/voyages/active` + `/api/voyages/active` | — | `List[Voyage]` | `api.ts::getActiveVoyages()` ? App.tsx + MobileApp | ? Working |
| POST | `/voyages/{id}/end` + `/api/voyages/{id}/end` | path param | `EndVoyageResponse` | `api.ts::endVoyage()` ? VoyageTracker | ? Working |

#### Voice (`backend/app/api/voice.py`)

| Method | Path | Request | Response | Frontend consumer | Status |
|---|---|---|---|---|---|
| POST | `/voice/transcribe` + `/api/voice/transcribe` | `multipart: file + language` | `{transcript, language, engine}` | `api.ts::transcribeVoice()` ? useVoiceRecorder | ? BROKEN — Sarvam rejects audio/webm |
| POST | `/voice/speak` + `/api/voice/speak` | `{text, language, voice_id}` | Raw WAV bytes `audio/wav` | `api.ts::speakText()` ? MobileApp + ChatPanel | ? Working |

---

## 3. Data Model — Pydantic Schemas

All canonical schemas consolidated into: `backend/app/schemas.py` (via ARCH-001).

### 3.1 Core Shared Types

| Schema | Key Fields |
|---|---|
| `Location` | `name, latitude, longitude, state?` |
| `Provenance` | `source, timestamp, mode, confidence?, note?` |
| `Measurement` | `value?, unit, label, provenance` |
| `AgentResult` | `agent, ok, location?, data{}, measurements{}, risk?, unavailable[], source, timestamp, confidence?, mode, latency_ms?, error?` |

### 3.2 Chat Pipeline Schemas

| Schema | Key Fields |
|---|---|
| `ChatRequest` | `message, language?, latitude?, longitude?, location_name?, session_id` |
| `Intent` | `intent, activity, location?, location_text, date?, time?, language, raw_query, needs[], missing[]` |
| `RiskFactor` | `key, label, factor, weight, contribution, detail` |
| `RiskAssessment` | `score, category, factors[], overrides[], official_warning, go, headline, advice, window?, sources[], generated_at, mode` |
| `PFZZone` | `rank, latitude, longitude, distance_km, bearing, sst_c?, chlorophyll_mg_m3?, wave_height_m?, confidence, rationale, source, timestamp` |
| `RouteOption` | `name, kind, legs[], distance_km, eta_minutes, risk_score, risk_category, penalties{}, recommended, notes, waypoint_conditions[]` |
| `GeofenceAlert` | `zone_name, zone_type, distance_km, inside, severity, message` |
| `EvidenceRow` | `label, value, source, timestamp, confidence?, mode` — "why table" row in ChatResponse |
| `AgentTrace` | `agent, status, latency_ms, summary, source, mode` |
| `ChatResponse` | `session_id, language, answer, intent, risk?, pfz[], routes[], geofence[], alerts[], evidence[], trace[], suggestions[], mode, disclaimer, explanation_source, elapsed_ms` |

### 3.3 ORCA 2.0 Pipeline Schemas

| Schema | Key Fields |
|---|---|
| `Evidence` | `metric, value, unit?, source, observed_at, retrieved_at, valid_from?, valid_until?, geometry?, confidence[0-1], authority_level, mode, conflict_status?, conflict_reason?` |
| `AdvisoryConstraint` | `authority, constraint_type, named_region, geometry?, severity, valid_from, valid_until, source_text, source_reference, confidence, localized_summaries{}` |
| `DecisionState` | `request_id?, status, risk_score, reasons[], active_advisories[], trip_window?, route?, trip_economics?, language, explanation, generated_at` |
| `AlertEvent` | `voyage_id, previous_status, new_status, reason, safe_port{}, triggered_at` |
| `ORCAState` | `request_id, intent, raw_query, language, location?, evidence[], advisories[], conflict_log[], decision?, trace[]` |

### 3.4 Schema Naming Conflicts / Ambiguities

| Name | Issue |
|---|---|
| `Evidence` | **One canonical definition** in `schemas.py`. `Evidence_v2 = Evidence` is a kept-for-compat alias. |
| `EvidenceRow` | The OLD "why table" row (`label/value/source` strings). Legitimately different from `Evidence` (the typed metric wrapper). Both exist. |
| `frontend/types.ts::Evidence` | Maps to `EvidenceRow` shape (label/value/source string fields). |
| `frontend/types.ts::Evidence_v2` | Maps to the ORCA 2.0 `Evidence` schema (metric/confidence/authority_level etc.). |

---

## 4. Voice Layer — Exact Implementation

### 4.1 STT — `POST /voice/transcribe`

**File:** `backend/app/api/voice.py`

```python
@router.post("/voice/transcribe", response_model=TranscribeResponse)
@router.post("/api/voice/transcribe", ...)   # alias
async def transcribe_endpoint(file: UploadFile = File(...), language: str = Form("hi-IN")):
    audio_bytes = await file.read()
    text = transcribe(
        audio_bytes,
        language_hint=language,
        filename=file.filename or "audio.wav",
        content_type=file.content_type or "audio/wav",
    )
    return TranscribeResponse(transcript=text, language=normalize_language_code(language), engine="sarvam_saaras")
```

**Service:** `backend/app/services/voice.py::transcribe()`

```python
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

files = {"file": (filename, audio_bytes, content_type)}
data = {"model": "saaras:v3", "language_code": locale}
headers = {"api-subscription-key": SARVAM_API_KEY}
resp = httpx.Client(timeout=12).post(SARVAM_STT_URL, headers=headers, files=files, data=data)
```

- **Auth env var:** `SARVAM_API_KEY` from `.env` — confirmed set and valid.
- **Success:** Returns `resp.json()["transcript"].strip()` ? `TranscribeResponse`
- **Failure:** `RuntimeError` ? HTTP 500 `{error: str, browser_fallback: true}`
- **Missing key:** `ValueError` ? HTTP 503 `{error: "SARVAM_API_KEY not configured", browser_fallback: true}`

> **?? CRITICAL BUG (STT-001):** Sarvam Saaras v3 only accepts these MIME types:
> `audio/mpeg, audio/mp3, audio/wav, audio/x-wav, audio/wave, audio/pcm_s16le, audio/ogg`
> **It does NOT accept `audio/webm`.**
> The frontend `useVoiceRecorder` hook uses `MediaRecorder` which defaults to `audio/webm;codecs=opus` in Chrome.
> This causes every transcribe call to return HTTP 400.

### 4.2 TTS — `POST /voice/speak`

**File:** `backend/app/services/voice.py::speak()`

```python
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
payload = {
    "inputs": [text[:500]],
    "target_language_code": locale,
    "speaker": chosen_speaker,     # default "aditya"
    "model": "bulbul:v3",
    "speech_sample_rate": 16000,
    "enable_preprocessing": True,
}
resp = httpx.Client(timeout=12).post(SARVAM_TTS_URL, headers=headers, json=payload)
audio_bytes = base64.b64decode(resp.json()["audios"][0])
```

- **On success:** Returns raw WAV bytes; endpoint returns `Response(content=audio_bytes, media_type="audio/wav")`
- **Status:** ? Confirmed working.
- **Speakers available:** `aditya, ritu, ashutosh, priya, neha, rahul, pooja, rohan, simran, kavya, amit, dev`

---

## 5. Mock Data / Source Registry

### 5.1 Demo Store (`backend/app/data/demo_store.py`)

Pure-Python in-memory store. No disk reads at runtime. Keyed by **hour of day** (not date), so "tomorrow 6 AM" and "today 6 AM" resolve to the same conditions — intentional for demo reliability.

**5 scenarios, each keyed to a port:**

| Port | Scenario | Risk level |
|---|---|---|
| Mumbai | `rough_clearing` | HIGH morning, clears after 11:00 |
| Goa | `calm` | LOW all day |
| Paradip | `cyclone` | EXTREME — official severe warning |
| Kochi | `moderate_pfz` | MODERATE — excellent PFZ zones |
| Digha | `rough_high` | HIGH all day |

**Data shape per keyframe:**
```python
{hour: {"wave": float, "period": float, "wind": float, "wind_dir": float,
        "rain": float, "visibility": float, "sst": float, "current": float, "chl": float}}
```

**Flow into pipeline:**
1. Agent calls `demo_store.conditions(port_name, dt)` in DEMO mode
2. `conditions()` looks up scenario via `PORT_SCENARIO[port_name]`, linearly interpolates between hourly keyframes
3. Agent wraps returned values in `Measurement` objects ? `AgentResult`
4. `agent_result_to_evidence_list()` converts to `Evidence` records for graph

**Plugging in a live source:**  
Each agent has `if get_data_mode() == "LIVE"` branch calling `live_client.py` (Open-Meteo) or `stormglass_client.py` (StormGlass). Toggle with `POST /api/config/mode {"mode": "LIVE"}`. The return shape of each agent remains identical — only the source of numbers changes.

**PFZ zones:** `demo_store.pfz_zones()` generates synthetic zones from configurable offsets around the nearest port. Live replacement: call INCOIS API, return same `List[Dict]` shape with `{latitude, longitude, distance_km, bearing, sst_c, chlorophyll_mg_m3, wave_height_m}`.

---

## 6. Frontend Component Inventory

### 6.1 Desktop App — App.tsx + all components

| Component | File | Backend endpoints called | Status |
|---|---|---|---|
| `Landing` | `Landing.tsx` | None (static marketing page) | ? Keep |
| `App.tsx` orchestration | `App.tsx` | `/api/fishing`, `/api/map/zones`, `/api/authority/dashboard`, `/api/health`, `/plan`, `/trace/{id}`, `/state/{id}`, `/voyages/active` | ? Working |
| `FishingPanel` | `FishingPanel.tsx` | Props only — no direct fetch | ? Keep |
| `MarineMap` | `MarineMap.tsx` | `/api/field` (grid), `/api/position` (on drag) | ? Working |
| `ChatPanel` | `ChatPanel.tsx` | `/api/chat/stream` (SSE) | ? Working |
| `AuthorityPanel` | `AuthorityPanel.tsx` | `/api/authority/dashboard` | ? Working |
| `SystemPanel` | `SystemPanel.tsx` | `/api/forecast`, `/api/config`, `/api/config/mode` | ? Working |
| `RiskTimeline` | `RiskTimeline.tsx` | `/api/risk/timeline` | ? Working |
| `AgentTracePanel` | `AgentTrace.tsx` | Props from ChatPanel SSE stream | ? Keep |
| `EvidenceProvenancePanel` | `EvidenceProvenancePanel.tsx` | `/api/state/{id}` | ? Working |
| `ConflictLogPanel` | `ConflictLogPanel.tsx` | `/api/state/{id}` | ?? Wired, but `conflict_log` always empty (BE-003) |
| `DecisionPipelineVisualizer` | `DecisionPipelineVisualizer.tsx` | `/api/trace/{id}` | ? Working |
| `VoyageTracker` | `VoyageTracker.tsx` | `/voyages/start`, `/voyages/{id}/end`, `/alerts/trigger` | ? Working |
| `AlertBanner` | `AlertBanner.tsx` | Props only | ? Keep |
| `PFZList` | `PFZList.tsx` | Props from App.tsx | ? Keep |
| `RiskCard` | `RiskCard.tsx` | Props only | ? Keep |
| `ConditionsStrip` | `ConditionsStrip.tsx` | Props only | ? Keep |
| `RiskDial` | `RiskDial.tsx` | Props only | ? Keep |
| `GuidedTour` | `GuidedTour.tsx` | None | ? Keep |
| `LocationPicker` | `LocationPicker.tsx` | None (static port list) | ? Keep |
| `FlowLayer` | `FlowLayer.ts` | Called from MarineMap | ? Keep |
| `glyphs` | `glyphs.tsx` | None | ? Keep |

**Components to delete:** None. Every component has a legitimate purpose. `ConflictLogPanel` needs BE-003 to show data, but the component itself is correct.

### 6.2 Mobile App — MobileApp.tsx (3 tabs)

| Tab | Endpoints | Status |
|---|---|---|
| Today (boat icon) | `/api/fishing`, `/api/map/zones`, `/voyages/active`, `/voyages/{id}/end`, `/voyages/start` | ? Working |
| Map | `/api/field` via MarineMap sub-component | ? Working |
| Ask (mic icon) — text | `/api/chat` (non-streaming) | ? Working |
| Ask — voice input (STT) | `/api/voice/transcribe` via useVoiceRecorder | ? BROKEN (webm format rejection) |
| Ask — voice output (TTS) | `/api/voice/speak` — auto-plays answer | ? Working |

---

## 7. Backend Capabilities With No Frontend Consumer

These endpoints are fully working but have zero frontend calls — capabilities judges cannot currently see.

| Endpoint | Potential UI | Effort |
|---|---|---|
| `GET /api/risk` | Per-location full risk breakdown card | Low |
| `GET /api/alerts?lat&lon` | Live geofence + marine alert card on mobile | Low |
| `GET /api/map/ports` | Port markers layer on MarineMap | Low |
| `GET /api/map/pfz?lat&lon` | PFZ zone GeoJSON layer on MarineMap | Low |
| `GET /api/scenarios` | Demo scenario picker button in UI | Low |
| `POST /api/routes` | Point-to-point route planner panel | Medium |
| `GET /api/risk/timeline` on mobile | Risk chart in MobileApp Today tab | Low — RiskTimeline component exists |
| `/api/chat/reset` button | "New conversation" button in ChatPanel | Low |

---

## 8. Known Gaps and Open Issues

| ID | Issue | Severity |
|---|---|---|
| **STT-001** | `useVoiceRecorder` records `audio/webm;codecs=opus` (Chrome default). Sarvam Saaras v3 rejects it (HTTP 400). Fix: convert to WAV in browser via `AudioContext.decodeAudioData()` before upload, or use `SpeechRecognition` as primary (non-Sarvam). | ?? High |
| **BE-003** | `conflict_resolver_node` writes to `conflict_log` but does NOT write reconciled evidence back into state. `constraint_engine_node` runs on raw possibly-conflicting evidence. `ConflictLogPanel` always shows empty. | ?? Medium |
| **API-001** | `MobileApp.tsx Ask` tab uses non-streaming `POST /api/chat`. Desktop `ChatPanel.tsx` uses SSE `POST /api/chat/stream`. Mobile users miss the live agent-by-agent progress indicator. | ?? Medium |
| **FE-001** | `checkPosition()` / `/api/position` not called in MobileApp — mobile users get no geofence warnings while moving on map. | ?? Medium |
