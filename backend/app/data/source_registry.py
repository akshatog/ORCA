"""Centralized Data Source Registry for ORCA 2.0.

Decouples specialist agents from hardcoded API/scraper clients.
Provides capability-based source discovery:
  capability -> ordered list of {source_name, fetch_fn, priority, is_live, refresh_interval_s}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class SourceMetadata:
    capability: str
    source_name: str
    fetch_fn: Optional[Callable[..., Any]]
    priority: int  # Lower number = higher priority
    is_live: bool
    refresh_interval_s: int
    description: str = ""


# In-memory registry storage: capability -> list of SourceMetadata
_REGISTRY: Dict[str, List[SourceMetadata]] = {}


def register_source(
    capability: str,
    source_name: str,
    fetch_fn: Optional[Callable[..., Any]],
    priority: int = 10,
    is_live: bool = True,
    refresh_interval_s: int = 1800,
    description: str = "",
) -> SourceMetadata:
    """Register a data provider under a given marine intelligence capability."""
    meta = SourceMetadata(
        capability=capability.lower().strip(),
        source_name=source_name,
        fetch_fn=fetch_fn,
        priority=priority,
        is_live=is_live,
        refresh_interval_s=refresh_interval_s,
        description=description,
    )
    cap = meta.capability
    if cap not in _REGISTRY:
        _REGISTRY[cap] = []

    # Replace existing source with same name or append
    _REGISTRY[cap] = [s for s in _REGISTRY[cap] if s.source_name != source_name]
    _REGISTRY[cap].append(meta)
    _REGISTRY[cap].sort(key=lambda s: s.priority)
    return meta


def get_sources(capability: str) -> List[SourceMetadata]:
    """Retrieve all providers registered for a capability, sorted by priority (1st = top)."""
    return list(_REGISTRY.get(capability.lower().strip(), []))


def get_primary_source(capability: str) -> Optional[SourceMetadata]:
    """Retrieve the highest-priority provider for a capability."""
    sources = get_sources(capability)
    return sources[0] if sources else None


def list_all_sources() -> Dict[str, List[SourceMetadata]]:
    """Return complete directory of all registered capabilities and sources."""
    return {k: list(v) for k, v in _REGISTRY.items()}


def clear_registry() -> None:
    """Reset registry for testing."""
    _REGISTRY.clear()


def init_default_sources() -> None:
    """Register standard ORCA 2.0 marine data providers."""
    # 1. Weather
    try:
        from .live_client import fetch_weather
    except Exception:
        fetch_weather = None
    try:
        from .stormglass_client import fetch_stormglass_point
    except Exception:
        fetch_stormglass_point = None

    register_source(
        capability="weather",
        source_name="Open-Meteo",
        fetch_fn=fetch_weather,
        priority=1,
        is_live=True,
        refresh_interval_s=1800,
        description="Public hourly atmospheric forecast (wind, rain, temperature, visibility)",
    )
    register_source(
        capability="weather",
        source_name="StormGlass",
        fetch_fn=fetch_stormglass_point,
        priority=2,
        is_live=True,
        refresh_interval_s=7200,
        description="Secondary weather & atmospheric data adapter",
    )

    # 2. Marine / Ocean
    try:
        from .live_client import fetch_marine
    except Exception:
        fetch_marine = None

    register_source(
        capability="ocean",
        source_name="Open-Meteo Marine",
        fetch_fn=fetch_marine,
        priority=1,
        is_live=True,
        refresh_interval_s=1800,
        description="Hourly sea state, wave height, wave period, SST",
    )
    register_source(
        capability="ocean",
        source_name="StormGlass Ocean",
        fetch_fn=fetch_stormglass_point,
        priority=2,
        is_live=True,
        refresh_interval_s=7200,
        description="Tidal streams and ocean surface currents",
    )

    # 3. Cyclone & Alerts
    try:
        from .live_client import fetch_gdacs
    except Exception:
        fetch_gdacs = None
    try:
        from .advisory_scraper import scrape_imd_bulletin
    except Exception:
        scrape_imd_bulletin = None

    register_source(
        capability="cyclone",
        source_name="GDACS",
        fetch_fn=fetch_gdacs,
        priority=1,
        is_live=True,
        refresh_interval_s=900,
        description="Global Disaster Alert and Coordination System cyclone RSS feed",
    )
    register_source(
        capability="cyclone",
        source_name="IMD Bulletins",
        fetch_fn=scrape_imd_bulletin,
        priority=2,
        is_live=True,
        refresh_interval_s=3600,
        description="Official India Meteorological Department coastal warnings",
    )

    # 4. PFZ
    try:
        from .advisory_scraper import scrape_incois_pfz
    except Exception:
        scrape_incois_pfz = None

    register_source(
        capability="pfz",
        source_name="INCOIS PFZ",
        fetch_fn=scrape_incois_pfz,
        priority=1,
        is_live=True,
        refresh_interval_s=21600,
        description="INCOIS satellite-derived chlorophyll & SST fishing zones",
    )


# Initialize default providers upon import
init_default_sources()
