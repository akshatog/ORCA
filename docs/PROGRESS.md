# ORCA — Progress Log

Append one line per completed (or meaningfully blocked) task. Whoever
finished the task writes it — or tells their coding agent to write it as
the last step.

Format:
```
YYYY-MM-DD HH:MM | TASK-ID | done: <what> | open: <what's left, if anything> | deviation: <if code differs from spec, why>
```

---

2026-09-10 20:30 | SETUP | done: copied old ORCA codebase into ORCA 2.0 repo (backend, frontend, images, root files, all .md files) | open: none | deviation: copied from D:\Desktop\ORCA, not built fresh
2026-09-10 21:00 | DOCS | done: updated all docs (00_overview, 02_schemas, 05_api_contracts, 06_team_and_assignments, 07_stack_and_models, 08_implementation_phases, DECISIONS.md, AGENT.md) to reflect migration approach, solo builder mode, dual schema strategy, Gemini Flash | open: none | deviation: docs now reflect upgrade-not-rebuild reality

2026-09-10 22:35 | TASK-0.1 | done: extracted RiskConfig + trip economics to risk_thresholds.yaml and trip_economics.yaml, loaded at startup with fallbacks | open: TASK-0.2 through 8.13 | deviation: none
2026-09-10 22:36 | TASK-0.2 | done: implemented schemas_v2.py (Evidence, AdvisoryConstraint, DecisionState, AlertEvent, ORCAState, make_evidence, converters) with 16 passing unit tests | open: TASK-0.3 through 8.13 | deviation: none
2026-09-10 22:37 | TASK-0.3 | done: implemented centralized mock_data fixtures and edge_cases with 8 Evidence_v2 edge cases | open: TASK-0.4 through 8.13 | deviation: none
2026-09-10 22:38 | TASK-0.4 | done: logged all Phase 0 foundation decisions in DECISIONS.md | open: Phase 1 (TASK-1.1 through TASK-1.2) | deviation: none
2026-09-10 22:44 | TASK-1.1 | done: implemented multi-provider LLM fallback chain (Groq -> Cerebras -> Gemini -> Template) in services/llm.py with passing tests | open: TASK-1.2 through 8.13 | deviation: none
2026-09-10 22:45 | TASK-1.2 | done: implemented Advisory Compiler in services/advisory_compiler.py with confidence threshold and heuristic fallback | open: Phase 2 (TASK-2.1 through TASK-2.5) | deviation: none
2026-09-10 22:50 | TASK-2.1 | done: implemented LangGraph StateGraph pipeline in graph/ package with ASCII topology and mock run returning valid ORCAState | open: TASK-2.2 through 8.13 | deviation: none
2026-09-10 22:52 | TASK-2.2 | done: implemented POST /plan endpoint returning DecisionState and persisting in-memory state | open: TASK-2.3 through 8.13 | deviation: none
2026-09-10 22:52 | TASK-2.3 | done: implemented GET /trace/{request_id} endpoint returning execution trace with 404 handling | open: TASK-2.4 through 8.13 | deviation: none
2026-09-10 22:53 | TASK-2.4 | done: verified legacy /api/chat and smoke_test demo scenarios all pass with zero regressions | open: TASK-2.5 through 8.13 | deviation: none
2026-09-10 22:56 | TASK-2.5 | done: implemented route waypoint risk scoring (path-integrated risk) with WaypointCondition schema and storm band re-ranking | open: Phase 3 (TASK-3.1 through TASK-3.4) | deviation: none
2026-09-10 23:00 | TASK-3.1 | done: implemented Conflict Resolver in services/conflict_resolver.py with authority hierarchy and conflict logging | open: TASK-3.2 through 8.13 | deviation: none
2026-09-10 23:02 | TASK-3.2 | done: implemented in-memory voyage store in app/data/voyage_store.py with start/get/update/end lifecycle and unit tests | open: TASK-3.3 through 8.13 | deviation: none
2026-09-10 23:04 | TASK-3.3 | done: implemented alert engine with on_evidence_change, deterioration detection, safe-port recommendations, and unit tests | open: TASK-3.4 through 8.13 | deviation: none
2026-09-10 23:06 | TASK-3.4 | done: implemented voyage tracking and alert trigger API endpoints in api/voyages.py mounted in main.py, verified with integration tests and full smoke test | open: Phase 4 (TASK-4.1 through TASK-4.9) | deviation: none
2026-09-10 23:08 | TASK-4.1 | done: implemented parse_gdacs_xml and fetch_gdacs with 15min TTL in live_client.py, Indian Ocean filtering, alert engine integration, and unit tests | open: TASK-4.2 through 8.13 | deviation: none
2026-09-10 23:09 | TASK-4.2 | done: implemented StormGlass adapter in data/stormglass_client.py with 0.1 deg spatial caching, 2hr TTL, quota guards, graceful fallbacks, and unit tests | open: TASK-4.3 through 8.13 | deviation: none
2026-09-10 23:10 | TASK-4.3 | done: implemented IMD Advisory Scraper in data/advisory_scraper.py with BeautifulSoup HTML extraction, pdfplumber PDF extraction, SHA-256 fingerprint caching, and alert engine integration | open: TASK-4.4 through 8.13 | deviation: none
2026-09-10 23:11 | TASK-4.4 | done: implemented INCOIS PFZ Scraper in data/advisory_scraper.py with coordinate/SST/chlorophyll extraction, 6hr TTL, and unit tests | open: TASK-4.5 through 8.13 | deviation: none
2026-09-10 23:14 | TASK-4.5 | done: implemented Tiered Scheduler in data/scheduler.py with 5 background cadence jobs (15m, 30m, 1h, 2h, 6h), startup warmup, and unit tests | open: TASK-4.6 through 8.13 | deviation: none
2026-09-10 23:15 | TASK-4.6 | done: implemented capability-based Source Registry in data/source_registry.py with priorities, defaults, discovery functions, and unit tests | open: TASK-4.7 through 8.13 | deviation: none
2026-09-10 23:16 | TASK-4.7 | done: implemented Sarvam AI Saaras STT and Bulbul TTS voice service in services/voice.py and endpoints in api/voice.py with browser fallbacks and unit tests | open: TASK-4.8 through 8.13 | deviation: none
2026-09-10 23:18 | TASK-4.8 | done: extended Language types, added Unicode script detection for Indian languages (ta, te, bn, ml, gu, kn, or) and regional phrasebooks in services/i18n.py | open: TASK-4.9 through 8.13 | deviation: none
2026-09-10 23:19 | TASK-4.9 | done: implemented advisory translation using Sarvam Mayura in services/translate.py, populating localized_summaries on AdvisoryConstraint, with unit tests | open: Phase 5 (TASK-5.1 through TASK-5.2) | deviation: none
2026-09-10 23:23 | TASK-5.1 | done: added ORCA 2.0 TypeScript types (Evidence_v2, AdvisoryConstraint, DecisionState, AlertEvent, ORCAState, TraceEntry, WaypointCondition, Voyage) to types.ts, verified with npx tsc --noEmit | open: TASK-5.2 through 8.13 | deviation: none
2026-09-10 23:25 | TASK-5.2 | done: implemented ORCA 2.0 client API functions (fetchPlan, fetchTrace, startVoyage, endVoyage, triggerAlert, transcribeVoice, speakText) in api.ts, verified with tsc and vite build | open: Phase 6 (TASK-6.1 through TASK-6.8) | deviation: none
2026-09-10 23:26 | TASK-6.1-6.8 | done: executed and verified complete automated test suites (76 total passing tests across schemas, risk engine, advisory compiler, conflict resolver, alert engine, route scoring, scheduler, language detection) | open: Phase 7 (TASK-7.1 through TASK-7.3) & Phase 8 | deviation: none
2026-09-10 23:33 | TASK-7.1 | done: updated DECISIONS.md with Phase 1-6 architectural decisions and 08_implementation_phases.md with completed milestones | open: TASK-7.2 through 8.13 | deviation: none
2026-09-10 23:34 | TASK-7.2 | done: executed comprehensive end-to-end API smoke test (10/10 endpoints passing) and legacy 5-scenario demo test (100% pass) | open: TASK-7.3 through 8.13 | deviation: none
2026-09-10 23:35 | TASK-7.3 | done: updated AGENT.md with Phase 8 roadmap, component specifications, and developer instructions | open: Phase 8 (TASK-8.1 through TASK-8.13) | deviation: none
2026-09-10 23:40 | TASK-8.1 | done: implemented EvidenceProvenancePanel with authority tiers, confidence meters, sensor freshness badges, and search | open: TASK-8.2 through 8.13 | deviation: none
2026-09-10 23:41 | TASK-8.2 | done: implemented ConflictLogPanel showing winning authoritative sources, overridden candidates, and rationale | open: TASK-8.3 through 8.13 | deviation: none
2026-09-10 23:42 | TASK-8.3 | done: implemented DecisionPipelineVisualizer with LangGraph DAG node stepper, latency breakdown, and state telemetry drawer | open: TASK-8.4 through 8.13 | deviation: none
2026-09-10 23:43 | TASK-8.4 | done: implemented VoyageTracker with active fleet list, start voyage from port, live storm alert trigger, and end voyage | open: TASK-8.5 through 8.13 | deviation: none
2026-09-10 23:44 | TASK-8.5 | done: implemented AlertBanner with urgent hazard display, condition deterioration alerts, and 1-click safe harbour diversion | open: TASK-8.6 through 8.13 | deviation: none
2026-09-10 23:45 | TASK-8.6 | done: wired desktop App.tsx with Ops & Provenance tab, live state polling, safe port diversion, and AlertBanner | open: TASK-8.7 through 8.13 | deviation: none
2026-09-10 23:46 | TASK-8.7 | done: updated MobileApp.tsx with voyage tracking card, live storm alerts, safe port diversion, and voice actions | open: TASK-8.8 through 8.13 | deviation: none
2026-09-10 23:47 | TASK-8.8 | done: implemented 7-language selector (en, hi, mr, ta, te, bn, ml) across Desktop and Mobile headers | open: TASK-8.9 through 8.13 | deviation: none
2026-09-10 23:48 | TASK-8.9 | done: implemented public/sw.js maritime caching service worker with network-first for live APIs and cache-first for fonts/assets | open: TASK-8.10 through 8.13 | deviation: none
2026-09-10 23:48 | TASK-8.10 | done: registered service worker in main.tsx with offline detection and console readiness verification | open: TASK-8.11 through 8.13 | deviation: none
2026-09-10 23:49 | TASK-8.11 | done: verified Sarvam Bulbul TTS and Saaras STT voice integration on both mobile and desktop with browser fallback | open: TASK-8.12 through 8.13 | deviation: none
2026-09-10 23:50 | TASK-8.12 | done: implemented colored route waypoint risk markers (green/amber/red circle markers with wave, wind, segment risk tooltips) in MarineMap.tsx | open: TASK-8.13 | deviation: none
2026-09-10 23:52 | TASK-8.13 | done: verified full frontend build with npx tsc --noEmit (0 errors), npm run build (clean production bundle), and backend test suite (76/76 passing, 10/10 endpoints passing) | open: none | deviation: none
<!-- entries go here, oldest first -->
2026-09-11 14:00 | AUDIT | done: ran full engineering audit (ORCA_AUDIT/), verified all findings against live code, produced docs/AUDIT_AND_STATUS.md in-repo with complete findings, fix status, and planned schema consolidation | open: P3 fixes, schema merge | deviation: audit rated 6.5/10 — v1 solid, v2 seams confirmed real
2026-09-11 14:00 | FIX-API-001 | done: fixed WaypointCondition field drift — aligned types.ts + MarineMap.tsx to backend wire fields (lat/lon/wave_m/wind_kmh/risk_factor/risk_level), added ?.toFixed() guards | open: none | deviation: required reading MarineMap.tsx lines 343-378 + schemas.py line 123-130
2026-09-11 14:00 | FIX-INT-001 | done: fixed v2 dev routing — added Vite proxy for /plan /trace /state /voyages /alerts /voice; registered /api aliases in plan.py; standardised api.ts to BASE="/api" | open: none | deviation: none
2026-09-11 14:00 | FIX-BE-001 | done: fixed route_node PFZ coordinate extraction (was reading non-existent "coordinates" key, now reads latitude/longitude); picks highest-confidence zone; derives potential from chlorophyll (INCOIS methodology) | open: none | deviation: none
2026-09-11 14:00 | FIX-DUP-001 | done: unified v2 risk scoring — constraint_engine_node now delegates to risk_engine.assess(); gis_node explicitly stores GIS scalars as Evidence; _build_cyclone_alerts_for_risk_engine() bridges schema gap | open: none | deviation: deterministic safety floors unchanged
2026-09-11 14:00 | CONTRACT-TESTS | done: added test_contract_p1_p2.py with 8 contract tests covering API-001/BE-001/DUP-001 regression guards; full suite now 84/84 passing | open: none | deviation: none
2026-09-11 14:08 | DOCS | done: committed AUDIT_AND_STATUS.md to docs/, updated DECISIONS.md with 7 new entries, updated PROGRESS.md, updated .gitignore (postman/, .postman/, ORCA_AUDIT/) | open: none | deviation: none
2026-09-11 14:08 | GIT | done: committed all P1/P2 fixes on orca-2.0 branch as stable checkpoint; created schema-consolidation branch from this commit for upcoming dual-schema merge | open: schema merge on schema-consolidation branch | deviation: none
2026-09-11 15:48 | ARCH-001 | done: merged schemas_v2.py into schemas.py. v1 Evidence renamed EvidenceRow. schemas_v2.py deleted. 30 files updated. Tests passing 82/82. | open: merge schema-consolidation branch back to orca-2.0 | deviation: none
2026-09-11 16:00 | FIX-P3 | done: LANG-002 regex widened, ERR-002 422 error fix for mode switch, INT-002 404 handler added for api misses, FE-002/003 error surfacing on plan/voyage/alerts. All tests passing. | open: BE-003 | deviation: none
