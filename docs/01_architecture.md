# ORCA — Architecture

## Primary pipeline (operational intent)

```
USER
 │
 ▼
Intent Planner (LLM: classify operational vs analytical, extract params)
 │
 ├─────────────┬─────────────┬─────────────┐
 ▼             ▼             ▼             ▼
Weather      Marine         PFZ         Advisory
 Agent        Agent        Agent         Agent
 │             │             │             │
 └─────────────┴──────┬──────┴─────────────┘
                       ▼
               Evidence Store (shared state — every result lands here as
               an Evidence object, nothing else flows between stages)
                       │
                       ▼
             Authority / Conflict Policy
      (resolves disagreeing sources BEFORE constraints run —
       e.g. two wave-height readings that disagree get resolved
       to one, tagged conflict_status, before the safety engine
       ever sees them)
                       │
                       ▼
              Constraint Engine
        (deterministic — normalize → weighted sum → floors
         that only raise risk, never lower it. NO LLM INPUT
         ENTERS THIS STAGE.)
                       │
                       ▼
             Provisional Trip Window
                       │
                       ▼
            Voyage / Route Optimizer
        (GIS math, A*-with-zone-penalty routing — deterministic)
                       │
                       ▼
              Refined Trip Window
                       │
                       ▼
               Decision State
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Explanation          Trip Economics
        (LLM narrates       (deterministic formula,
         the decision,       see 04_risk_and_
         does not make it)   economics_config.md)
              │                 │
              └────────┬────────┘
                       ▼
           Fisherman App  /  Research Web
```

## Secondary pipeline (monitoring / alert path — reuses the Constraint Engine)

```
New evidence arrives (scheduled poll, or a pushed advisory)
                       │
                       ▼
              on_evidence_change(new_evidence)
                       │
                       ▼
        Find all active voyages whose region/time
        window intersects the new evidence
                       │
                       ▼
        Re-run Constraint Engine for each affected voyage
                       │
                       ▼
              Status changed for the worse?
                 │              │
                YES             NO
                 │              │
                 ▼              ▼
           AlertEvent         (no-op)
                 │
                 ▼
     Compute safe-port recommendation
     (nearest port NOT inside an active NO_GO zone)
                 │
                 ▼
        Push notification → Fisherman App
        (+ optional spoken alert via Voice Gateway)
```

## Analytical branch (research web — sibling, not a fork)

Same core (planner → agents → evidence → constraints), but the Intent Planner
classifies the request as `analytical` instead of `operational`, and the
response surfaces the full evidence trail, agent execution trace, and
historical comparisons instead of a single go/no-go decision. It is the same
graph, same nodes, different terminal formatting and depth of exposure — not
a separate system.

```
                   ORCA CORE
                       │
             ┌─────────┴─────────┐
             │                   │
        Operational          Analytical
           Intent               Intent
             │                   │
             ▼                   ▼
       Fisherman App         Research Web
```

## LangGraph state object

```python
class ORCAState(BaseModel):
    request_id: str
    intent: Literal["operational", "analytical"]
    raw_query: str
    language: str
    location: Optional[dict] = None          # GeoJSON point
    evidence: list[Evidence] = []
    advisories: list[AdvisoryConstraint] = []
    conflict_log: list[dict] = []             # what was resolved, and how
    decision: Optional["DecisionState"] = None
    trace: list[dict] = []                    # every node's input/output, for research web
```

Every agent node reads from and writes to this one object. No agent passes
data directly to another agent — everything goes through `ORCAState`. This is
what makes the graph traceable (the `trace` list is literally your "agent
trace" feature for the research web, for free, if every node appends to it).

## Migration status: ThreadPoolExecutor → LangGraph (IN PROGRESS)

The old codebase (`agents/planner.py`) uses `ThreadPoolExecutor` for
concurrent agent execution. This works and remains the active path for
the legacy `/api/chat` endpoint. LangGraph is being built alongside it:

- Each agent function is wrapped as a **LangGraph node** in `graph/nodes.py`
  (function taking `ORCAState`, returning a partial state update).
- The fan-out/fan-in is **explicit parallel edges**: Intent → [Weather,
  Marine, PFZ, Advisory, GIS] → Evidence Store → Constraint Engine → Route
  → Explanation.
- The compiled graph powers the new `POST /plan` endpoint and can be
  **visualized** — this IS the architecture diagram for judges, generated
  from real code.
- The old `planner.py::handle()` stays working for `/api/chat` — both
  paths coexist until the frontend is fully wired to `/plan`.

### New nodes not in the old planner:
- **Evidence Store** — merges all evidence, identifies conflicts
- **Conflict Resolver** — authority-based resolution before constraint engine
- **Advisory Compiler** — LLM parses bulletin text into AdvisoryConstraint

## Non-negotiable boundary (repeat this in every module's spec)

LLM calls exist only in: Intent Planner (classify + extract params),
Advisory Compiler (parse narrative bulletin text into structured fields, with
a confidence score), and Explanation (narrate the decision in the target
language). Every other node — Constraint Engine, Route Optimizer, Authority/
Conflict Policy, GIS calculations — is deterministic code with no LLM in the
loop.
