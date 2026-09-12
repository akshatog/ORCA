# ORCA 2.0 — Live Data Implementation Plan

> Planning document only. No runtime code is changed by this document.
>
> This plan is aligned to `AGENT.md`, the completed audit/blueprint, `docs/AUDIT_AND_STATUS.md`, `docs/BACKEND_REALITY.md`, the current backend, and the frozen safety rule: LLMs may interpret narrative text and explain results, but may not decide safety, perform GIS math, validate time/geometry, or override deterministic constraints.

## 1. Current-state diagnosis

ORCA has two supported request paths:

- `POST /api/chat`: legacy, demo-critical path through `agents/planner.py`.
- `POST /plan` and `/api/plan`: LangGraph path through `graph/nodes.py`.

Both use the same specialist agents and deterministic `services/risk_engine.py`. The current data layer is not yet an honest, field-level live-data system:

1. Open-Meteo is the only provider directly used by weather/ocean agents.
2. GDACS, IMD, INCOIS, and StormGlass code exists, but agents do not consistently consume it through a shared broker.
3. `data/scheduler.py` exists but is not started by FastAPI lifespan.
4. Existing caches and `/plan` state are process-memory only; restart or another worker loses them.
5. `cyclone_agent.py` and `pfz_agent.py` always use demo fixtures.
6. `ocean_agent.py` can combine live wave/SST with demo current/chlorophyll while labeling the aggregate result `LIVE`.
7. `weather_agent.py` silently falls back to demo values when live retrieval fails.
8. `stormglass_client.py` generates fallback estimates and caches them, which can blur synthetic and observed data.
9. `advisory_scraper.py` contains hard-coded IMD/INCOIS product URLs that have not been manually verified for stability, terms, or machine-use permission.
10. `source_registry.py` is an in-memory capability catalogue, not a deterministic field selector.
11. There is no durable last-known-good (LKG) evidence store, scheduler lease, source health model, or field-level provenance ladder.
12. MOSDAC and Coast Guard/manual advisory ingestion are absent.

The implementation must therefore add a parallel evidence acquisition layer without rewriting protected safety/demo components.

## 2. Goals and non-goals

### Goals

- Produce one typed evidence record per metric, location/geometry, and valid time.
- Select evidence deterministically using `LIVE → CACHED → STALE → INSUFFICIENT`.
- Persist raw fetch metadata, normalized evidence, LKG values, source health, and scheduler leases in SQLite.
- Keep demo data explicitly isolated behind a required `scenario_id`; never use demo as an implicit live fallback.
- Make source/product URLs configurable and default-disabled where not manually verified.
- Start refresh jobs through FastAPI lifespan with multi-worker-safe SQLite leases.
- Preserve `/api/chat`, `/api/plan`, `/plan`, response schemas, risk behavior, and frontend expectations.
- Expose operational health without leaking secrets or full upstream payloads.
- Make every safety-relevant value traceable to source, observation time, retrieval time, validity, confidence, and mode.

### Non-goals

- No rewrite of the risk engine, route optimizer, geometry, legacy planner, demo store, or frontend design system.
- No new safety thresholds or schema-field changes without a prior `DECISIONS.md` entry.
- No claim that PFZ detects fish; it remains a potential-zone recommendation.
- No unapproved scraping, CAPTCHA bypass, authentication circumvention, or invented stable government endpoints.
- No silent synthetic estimates in LIVE mode.
- No distributed database in the demo phase; SQLite is the durable single-host LKG and coordination store.
- No guarantee of historical reanalysis or nationwide gridded ingestion in the immediate demo milestone.

## 3. Target architecture

```mermaid
flowchart TD
    Q[API request or scheduled refresh] --> C[DataBroker]
    C --> R[Source registry + data_sources.yaml]
    R --> A[Enabled adapters]
    A --> OM[Open-Meteo]
    A --> GD[GDACS]
    A --> SG[StormGlass]
    A --> IMD[IMD verified product]
    A --> INC[INCOIS verified product]
    A --> MOS[MOSDAC batch import]
    A --> CG[Coast Guard/manual advisory import]

    OM & GD & SG & IMD & INC & MOS & CG --> N[Normalize to field-level Evidence]
    N --> DB[(SQLite evidence store)]
    DB --> P[Deterministic SelectionPolicy]
    P -->|LIVE/CACHED/STALE| E[Selected Evidence bundle]
    P -->|none acceptable| I[INSUFFICIENT]

    D[DemoScenarioProvider] -->|only when mode=DEMO and scenario_id supplied| E
    E --> W[Weather/Ocean/PFZ/Cyclone agents]
    W --> G[LangGraph and legacy adapters]
    G --> RE[Protected deterministic risk engine]
    RE --> API[/api/chat and /api/plan]

    L[FastAPI lifespan scheduler] --> LEASE[(SQLite leases)]
    LEASE --> C
    DB --> H[/api/health/data]
```

### Architectural invariants

1. Adapters fetch and normalize; they do not choose winners or decide safety.
2. `SelectionPolicy` is pure and deterministic.
3. `DataBroker` is the only new entry point agents use for external evidence.
4. Demo evidence is never written as an LKG candidate for live selection.
5. A mixed bundle retains per-field modes; no aggregate `LIVE` label is inferred from one live field.
6. Official advisories can outrank forecasts through existing conflict/safety policy, but only after validity and geometry checks performed deterministically.
7. Failed refreshes never overwrite a valid LKG record.

## 4. Deterministic live → cached → stale → insufficient ladder

Selection is per metric, spatial key, and requested time—not per agent response.

### Definitions

- **LIVE**: a successful upstream response obtained during the current broker operation, normalized and valid for the request.
- **CACHED**: a previously successful LKG record whose age is within the source/metric `fresh_ttl_seconds` and whose validity window covers the request.
- **STALE**: an LKG record older than fresh TTL but no older than `max_stale_seconds`, still structurally valid, and not explicitly expired by `valid_until`.
- **INSUFFICIENT**: no eligible live, cached, or permitted stale evidence exists. This is a selection outcome, not fabricated evidence and not DEMO.
- **DEMO**: evidence returned only by `DemoScenarioProvider` when the caller explicitly selects DEMO and supplies a valid `scenario_id`.

### Selection order

For each required metric:

1. Reject disabled sources, malformed records, impossible units/ranges, invalid geometry, future-skewed observations, and records outside `valid_from/valid_until`.
2. If the request permits network access, query enabled adapters in configured priority order, respecting circuit breaker, quota, and timeout.
3. Among successful current-fetch candidates, select by:
   1. authority rank,
   2. configured source priority,
   3. observation-time proximity to requested time,
   4. retrieval time,
   5. stable source ID lexical tie-break.
4. If no current candidate, select the best fresh LKG and label `CACHED`.
5. If no fresh LKG, select the best allowed stale LKG and label `STALE`; attach age and stale reason.
6. Otherwise return `INSUFFICIENT` for that metric.
7. Required safety metrics missing after selection force the existing decision path to `INSUFFICIENT_EVIDENCE`; optional enrichment metrics remain unavailable and must not be synthesized.

### Required minimum evidence

Initial gate for a fishing-safety decision:

- wave height,
- wind speed,
- active official/cyclone advisory status (a successful “none active” poll is evidence),
- location and requested time.

Rain, visibility, wave period, SST, current, chlorophyll, and PFZ may enrich the result but cannot be silently invented. The exact required set must be configurable by intent and documented before implementation; changing safety semantics requires a `DECISIONS.md` entry.

### Staleness policy

Defaults are conservative starting values, configurable per source/metric:

| Data class | Fresh TTL | Maximum stale use | Notes |
|---|---:|---:|---|
| Open-Meteo forecast | 30 min | 3 hr | Must still cover requested forecast time |
| GDACS events | 15 min | 60 min | Expired/closed events are never reused |
| StormGlass point data | 2 hr | 6 hr | Quota-aware; no synthetic fallback |
| IMD advisory | 1 hr | Until explicit validity end, capped at 6 hr without validity | Official validity wins |
| INCOIS PFZ/advisory | 6 hr | 24 hr | Product issue/validity metadata wins |
| MOSDAC batch product | Product cadence | One product cycle | Never label batch data LIVE |
| Manual advisory | Until `valid_until` | None after expiry | Requires issuer/reference/audit fields |

A stale official NO_GO remains active only while its explicit validity window covers the request. Missing validity must not be guessed into an indefinite warning.

## 5. Explicit demo isolation

- Add `DemoScenarioProvider` in `data/demo_scenarios.py` as a read-only wrapper around protected `demo_store.py`.
- DEMO calls require `scenario_id`; location/hour inference is retained only inside the legacy compatibility adapter until callers are migrated.
- LIVE mode never calls `demo_store`, `DemoScenarioProvider`, or synthetic StormGlass fallback.
- A failed live request returns cached/stale/insufficient—not demo.
- Demo records carry `mode=DEMO`, `source=DEMO:<scenario_id>`, deterministic timestamps/validity, and `scenario_id` in metadata.
- Demo records are stored separately or marked `is_demo=1`; selection SQL for live requests includes `is_demo=0`.
- `/api/config/mode` remains backward compatible, but its note must no longer promise demo fallback in LIVE mode.
- Add a startup assertion/test that no enabled live adapter imports `demo_store`.

## 6. Source-to-metric matrix

| Source | Metrics/products | Authority | Immediate role | Fallback/selection notes |
|---|---|---|---|---|
| Open-Meteo Forecast | wind speed/direction, rain probability, visibility, air temperature | external forecast | Primary weather | Keyless; attribution and rate limits honored |
| Open-Meteo Marine | wave height/period/direction, swell, SST; currents only if verified in returned product | external forecast | Primary marine | Preserve provider/model metadata per field |
| GDACS | tropical cyclone event, alert level, position/geometry, wind/category when present | external/official event aggregation | Primary cyclone event feed | Keyless; absence must be represented by successful poll metadata |
| StormGlass | current speed/direction, tide where licensed endpoint supports it, secondary wave/SST | external forecast | Quota-limited enrichment | API key; cache by grid/time; never per UI query if cache can answer |
| IMD | fisherman/coastal warnings, cyclone/marine bulletins | official advisory/forecast | Disabled until verified | URL/product configurable; no scraping until terms and format reviewed |
| INCOIS | PFZ advisories, ocean-state/advisory products, possibly verified services/downloads | official advisory/forecast | Disabled until verified | URL/product configurable; no assumed stable endpoint |
| MOSDAC | registered batch satellite/ocean products such as SST/chlorophyll when licensed | official forecast/derived product | Post-demo batch ingestion | Download/import only after registration and product verification |
| Coast Guard/manual | authorized navigation/safety advisories or syndication references | official advisory if authenticated/authorized | Manual ingestion | No confirmed public machine feed; require provenance and operator audit |

No source is authoritative for a metric merely because its adapter exists. Authority is configured per product and verified during onboarding.

## 7. Per-source implementation details

### 7.1 Open-Meteo

- Wrap existing protected `live_client.py`; do not rewrite it.
- Add adapters that translate its returned dictionaries into field-level evidence.
- Keep current timeout/cache behavior as an upstream optimization, but persist successful normalized values in SQLite.
- Validate requested variables against actual response fields; do not claim currents unless the configured Open-Meteo product returns them.
- Record model/provider metadata when available, request coordinates, forecast timestamp, retrieval timestamp, and attribution.
- Batch/round coordinates only where accuracy remains acceptable and the cache key records the rounding policy.
- On failure, broker selects SQLite LKG; adapter never calls demo data.

### 7.2 GDACS

- Move/wrap current GDACS parsing behind `adapters/gdacs.py`; protected `live_client.py` remains unchanged.
- Support verified public RSS/REST/GeoJSON formats through configuration.
- Normalize event ID, event type, alert level, status, geometry/position, issue/update time, and source reference.
- Deduplicate by upstream event ID plus update timestamp/content hash.
- Filter to relevant geography only after retaining raw event metadata.
- Emit both active-event evidence and a poll-success record so “no active cyclone” is distinguishable from “feed unavailable.”
- Trigger `on_evidence_change` only after a committed, materially changed normalized record.

### 7.3 IMD

- **All endpoint/product URLs remain configurable and disabled until manually verified. Do not invent or hard-code a stable endpoint.**
- Prefer a verified official API, CAP/RSS feed, or documented download. HTML/PDF scraping remains disabled pending terms review.
- Configuration must include product type, URL, enabled flag, parser version, expected content type, attribution, and terms-review reference.
- Archive content hash and source reference; store raw payload only if licensing permits.
- Parse deterministic metadata first. Narrative-to-constraint compilation may use the existing advisory compiler, but confidence below threshold yields insufficient evidence and never a safety downgrade.
- Require explicit validity; if absent, use a conservative configurable cap and flag `validity_inferred=true` for review.

### 7.4 INCOIS

- **All endpoint/product URLs remain configurable and disabled until manually verified. Do not invent or hard-code a stable endpoint.**
- Prefer verified official feeds/services/downloads. Scraping remains disabled pending terms and robots review.
- Separate adapters by product: PFZ advisory, ocean-state advisory, and any verified gridded service.
- PFZ parser must retain landing centre, bearing, distance/depth, issue time, validity, source reference, and geometry confidence.
- Convert named-location/bearing products to geometry only through deterministic GIS code; low-confidence geocoding does not become a recommended zone.
- PFZ ranking remains deterministic and restricted-zone filtering remains in existing GIS/PFZ logic.

### 7.5 StormGlass

- Require `STORMGLASS_API_KEY`; missing key means source disabled/unavailable, not synthetic fallback.
- Replace direct use of `_get_fallback_data` in the new adapter path with a typed failure.
- Track daily request budget, 402/429 responses, reset time, and circuit-breaker state in SQLite.
- Cache by rounded grid cell, requested time bucket, and parameter set.
- Schedule refreshes for active voyages and configured demo ports; avoid per-user upstream calls when an eligible cache exists.
- Preserve the selected StormGlass sub-provider for each field when the response contains multiple models.

### 7.6 MOSDAC

- **All endpoint/product URLs remain configurable and disabled until manually verified. Do not invent or hard-code a stable endpoint.**
- Treat as registered, official batch download—not an interactive request dependency.
- Implement a manifest-driven importer: product ID, file path, checksum, issue time, coverage, license, parser version.
- Store imported evidence as `CACHED`, never `LIVE`, because it is batch-delivered.
- Keep credentials outside YAML and logs. Do not automate login flows unless officially documented and permitted.
- Initial production-hardening target: SST/chlorophyll products only after product semantics and spatial resolution are validated.

### 7.7 Coast Guard/manual advisories

- **All endpoint/product URLs remain configurable and disabled until manually verified. Do not invent or hard-code a stable endpoint.**
- No confirmed public machine feed is assumed.
- Support authorized manual ingestion or verified IMD/INCOIS syndication only.
- Manual record requires authority, title, exact source reference, source text/excerpt, issue time, validity, severity, region/geometry, operator identity, ingestion time, and content hash.
- Require authenticated operator access and append-only audit history before production use.
- Manual advisories cannot be silently edited; corrections create a superseding record.

## 8. SQLite design

Default database: `backend/var/orca_data.sqlite3` (directory created at startup; database ignored by Git).

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

CREATE TABLE schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL,
  checksum TEXT NOT NULL
);

CREATE TABLE source_products (
  source_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 0,
  authority_level TEXT NOT NULL,
  priority INTEGER NOT NULL,
  endpoint_url TEXT,
  refresh_seconds INTEGER NOT NULL,
  fresh_ttl_seconds INTEGER NOT NULL,
  max_stale_seconds INTEGER NOT NULL,
  terms_status TEXT NOT NULL DEFAULT 'unverified',
  parser_version TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  PRIMARY KEY (source_id, product_id)
);

CREATE TABLE fetch_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  http_status INTEGER,
  latency_ms INTEGER,
  records_seen INTEGER NOT NULL DEFAULT 0,
  records_written INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT,
  error_class TEXT,
  error_message_redacted TEXT,
  worker_id TEXT,
  FOREIGN KEY (source_id, product_id)
    REFERENCES source_products(source_id, product_id)
);

CREATE TABLE evidence_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  metric TEXT NOT NULL,
  value_json TEXT NOT NULL,
  unit TEXT,
  source_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  upstream_record_id TEXT,
  observed_at TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  valid_from TEXT,
  valid_until TEXT,
  geometry_json TEXT,
  spatial_key TEXT NOT NULL,
  confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
  authority_level TEXT NOT NULL,
  original_mode TEXT NOT NULL,
  is_demo INTEGER NOT NULL DEFAULT 0,
  scenario_id TEXT,
  content_hash TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  fetch_run_id INTEGER,
  superseded_by INTEGER,
  created_at TEXT NOT NULL,
  UNIQUE(source_id, product_id, metric, spatial_key, observed_at, content_hash),
  FOREIGN KEY(fetch_run_id) REFERENCES fetch_runs(id),
  FOREIGN KEY(superseded_by) REFERENCES evidence_records(id)
);

CREATE INDEX idx_evidence_lookup
  ON evidence_records(metric, spatial_key, is_demo, observed_at DESC, retrieved_at DESC);
CREATE INDEX idx_evidence_validity
  ON evidence_records(valid_from, valid_until);

CREATE TABLE source_health (
  source_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  last_attempt_at TEXT,
  last_success_at TEXT,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  circuit_open_until TEXT,
  quota_remaining INTEGER,
  quota_reset_at TEXT,
  last_http_status INTEGER,
  last_error_class TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(source_id, product_id)
);

CREATE TABLE scheduler_leases (
  job_name TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  lease_until TEXT NOT NULL,
  heartbeat_at TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE manual_advisory_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  evidence_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  operator_id TEXT NOT NULL,
  reason TEXT,
  occurred_at TEXT NOT NULL,
  FOREIGN KEY(evidence_id) REFERENCES evidence_records(id)
);
```

Implementation rules:

- Store timestamps as UTC ISO-8601 strings.
- Use parameterized SQL only.
- Transactions wrap fetch-run completion and evidence writes.
- LKG means the newest eligible successful evidence record; no mutable “current value” row is required.
- Retention job deletes old non-advisory records only after configurable retention; audit/advisory records follow licensing and safety retention policy.
- Raw payload storage is optional and disabled by default; if enabled, use a separate table/file store with size limits and license controls.

## 9. Interfaces and pseudocode

```python
@dataclass(frozen=True)
class EvidenceQuery:
    metrics: tuple[str, ...]
    lat: float
    lon: float
    requested_at: datetime
    allow_network: bool = True
    allow_stale: bool = True
    mode: Literal['LIVE', 'DEMO'] = 'LIVE'
    scenario_id: str | None = None

@dataclass(frozen=True)
class SelectionResult:
    metric: str
    status: Literal['LIVE', 'CACHED', 'STALE', 'INSUFFICIENT', 'DEMO']
    evidence: Evidence | None
    reason: str
    age_seconds: int | None
    attempted_sources: tuple[str, ...]

class SourceAdapter(Protocol):
    source_id: str
    product_id: str
    def fetch(self, query: EvidenceQuery) -> list[Evidence]: ...

class EvidenceRepository(Protocol):
    def record_fetch(self, ...): ...
    def put_success(self, evidence: Sequence[Evidence], fetch_run_id: int): ...
    def candidates(self, metric: str, spatial_key: str, at: datetime): ...
    def health(self, source_id: str, product_id: str): ...

class SelectionPolicy:
    def select(self, query, live_candidates, cached_candidates) -> list[SelectionResult]: ...

class DataBroker:
    def get_evidence(self, query: EvidenceQuery) -> list[SelectionResult]: ...
```

Broker pseudocode:

```text
get_evidence(query):
  validate query
  if query.mode == DEMO:
      require query.scenario_id
      return demo_provider.get(query.scenario_id, query)

  assert query.scenario_id is None
  spatial_key = deterministic_spatial_key(query.lat, query.lon)
  live_candidates = []

  if query.allow_network:
    for adapter in registry.enabled_for(query.metrics):
      if health.circuit_open(adapter) or quota.exhausted(adapter): continue
      if repository.has_fresh_coverage(adapter, query): continue
      acquire per-source refresh lease or continue
      run_id = repository.start_fetch(adapter)
      try:
        records = adapter.fetch(query)
        validate and normalize every record
        repository.commit_success(run_id, records)
        live_candidates.extend(records)
      except TypedAdapterError as error:
        repository.commit_failure(run_id, redact(error))
      finally:
        release refresh lease

  cached = repository.candidates(query.metrics, spatial_key, query.requested_at)
  return selection_policy.select(query, live_candidates, cached)
```

Scheduler lease pseudocode:

```text
BEGIN IMMEDIATE
row = SELECT lease WHERE job_name = ?
if row absent or lease_until < now or owner_id == me:
    UPSERT owner_id=me, lease_until=now+lease_duration, heartbeat_at=now,
           generation=previous+1
    COMMIT; run job
else:
    ROLLBACK; skip
heartbeat while running
release by setting lease_until=now only if owner_id and generation still match
```

Agent compatibility pseudocode:

```text
weather_agent:
  results = broker.get_evidence(wind, rain, visibility, temperature)
  map each selected field to existing Measurement/AgentResult
  aggregate mode = worst/least-fresh status for compatibility only
  preserve field-level provenance in measurements
  never fill missing fields from demo in LIVE mode
```

## 10. Exact files to add/change

### Add

- `backend/app/data/models.py` — broker/query/result/internal typed models; do not duplicate frozen wire schemas.
- `backend/app/data/evidence_cache.py` — SQLite migrations, repository, transactions, retention.
- `backend/app/data/selection_policy.py` — pure deterministic ladder.
- `backend/app/data/broker.py` — orchestration and adapter isolation.
- `backend/app/data/demo_scenarios.py` — explicit scenario provider wrapping protected demo store.
- `backend/app/data/adapters/__init__.py`
- `backend/app/data/adapters/base.py`
- `backend/app/data/adapters/open_meteo.py`
- `backend/app/data/adapters/gdacs.py`
- `backend/app/data/adapters/stormglass.py`
- `backend/app/data/adapters/imd.py`
- `backend/app/data/adapters/incois.py`
- `backend/app/data/adapters/mosdac.py`
- `backend/app/data/adapters/manual_advisory.py`
- `backend/config/data_sources.yaml`
- `backend/tests/test_evidence_cache.py`
- `backend/tests/test_selection_policy.py`
- `backend/tests/test_data_broker.py`
- `backend/tests/test_demo_isolation.py`
- `backend/tests/test_lifespan_scheduler.py`
- `backend/tests/test_source_adapters.py`
- `backend/tests/fixtures/data_sources/` — licensed/synthetic parser fixtures only.

### Change

- `backend/app/data/source_registry.py` — load validated product config and adapter factories; retain old functions during migration.
- `backend/app/data/scheduler.py` — broker refresh jobs, leases, idempotent start/stop, no direct demo fallback.
- `backend/app/main.py` — FastAPI lifespan startup/shutdown, migrations, scheduler, expanded health route.
- `backend/app/config.py` — typed env/config access; update LIVE semantics to no demo fallback.
- `backend/app/agents/weather_agent.py` — broker-backed field evidence with compatibility envelope.
- `backend/app/agents/ocean_agent.py` — remove mixed live/demo labeling; broker-backed fields.
- `backend/app/agents/cyclone_agent.py` — broker-backed GDACS/advisory evidence; explicit demo provider only.
- `backend/app/agents/pfz_agent.py` — broker-backed verified PFZ evidence; explicit demo provider only.
- `backend/app/graph/nodes.py` — consume field evidence and propagate insufficient status without changing deterministic safety logic.
- `backend/app/api/plan.py` — optional `scenario_id`, compatibility behavior, and evidence status headers/metadata only if schema permits.
- `backend/app/api/routes.py` — mode semantics, source-health/config output, no claim of demo fallback in LIVE.
- `backend/app/data/advisory_scraper.py` — remove hard-coded active defaults; parser utilities only; verified URLs from config.
- `backend/app/data/stormglass_client.py` — new adapter path returns typed unavailable instead of synthetic fallback; retain legacy behavior only behind compatibility flag until migrated.
- `backend/requirements.txt` — add only required scheduler/parser dependencies actually imported (current code uses APScheduler, BeautifulSoup, pdfplumber but requirements do not list them).
- `.gitignore` — ignore `backend/var/*.sqlite3*`, imported licensed data, and local source overrides.
- `docs/DECISIONS.md` — append decisions before any frozen schema or safety-semantic change.
- `docs/PROGRESS.md`, `docs/03_data_sources.md`, `docs/05_api_contracts.md`, `docs/AUDIT_AND_STATUS.md` — update after implementation and verification.

### Protected files: no changes

- `backend/app/services/risk_engine.py`
- `backend/app/services/route_optimizer.py`
- `backend/app/data/live_client.py`
- `backend/app/data/geo.py`
- `backend/app/data/demo_store.py`
- `backend/app/agents/planner.py`
- `frontend/src/index.css`

Adapters wrap protected files where needed. Any discovered defect in a protected file is documented and handled outside it unless the owner explicitly changes repository policy.

## 11. Configuration and environment variables

`backend/config/data_sources.yaml` contains non-secret defaults:

```yaml
version: 1
database:
  path: var/orca_data.sqlite3
sources:
  open_meteo:
    enabled: true
    products:
      forecast: {enabled: true, refresh_seconds: 1800, fresh_ttl_seconds: 1800, max_stale_seconds: 10800}
      marine: {enabled: true, refresh_seconds: 1800, fresh_ttl_seconds: 1800, max_stale_seconds: 10800}
  gdacs:
    enabled: true
    products:
      cyclone: {enabled: true, refresh_seconds: 900, fresh_ttl_seconds: 900, max_stale_seconds: 3600}
  stormglass:
    enabled: false
    products:
      point: {enabled: false, refresh_seconds: 7200, fresh_ttl_seconds: 7200, max_stale_seconds: 21600}
  imd:
    enabled: false
    endpoint_url: null
    terms_status: unverified
  incois:
    enabled: false
    endpoint_url: null
    terms_status: unverified
  mosdac:
    enabled: false
    endpoint_url: null
    terms_status: unverified
  coast_guard_manual:
    enabled: false
    endpoint_url: null
    terms_status: unverified
```

Environment variables:

- `ORCA_DATA_MODE=DEMO|LIVE`
- `ORCA_DATA_CONFIG=backend/config/data_sources.yaml`
- `ORCA_DATA_DB=backend/var/orca_data.sqlite3`
- `ORCA_SCHEDULER_ENABLED=0|1`
- `ORCA_SCHEDULER_WARMUP=0|1`
- `ORCA_WORKER_ID=<unique instance id>`
- `ORCA_LIVE_TIMEOUT=<seconds>`
- `ORCA_ALLOW_STALE=0|1`
- `ORCA_LEGACY_LIVE_DEMO_FALLBACK=0|1` — temporary, default `0`, removal scheduled after compatibility verification.
- `STORMGLASS_API_KEY=<secret>`
- `IMD_PRODUCT_URL=<manually verified URL>`
- `INCOIS_PRODUCT_URL=<manually verified URL>`
- `MOSDAC_PRODUCT_URL=<manually verified URL>`
- `COAST_GUARD_PRODUCT_URL=<manually verified URL, if one is authorized>`
- `ORCA_MANUAL_ADVISORY_TOKEN=<secret>`

URL env vars do not enable a source by themselves. Both manual verification and `enabled: true` are required.

## 12. Observability and health endpoint

Extend `GET /api/health` without removing existing keys. Add a `data` object. Also add `GET /api/data-sources/status` for detailed per-source and per-metric freshness, cache mode, last success/error, and coverage diagnostics; it must follow the same redaction rules below.

Example health payload:

```json
{
  "status": "ok",
  "version": "...",
  "data_mode": "LIVE",
  "agents": ["..."],
  "data": {
    "database": {"status": "ok", "journal_mode": "wal", "schema_version": 1},
    "scheduler": {"enabled": true, "owner": false, "last_tick_at": "..."},
    "sources": {
      "open_meteo:marine": {
        "enabled": true,
        "status": "healthy",
        "last_success_at": "...",
        "age_seconds": 120,
        "consecutive_failures": 0,
        "circuit_open_until": null
      }
    },
    "coverage": {"required_metrics_available": 4, "required_metrics_total": 4}
  }
}
```

Rules:

- Overall HTTP health remains 200 when optional sources are degraded.
- Return 503 only when the application cannot serve decisions safely (database unavailable and no safe compatibility path, or required evidence policy cannot initialize).
- Never expose API keys, full URLs containing tokens, raw bulletin text, operator identity, or stack traces.
- Structured logs include request/fetch ID, source/product, status, latency, record count, selected mode, cache age, and redacted error class.
- Metrics counters: fetch success/failure, selected LIVE/CACHED/STALE/INSUFFICIENT, lease contention, quota remaining, parser rejection, and decision insufficient count.

## 13. Security, licensing, and scraping rules

- Secrets only in environment/secret manager; never YAML, SQLite metadata, logs, fixtures, or Git.
- Validate URL scheme and optionally allowlist hosts to prevent SSRF from configurable endpoints.
- Set strict timeouts, response-size limits, redirect limits, content-type checks, and parser bounds.
- Parameterize SQL and validate JSON/GeoJSON size/depth.
- Manual ingestion requires authentication, authorization, audit logging, and rate limits.
- Preserve required attribution for Open-Meteo, GDACS, StormGlass, and official products in UI/API metadata.
- Record terms/license review status per product. Disabled is mandatory while status is `unverified` or `prohibited`.
- Respect robots.txt and published terms. Do not scrape login-protected pages, bypass controls, or automate undocumented sessions.
- Store raw payloads only when permitted; otherwise retain hashes, normalized facts, and source references.
- Parser fixtures must be synthetic or redistributable.
- IMD, INCOIS, MOSDAC, and Coast Guard endpoint/product URLs remain configurable and disabled until manually verified. No stable endpoint is asserted by this plan.

## 14. Deployment and multi-worker scheduler safeguards

- Initialize database/migrations in FastAPI lifespan before accepting traffic.
- Start scheduler in lifespan only when enabled; stop and join it on shutdown.
- Every scheduled job must acquire a SQLite lease using `BEGIN IMMEDIATE` before network access.
- Lease duration exceeds expected job timeout; heartbeat long jobs; generation fencing prevents an expired owner from committing after takeover.
- Evidence writes are idempotent through unique keys/content hashes.
- WAL and busy timeout support concurrent readers; keep write transactions short.
- Do not use `--reload` with production scheduler enabled; reload child processes can duplicate jobs.
- In multi-host deployment, SQLite on local disks cannot coordinate workers. Run exactly one scheduler deployment or move leases/evidence to a shared database before horizontal scaling.
- Scheduler failure must not stop API reads from LKG.
- Warmup is optional and bounded; startup must not block indefinitely on upstream services.
- Back up SQLite before migrations; migrations are forward-only with a documented restore point.

## 15. Migration and backward compatibility

### `/api/chat`

- Do not modify protected `agents/planner.py`.
- Migrate specialist agents behind their existing `run(...) -> AgentResult` interfaces.
- Preserve existing field names, units, risk categories, and response shape.
- Existing DEMO behavior remains available when global mode is DEMO; compatibility adapter derives the historical scenario ID and logs that implicit selection is legacy-only.
- In LIVE mode, missing fields remain `None`/unavailable and provenance states cache/stale status. No demo substitution.
- Run all existing smoke scenarios before each rollout.

### `/api/plan` and `/plan`

- Preserve `PlanRequest` fields and `DecisionState` response.
- Add optional `scenario_id` only as backward-compatible input.
- If DEMO mode is requested without `scenario_id`, return 422 for new callers; a temporary compatibility rule may map legacy requests only when explicitly enabled.
- Continue setting `X-Request-ID`.
- Do not change frozen `Evidence`/`DecisionState` fields without first logging a decision. Internal `INSUFFICIENT` selection maps to existing `DecisionState.status=INSUFFICIENT_EVIDENCE`.
- Keep `/api/*` aliases and root v2 routes.

### Rollout strategy

1. Shadow broker: fetch/store/select while agents still use old paths; compare values and provenance.
2. Enable broker for one agent/source at a time behind flags.
3. Default new `/plan` to broker after acceptance gates.
4. Migrate legacy `/api/chat` specialist calls last.
5. Remove compatibility fallback only after demo and regression sign-off.

## 16. Phased milestones, dependencies, rollback points, tests, and gates

### Priority A — immediate demo readiness

#### Phase 0 — Decisions, config, and baseline

Dependencies: none.

Tasks:

- [ ] Append decisions for no silent demo fallback, field-level evidence, SQLite LKG, and URL verification policy.
- [ ] Capture baseline `/api/chat`, `/api/plan`, health, and five demo scenario outputs.
- [ ] Add disabled-by-default `data_sources.yaml`.
- [ ] Add database/config validation tests.

Acceptance gate:

- Existing tests and smoke scenarios pass unchanged.
- IMD/INCOIS/MOSDAC/Coast Guard are disabled with null/configurable URLs.

Rollback: remove new config/doc decision entries only by a new reversing decision; runtime remains untouched.

#### Phase 1 — SQLite evidence cache and selection policy

Dependencies: Phase 0.

Tasks:

- [ ] Implement migrations/repository and WAL settings.
- [ ] Implement pure selection policy and deterministic tie-breaks.
- [ ] Add retention and corruption/error handling.
- [ ] Test restart persistence, concurrent reads, idempotent writes, expiry boundaries, and invalid records.

Acceptance gate:

- Unit tests cover LIVE, CACHED, STALE, INSUFFICIENT, explicit expiry, authority tie, and stable tie-break.
- Failed fetch cannot overwrite LKG.
- Database survives process restart.

Rollback: disable broker flag; retain database for inspection; restore pre-migration backup if schema initialization fails.

#### Phase 2 — Broker plus Open-Meteo and GDACS

Dependencies: Phase 1.

Tasks:

- [ ] Implement adapter protocol and broker.
- [ ] Wrap protected Open-Meteo client.
- [ ] Wrap GDACS parser/fetcher.
- [ ] Add field validation and poll-success evidence.
- [ ] Run broker in shadow mode and compare current agent values.

Acceptance gate:

- Forced network failure returns CACHED/STALE/INSUFFICIENT, never DEMO.
- Every selected field has correct source/time/mode.
- GDACS calm/no-event is distinguishable from unavailable feed.
- No protected file changed.

Rollback: turn off broker source flags; agents continue old path.

#### Phase 3 — Explicit demo isolation and agent migration

Dependencies: Phase 2.

Tasks:

- [ ] Add `DemoScenarioProvider` and scenario validation.
- [ ] Migrate weather, ocean, cyclone, and PFZ agents behind existing interfaces.
- [ ] Remove mixed live/demo aggregate claims.
- [ ] Map missing required evidence to `INSUFFICIENT_EVIDENCE` in LangGraph.
- [ ] Preserve legacy demo compatibility behind a temporary flag.

Acceptance gate:

- Static/import test proves live adapters do not import demo store.
- LIVE outage never returns a DEMO field.
- DEMO requires/records scenario ID for new `/plan` calls.
- Five legacy demo scenarios and `/api/chat` response contracts pass.
- Protected risk engine produces unchanged results for identical inputs.

Rollback: per-agent feature flags restore old data acquisition; protected planner/risk code remains unchanged.

#### Phase 4 — Lifespan scheduler, leases, and health

Dependencies: Phases 1–3.

Tasks:

- [ ] Add lifespan migration/start/stop.
- [ ] Convert jobs to broker refreshes.
- [ ] Add SQLite lease/fencing and bounded warmup.
- [ ] Expand health response while preserving old keys.
- [ ] Add structured logs and counters.

Acceptance gate:

- Two worker processes contend and exactly one executes each leased job.
- Lease takeover works after simulated crash.
- Shutdown stops scheduler cleanly.
- API serves LKG while upstreams fail.
- Health redacts secrets and reports source age/failure.

Rollback: `ORCA_SCHEDULER_ENABLED=0`; API remains read-only against LKG/old path.

#### Phase 5 — Demo rehearsal gate

Dependencies: Phases 0–4.

Tasks:

- [ ] Pre-demo manual refresh of Open-Meteo/GDACS.
- [ ] Verify offline DEMO scenarios with explicit IDs.
- [ ] Verify LIVE outage ladder by blocking network.
- [ ] Back up SQLite and capture health screenshot/output.
- [ ] Freeze runtime changes after sign-off.

Acceptance gate:

- Demo can run fully offline in DEMO mode.
- LIVE mode is honest under outage.
- `/api/chat`, `/api/plan`, `/plan`, routes, and frontend smoke tests pass.
- No unverified government source is enabled.

Rollback: switch to DEMO with rehearsed scenario ID; do not enable silent fallback.

### Priority B — post-demo production hardening

#### Phase 6 — StormGlass quota-safe integration

Dependencies: broker, cache, health.

- [ ] Verify account/product terms and parameters.
- [ ] Add quota ledger/circuit breaker.
- [ ] Integrate current/tide fields without synthetic fallback.
- [ ] Test 401/402/429, quota reset, multi-worker budget, and stale selection.

Gate: daily request cap cannot be exceeded under expected worker/query load.

Rollback: disable StormGlass; current/tide become unavailable or use other verified evidence.

#### Phase 7 — IMD and INCOIS onboarding

Dependencies: legal/terms and endpoint/product manual verification.

- [ ] Record verified product URL and review evidence outside secrets.
- [ ] Prefer API/CAP/RSS/download; enable scraping only if permitted.
- [ ] Build parser fixtures and validity/geometry tests.
- [ ] Shadow ingest before selection eligibility.
- [ ] Enable one product at a time.

Gate: parser handles valid, malformed, changed layout, expired, duplicate, and low-confidence cases; attribution and terms approved.

Rollback: disable product; retain prior LKG only within validity/stale policy.

#### Phase 8 — MOSDAC batch and manual advisories

Dependencies: registration/license, authenticated operator path.

- [ ] Implement checksum manifest importer.
- [ ] Validate SST/chlorophyll semantics and coverage.
- [ ] Implement authenticated append-only manual advisory workflow.
- [ ] Add supersession and audit tests.

Gate: imported/manual records are reproducible, licensed, attributable, and cannot be silently altered.

Rollback: disable importer/manual endpoint; preserve audit records.

#### Phase 9 — Production operations

Dependencies: all selected sources stable.

- [ ] Add shared database plan before multi-host scaling.
- [ ] Add backups, restore drill, retention, dashboards, alerts, and SLOs.
- [ ] Lock CORS and manual-ingestion authentication.
- [ ] Load/soak test scheduler and API.
- [ ] Conduct security and license review.

Gate: restore drill succeeds; no duplicate jobs; source outage and database contention meet SLO.

## 17. Detailed cross-cutting test checklist

- [ ] Schema validation: malformed value/unit/time/geometry/confidence rejected.
- [ ] Selection: exact TTL boundary, max-stale boundary, expired validity, future skew, authority/priority ties.
- [ ] Failure: DNS, timeout, TLS, 4xx, 5xx, invalid JSON/XML/HTML/PDF, oversized payload.
- [ ] Cache: restart persistence, failed-write rollback, duplicate content, concurrent writers, WAL recovery.
- [ ] Demo: explicit scenario, unknown scenario, no scenario, live/demo cross-contamination query.
- [ ] Open-Meteo: partial fields remain partial; no aggregate LIVE over demo/missing fields.
- [ ] GDACS: active event, no event, duplicate update, moved track, closed/expired event.
- [ ] StormGlass: missing key, quota exhausted, provider subfield selection, stale cache.
- [ ] Advisory: official NO_GO with mild weather still triggers existing floor; low-confidence parse becomes insufficient.
- [ ] PFZ: missing geometry, restricted-zone exclusion, expired advisory, no invented chlorophyll.
- [ ] Scheduler: duplicate workers, crash before commit, crash after lease, long job heartbeat, clock skew tolerance.
- [ ] API: old aliases, response models, `X-Request-ID`, JSON 404, health compatibility.
- [ ] Security: secret redaction, SSRF allowlist, SQL injection, decompression/response-size limits.
- [ ] Licensing: attribution present; disabled source cannot fetch; unverified URL cannot enable.

## 18. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Government product URL/layout changes | Parser failure or wrong advisory | Disabled until verified; content-type/schema checks; fixtures; circuit breaker; LKG with validity cap |
| Silent demo contamination | Misleading safety claim | Separate provider/table flag; explicit scenario ID; import/static tests; no live fallback |
| SQLite lock contention | Delayed refresh/write | WAL, busy timeout, short transactions, one leased writer per job, load tests |
| Multi-host deployment with local SQLite | Duplicate jobs/divergent LKG | Single scheduler deployment; shared DB migration before horizontal scale |
| StormGlass quota exhaustion | Missing current/tide | Budget ledger, scheduled regional cache, circuit breaker, optional metric semantics |
| Stale official warning mishandled | Unsafe or overly restrictive decision | Explicit validity rules; no indefinite inference; deterministic tests |
| Parser/LLM extracts wrong advisory | Safety error | Deterministic metadata first; confidence threshold; original excerpt/reference; human review; existing floors only consume accepted constraints |
| Backward-compat regression | Demo/frontend failure | Existing interfaces, feature flags, shadow mode, golden responses, protected files untouched |
| License violation/raw payload retention | Legal/reputational harm | Product review status, minimal storage, attribution, configurable retention, no scraping until approved |
| Scheduler starts in every reload worker | Duplicate upstream calls | Lifespan lease, scheduler flag, reload warning, idempotent writes |
| Documentation conflicts with current schema consolidation | Implementation drift | Treat current `schemas.py` as reality; update stale dual-schema docs through decision/progress process |

## 19. Definition of done

### Immediate demo readiness

- SQLite LKG, deterministic selection, broker, Open-Meteo/GDACS adapters, explicit demo provider, lifespan scheduler leases, and health reporting are implemented and tested.
- LIVE mode never silently returns demo/synthetic values.
- Every displayed safety-relevant field has field-level provenance and correct mode.
- Required missing evidence maps to `INSUFFICIENT_EVIDENCE` without changing protected risk logic.
- `/api/chat`, `/api/plan`, `/plan`, aliases, frontend smoke tests, and five demo scenarios pass.
- IMD, INCOIS, MOSDAC, and Coast Guard endpoint/product URLs are configurable, disabled, and not represented as stable until manually verified.
- Protected files remain unchanged.
- Rollback flags and a pre-demo SQLite backup are verified.

### Post-demo production hardening

- StormGlass quota controls are proven.
- Each enabled IMD/INCOIS/MOSDAC/Coast Guard/manual product has documented manual verification, terms/license approval, attribution, parser tests, and operational monitoring.
- Backup/restore, retention, security controls, multi-worker behavior, and production SLOs are tested.
- Compatibility flags are removed only after both API paths and frontend consumers are migrated and signed off.
