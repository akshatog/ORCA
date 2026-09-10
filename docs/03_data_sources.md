# ORCA — Data Sources

## Confirmed sources, by tier

**Tier 1 — live, working now, keyless or instant-signup**
- **Open-Meteo** (Marine + Forecast) — wave height/period/direction, SST,
  swell, wind, rain, visibility, pressure. Backbone source. **Already
  integrated** in `data/live_client.py` with TTL caching (600s). Before
  adding a new provider for a field, check Open-Meteo's field list first.
- **StormGlass** — wave, swell, wind, **tide**, **sea current**, water temp.
  Free tier: 50 requests/day. Sign-up is instant. This is your only source
  for tide and current. Cache per-region on an interval — never per user
  query, the quota won't survive that. **Adapter: TASK-4.2.**
- **GDACS** — free, keyless RSS/XML feed of active global disaster events
  including tropical cyclones (position, wind speed/category, alert level
  green/orange/red). Use this for cyclone track/position — do not attempt to
  scrape IMD for this specifically. **Adapter: TASK-4.1.**

**Tier 3 — real, but gated: treat as `CACHED`, never `LIVE`**
- **IMD** — the official API (`api.imd.gov.in`) requires IP whitelisting
  after an approval process; not viable this round. Instead: fetch the
  **fisherman warning bulletin PDFs** (publicly accessible, no auth) on a
  schedule — a few times a day is enough, these aren't issued continuously.
- **INCOIS PFZ text advisories** — real, human-readable pages, confirmed
  format (location, depth, distance/direction from named landing centres),
  no clean API. Fetch periodically, cache, feed into PFZ ranking logic.
  Separately: check INCOIS's ERDDAP/Live Access Server (under Data Holdings)
  — if it's actually open and queryable, it's a much cleaner path for
  gridded ocean data (SST, currents). Unconfirmed — 20 minutes to check,
  promote to Tier 1 if it works.
- **MOSDAC** — has Open Data (no registration), Order Data (cart → SFTP
  delivery, not instant), and a documented Data Download API
  (`config.json` + `mdapi.py`). Access level being checked directly —
  see `DECISIONS.md` for the outcome once confirmed. Assume `CACHED` /
  batch-file delivery until proven otherwise.

**Tier 4 — not pursued this round**
- Damini (lightning) — no accessible public API confirmed. Keep `LIGHTNING`
  as a schema-level hazard type if you want to demonstrate it exists, populate
  with a clearly labeled synthetic event — never present it as real.

## The one caching pattern, used for every Tier 3 source

```python
def scheduled_refresh_job(source_name: str, fetch_fn, interval_minutes: int):
    """
    Calls fetch_fn(). On success: parse, wrap in Evidence with
    mode="CACHED", retrieved_at=now, write to the shared cache.
    On failure: keep the last known-good cached value, log the failure,
    never crash, never silently claim LIVE when it isn't.
    """
```

The live request path never calls IMD/INCOIS/MOSDAC directly — it always
reads from this cache. This is the honest design the `mode: CACHED` field
exists to represent, not a workaround.

**Before presenting:** run one final manual refresh right before the demo
rather than trusting a background job fired unattended at the right moment.

## Development sequencing

1. Build the entire backend against realistic **fixture data** first (see
   `08_testing_and_edge_cases.md` for the required edge cases — low
   confidence, conflicting sources, expired validity, missing field). The
   reasoning pipeline cannot tell the difference between fixture, cached, or
   live data — it only ever consumes typed `Evidence` objects.
2. Data teammate builds live adapters in parallel, against the same schema,
   with zero dependency on core reasoning being finished first.
3. "Integration" is registering a new fetch function into the source
   registry — the reasoning pipeline does not change when the source
   underneath it changes.

## Risk-threshold sanity check (do this once real data flows)

Once real data is live, do a quick pass on the Constraint Engine's floor
values (`04_risk_and_economics_config.md`) against real observed ranges —
not a redesign, just confirm the floors still feel right against real
wave/wind distributions rather than fixture ranges.
