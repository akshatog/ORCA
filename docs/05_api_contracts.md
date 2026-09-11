# ORCA — API Contracts

Every endpoint below is what the system exposes. The old `/api/chat` path remains
for backward compatibility with the existing frontend. The new ORCA 2.0 endpoints
(`/plan`, `/trace`, `/voyages`, `/alerts`) are the canonical API going forward.

---

## ORCA 2.0 API (new endpoints)

### `POST /plan`
The primary decision endpoint. Replaces `/api/chat` for new consumers.

Request:
```json
{ "location": {"lat": 19.07, "lon": 72.87}, "intent_text": "can I fish tomorrow?", "language": "hi-IN" }
```
Response: full `DecisionState` (see `02_schemas.md`).

### `GET /trace/{request_id}`
Returns the `ORCAState.trace` list for that request — powers the research
web's agent-trace view. Each entry:
```json
{"node_name": "weather", "input_summary": "...", "output_summary": "...", "timestamp": "..."}
```

### `POST /voyages/start`
Start tracking an active voyage for alert monitoring.

Request:
```json
{ "location": {"lat": 19.07, "lon": 72.87}, "region_geometry": null }
```
Response:
```json
{ "voyage_id": "v-abc123", "started_at": "2026-09-10T06:00:00+05:30" }
```

### `GET /voyages/active`
Returns all active voyages the alert system is monitoring.

Response:
```json
[{ "voyage_id": "v-abc123", "location": {"lat": 19.07, "lon": 72.87}, "started_at": "...", "status": "ACTIVE", "last_decision": {...} }]
```

### `POST /voyages/{voyage_id}/end`
Stop tracking a voyage.

Response: `{ "status": "ended" }`

### `POST /alerts/trigger`
Manually inject new evidence and trigger `on_evidence_change`. For demo use —
simulates a new advisory arriving while a voyage is active.

Request:
```json
{ "evidence": { "metric": "advisory_no_go", "value": "severe_warning", "source": "IMD", ... } }
```
Response:
```json
{ "alerts": [{ "voyage_id": "v-abc123", "previous_status": "SAFE", "new_status": "UNSAFE", "reason": "...", "safe_port": {...} }] }
```

---

## Legacy API (still working, used by existing frontend)

These endpoints remain functional. The existing frontend calls them directly.

### `POST /api/chat`
The old chat endpoint. Request: `ChatRequest`, Response: `ChatResponse`.
Internally uses `planner.py::handle()`.

### `POST /api/chat/stream`
SSE streaming version of `/api/chat`. Yields agent events then final response.

### `GET /api/fishing?lat=&lon=&language=`
Fishing conditions: ranked PFZ zones, trip economics, species, safe window.

### `GET /api/forecast?lat=&lon=&hours=`
Hourly forecast for risk timeline.

### `GET /api/authority/dashboard`
All ports scored — the research web monitoring view.

### `GET /api/map/zones`
Geofence zones as GeoJSON features for map rendering.

### `GET /api/routes?from_lat=&from_lon=&to_lat=&to_lon=`
Route options (safest/shortest/alternate) with risk scores.

### `GET /api/field?bbox=&nx=&ny=`
Wind/current/SST grid for sea-in-motion flow visualization.

### `GET /api/health`
Health check with agent list, version, data mode.

### `POST /api/mode`
Toggle between LIVE and DEMO data mode.

---

## Data layer internal endpoints

These are internal functions called by agents, not HTTP endpoints:

### `on_evidence_change(new_evidence: Evidence) -> list[AlertEvent]`
Called by the data layer's scheduler (or manual trigger) when fresh evidence
arrives. Iterates active voyages, re-runs constraint engine, returns AlertEvents.

---

## Frontend → Backend contract

| Surface | Endpoints used |
|---|---|
| Fisherman app (Today tab) | `/api/fishing`, `/api/chat`, `/plan`, `/voyages/*` |
| Fisherman app (Ask tab) | `/api/chat`, `/api/chat/stream` |
| Fisherman app (Map) | `/api/map/zones`, `/api/field`, `/api/routes` |
| Research web (Authority) | `/api/authority/dashboard` |
| Research web (Trace) | `/trace/{id}` |
| Research web (Evidence) | `/plan` response includes full evidence list |
| Alert system | `/voyages/*`, `/alerts/trigger` |
