# ORCA — Decisions Log

Append-only. Never delete an entry — if a decision is reversed, add a new
dated entry saying so, don't edit the old one out.

Format:
```
## YYYY-MM-DD — <short title>
Decision: <what was decided>
Reason: <why>
Affects: <which doc/module this changes, if any>
```

---

## 2026-09-10 — Repo restart
Decision: new repo, clean history, starting today. Old repo (found team's
submission) is read-only reference only.
Reason: history/optics + AI-agent editing reliability — see chat log.
Affects: everything.

## 2026-09-10 — Scope
Decision: no features cut. AI-assisted development via coding agents means
spec clarity is the bottleneck, not raw hours.
Reason: team decision.
Affects: `00_overview.md` fallback ladder exists as a safety net only.

## 2026-09-10 — Voice sequencing
Decision: voice is built last, after Core + Safety are demo-stable.
Reason: longest to verify; don't let it block or destabilize the core path.
Affects: `08_implementation_phases.md` Phase 6.

## 2026-09-10 — Keep old codebase, upgrade to ORCA 2.0
Decision: use the old ORCA codebase as foundation and upgrade it to meet
ORCA 2.0 specs. Do not rebuild from scratch.
Reason: old codebase has ~22 hours of working code — risk engine, route
optimizer, live data client, full frontend, trilingual i18n. Rebuilding
would waste 2 of the 3 available days.
Affects: entire approach. Backend and frontend from `D:\Desktop\ORCA` copied
into this repo.

## 2026-09-10 — Dual schema strategy
Decision: keep old `schemas.py` for internal backward compat with existing
agents and frontend. Add new `schemas_v2.py` for ORCA 2.0 API contracts.
Bridge with converter functions.
Reason: (a) is safer — old frontend stays working, new `/plan` endpoint uses
new schemas. Full migration to single schema set is a cleanup pass after
everything works.
Affects: `02_schemas.md`, `AGENT.md`.

## 2026-09-10 — Groq → Gemini Flash
Decision: replace Groq LLM with Gemini Flash (`gemini-2.0-flash`) as the
primary LLM provider. Keep Groq as fallback if only Groq key is set.
Reason: Gemini Flash is faster, cheaper, better multilingual support,
and aligns with the ORCA 2.0 spec.
Affects: `services/llm.py`, `config.py`, `requirements.txt`, `.env`.

## 2026-09-10 — Centralized mock data
Decision: all mock/fixture data lives in `data/mock_data/` directory, not
hardcoded across individual agents.
Reason: easy to find, easy to replace with live data, easy to add edge cases.
`demo_store.py` stays for backward compat with old frontend path.
Affects: `data/mock_data/` (new), all agents that consume fixtures.

## 2026-09-10 — Frontend as PWA
Decision: frontend stays as PWA (React + TypeScript), not React Native.
Mobile view via `?m=1` parameter, `MobileApp.tsx` component.
Reason: team doesn't have React Native experience. PWA is installable,
service-worker-cached, and already working.
Affects: `07_stack_and_models.md`.

## 2026-09-10 — LangGraph yes
Decision: build LangGraph state graph (Phase 2). The old ThreadPoolExecutor
planner stays working for `/api/chat` backward compat.
Reason: compiled graph visualization is a judge-ready artifact. The old
planner docstring already says nodes are shaped for LangGraph.
Affects: `graph/` package (new), `requirements.txt`.

## 2026-09-10 — Solo builder mode
Decision: Akshay builds the backend + migration solo with AI agents for now.
Teammates join later for frontend polish, data sources, voice.
Reason: faster to build solo than to coordinate 5 people on day 1. Team
assignments updated when teammates join.
Affects: `06_team_and_assignments.md`.

## 2026-09-10 — Multi-provider LLM fallback chain
Decision: Use Groq (primary) → Cerebras (fallback 1) → Gemini Flash (fallback 2) → Template engine (nuclear) as the LLM call chain.
Reason: Single-provider free tiers hit rate limits during active development and demos. Groq has 30 RPM which is plenty, but Cerebras 1M tokens/day covers overflow. No single point of failure.
Affects: `services/llm.py`, `AGENT.md`, `.env`, `requirements.txt`.

## 2026-09-10 — Voice provider: Sarvam AI (not ElevenLabs)
Decision: Use Sarvam Saaras (STT) + Bulbul (TTS). ElevenLabs rejected.
Reason: ElevenLabs has no STT capability at all — it's TTS-only. For a voice agent you need both. Sarvam supports 22 Indian languages for STT and 11 for TTS, is India-native (better Hinglish/code-switching), INR-priced, and allows commercial use on free credits.
Affects: `services/voice.py` (new), `api/voice.py` (new), `SARVAM_API_KEY` env var.

## 2026-09-10 — Scraper refresh intervals (tiered)
Decision: Different polling intervals per source: GDACS 15min, Open-Meteo 30min, IMD 1hr, StormGlass 2hr, INCOIS PFZ 6hr.
Reason: User caught that 6hr was too long for cyclone data — cyclones can intensify rapidly. Each interval is chosen based on how fast the data actually changes, not a blanket value. IMD 1hr catches emergency bulletins (published any time) while being respectful to their server.
Affects: `data/scheduler.py` (new), `data/advisory_scraper.py` (new).

## 2026-09-10 — Full multilingual support (5 layers)
Decision: Implement multilingual across all 5 layers: UI strings, chatbot text, STT, TTS, advisory translation. Priority: EN/HI/MR (now) → TA/TE/BN/ML (Sep 11).
Reason: Coastal India has 9 major fishing languages. The app is useless to a Tamil Nadu fisherman who only reads Tamil. Voice without regional language STT is similarly broken.
Affects: `services/i18n.py`, `schemas.py` (Language type), `services/translate.py` (new), `services/voice.py`, all agent explanation prompts.

## 2026-09-10 — Route waypoint risk scoring (path-integrated risk)
Decision: After A* returns route candidates, score each route by sampling conditions at ~5 waypoints along the path. Score = 0.7 × avg(waypoint_risk) + 0.3 × max_spike. Routes re-ranked by this score, not just zone penalties.
Reason: The existing A* only avoids static restricted zones. It doesn't know that Route A passes through a storm band at 20-30km. Path-integrated risk makes the recommendation actually reflect what the fisherman will experience. The max_spike term prevents a route averaging as "moderate safe" when it has one very dangerous segment.
Affects: `services/route_optimizer.py`, `schemas.py` (WaypointCondition type, RouteOption fields), route agent/node, `config/risk_thresholds.yaml` (waypoint weights).

## 2026-09-10 — YAML Configuration & Fallbacks
Decision: Risk model weights, thresholds, deterministic safety floors, route waypoint scoring weights, and trip economics extracted from Python code into `backend/config/risk_thresholds.yaml` and `backend/config/trip_economics.yaml`. Loaded at startup in `backend/app/config.py` with automatic fallback to hardcoded defaults if files are missing or malformed.
Reason: Centralizes all judge-inspectable risk factors and economics parameters in human-readable YAML outside business logic, enabling hot adjustments and transparent auditability without editing code.
Affects: `backend/config/risk_thresholds.yaml`, `backend/config/trip_economics.yaml`, `backend/app/config.py`.

## 2026-09-10 — ORCA 2.0 Schemas and Dual-Schema Interop
Decision: Built `backend/app/schemas_v2.py` implementing `Evidence`, `AdvisoryConstraint`, `DecisionState`, `AlertEvent`, and `ORCAState` with strict boundary validation (confidence 0.0–1.0, risk_score 0–100) and converters (`measurement_to_evidence`, `agent_result_to_evidence_list`, `risk_assessment_to_decision_state`). Kept `schemas.py` 100% untouched.
Reason: Preserves complete backward compatibility for existing 10 agents, `/api/chat`, and 17 frontend components while giving the new LangGraph engine and `/plan` endpoint clean, typed contracts.
Affects: `backend/app/schemas_v2.py`, `backend/tests/test_schemas_v2.py`.

## 2026-09-10 — Centralized Mock Data & Edge Cases
Decision: Centralized all test fixtures and 8 explicit edge cases in `backend/app/data/mock_data/` (`fixtures.py`, `edge_cases.py`, `__init__.py`) returning typed `Evidence_v2` and `AdvisoryConstraint` objects.
Reason: Guarantees that the pipeline, safety floors, conflict resolver, and fallbacks can be exhaustively exercised and validated without calling external networks or relying on scattered mocks in agents.
Affects: `backend/app/data/mock_data/`, `backend/tests/test_mock_data.py`.

## 2026-09-10 — Advisory Compiler and Confidence Guardrails
Decision: If LLM generated confidence for an advisory is below 0.70 or if the advisory text cannot be parsed reliably, fall back automatically to rule-based heuristic extraction without crashing or blocking.
Reason: Marine safety cannot depend on unverified or low-confidence LLM parsing of weather warnings. Deterministic regex and severity floors guarantee consistent constraint generation.
Affects: `backend/app/services/advisory_compiler.py`, `backend/tests/test_advisory_compiler.py`.

## 2026-09-10 — LangGraph StateGraph Architecture
Decision: Implement LangGraph StateGraph pipeline (`backend/app/graph/`) with node progression: Data Ingestion → Conflict Resolution → Safety Evaluation → Route Optimization → Advisory Compilation → Trace Finalization.
Reason: Decouples sequential decision-making steps, logs full state transition traces for auditability by judges, and cleanly exposes `POST /plan` and `GET /trace/{request_id}` endpoints.
Affects: `backend/app/graph/`, `backend/app/api/plan.py`.

## 2026-09-10 — Authority-Tiered Conflict Resolution
Decision: Conflict resolution hierarchy strictly ordered: INCOIS/IMD Official Regulatory Advisories (Tier 1) > Physical Sensor / Buoy / StormGlass (Tier 2) > Open-Meteo Numerical Weather Predictions (Tier 3) > Crowd/Historical Observations (Tier 4).
Reason: Prevents satellite forecast models from overriding high-severity official cyclone warnings, maintaining regulatory compliance and seafarer safety.
Affects: `backend/app/services/conflict_resolver.py`, `backend/tests/test_conflict_resolver.py`.

## 2026-09-10 — Active Voyage Store & In-Flight Deterioration Alerts
Decision: In-memory Voyage Store tracks active fishing trips with GPS coordinates, assigned vessels, active routes, and target PFZs. When new evidence or alerts arrive via `on_evidence_change()`, the engine re-evaluates risk, detects condition deterioration, and calculates the nearest safe harbour with bearing and distance.
Reason: Real fishermen need continuous monitoring while at sea, not just pre-trip planning. Emergency diversion recommendations save lives if storms intensify after departure.
Affects: `backend/app/data/voyage_store.py`, `backend/app/services/alert_engine.py`, `backend/app/api/voyages.py`.

## 2026-09-10 — Multi-Source Tiered Background Scrapers & Scheduler
Decision: Implemented background scheduler (APScheduler) with source-tailored refresh intervals: GDACS cyclone XML (15 min), Open-Meteo forecasts (30 min), IMD weather warnings with SHA-256 fingerprinting (1 hr), StormGlass marine data with 0.1° cell caching (2 hr), and INCOIS PFZ maps (6 hr).
Reason: Balances rapid notification of sudden extreme weather against external API rate limits, bandwidth constraints, and government portal scrape etiquette.
Affects: `backend/app/data/live_client.py`, `backend/app/data/stormglass_client.py`, `backend/app/data/advisory_scraper.py`, `backend/app/data/scheduler.py`.

## 2026-09-10 — Capability-Based Source Registry
Decision: Register data sources with capabilities (`cyclone`, `pfz`, `wave_height`, `wind_speed`, `weather_warning`) and priorities.
Reason: Allows runtime discovery of preferred and fallback providers for any marine metric without hardcoding provider logic in planner nodes.
Affects: `backend/app/data/source_registry.py`, `backend/tests/test_source_registry.py`.

## 2026-09-10 — Regional Language Extension & Script Detection
Decision: Added regional language support (`ta`, `te`, `bn`, `ml`, `gu`, `kn`, `or`) using fast Unicode codepoint script detection and Sarvam Mayura machine translation for advisories, alongside a resilient `SupportedLanguage` TypeScript type in frontend.
Reason: Enables immediate language detection without extra network calls, translates official English/Hindi advisories to the coastal fisherman's mother tongue, and preserves existing UI component dictionary typing in the frontend.
Affects: `backend/app/services/i18n.py`, `backend/app/services/translate.py`, `frontend/src/types.ts`.

## 2026-09-10 — Deterministic Safety Floor Test Suite
Decision: 76 unit tests across 15 test modules covering schema validation, deterministic safety floors (wind > 35 knots, wave > 3.0m, cyclone within 100km triggering immediate NO-GO), conflict resolution, advisory compiling, route scoring, scheduler, voice, and translation.
Reason: Ensures zero regression of legacy endpoints (`/api/chat`) and verifies mathematical safety invariants before any frontend UI integration.
Affects: `backend/tests/`.

<!-- Add new entries above this line, newest at the bottom of the log but
     above this comment, so the file reads chronologically top-to-bottom. -->

