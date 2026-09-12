"""Ocean agent — wave height/period, sea state, SST, surface current, chlorophyll."""
from __future__ import annotations

from datetime import datetime

from ..data import demo_store, live_client
from ..schemas import AgentResult, Location
from .base import live_enabled, measurement, timed


@timed
def run(location: Location, when: datetime) -> AgentResult:
    stamp = when.isoformat(timespec="seconds")
    mode, source = "DEMO", "DEMO"
    unavailable = []

    live = live_client.fetch_marine(location.latitude, location.longitude, when) if live_enabled() else None
    cond = demo_store.conditions(location.name, when)

    if live and live.get("wave_height_m") is not None:
        mode, source = "LIVE", "OPEN_METEO"
        wave = live["wave_height_m"]
        period = live.get("wave_period_s")
        sst = live.get("sst_c")
        stamp = live.get("valid_time", stamp)

        # Open-Meteo Marine provides ocean_current_velocity — use it if present.
        current = live.get("current_speed_ms")
        if current is None:
            current = cond["current"]
            unavailable.append("surface current not available from provider for this location — demo value shown")
    else:
        if live_enabled():
            unavailable.append("live marine provider unreachable — using cached demo data")
        wave = cond["wave"]
        period = cond["period"]
        sst = cond["sst"]
        current = cond["current"]

    # Chlorophyll: try MOSDAC satellite (OceanSat-3 L4 daily composite) in LIVE mode.
    # Falls back to demo_store value if credentials missing or file unavailable.
    chl = cond["chl"]
    if live_enabled():
        try:
            from ..data.mosdac_client import fetch_mosdac_chlorophyll
            mosdac_chl = fetch_mosdac_chlorophyll(location.latitude, location.longitude, when)
            if mosdac_chl is not None:
                chl = mosdac_chl
            else:
                unavailable.append("MOSDAC chlorophyll unavailable — demo value shown")
        except Exception:
            unavailable.append("MOSDAC chlorophyll unavailable — demo value shown")

    state = demo_store.sea_state(float(wave))

    return AgentResult(
        agent="ocean",
        ok=True,
        location=location,
        data={
            "wave_height_m": round(float(wave), 2),
            "wave_period_s": None if period is None else round(float(period), 1),
            "sea_state": state,
            "sst_c": None if sst is None else round(float(sst), 1),
            "current_speed_ms": round(float(current), 2),
            "chlorophyll_mg_m3": round(float(chl), 2),
        },
        measurements={
            "wave_height": measurement(round(float(wave), 2), "m", "Wave height", source, stamp, mode),
            "wave_period": measurement(None if period is None else round(float(period), 1),
                                       "s", "Wave period", source, stamp, mode),
            "sst": measurement(None if sst is None else round(float(sst), 1),
                               "deg C", "Sea surface temperature", source, stamp, mode),
        },
        unavailable=unavailable,
        source=source,
        timestamp=stamp,
        confidence=0.88 if mode == "LIVE" else 0.75,
        mode=mode,  # type: ignore[arg-type]
    )
