# ORCA — Project Overview

**SIH Problem Statement 26176. Round 2: Sep 12, 2026.**
**Build started Sep 10, 2026. Solo builder with AI coding agents.**

## The one-line spine

> ORCA helps fishermen decide where, when, and whether to fish — and keeps
> monitoring that decision while they're at sea. Two faces, one intelligence core.

Every feature, every task, every file must trace back to this sentence. If it
doesn't, it doesn't get built this round.

## Product shape

```
                     ORCA CORE (one backend, one agent graph)
                          │
             ┌────────────┴────────────┐
             │                         │
      FISHERMAN APP               RESEARCH WEB
      "What do I do?"             "Why / what is happening?"
      few actions, voice-first     evidence, agent trace, history
```

Both consume the same `/plan`, `/trace`, `/voyages`, `/alerts` API. The fisherman
never sees agent traces or raw evidence tables. The researcher/analyst view
exposes exactly that.

## The four capabilities that matter

1. **Intelligent trip planning** — weather + marine + PFZ + advisory → go/no-go,
   with reasons.
2. **Live voyage safety + alert + safe-port rerouting** — this is the headline
   demo moment. A voyage in progress must react to a new advisory.
3. **Voice-first regional experience** — Hindi + English solid first, more
   languages only once those two are bulletproof. Built LAST, after everything
   else works, because it takes the longest to verify.
4. **Research/analysis platform** — evidence provenance, agent trace, historical
   trends. This is what makes the "agentic AI" claim defensible under judge
   questioning.

## The one rule every module must obey

> The LLM plans, orchestrates, interprets narrative text, explains, and
> translates. The LLM never decides safety, never does GIS math, never
> determines boundary intersection or time validity, never calculates routes,
> and never arbitrates authoritative safety decisions.

## Current state — what already exists

This is a **migration** of a fully working codebase. The following are already
built and working (do not rebuild):

- **10 agents** (intent, planner, weather, ocean, pfz, cyclone, gis, risk,
  route, explanation) — concurrent via ThreadPoolExecutor
- **Risk engine** — piecewise-linear hazard curves + deterministic safety floors
- **Route optimizer** — full A* with zone-penalty grid
- **Live data client** — Open-Meteo Marine + Forecast with TTL cache
- **Trip economics** — fuel cost, catch probability, species, return-by time
- **17 frontend components** — trilingual (EN/HI/MR), fisherman app + research web
- **Design system** — nautical chart aesthetic, 30KB CSS, full animation system
- **Demo data store** — rehearsed scenarios per port (Mumbai/Goa/Paradip/Kochi/Digha)

## What's being built new (the ORCA 2.0 upgrades)

- **LangGraph** state graph (replacing ThreadPoolExecutor planner)
- **Gemini Flash** LLM (replacing Groq)
- **Advisory Compiler** — LLM parses IMD bulletin text → AdvisoryConstraint
- **Conflict Resolver** — authority-based evidence resolution
- **Voyage tracking** + `on_evidence_change` alert system
- **GDACS live cyclone feed** + StormGlass tide/current adapter
- **`POST /plan`** + **`GET /trace/{id}`** endpoints (new ORCA 2.0 API)
- **New schemas** (`schemas_v2.py`) alongside existing schemas

## Repo conventions

- `docs/` — this folder. Source of truth.
- `docs/DECISIONS.md` — append-only log of every real decision.
- `docs/PROGRESS.md` — updated after every completed task.
- Task IDs: `TASK-0.1`, `TASK-1.1`, etc. — referenced in commits and PROGRESS.md.
- `AGENT.md` — how coding agents should work in this repo.

## Reading order for a new coding agent session

1. `AGENT.md` — how to work
2. This file — what we're building
3. `01_architecture.md` — pipeline design
4. `02_schemas.md` — schema contracts
5. `DECISIONS.md` + `PROGRESS.md` — what changed, what's done
6. Whichever task-specific file applies (`03`–`09`)
