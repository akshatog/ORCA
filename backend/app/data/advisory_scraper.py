"""Scraper and bulletin parser for IMD Weather Advisories and INCOIS PFZ bulletins.

IMD Scraper:
- PRIMARY: Parses the public IMD CAP RSS feed (machine-readable XML, no key required).
  URL: https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml
  Each item links to a full CAP XML with: severity, onset, expires, area polygon.
  Filtered to marine/coastal/fishermen/cyclone categories.
- FALLBACK: Scrapes mausam.imd.gov.in/responsive/coastal_bulletin.php HTML/PDF.
- SHA-256 fingerprinting prevents re-processing unchanged bulletins.
- 1 hour refresh interval.

INCOIS PFZ Scraper:
- Fetches the 8 regional TextData endpoints (SEC001–SEC008) which return parseable
  HTML tables with: Landing Centre, Bearing, Distance, Depth, DMS coordinates.
  SEC001=Gujarat/Diu, SEC002=Maharashtra, SEC003=Goa, SEC004=Karnataka,
  SEC005=Kerala, SEC006=Tamil Nadu, SEC007=Andhra Pradesh, SEC008=Odisha/WB
- Implements DMS → decimal coordinate conversion.
- 6 hour refresh interval (INCOIS updates 1–2x/day).
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from ..schemas import AdvisoryConstraint, make_evidence
from ..services.advisory_compiler import compile_advisory

log = logging.getLogger(__name__)

# IMD — primary CAP RSS (public, no key required)
IMD_CAP_RSS_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"
# IMD — HTML/PDF fallback
IMD_COASTAL_URL = "https://mausam.imd.gov.in/responsive/coastal_bulletin.php"

# INCOIS — 8 confirmed regional TextData endpoints
INCOIS_SECTOR_URLS: Dict[str, str] = {
    "SEC001": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC001",  # Gujarat/Diu
    "SEC002": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC002",  # Maharashtra
    "SEC003": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC003",  # Goa
    "SEC004": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC004",  # Karnataka
    "SEC005": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC005",  # Kerala
    "SEC006": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC006",  # Tamil Nadu
    "SEC007": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC007",  # Andhra Pradesh
    "SEC008": "https://incois.gov.in/MarineFisheries/TextData?secid=SEC008",  # Odisha/WB
}

# Marine/coastal keywords to filter CAP alerts for maritime relevance
_MARINE_KEYWORDS = {
    "fishermen", "coastal", "cyclone", "marine", "sea", "wave", "storm",
    "tidal", "tsunami", "arabian", "bengal", "lakshadweep", "andaman",
    "high seas", "port", "warning",
}

# CAP severity → ORCA severity mapping
_CAP_SEVERITY_MAP = {
    "extreme": "severe",
    "severe": "severe",
    "moderate": "high",
    "minor": "moderate",
    "unknown": "low",
}

# 1 hour refresh for IMD; 6 hours for INCOIS PFZ
IMD_TTL = 3600.0
PFZ_TTL = 21600.0

_seen_imd_hashes: Dict[str, List[AdvisoryConstraint]] = {}
_last_imd_fetch: Tuple[float, List[AdvisoryConstraint]] = (0.0, [])
_last_pfz_fetch: Tuple[float, List[Dict[str, Any]]] = (0.0, [])
_lock = threading.Lock()


# ─────────────────────────── Coordinate helpers ───────────────────────────────

def dms_to_decimal(dms_str: str) -> Optional[float]:
    """Convert a DMS coordinate string to decimal degrees.

    Handles formats like:
        "18°51'N"  →  18.85
        "72° 30' E"  →  72.5
        "18.5N"  →  18.5  (already decimal, just strip direction)
    Returns None if unparseable.
    """
    if not dms_str:
        return None
    dms_str = dms_str.strip()

    # Direction
    direction = 1.0
    if dms_str[-1].upper() in ("S", "W"):
        direction = -1.0
    dms_str = dms_str.rstrip("NSEWnsew").strip()

    # Try pure decimal first  "18.5"
    try:
        return float(dms_str) * direction
    except ValueError:
        pass

    # DMS with °, ', optional "
    m = re.match(
        r"(\d+)\s*°\s*(\d+)?\s*'?\s*(\d+(?:\.\d+)?)?\s*\"?",
        dms_str,
    )
    if not m:
        return None
    deg = float(m.group(1))
    mins = float(m.group(2) or 0)
    secs = float(m.group(3) or 0)
    return direction * (deg + mins / 60.0 + secs / 3600.0)


# ──────────────────────────── HTML text helpers ───────────────────────────────

def extract_text_from_html(html_str: str) -> str:
    """Extract readable text from HTML string using BeautifulSoup."""
    if not html_str or not html_str.strip():
        return ""
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.extract()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as exc:
        log.warning("HTML text extraction error: %s", exc)
        return ""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber."""
    if not pdf_bytes:
        return ""
    parts: List[str] = []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
    except Exception as exc:
        log.warning("PDF extraction failed: %s", exc)
    return "\n\n".join(parts)


# ────────────────────────────── IMD CAP RSS ───────────────────────────────────

def _is_marine_cap(title: str, description: str, category: str) -> bool:
    """Return True if this CAP item is relevant to marine/coastal operations."""
    text = f"{title} {description} {category}".lower()
    return any(kw in text for kw in _MARINE_KEYWORDS)


def _fetch_cap_item_xml(item_link: str, client: httpx.Client) -> Optional[Dict[str, Any]]:
    """Fetch and parse a single CAP XML document linked from the RSS."""
    try:
        r = client.get(item_link, timeout=6.0, follow_redirects=True)
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)
        ns = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

        def find(tag: str) -> str:
            el = root.find(f"cap:info/cap:{tag}", ns) or root.find(f"cap:{tag}", ns)
            return (el.text or "").strip() if el is not None else ""

        severity_raw = find("severity").lower()
        category = find("category")
        event = find("event")
        headline = find("headline")
        onset = find("onset")
        expires = find("expires")
        area_desc = find("areaDesc")

        # Polygon: "lat,lon lat,lon ..."
        poly_el = root.find("cap:info/cap:area/cap:polygon", ns)
        polygon_text = (poly_el.text or "").strip() if poly_el is not None else ""

        severity = _CAP_SEVERITY_MAP.get(severity_raw, "moderate")
        official = severity in ("severe",)

        return {
            "severity": severity,
            "official": official,
            "headline": headline or event,
            "area_desc": area_desc,
            "onset": onset,
            "expires": expires,
            "polygon_text": polygon_text,
            "category": category,
            "source": "IMD_CAP",
        }
    except Exception as exc:
        log.debug("CAP item fetch failed (%s): %s", item_link, exc)
        return None


def scrape_imd_cap_rss(force: bool = False) -> List[Dict[str, Any]]:
    """Fetch the IMD CAP RSS feed and return marine-relevant alerts.

    Returns a list of alert dicts compatible with cyclone_agent expectations:
        {severity, official, headline, area_desc, onset, expires, source}
    Cached for IMD_TTL (1 hour).
    """
    global _last_imd_fetch
    now = time.monotonic()
    with _lock:
        if not force and _last_imd_fetch[0] > now:
            return _last_imd_fetch[1]  # type: ignore[return-value]

    alerts: List[Dict[str, Any]] = []
    try:
        with httpx.Client(timeout=8.0) as client:
            rss_resp = client.get(IMD_CAP_RSS_URL, follow_redirects=True)
            if rss_resp.status_code != 200:
                log.warning("IMD CAP RSS returned %s", rss_resp.status_code)
                return _last_imd_fetch[1]  # type: ignore[return-value]

            root = ET.fromstring(rss_resp.text)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall("item")

            for item in items:
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                category = (item.findtext("category") or "").strip()

                if not _is_marine_cap(title, desc, category):
                    continue

                if link:
                    detail = _fetch_cap_item_xml(link, client)
                    if detail:
                        alerts.append(detail)
                    else:
                        # Minimal alert from RSS title alone
                        alerts.append({
                            "severity": "moderate",
                            "official": True,
                            "headline": title,
                            "area_desc": desc[:200],
                            "onset": None,
                            "expires": None,
                            "source": "IMD_CAP_RSS",
                        })
    except Exception as exc:
        log.warning("IMD CAP RSS fetch failed: %s", exc)

    with _lock:
        _last_imd_fetch = (now + IMD_TTL, alerts)  # type: ignore[assignment]
    log.info("[IMD CAP] Fetched %d marine/coastal alerts from RSS feed", len(alerts))
    return alerts


# ─────────────────────── IMD HTML/PDF bulletin fallback ───────────────────────

def scrape_imd_bulletin(
    html_content: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    url: Optional[str] = None,
    force: bool = False,
) -> List[AdvisoryConstraint]:
    """Scrape and compile IMD marine bulletin (HTML/PDF fallback path).

    Uses SHA-256 fingerprinting so only changed bulletins trigger re-compilation.
    The primary live path is scrape_imd_cap_rss(); this is the fallback.
    """
    global _last_imd_fetch
    now = time.monotonic()
    if not force and not html_content and not pdf_bytes and _last_imd_fetch[0] > now:
        return _last_imd_fetch[1]  # type: ignore[return-value]

    raw_bytes: bytes = b""
    text = ""
    source_ref = url or "IMD-COASTAL-BULLETIN"

    if pdf_bytes:
        raw_bytes = pdf_bytes
        text = extract_text_from_pdf(pdf_bytes)
    elif html_content:
        raw_bytes = html_content.encode("utf-8")
        text = extract_text_from_html(html_content)
    else:
        target_url = url or IMD_COASTAL_URL
        try:
            r = httpx.get(target_url, timeout=8.0, follow_redirects=True)
            if r.status_code == 200:
                raw_bytes = r.content
                if "application/pdf" in r.headers.get("content-type", "") or target_url.endswith(".pdf"):
                    text = extract_text_from_pdf(raw_bytes)
                else:
                    text = extract_text_from_html(r.text)
        except Exception as exc:
            log.warning("IMD scrape request to %s failed: %s", target_url, exc)
            return _last_imd_fetch[1]  # type: ignore[return-value]

    if not text.strip():
        return []

    content_hash = hashlib.sha256(raw_bytes or text.encode("utf-8")).hexdigest()
    with _lock:
        if content_hash in _seen_imd_hashes and not force:
            log.info("IMD bulletin hash unchanged (%s…), reusing cache.", content_hash[:8])
            return _seen_imd_hashes[content_hash]

    advisories = compile_advisory(text, source_reference=source_ref)

    with _lock:
        _seen_imd_hashes[content_hash] = advisories
        _last_imd_fetch = (now + IMD_TTL, advisories)  # type: ignore[assignment]

    if advisories:
        try:
            from ..services.alert_engine import on_evidence_change
            on_evidence_change(new_advisories=advisories)
        except Exception as exc:
            log.warning("Failed triggering alert engine from IMD scraper: %s", exc)

    return advisories


# ─────────────────────────────── INCOIS PFZ ───────────────────────────────────

# Sector → approximate central lat/lon for sectors where table parse fails
_SECTOR_FALLBACK_COORDS: Dict[str, Tuple[float, float]] = {
    "SEC001": (21.5, 69.5),   # Gujarat
    "SEC002": (18.9, 72.8),   # Maharashtra
    "SEC003": (15.5, 73.8),   # Goa
    "SEC004": (14.0, 74.3),   # Karnataka
    "SEC005": (10.5, 76.2),   # Kerala
    "SEC006": (10.0, 79.8),   # Tamil Nadu
    "SEC007": (15.5, 80.5),   # Andhra Pradesh
    "SEC008": (20.5, 87.5),   # Odisha/WB
}


def _parse_incois_sector_table(html: str, sector_id: str) -> List[Dict[str, Any]]:
    """Parse an INCOIS TextData HTML table for a single sector.

    The table columns (confirmed from live inspection) are:
        Landing Centre | Bearing | Distance | Depth | Latitude | Longitude
    Returns a list of zone dicts.
    """
    zones: List[Dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        if not tables:
            return zones

        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header row
                cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if len(cols) < 4:
                    continue

                # Try to extract lat/lon — columns 4 and 5 (0-indexed)
                lat_str = cols[4] if len(cols) > 4 else ""
                lon_str = cols[5] if len(cols) > 5 else ""

                lat = dms_to_decimal(lat_str)
                lon = dms_to_decimal(lon_str)

                if lat is None or lon is None:
                    continue

                # Validate geographic bounds (Indian coastal waters)
                if not (5.0 <= lat <= 30.0 and 60.0 <= lon <= 100.0):
                    continue

                distance_str = cols[2] if len(cols) > 2 else "25"
                bearing_str = cols[1] if len(cols) > 1 else ""
                depth_str = cols[3] if len(cols) > 3 else ""
                landing_centre = cols[0] if cols else sector_id

                try:
                    distance_km = float(re.sub(r"[^\d.]", "", distance_str) or "25")
                except ValueError:
                    distance_km = 25.0

                try:
                    bearing_deg = float(re.sub(r"[^\d.]", "", bearing_str) or "0")
                except ValueError:
                    bearing_deg = 0.0

                try:
                    depth_m = float(re.sub(r"[^\d.]", "", depth_str) or "50")
                except ValueError:
                    depth_m = 50.0

                zones.append({
                    "zone_id": f"INCOIS-{sector_id}-{len(zones)+1:02d}",
                    "landing_centre": landing_centre,
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "bearing_deg": bearing_deg,
                    "distance_km": distance_km,
                    "depth_m": depth_m,
                    # INCOIS TextData does not provide SST/CHL directly;
                    # these will be supplemented by the ocean agent from Open-Meteo.
                    "sst_c": None,
                    "chlorophyll_mg_m3": None,
                    "confidence": 0.92,
                    "source": "INCOIS",
                    "source_type": "official_bulletin",
                    "sector": sector_id,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                })
    except Exception as exc:
        log.warning("[INCOIS] Failed parsing sector %s table: %s", sector_id, exc)

    return zones


def scrape_incois_pfz(
    html_content: Optional[str] = None,
    text_content: Optional[str] = None,
    url: Optional[str] = None,
    force: bool = False,
) -> List[Dict[str, Any]]:
    """Scrape INCOIS Potential Fishing Zone advisories from all 8 regional sectors.

    Fetches each TextData sector endpoint, parses the HTML table,
    and returns a combined list of PFZ zone dicts. Cached for PFZ_TTL (6 hours).

    If `html_content` or `text_content` are provided (e.g. for unit testing),
    they are used instead of fetching live.
    """
    global _last_pfz_fetch
    now = time.monotonic()
    with _lock:
        if not force and not html_content and not text_content and not url and _last_pfz_fetch[0] > now:
            return _last_pfz_fetch[1]

    # ── Test/override path ──────────────────────────────────────────────────
    if html_content or text_content:
        text = text_content or extract_text_from_html(html_content or "")
        # Legacy regex path for text-only input
        zones = _parse_pfz_text_fallback(text)
        with _lock:
            _last_pfz_fetch = (now + PFZ_TTL, zones)
        return zones

    # ── Single custom URL (legacy caller) ──────────────────────────────────
    if url:
        sector_id = "SEC_CUSTOM"
        try:
            r = httpx.get(url, timeout=8.0, follow_redirects=True)
            if r.status_code == 200:
                zones = _parse_incois_sector_table(r.text, sector_id)
                with _lock:
                    _last_pfz_fetch = (now + PFZ_TTL, zones)
                return zones
        except Exception as exc:
            log.warning("INCOIS custom URL fetch failed: %s", exc)
        return _last_pfz_fetch[1]

    # ── Primary: fetch all 8 sector endpoints ──────────────────────────────
    all_zones: List[Dict[str, Any]] = []
    with httpx.Client(timeout=8.0) as client:
        for sector_id, sector_url in INCOIS_SECTOR_URLS.items():
            try:
                r = client.get(sector_url, follow_redirects=True)
                if r.status_code == 200:
                    sector_zones = _parse_incois_sector_table(r.text, sector_id)
                    all_zones.extend(sector_zones)
                    log.debug("[INCOIS] %s → %d zone(s)", sector_id, len(sector_zones))
                else:
                    log.warning("[INCOIS] %s returned HTTP %s", sector_id, r.status_code)
            except Exception as exc:
                log.warning("[INCOIS] Failed fetching %s: %s", sector_id, exc)

    log.info("[INCOIS PFZ] Fetched %d total zones across all sectors", len(all_zones))
    with _lock:
        _last_pfz_fetch = (now + PFZ_TTL, all_zones)
    return all_zones


def _parse_pfz_text_fallback(text: str) -> List[Dict[str, Any]]:
    """Legacy regex-based parser for unstructured text. Used only as last resort."""
    zones: List[Dict[str, Any]] = []
    coord_matches = re.findall(
        r"(\d{1,2}(?:\.\d+)?)\s*°?\s*([NSns])[,;\s]+(\d{1,3}(?:\.\d+)?)\s*°?\s*([EWew])",
        text,
    )
    dist_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:km|kms|nmi)", text, re.IGNORECASE)
    sst_matches = re.findall(r"(\d{2}(?:\.\d+)?)\s*°?\s*C", text)
    chl_matches = re.findall(r"(\d+(?:\.\d+)?)\s*mg\s*/\s*m3?", text, re.IGNORECASE)

    for i, match in enumerate(coord_matches):
        lat = float(match[0]) * (-1 if match[1].upper() == "S" else 1)
        lon = float(match[2]) * (-1 if match[3].upper() == "W" else 1)
        dist = float(dist_matches[i]) if i < len(dist_matches) else 25.0
        sst = float(sst_matches[i]) if i < len(sst_matches) else None
        chl = float(chl_matches[i]) if i < len(chl_matches) else None

        zones.append({
            "zone_id": f"INCOIS-PFZ-{i+1:02d}",
            "latitude": lat,
            "longitude": lon,
            "distance_km": dist,
            "sst_c": sst,
            "chlorophyll_mg_m3": chl,
            "confidence": 0.88,
            "source": "INCOIS",
            "source_type": "official_bulletin",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        })
    return zones


# ─────────────────────────────── Cache reset ──────────────────────────────────

def clear_scraper_cache() -> None:
    """Reset scraper caches (for unit testing and mode toggle)."""
    global _last_imd_fetch, _last_pfz_fetch
    with _lock:
        _seen_imd_hashes.clear()
        _last_imd_fetch = (0.0, [])
        _last_pfz_fetch = (0.0, [])
