# ORCA — Edge Cases & Testing Boundary

## Testing rule

**Test anything that decides safety or parses untrusted external text. Skip
heavy testing on pure plumbing.**

Must test (3 cases each: valid, missing/malformed input, boundary value):
- `Evidence` / `AdvisoryConstraint` / `DecisionState` schema validation
- Constraint Engine (floors only raise, weighted sum, status transitions)
- Advisory Compiler confidence threshold → `INSUFFICIENT_EVIDENCE` branch

Skip dedicated test suites for: GIS distance math, generic HTTP-caching
wrappers, UI rendering. Sanity-check these by running them, don't build
formal test files for them this round.

## Required fixture edge cases (Phase 1)

Build these into your mock data deliberately — not just happy-path values:

1. **Low-confidence advisory** — an `AdvisoryConstraint` with
   `confidence < 0.70`, to exercise the `INSUFFICIENT_EVIDENCE` path.
2. **Conflicting sources** — two `Evidence` objects for the same metric and
   region disagreeing (e.g. two wave-height readings 1.5x apart), to exercise
   the Authority/Conflict Policy stage.
3. **Expired validity window** — an `Evidence` object whose `valid_until`
   is in the past, to exercise `STALE` handling.
4. **Missing field** — a partially-populated `Evidence` object (e.g. no
   `geometry`) to confirm downstream code degrades gracefully instead of
   crashing.
5. **Network failure** — simulate a dead data-layer endpoint, confirm the
   cache fallback returns the correct `mode` rather than erroring.
6. **Official NO_GO with mild local numbers** — an official advisory says
   NO_GO for a region while the local wind/wave readings look mild, to
   confirm the floor logic (`official_advisory: true`) actually overrides
   the weighted score rather than being averaged into it.
7. **Cyclone override** — a GDACS orange/red alert covering the region
   while other evidence reads calm, to confirm `CYCLONE_FLOOR` fires.
8. **Ambiguous intent** — a query the Intent Planner can't confidently
   classify as operational vs analytical — confirm it asks for
   clarification rather than guessing into a safety-relevant branch.

## Test-forced-failure requirement (Person A, Data layer)

Every adapter, without exception: test the forced-failure path — confirm it
degrades to the last cached value cleanly, never crashes, never silently
claims `LIVE` when it isn't.
