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

<!-- Add new entries above this line, newest at the bottom of the log but
     above this comment, so the file reads chronologically top-to-bottom. -->
