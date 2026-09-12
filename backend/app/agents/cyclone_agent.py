"""Cyclone / marine-alert agent.

Highest-priority agent in the system. If it reports an official severe warning,
the risk engine's deterministic floor forces EXTREME regardless of what every
other agent — or the language model — thinks.

LIVE mode: fetches the IMD CAP RSS feed via advisory_scraper.scrape_imd_cap_rss()
           and falls back to the GDACS feed if the CAP feed is empty.
DEMO mode: uses the demo_store as before.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from ..data import demo_store
from ..schemas import AgentResult, Location
from .base import live_enabled, timed

SEVERITY_RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}


def _cap_alerts_to_agent_format(cap_alerts: List[Dict]) -> List[Dict]:
    """Convert CAP RSS alert dicts to the format expected by the risk engine."""
    result = []
    for a in cap_alerts:
        result.append({
            "severity": a.get("severity", "moderate"),
            "official": a.get("official", True),
            "headline": a.get("headline", "IMD Marine Advisory"),
            "area_desc": a.get("area_desc", ""),
            "onset": a.get("onset"),
            "expires": a.get("expires"),
            "source": a.get("source", "IMD_CAP"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return result


@timed
def run(location: Location, when: datetime) -> AgentResult:
    stamp = when.isoformat(timespec="seconds")
    alerts: List[Dict] = []
    source = "DEMO"
    mode = "DEMO"

    if live_enabled():
        # Primary: IMD CAP RSS feed
        try:
            from ..data.advisory_scraper import scrape_imd_cap_rss
            cap_alerts = scrape_imd_cap_rss()
            if cap_alerts:
                alerts = _cap_alerts_to_agent_format(cap_alerts)
                source = "IMD_CAP"
                mode = "LIVE"
                stamp = datetime.now(timezone.utc).isoformat()
        except Exception:
            pass

        # Secondary: GDACS if IMD CAP returned nothing
        if not alerts:
            try:
                from ..data.live_client import fetch_gdacs
                gdacs_entries = fetch_gdacs()
                for entry in gdacs_entries:
                    alerts.append({
                        "severity": "severe" if entry.get("alert_level", "").lower() in ("red", "orange") else "moderate",
                        "official": True,
                        "headline": entry.get("title", "GDACS Marine Event"),
                        "area_desc": entry.get("description", ""),
                        "onset": entry.get("pub_date"),
                        "expires": None,
                        "source": "GDACS",
                        "timestamp": stamp,
                    })
                if gdacs_entries:
                    source = "GDACS"
                    mode = "LIVE"
            except Exception:
                pass

    # Final fallback: demo store
    if not alerts:
        alerts = demo_store.alerts(location.name, when)
        source = "DEMO"
        mode = "DEMO"

    alerts.sort(key=lambda a: SEVERITY_RANK.get(str(a.get("severity")).lower(), 0), reverse=True)
    worst = alerts[0] if alerts else None
    official = any(a.get("official") for a in alerts)

    return AgentResult(
        agent="cyclone",
        ok=True,
        location=location,
        data={
            "alerts": alerts,
            "count": len(alerts),
            "official_warning_active": official,
            "highest_severity": (worst or {}).get("severity"),
            "headline": (worst or {}).get("headline"),
        },
        source=source,
        timestamp=stamp,
        confidence=0.95 if alerts else 0.8,
        mode=mode,  # type: ignore[arg-type]
    )
