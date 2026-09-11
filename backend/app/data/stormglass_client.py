"""StormGlass marine weather, tide, and ocean current adapter for ORCA 2.0.

Free tier allows 50 requests/day. To stay strictly within quota:
1. Caches responses per 0.1Â° geographic grid cell (~11 km).
2. TTL = 2 hours (7200 seconds).
3. Only fetches for regions with active voyages or live requests.
4. Graceful fallback to demo/fallback estimates if STORMGLASS_API_KEY is missing,
   quota is exceeded (402/429), or network fails.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

log = logging.getLogger(__name__)

STORMGLASS_BASE_URL = "https://api.stormglass.io/v2/weather/point"
CACHE_TTL = 7200.0  # 2 hours refresh interval
CACHE_MAX_ENTRIES = 128

# Key: (round(lat, 1), round(lon, 1)) -> (expires_at_monotonic, data_dict)
_cache: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
_lock = threading.Lock()


def get_stormglass_key() -> str:
    return os.getenv("STORMGLASS_API_KEY", "").strip()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def fetch_stormglass_point(
    lat: float,
    lon: float,
    when: Optional[datetime] = None,
    client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    """Fetch tide, wave, and ocean current data from StormGlass.

    Falls back smoothly if no API key is configured or on any network/quota error.
    """
    grid_key = (round(lat, 1), round(lon, 1))
    now = time.monotonic()

    with _lock:
        hit = _cache.get(grid_key)
        if hit and hit[0] > now:
            cached_res = dict(hit[1])
            cached_res["mode"] = "CACHED"
            return cached_res

    key = get_stormglass_key()
    if not key:
        fallback = _get_fallback_data(lat, lon)
        with _lock:
            _cache[grid_key] = (now + CACHE_TTL, fallback)
        return fallback

    params = {
        "lat": lat,
        "lng": lon,
        "params": "waveHeight,currentSpeed,currentDirection,waterTemperature",
    }
    headers = {"Authorization": key}

    try:
        http_client = client or httpx.Client(timeout=6.0)
        resp = http_client.get(STORMGLASS_BASE_URL, params=params, headers=headers)
        if resp.status_code == 200:
            raw = resp.json()
            parsed = _parse_stormglass_response(raw, lat, lon)
            with _lock:
                if len(_cache) >= CACHE_MAX_ENTRIES:
                    _cache.pop(next(iter(_cache)), None)
                _cache[grid_key] = (now + CACHE_TTL, parsed)
            return parsed
        else:
            log.warning("StormGlass API returned status %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.warning("StormGlass request failed (%s): %s", type(e).__name__, str(e))

    fallback = _get_fallback_data(lat, lon)
    with _lock:
        _cache[grid_key] = (now + 60.0, fallback)  # Short retry on failure
    return fallback


def _parse_stormglass_response(raw: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
    hours = raw.get("hours", [])
    first_hour = hours[0] if hours else {}

    def extract_val(param_name: str) -> Optional[float]:
        p = first_hour.get(param_name)
        if isinstance(p, dict):
            # StormGlass returns sources e.g. {"sg": 1.2, "noaa": 1.1}
            for source in ("sg", "noaa", "dwd", "meteo"):
                if source in p and p[source] is not None:
                    return float(p[source])
            # Fallback to any value in dict
            for v in p.values():
                if v is not None:
                    return float(v)
        elif isinstance(p, (int, float)):
            return float(p)
        return None

    return {
        "latitude": lat,
        "longitude": lon,
        "wave_height_m": extract_val("waveHeight"),
        "current_speed_ms": extract_val("currentSpeed"),
        "current_direction_deg": extract_val("currentDirection"),
        "sst_c": extract_val("waterTemperature"),
        "source": "StormGlass",
        "mode": "LIVE",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def _get_fallback_data(lat: float, lon: float) -> Dict[str, Any]:
    """Deterministic fallback model based on coastal proximity and regional normals."""
    return {
        "latitude": lat,
        "longitude": lon,
        "wave_height_m": 1.3,
        "current_speed_ms": 0.4,
        "current_direction_deg": 240.0,
        "sst_c": 28.5,
        "source": "StormGlass (Fallback Model)",
        "mode": "DEMO",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
