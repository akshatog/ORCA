# ORCA — Implementation Phases

Round 2 demo: **Sep 12, 2026**. Available days: Sep 10, Sep 11, Sep 12 morning.
Solo builder with AI coding agents.

---

## Phase 0 — Foundation (Sep 10) [COMPLETED]
TASK-0.1 Config YAML, TASK-0.2 schemas_v2.py, TASK-0.3 mock data, TASK-0.4 DECISIONS.md

**Status:** Completed & committed (`b7ceafc`, `2ced700`, `4a4cbe0`, `bbfe991`).

## Phase 1 — LLM Layer (Sep 10) [COMPLETED]
TASK-1.1 Multi-provider LLM (Groq→Cerebras→Gemini→Template), TASK-1.2 Advisory Compiler

**Status:** Completed & committed (`1cdd0e7`, `f72c67a`).

## Phase 2 — Core Pipeline (Sep 10) [COMPLETED]
TASK-2.1 LangGraph graph, TASK-2.2 POST /plan, TASK-2.3 GET /trace/{id},
TASK-2.4 verify /api/chat, TASK-2.5 route waypoint risk scoring

**Status:** Completed & committed (`94d9f59`, `325ec44`, `831ea11`).
**Milestone:** `/plan` returns valid `DecisionState`. Routes have `waypoint_conditions[]` with colored risk dots.

## Phase 3 — Safety & Alerts (Sep 10) [COMPLETED]
TASK-3.1 Conflict Resolver, TASK-3.2 Voyage store, TASK-3.3 on_evidence_change,
TASK-3.4 Voyage/alert API

**Status:** Completed & committed (`25b09e7`, `d81a463`, `f65c6b2`, `4c7ec3b`).
**Milestone:** Start voyage → inject severe advisory → `AlertEvent` fires → safe port returned.

## Phase 4 — Data Layer (Sep 10) [COMPLETED]
TASK-4.1 GDACS (15min), TASK-4.2 StormGlass (2hr), TASK-4.3 IMD scraper (1hr),
TASK-4.4 INCOIS PFZ scraper (6hr), TASK-4.5 Tiered scheduler, TASK-4.6 Source registry,
TASK-4.7 Sarvam voice (STT+TTS), TASK-4.8 Language extension (TA/TE/BN/ML),
TASK-4.9 Advisory translation

**Status:** Completed & committed (`85dd8a3`, `46c73b4`, `d264326`, `1e322ef`, `c86bae3`, `c0d1592`, `5980c3b`).
**Milestone:** Live data flowing. Scrapers pull advisories/PFZs. Sarvam voice & Mayura translation operational.

## Phase 5 — Frontend Minimal Wiring (Sep 10) [COMPLETED]
TASK-5.1 New TypeScript types (including WaypointCondition, SupportedLanguage), TASK-5.2 New API functions

**Status:** Completed & committed (`242f4b3`, `ff6d7eb`). Clean TypeScript compile and Vite build.

## Phase 6 — Testing (Sep 10) [COMPLETED]
TASK-6.1 Schema tests, TASK-6.2 Risk engine, TASK-6.3 Advisory compiler,
TASK-6.4 Conflict resolver, TASK-6.5 Alert engine, TASK-6.6 Route waypoint scoring,
TASK-6.7 Scheduler, TASK-6.8 Language detection

**Status:** Completed & committed (`7b1b013`). 76 passing automated unit tests across 15 suites.

## Phase 7 — Polish & Docs (Sep 10) [IN PROGRESS]
TASK-7.1 Update all docs, TASK-7.2 Smoke test all endpoints, TASK-7.3 Update AGENT.md

## Phase 8 — Full Frontend Build (Sep 11) [NEXT]
TASK-8.1 Evidence Provenance Panel, TASK-8.2 Conflict Log, TASK-8.3 Decision Pipeline Viz,
TASK-8.4 Voyage Tracker, TASK-8.5 Alert Banner, TASK-8.6 Wire Research Web,
TASK-8.7 Wire Fisherman App, TASK-8.8 Language switcher upgrade (TA/TE/BN/ML),
TASK-8.9 PWA service worker + offline cache, TASK-8.10 PWA manifest,
TASK-8.11 Voice UI (Sarvam STT/TTS), TASK-8.12 Route waypoint colored dots,
TASK-8.13 Frontend build + full integration test

---

## Schedule

```
SEP 10 (Today):
  Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 (ALL BACKEND + CORE TESTS COMPLETE)
  Phase 7: Docs & API Smoke Testing (current)

SEP 11 (Tomorrow):
  Phase 8: Full Frontend Build (Components, PWA offline, Voice UI, Map dots, E2E)

SEP 12 (Morning only):
  Final smoke test, backup demo video, judge presentation readiness. NO new features.
```

---

## Key API keys needed before starting

```ini
GROQ_API_KEY=       # groq.com — free, instant signup
CEREBRAS_API_KEY=   # cerebras.ai — free, instant signup
GEMINI_API_KEY=     # aistudio.google.com — free
SARVAM_API_KEY=     # sarvam.ai — ₹100 free credits
STORMGLASS_API_KEY= # stormglass.io — 50 req/day free
```

## Scraper refresh intervals (final)

| Source | Interval | Rationale |
|---|---|---|
| GDACS (cyclone) | **15 min** | Cyclones intensify fast. Long lag = danger. |
| Open-Meteo | **30 min** | Hourly forecast, cache already handles bursts |
| IMD advisories | **1 hr** | Emergency bulletins any time; 1hr is safe + respectful |
| StormGlass | **2 hr** | Tidal, slow changes; 50 req/day budget |
| INCOIS PFZ | **6 hr** | Satellite-derived, updates 1-2x/day max |

## Update discipline

After every task: `PROGRESS.md` entry → commit with `TASK-X.Y:` prefix → verify.
