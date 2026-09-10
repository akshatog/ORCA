# ORCA — Implementation Phases

Round 2 demo: **Sep 12, 2026**. Available days: Sep 10, Sep 11, Sep 12 morning.
Solo builder with AI coding agents.

---

## Phase 0 — Foundation (Sep 10, first)
TASK-0.1 Config YAML, TASK-0.2 schemas_v2.py, TASK-0.3 mock data, TASK-0.4 DECISIONS.md

**Blocking:** Nothing else starts until schemas + mock data exist.

## Phase 1 — LLM Layer (Sep 10)
TASK-1.1 Multi-provider LLM (Groq→Cerebras→Gemini→Template), TASK-1.2 Advisory Compiler

## Phase 2 — Core Pipeline (Sep 10)
TASK-2.1 LangGraph graph, TASK-2.2 POST /plan, TASK-2.3 GET /trace/{id},
TASK-2.4 verify /api/chat, TASK-2.5 route waypoint risk scoring

**Milestone:** `/plan` returns valid `DecisionState`. Routes have `waypoint_conditions[]` with colored risk dots.

## Phase 3 — Safety & Alerts (Sep 10)
TASK-3.1 Conflict Resolver, TASK-3.2 Voyage store, TASK-3.3 on_evidence_change,
TASK-3.4 Voyage/alert API

**Milestone:** Start voyage → inject severe advisory → `AlertEvent` fires → safe port returned.

## Phase 4 — Data Layer (Sep 11 morning)
TASK-4.1 GDACS (15min), TASK-4.2 StormGlass (2hr), TASK-4.3 IMD scraper (1hr),
TASK-4.4 INCOIS PFZ scraper (6hr), TASK-4.5 Tiered scheduler, TASK-4.6 Source registry,
TASK-4.7 Sarvam voice (STT+TTS), TASK-4.8 Language extension (TA/TE/BN/ML),
TASK-4.9 Advisory translation

**Milestone:** Live data flowing. Scraper pulls real advisory. Hindi voice works.
Tamil-script query detected and answered in Tamil.

## Phase 5 — Frontend Minimal Wiring (Sep 10, end of day)
TASK-5.1 New TypeScript types (including WaypointCondition), TASK-5.2 New API functions

## Phase 6 — Testing (Sep 10 evening + Sep 11)
TASK-6.1 Schema tests, TASK-6.2 Risk engine, TASK-6.3 Advisory compiler,
TASK-6.4 Conflict resolver, TASK-6.5 Alert engine, TASK-6.6 Route waypoint scoring,
TASK-6.7 Scheduler, TASK-6.8 Language detection

## Phase 7 — Polish & Docs (Sep 11 evening)
TASK-7.1 Update all docs, TASK-7.2 Smoke test all endpoints, TASK-7.3 Update AGENT.md

## Phase 8 — Full Frontend Build (Sep 11)
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
  Phase 0 → 1 → 2 → 3 → 5 → 6 (core tests)
  Target: full backend pipeline against mock data

SEP 11 (Tomorrow):
  Phase 4 (full day) → Phase 8 → Phase 6 (remaining) → Phase 7
  Target: live data, voice, 6 languages, full frontend

SEP 12 (Morning only):
  Final smoke test, backup demo video. NO new features.
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
