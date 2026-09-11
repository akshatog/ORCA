# ORCA Development Rules

## Safety-first principles

1. **The LLM never decides safety.** Risk scores come from deterministic code
   with documented hazard curves and configurable floors. No LLM output may
   enter the Constraint Engine, Route Optimizer, or any GIS calculation.

2. **Floors only raise, never lower.** An official advisory can force a risk
   score up to 92, but no data can force it below what the weighted model
   produces. This is the core safety invariant.

3. **Data mode is always honest.** A `CACHED` value never becomes `LIVE` after
   the fact. A `DEMO` value is always labeled with the disclaimer. The `mode`
   field is the system's honesty contract.

## Code conventions

4. **Config in YAML, not in code.** Risk thresholds live in
   `config/risk_thresholds.yaml`. Trip economics in `config/trip_economics.yaml`.
   API keys in `.env`. Never hardcode these as Python literals inside logic files.

5. **Mock data in one place.** All fixtures live in `data/mock_data/`. Not
   scattered across agents. Not hardcoded in API routes.

6. **Dual schemas, don't break the old path.** `schemas.py` powers the existing
   frontend. `schemas_v2.py` powers the new API. Both coexist. Converters bridge
   them. When modifying agents, check which schema they return.

7. **Graceful degradation everywhere.** No adapter, agent, or service may crash
   on failure. Return last-known-good cached data with correct `mode`, or return
   empty results with an error field. Never silently error.

## Commit and tracking discipline

8. **One commit per task.** Message format: `TASK-X.Y: <what>`. Never commit
   broken code — verify first.

9. **PROGRESS.md updated in every task commit.** One line per task. If you
   deviated from spec, also log in DECISIONS.md.

10. **Tests for safety logic.** Test anything that decides safety or parses
    untrusted text. Skip heavy test suites for plumbing/UI. See
    `09_testing_and_edge_cases.md` for the boundary.

## Architecture boundaries

11. **Agents don't talk to each other.** Every agent reads from and writes to
    `ORCAState` (or returns `AgentResult` in the old path). No agent passes data
    directly to another agent.

12. **The Constraint Engine is called, never imported.** Core calls the safety
    engine via its function interface. Core does not inline risk-scoring logic.

13. **Route Optimizer is deterministic.** A* on a cost-weighted grid. No LLM
    in the loop. No randomness.

14. **Keep existing components intact.** `risk_engine.py`, `route_optimizer.py`,
    `live_client.py`, `geo.py`, `demo_store.py` are battle-tested. Do not
    refactor, "improve," or rewrite them unless fixing a specific bug.
