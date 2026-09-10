# AGENT.md — Rules for any coding agent working in this repo

This file governs *how* you work. `docs/` governs *what* you build.

## Context — Read this first

ORCA 2.0 is a **migration** of a proven, working codebase — not a greenfield build.
The `backend/` and `frontend/` directories contain a fully functional app (10 agents,
risk engine with deterministic safety floors, A* route optimizer, trilingual UI with
17 components). We are upgrading it to the ORCA 2.0 architecture spec, not rebuilding.

**Builder:** Solo builder (Akshay) with AI coding agents. Teammates join later.
**Deadline:** SIH Round 2 demo on **Sep 12, 2026**.
**LLM chain:** Groq (`llama-3.3-70b`) → Cerebras (`llama-3.1-70b`) → Gemini Flash 2.0 → Template engine.
Config env vars: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`, `SARVAM_API_KEY`, `STORMGLASS_API_KEY`.

## Reading order for a new session

1. This file (you're here)
2. `docs/00_overview.md` — project spine
3. `docs/01_architecture.md` — pipeline design
4. `docs/02_schemas.md` — frozen schema contracts (dual-schema strategy, see below)
5. `docs/DECISIONS.md` — what changed and why
6. `docs/PROGRESS.md` — what's done, what's open
7. Whatever task-specific doc applies (`03`–`09`)

## Dual-schema strategy

The codebase has **two** schema files:
- `backend/app/schemas.py` — the OLD internal schemas. The existing frontend, all 10
  agents, and the old `/api/chat` endpoint use these. **Do not break them.**
- `backend/app/schemas_v2.py` — the NEW ORCA 2.0 API-facing schemas (`Evidence_v2`,
  `DecisionState`, `AdvisoryConstraint`, `AlertEvent`, `ORCAState`). The new `/plan`
  endpoint and LangGraph graph use these.

Converter functions in `schemas_v2.py` bridge old → new. When in doubt, keep the old
path working and build the new path alongside it.

## Source of truth

- `docs/` is authoritative. If code disagrees with `docs/`, the docs are right — flag
  the mismatch in `docs/DECISIONS.md`, don't silently patch.
- `docs/02_schemas.md` is frozen for the new schemas. Do not add, rename, or change
  any field without a `DECISIONS.md` entry **before** the change.

## The one rule that overrides everything

The LLM may plan, orchestrate, interpret narrative text, explain, and translate.
**The LLM may never decide safety, perform GIS math, determine boundary intersection,
do time-validity checks, calculate routes, or arbitrate authoritative safety decisions.**

If a task asks you to route LLM output into a safety-critical field (`DecisionState.status`,
a floor calculation, a geometry) — stop and flag it. The task is wrong, not you.

## What NOT to touch

These components are battle-tested. Do not rewrite, refactor, or "improve" them:

| File | Why |
|---|---|
| `services/risk_engine.py` | Piecewise-linear curves + deterministic floors. Already better than the spec. |
| `services/route_optimizer.py` | Full A* with zone-penalty grid. Already built. |
| `data/live_client.py` | Open-Meteo caching. Battle-tested (burst throttling bug found and fixed). |
| `data/geo.py` | Ports, restricted zones, haversine, A* geometry. Pure Python, no deps. |
| `data/demo_store.py` | Fixture scenarios keyed by hour-of-day. Working. |
| `agents/planner.py` | Old orchestrator. Keep working for `/api/chat` backward compat. |
| `frontend/src/index.css` | 30KB design system. Proven. |

## Where things live

| Thing | Location |
|---|---|
| Risk thresholds | `backend/config/risk_thresholds.yaml` |
| Waypoint scoring weights | `backend/config/risk_thresholds.yaml` (route_scoring section) |
| Trip economics | `backend/config/trip_economics.yaml` |
| Mock/fixture data | `backend/app/data/mock_data/` |
| Old schemas (internal) | `backend/app/schemas.py` |
| New schemas (API) | `backend/app/schemas_v2.py` |
| LangGraph graph | `backend/app/graph/` |
| Voice service | `backend/app/services/voice.py` |
| Translate service | `backend/app/services/translate.py` |
| Advisory scraper | `backend/app/data/advisory_scraper.py` |
| Scheduler | `backend/app/data/scheduler.py` |
| Tests | `backend/tests/` |
| Env vars | `backend/.env` |

## Mock data rules

- ALL mock/fixture data lives in `backend/app/data/mock_data/`, never hardcoded in agents
- Every mock value is wrapped in the appropriate schema object
- Edge cases from `docs/09_testing_and_edge_cases.md` are explicitly modeled
- `demo_store.py` remains for the old frontend path — it's separate from mock_data

## Before you start any task

1. Read the task in the implementation plan or `docs/06_team_and_assignments.md`
2. Check `docs/DECISIONS.md` for anything that changed since the task was written
3. Check `docs/PROGRESS.md` for what's already done — don't rebuild completed work

## While implementing

- Match schemas exactly. Don't "improve" field names — if it looks wrong, that's a
  `DECISIONS.md` conversation, not a unilateral code change.
- Follow the testing boundary in `docs/09_testing_and_edge_cases.md` — test
  safety/parsing logic, skip formal suites for pure plumbing.
- Config values live in `config/*.yaml`, never as literals inside logic files.
- Prefer new clean files over surgically editing large existing files.
- Every new module must handle errors gracefully — never crash, never silently claim
  LIVE when data is CACHED/STALE/DEMO.

## After you finish a task

1. **Append** one line to `docs/PROGRESS.md`:
   ```
   YYYY-MM-DD HH:MM | TASK-ID | done: <what> | open: <what's left> | deviation: <if any, why>
   ```
2. If you deviated from spec, log it in `docs/DECISIONS.md` — not just in a comment.
3. **Commit** with the task ID in the message: `git commit -m "TASK-0.1: create config YAML files"`
4. **Verify** before claiming done — run the verification step specified in the task.

## Commit discipline

- One commit per completed task (or meaningful checkpoint within a large task)
- Message format: `TASK-X.Y: <what was done>`
- Never commit broken code — verify first
- `docs/PROGRESS.md` updated in the same commit as the task's code

## Reporting back

At the end of your run, report: files changed, tests run and results, anything flagged
rather than implemented. Don't report "done" if you skipped a stated acceptance test —
report what actually ran.