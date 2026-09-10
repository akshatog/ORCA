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
<!-- entries go here, oldest first -->
