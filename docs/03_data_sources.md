# ORCA — Data Sources

## Confirmed sources, by tier

**Tier 1 — live, working now, keyless or instant-signup**
- **Open-Meteo** (Marine + Forecast) — wave height/period/direction, SST,
  swell, wind, rain, visibility, pressure. Backbone source. **Already
  integrated** in `data/live_client.py` with TTL caching (600s).
- **GDACS** — free, keyless RSS/XML feed of active global disaster events
  including tropical cyclones (position, wind speed/category, alert level
  green/orange/red).
- **IMD** — fisherman warning bulletins are scraped periodically and parsed.
- **INCOIS** — PFZ text advisories and geospatial bounding data are retrieved live.
- **MOSDAC** — OceanSat-3 `E06OCM_L4_AC` Chlorophyll-a data is downloaded natively and parsed via h5py/scipy as NetCDF3/NetCDF4 data. Fully operational via scheduled task.

**Tier 3 — real, but gated: treat as `CACHED`, never `LIVE`**
(None currently. IMD, INCOIS, and MOSDAC were successfully promoted to Tier 1)

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
