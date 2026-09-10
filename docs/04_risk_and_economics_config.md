# ORCA — Risk Thresholds & Trip Economics

## Constraint Engine design

```
NORMALIZE  →  WEIGHTED SUM  →  DETERMINISTIC FLOORS  →  FINAL STATUS
```

Floors only ever raise the risk score — never lower it. Thresholds live in
config (below), never hardcoded inside logic.

```python
risk_score = weighted_score(evidence)   # normalize + weighted sum

if official_no_go_advisory:
    risk_score = max(risk_score, NO_GO_FLOOR)
if wave_height_m >= NO_GO_FLOOR_WAVE or wind_speed_kmph >= NO_GO_FLOOR_WIND:
    risk_score = max(risk_score, NO_GO_FLOOR)
if gdacs_alert_level in ("orange", "red"):
    risk_score = max(risk_score, CYCLONE_FLOOR)
```

## Config values (starting point — grounded, not arbitrary)

These are approximations informed by real advisory practice: INCOIS's own
Boat Safety Index approach flags an area as dangerous for small craft once
its wind/wave "enhancement factor" reaches 0.2; real IMD swell-surge
bulletins for Indian coastal fishing routes trigger a "ply with utmost
vigilance" advisory around 0.9–1.7 m swell height; the international
small-craft-advisory norm sits at roughly 20–33 knots sustained wind with
4–7 ft (1.2–2.1 m) seas, stepping up to gale warning at 34–47 knots.

```yaml
CAUTION_FLOOR:
  wave_height_m: 1.2
  wind_speed_kmph: 37        # ~20 knots

NO_GO_FLOOR:
  wave_height_m: 3.0
  wind_speed_kmph: 63        # ~34 knots, gale warning
  official_advisory: true    # any real IMD/INCOIS NO_GO bulletin always forces this

CYCLONE_FLOOR:
  gdacs_alert_level: ["orange", "red"]
```

**Honesty note for judges:** these are a reasonable hackathon approximation
grounded in real advisory thresholds, not a certified maritime-authority
standard. Say this plainly if asked — it's a stronger answer than pretending
otherwise.

## Advisory Compiler confidence rule

```
LLM parse confidence < 0.70  →  status = INSUFFICIENT_EVIDENCE
```

Never let a low-confidence LLM region/severity guess become a NO_GO. This is
one of your strongest "we considered failure modes" details — keep it
visible in the explanation output when it fires.

## Trip economics

```
trip_cost    = (distance_km * 2 * fuel_rate_l_per_km * fuel_price_per_l)
               + fixed_provisions_estimate
trip_revenue = estimated_catch_kg * avg_market_price_per_kg
trip_value   = trip_revenue - trip_cost
```

`estimated_catch_kg` derives from the PFZ advisory's stated catch-potential
label (INCOIS PFZ bulletins classify zones HIGH/MEDIUM/LOW) mapped through a
config'd kg-per-potential-level value, scaled by an assumed boat capacity.

**Provenance requirement:** wrap the output as an `Evidence` with
`authority_level: "derived"`, and list exactly which inputs produced it
(distance, fuel price, catch-potential label, market price) in a `reasons`
field on the `DecisionState.trip_economics` object. If a judge asks "where
did this number come from," you show the trail, not just the figure.

**Separation rule:** a profitable trip must never override a dangerous one.
`trip_economics` is informational and sits alongside `status`, never inside
the logic that computes `status`.

## Waypoint risk scoring weights

Also lives in `config/risk_thresholds.yaml`. These control route scoring:

```yaml
route_scoring:
  avg_weight: 0.70        # weight of average waypoint risk in path score
  spike_weight: 0.30      # weight of worst waypoint (storm-band penalty)
  wave_weight: 0.60       # within each waypoint: wave vs wind split
  wind_weight: 0.40
  samples_per_route: 5    # target number of waypoints sampled per route
  min_sample_spacing_km: 8.0  # never sample closer than this
```

Rule: `avg_weight + spike_weight` must equal 1.0. `wave_weight + wind_weight` must equal 1.0.
If YAML is missing, hardcoded defaults from `config.py` apply.

## Config file location

Put the YAML block above in `backend/config/risk_thresholds.yaml` and the economics
constants in `backend/config/trip_economics.yaml` — both loaded at startup by
`config.py`, never imported as Python literals inside the Constraint Engine module
itself. If the YAML files are missing, `config.py` falls back to the hardcoded
defaults in `RiskConfig`.
