"""Tiered Data Scheduler for ORCA 2.0.

Manages periodic background scrapers and API cache warming according to
the data refresh cadence defined in the project specification:
  - GDACS cyclone feed:      every 15 min (fast intensification)
  - Open-Meteo cache:        every 30 min (marine and atmospheric forecast)
  - IMD Advisory bulletins:  every 1 hr   (official emergency bulletins)
  - StormGlass cache:        every 2 hr   (tides and currents within 50 req/day quota)
  - INCOIS PFZ bulletins:    every 6 hr   (satellite-derived daily updates)

All jobs are warmed at startup so first user queries are answered from cache immediately.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from ..data.geo import PORTS
from ..data.voyage_store import get_active_voyages

log = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def job_fetch_gdacs() -> None:
    """Fetch GDACS cyclone feed (15 min)."""
    try:
        from .live_client import fetch_gdacs
        entries = fetch_gdacs(force=True)
        log.info("[Scheduler] GDACS checked: %d event(s) in Indian Ocean", len(entries))
    except Exception as e:
        log.warning("[Scheduler] GDACS fetch failed: %s", e)


def job_fetch_open_meteo() -> None:
    """Warm Open-Meteo marine and weather cache for key ports and active voyages (30 min)."""
    try:
        from .live_client import fetch_marine, fetch_weather
        now = datetime.now(timezone.utc)

        # Collect target coordinates from active voyages + top ports
        targets = []
        for v in get_active_voyages():
            targets.append((float(v.location["lat"]), float(v.location["lon"])))

        # Also warm primary demo ports
        for p in PORTS[:3]:  # Mumbai, Ratnagiri, Goa
            targets.append((p["lat"], p["lon"]))

        for lat, lon in targets:
            fetch_marine(lat, lon, now)
            fetch_weather(lat, lon, now)

        log.info("[Scheduler] Open-Meteo cache refreshed for %d location(s)", len(targets))
    except Exception as e:
        log.warning("[Scheduler] Open-Meteo cache refresh failed: %s", e)


def job_fetch_imd_advisory() -> None:
    """Scrape and compile IMD coastal bulletins (1 hr)."""
    try:
        from .advisory_scraper import scrape_imd_bulletin
        advisories = scrape_imd_bulletin(force=True)
        log.info("[Scheduler] IMD bulletin checked: %d active advisory constraint(s)", len(advisories))
    except Exception as e:
        log.warning("[Scheduler] IMD advisory check failed: %s", e)


def job_fetch_stormglass() -> None:
    """Warm StormGlass tide/current cache for active voyage regions (2 hr)."""
    try:
        from .stormglass_client import fetch_stormglass_point
        voyages = get_active_voyages()
        if voyages:
            for v in voyages:
                fetch_stormglass_point(float(v.location["lat"]), float(v.location["lon"]))
            log.info("[Scheduler] StormGlass refreshed for %d active voyage(s)", len(voyages))
        else:
            # Refresh default port
            default_port = PORTS[0]
            fetch_stormglass_point(default_port["lat"], default_port["lon"])
            log.info("[Scheduler] StormGlass refreshed for base port (%s)", default_port["name"])
    except Exception as e:
        log.warning("[Scheduler] StormGlass refresh failed: %s", e)


def job_fetch_incois_pfz() -> None:
    """Scrape INCOIS Potential Fishing Zones (6 hr)."""
    try:
        from .advisory_scraper import scrape_incois_pfz
        zones = scrape_incois_pfz(force=True)
        log.info("[Scheduler] INCOIS PFZ scraped: %d zone(s) active", len(zones))
    except Exception as e:
        log.warning("[Scheduler] INCOIS PFZ check failed: %s", e)


def start_scheduler(run_warmup: bool = False) -> BackgroundScheduler:
    """Initialize and start the tiered background scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True)

    # Register jobs with their designated intervals
    _scheduler.add_job(job_fetch_gdacs, "interval", minutes=15, id="fetch_gdacs_and_alert", replace_existing=True)
    _scheduler.add_job(job_fetch_open_meteo, "interval", minutes=30, id="fetch_open_meteo_cache", replace_existing=True)
    _scheduler.add_job(job_fetch_imd_advisory, "interval", hours=1, id="fetch_imd_advisory", replace_existing=True)
    _scheduler.add_job(job_fetch_stormglass, "interval", hours=2, id="fetch_stormglass_cache", replace_existing=True)
    _scheduler.add_job(job_fetch_incois_pfz, "interval", hours=6, id="fetch_incois_pfz", replace_existing=True)

    _scheduler.start()
    log.info("ORCA 2.0 Tiered Scheduler started with 5 background cadence jobs.")

    if run_warmup:
        # Run all jobs once at startup to warm caches
        job_fetch_gdacs()
        job_fetch_open_meteo()
        job_fetch_imd_advisory()
        job_fetch_stormglass()
        job_fetch_incois_pfz()

    return _scheduler


def stop_scheduler() -> None:
    """Shut down the background scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("ORCA 2.0 Tiered Scheduler stopped.")


def get_scheduler_status() -> Dict[str, Any]:
    """Inspect status of all configured background jobs."""
    if _scheduler is None or not _scheduler.running:
        return {"status": "stopped", "jobs": []}

    job_list: List[Dict[str, Any]] = []
    for job in _scheduler.get_jobs():
        job_list.append({
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "status": "running",
        "job_count": len(job_list),
        "jobs": job_list,
    }
