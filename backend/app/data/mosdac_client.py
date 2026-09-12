"""MOSDAC Data Download API client for ORCA 2.0.

MOSDAC (Meteorological and Oceanographic Satellite Data Archival Centre, ISRO)
provides satellite-derived Chlorophyll and SST data for the Indian Ocean.

This adapter wraps the MOSDAC Data Download API (mdapi) directly, replicating
the exact HTTP calls made by the official mdapi.py tool, so ORCA can fetch
real satellite files without running the external script.

API ENDPOINTS (reverse-engineered from official mdapi.py v2025):
  Search:   GET  https://mosdac.gov.in/apios/datasets.json
  Auth:     POST https://mosdac.gov.in/download_api/gettoken
  Download: GET  https://mosdac.gov.in/download_api/download
  Logout:   POST https://mosdac.gov.in/download_api/logout

DATASETS USED:
  - Chlorophyll: E06OCM_L4_AC    (OceanSat-3/EOS-06, L4 daily composite, ~4km)
  - SST:         3RIMG_L2B_SST   (INSAT-3DR, L2B, ~4km, ~hourly)

USAGE NOTES:
  - Set MOSDAC_USER and MOSDAC_PASS in backend/.env.
  - The adapter searches for files from today, downloads to a local cache dir,
    parses the HDF5/NetCDF file to extract the scalar value at the query point,
    and caches the result for CACHE_TTL seconds.
  - Requires: h5py (for HDF5), scipy (for nearest-point lookup). Both are
    lightweight and already common in scientific Python stacks.
  - 5000 file/day download limit. One file covers the full Indian Ocean.
    At 1 file/day each for CHL and SST we use 2 of 5000 — essentially no limit.

GRACEFUL DEGRADATION:
  - If credentials are missing → returns None (caller uses Open-Meteo/demo).
  - If MOSDAC server is unreachable → returns None.
  - If today's file is already in the local cache dir → uses it, no download.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx

log = logging.getLogger(__name__)

# MOSDAC API endpoints (from official mdapi.py)
_TOKEN_URL    = "https://mosdac.gov.in/download_api/gettoken"
_SEARCH_URL   = "https://mosdac.gov.in/apios/datasets.json"
_DOWNLOAD_URL = "https://mosdac.gov.in/download_api/download"
_LOGOUT_URL   = "https://mosdac.gov.in/download_api/logout"

# Dataset IDs
DATASET_CHL = "E06OCM_L4_AC"    # OceanSat-3 Chlorophyll L4 daily composite
DATASET_SST = "3RIMG_L2B_SST"   # INSAT-3DR SST L2B

# Cache TTL: 6 hours (these are daily composites; no point fetching more often)
CACHE_TTL = 21600.0

# Local directory where downloaded HDF5 files are stored
_DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "mosdac_cache"

# In-memory value cache: (dataset, date_str) → (expires_at, scalar_value_or_None)
_value_cache: Dict[Tuple[str, str], Tuple[float, Optional[float]]] = {}
_lock = threading.Lock()


def _get_credentials() -> Tuple[str, str]:
    """Return (username, password) from environment. Empty strings if not set."""
    user = os.getenv("MOSDAC_USER", "").strip()
    pwd  = os.getenv("MOSDAC_PASS", "").strip()
    return user, pwd


def _get_cache_dir() -> Path:
    cache_dir = Path(os.getenv("MOSDAC_CACHE_DIR", str(_DEFAULT_CACHE_DIR)))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _search_files(
    dataset_id: str,
    date: datetime,
    client: httpx.Client,
) -> list[Dict[str, Any]]:
    """Search MOSDAC catalog for files matching the dataset/date.

    Returns a list of file metadata dicts from the search response.
    NOTE: MOSDAC L4 files are GLOBAL coverage, so no bounding box is needed.
    The response key is 'entries' (not 'entry') and the download ID is the
    numeric 'id' field (gId), not 'identifier' which is the filename.
    """
    date_str = date.strftime("%Y-%m-%d")
    params: Dict[str, Any] = {
        "datasetId": dataset_id,
        "startTime": date_str,
        "endTime": date_str,
    }

    try:
        resp = client.get(_SEARCH_URL, params=params, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            # API returns 'entries' (plural), not 'entry'
            entries = data.get("entries", []) or []
            log.debug("[MOSDAC] Search %s %s -> %d file(s) (total=%s)",
                      dataset_id, date_str, len(entries), data.get("totalResults"))
            return entries
        else:
            log.warning("[MOSDAC] Search returned HTTP %s for %s", resp.status_code, dataset_id)
            return []
    except Exception as exc:
        log.warning("[MOSDAC] Search request failed: %s", exc)
        return []


def _authenticate(client: httpx.Client) -> Optional[str]:
    """Login to MOSDAC and return an access token, or None on failure."""
    username, password = _get_credentials()
    if not username or not password:
        return None

    try:
        resp = client.post(
            _TOKEN_URL,
            json={"username": username, "password": password},
            timeout=10.0,
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                log.info("[MOSDAC] Authenticated as %s", username)
                return token
        log.warning("[MOSDAC] Auth failed: HTTP %s — %s", resp.status_code, resp.text[:200])
        return None
    except Exception as exc:
        log.warning("[MOSDAC] Auth request failed: %s", exc)
        return None


def _logout(client: httpx.Client, username: str) -> None:
    """Best-effort logout to close the MOSDAC session."""
    try:
        client.post(_LOGOUT_URL, json={"username": username}, timeout=5.0)
    except Exception:
        pass


def _download_file(
    file_entry: Dict[str, Any],
    access_token: str,
    dest_dir: Path,
    client: httpx.Client,
) -> Optional[Path]:
    """Download a single MOSDAC file and return its local path.

    The numeric 'id' field (gId) is passed to the download endpoint.
    The 'identifier' field is the actual filename (e.g. E06OCML4AC_20260910_25km_v1.0.1.nc).
    Skips download if the file already exists in the cache directory.
    """
    # 'id' is the numeric gId used for download; 'identifier' is the filename
    file_gid   = str(file_entry.get("id", "")).strip()
    identifier = str(file_entry.get("identifier", file_gid)).strip()

    if not file_gid:
        log.warning("[MOSDAC] File entry missing id: %s", file_entry)
        return None

    # Use the actual filename from 'identifier' as the local filename
    if identifier and not identifier.isdigit():
        dest_path = dest_dir / identifier
    else:
        dest_path = dest_dir / f"mosdac_{file_gid}.nc"

    if dest_path.exists():
        log.debug("[MOSDAC] Cache hit: %s", dest_path.name)
        return dest_path

    try:
        params  = {"id": file_gid}
        headers = {"Authorization": f"Bearer {access_token}"}
        with client.stream("GET", _DOWNLOAD_URL, params=params, headers=headers, timeout=120.0) as resp:
            if resp.status_code != 200:
                log.warning("[MOSDAC] Download failed HTTP %s for gId=%s", resp.status_code, file_gid)
                return None
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
        log.info("[MOSDAC] Downloaded %s -> %s", identifier, dest_path.name)
        return dest_path
    except Exception as exc:
        log.warning("[MOSDAC] Download error for gId=%s: %s", file_gid, exc)
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return None


def _detect_format(file_path: Path) -> str:
    """Return 'netcdf3', 'hdf5', or 'unknown' by reading the file magic bytes."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        if header[:3] == b"CDF":
            return "netcdf3"
        if header[:4] == b"\x89HDF":
            return "hdf5"
    except Exception:
        pass
    return "unknown"


def _extract_point_value_nc(file_path: Path, lat: float, lon: float, variable_hint: str) -> Optional[float]:
    """Extract nearest-grid-point value from a MOSDAC NetCDF3 or HDF5/NetCDF4 file.

    MOSDAC L4 files (e.g. E06OCML4AC) are NetCDF3 classic (CDF\x01 magic).
    They must be read with scipy.io.netcdf_file, not h5py.

    Variable layout in E06OCM_L4_AC:
      chla : float32 shape (time=1, lev=1, lat=1080, lon=1440)
      lat  : float64 shape (1080,)  range -81 to 90
      lon  : float64 shape (1440,)  range 0 to 360
      fill : -9.99e+08
    """
    fmt = _detect_format(file_path)
    log.debug("[MOSDAC] File format: %s (%s)", fmt, file_path.name)

    # ── NetCDF3 path (scipy) ──────────────────────────────────────────────────
    if fmt == "netcdf3":
        try:
            import numpy as np
            from scipy.io import netcdf_file

            chl_candidates = ["chla", "chlor_a", "chl", "CHL", "chlorophyll"]
            sst_candidates = ["sst", "SST", "sea_surface_temperature"]
            candidates = chl_candidates if ("chl" in variable_hint.lower() or "ocm" in variable_hint.lower()) else sst_candidates

            with netcdf_file(str(file_path), "r", mmap=False) as f:
                vnames = list(f.variables.keys())

                # Find lat/lon
                lat_arr = lon_arr = None
                for lname in ["lat", "latitude", "LAT"]:
                    if lname in f.variables:
                        lat_arr = np.asarray(f.variables[lname][:].copy(), dtype=float)
                        break
                for lname in ["lon", "longitude", "LON"]:
                    if lname in f.variables:
                        lon_arr = np.asarray(f.variables[lname][:].copy(), dtype=float)
                        break

                if lat_arr is None or lon_arr is None:
                    log.warning("[MOSDAC] No lat/lon in NetCDF3 file %s. vars=%s", file_path.name, vnames)
                    return None

                # Find data variable
                data_var = None
                for c in candidates:
                    if c in f.variables:
                        data_var = f.variables[c]
                        data_arr = data_var[:].copy()
                        break

                if data_arr is None:
                    log.warning("[MOSDAC] No matching variable in %s (tried %s). Available: %s",
                                file_path.name, candidates, vnames)
                    return None

                # Get fill value and scale/offset
                fill   = getattr(data_var, "_FillValue", None)
                scale  = float(getattr(data_var, "scale_factor", 1.0))
                offset = float(getattr(data_var, "add_offset",   0.0))

                # Normalize longitude: MOSDAC uses 0-360, convert query lon if needed
                query_lon = lon % 360.0

                i = int(np.argmin(np.abs(lat_arr - lat)))
                j = int(np.argmin(np.abs(lon_arr - query_lon)))

                # data shape: (time, lev, lat, lon) or (lat, lon)
                if data_arr.ndim == 4:
                    raw = float(data_arr[0, 0, i, j])
                elif data_arr.ndim == 3:
                    raw = float(data_arr[0, i, j])
                else:
                    raw = float(data_arr[i, j])

                if fill is not None and abs(raw - float(fill)) < 1e4:
                    log.debug("[MOSDAC] Fill value at lat=%s lon=%s", lat, lon)
                    return None

                val = raw * scale + offset
                if not np.isfinite(val) or val < 0 or val > 200:
                    return None

                return round(val, 4)

        except ImportError:
            log.warning("[MOSDAC] scipy not installed. Run: pip install scipy")
            return None
        except Exception as exc:
            log.warning("[MOSDAC] NetCDF3 extraction error for %s: %s", file_path.name, exc)
            return None

    # ── HDF5 / NetCDF4 path (h5py) ───────────────────────────────────────────
    if fmt == "hdf5":
        try:
            import h5py
            import numpy as np

            chl_candidates = ["chlor_a", "chla", "chl", "CHL", "chlorophyll", "CHL_OCI"]
            sst_candidates = ["SST", "sst", "sea_surface_temperature", "LSTC", "COR_SST"]
            lat_candidates = ["latitude", "Latitude", "lat", "LAT", "Lat"]
            lon_candidates = ["longitude", "Longitude", "lon", "LON", "Lon"]

            candidates = chl_candidates if ("chl" in variable_hint.lower() or "ocm" in variable_hint.lower()) else sst_candidates

            with h5py.File(file_path, "r") as f:
                all_keys: list[str] = []
                f.visit(lambda k: all_keys.append(k))

                lat_arr = lon_arr = None
                for k in all_keys:
                    name = k.split("/")[-1]
                    if name in lat_candidates and lat_arr is None:
                        try: lat_arr = np.asarray(f[k][:], dtype=float)
                        except Exception: pass
                    if name in lon_candidates and lon_arr is None:
                        try: lon_arr = np.asarray(f[k][:], dtype=float)
                        except Exception: pass

                data_arr = data_key_found = None
                for candidate in candidates:
                    for k in all_keys:
                        if k.split("/")[-1].lower() == candidate.lower():
                            try:
                                arr = f[k][:]
                                if arr.size > 1:
                                    data_arr = arr
                                    data_key_found = k
                                    break
                            except Exception: pass
                    if data_arr is not None:
                        break

                if data_arr is None:
                    log.warning("[MOSDAC] No variable in HDF5 %s. Available: %s",
                                file_path.name, [k.split('/')[-1] for k in all_keys])
                    return None

                ds = f[data_key_found]
                scale  = float(ds.attrs.get("scale_factor", 1.0))
                offset = float(ds.attrs.get("add_offset",   0.0))
                fill   = ds.attrs.get("_FillValue", None)

                if lat_arr is not None and lon_arr is not None:
                    if lat_arr.ndim == 1 and lon_arr.ndim == 1:
                        i = int(np.argmin(np.abs(lat_arr - lat)))
                        j = int(np.argmin(np.abs(lon_arr - (lon % 360.0))))
                        raw = float(data_arr[i, j] if data_arr.ndim == 2 else data_arr[0, i, j])
                    else:
                        dist = (lat_arr - lat)**2 + (lon_arr - lon)**2
                        idx  = np.unravel_index(np.argmin(dist), dist.shape)
                        raw  = float(data_arr[idx] if data_arr.ndim == 2 else data_arr[0][idx])
                else:
                    raw = float(np.nanmean(data_arr))

                if fill is not None and raw == float(fill):
                    return None

                val = raw * scale + offset
                if not np.isfinite(val) or val < -900 or val > 900:
                    return None
                return round(val, 4)

        except ImportError:
            log.warning("[MOSDAC] h5py not installed. Run: pip install h5py")
            return None
        except Exception as exc:
            log.warning("[MOSDAC] HDF5 extraction error for %s: %s", file_path.name, exc)
            return None

    log.warning("[MOSDAC] Unknown file format for %s", file_path.name)
    return None


# Alias for backwards compatibility
_extract_point_value_h5 = _extract_point_value_nc



def fetch_mosdac_point(
    dataset_id: str,
    lat: float,
    lon: float,
    date: Optional[datetime] = None,
) -> Optional[float]:
    """Fetch a single scalar value (CHL or SST) from MOSDAC at the given point.

    1. Check in-memory cache.
    2. Check local NetCDF cache directory.
    3. Search MOSDAC catalog -> download -> extract -> cache.
    Returns the value (float) or None on any failure.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    date_str = date.strftime("%Y-%m-%d")
    cache_key = (dataset_id, date_str)

    now_mono = time.monotonic()
    with _lock:
        hit = _value_cache.get(cache_key)
        if hit and hit[0] > now_mono:
            return hit[1]

    username, _ = _get_credentials()
    if not username:
        log.debug("[MOSDAC] No credentials configured — skipping")
        return None

    cache_dir = _get_cache_dir()

    with httpx.Client(timeout=30.0) as client:
        # Step 1: search for today's file (global coverage, no bbox needed)
        entries = _search_files(dataset_id, date, client)

        # Fallback: try yesterday if today's composite isn't available yet
        if not entries:
            yesterday = date - timedelta(days=1)
            entries = _search_files(dataset_id, yesterday, client)
            if entries:
                log.debug("[MOSDAC] Using yesterday's %s file", dataset_id)

        if not entries:
            log.warning("[MOSDAC] No files found for %s on %s", dataset_id, date_str)
            _cache_value(cache_key, None, now_mono)
            return None

        file_entry = entries[0]
        file_gid   = str(file_entry.get("id", "")).strip()
        identifier = str(file_entry.get("identifier", file_gid)).strip()
        if identifier and not identifier.isdigit():
            dest_path = cache_dir / identifier
        else:
            dest_path = cache_dir / f"mosdac_{file_gid}.nc"

        if not dest_path.exists():
            # Need to download — authenticate first
            access_token = _authenticate(client)
            if not access_token:
                log.warning("[MOSDAC] Authentication failed — cannot download")
                _cache_value(cache_key, None, now_mono)
                return None

            dest_path = _download_file(file_entry, access_token, cache_dir, client)
            _logout(client, username)

            if not dest_path:
                _cache_value(cache_key, None, now_mono)
                return None

        # Step 3: extract point value
        value = _extract_point_value_nc(dest_path, lat, lon, dataset_id)
        _cache_value(cache_key, value, now_mono)
        return value


def _cache_value(key: Tuple[str, str], value: Optional[float], now_mono: float) -> None:
    ttl = CACHE_TTL if value is not None else 3600.0  # shorter retry if failed
    with _lock:
        _value_cache[key] = (now_mono + ttl, value)


def fetch_mosdac_chlorophyll(lat: float, lon: float, date: Optional[datetime] = None) -> Optional[float]:
    """Fetch Chlorophyll-a concentration (mg/m3) from OceanSat-3 L4 composite."""
    return fetch_mosdac_point(DATASET_CHL, lat, lon, date)


def fetch_mosdac_sst(lat: float, lon: float, date: Optional[datetime] = None) -> Optional[float]:
    """SST is sourced from Open-Meteo (preferred). This is a no-op kept for API compatibility.
    INSAT-3DR/3D SST datasets returned HTTP 500 'Data unavailable' in live testing.
    Open-Meteo Marine already provides SST natively for free.
    """
    log.debug("[MOSDAC] SST fetch skipped — using Open-Meteo SST instead")
    return None


def clear_mosdac_cache() -> None:
    """Clear in-memory cache (does not delete downloaded HDF5 files)."""
    with _lock:
        _value_cache.clear()
