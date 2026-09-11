"""ORCA configuration â€” data mode, risk weights, thresholds.

Everything a judge might question ("why these weights?", "is this data real?")
is centralised here so it can be shown on screen and defended in Q&A.
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field
from typing import Dict, Any


# --------------------------------------------------------------------------
# Load backend/.env if present (stdlib only, no python-dotenv needed).
# Variables already set in the shell environment take priority.
# --------------------------------------------------------------------------
def _load_dotenv() -> None:
    env_path = pathlib.Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with env_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:  # shell env wins
                os.environ[key] = value


_load_dotenv()



# --------------------------------------------------------------------------
# Data mode
# --------------------------------------------------------------------------
# LIVE : call public marine/weather APIs, fall back to cache/demo on failure.
# DEMO : serve only cached, clearly-labelled scenario data. Stage-safe.
#
# Default is DEMO so a laptop with no internet still runs the full pipeline.
DATA_MODE = os.getenv("ORCA_DATA_MODE", "DEMO").upper()

# Runtime-switchable copy so the mode can be flipped from the UI mid-demo
# ("watch â€” I'll switch it to live government-adjacent data now") without a
# restart. Always read through get_data_mode(); never trust the constant above.
_RUNTIME = {"data_mode": DATA_MODE}


def get_data_mode() -> str:
    return _RUNTIME["data_mode"]


def set_data_mode(mode: str) -> str:
    mode = (mode or "").strip().upper()
    if mode not in ("LIVE", "DEMO"):
        raise ValueError("mode must be LIVE or DEMO")
    _RUNTIME["data_mode"] = mode
    return mode

# Seconds before a live API call is abandoned in favour of cache/demo data.
LIVE_TIMEOUT_SECONDS = float(os.getenv("ORCA_LIVE_TIMEOUT", "4.0"))

# Optional LLM layer. ORCA runs fully without it (rule-based intent + template
# explanations). When a key is present the LLM only *rephrases* â€” it never
# computes a risk score. See services/llm.py.
LLM_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("ORCA_LLM_MODEL", "openai/gpt-oss-120b")
LLM_ENABLED  = bool(LLM_API_KEY) and os.getenv("ORCA_USE_LLM", "1") != "0"
LLM_TIMEOUT  = float(os.getenv("ORCA_LLM_TIMEOUT", "8.0"))  # per-call wall-clock limit


# --------------------------------------------------------------------------
# YAML config loading (backend/config/*.yaml) with hardcoded fallbacks
# --------------------------------------------------------------------------
def _load_yaml_dict(filename: str) -> dict:
    candidates = [
        pathlib.Path(__file__).parent.parent / "config" / filename,
        pathlib.Path(__file__).parent.parent.parent / "config" / filename,
    ]
    for path in candidates:
        if path.exists():
            try:
                import yaml
                with path.open(encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
    return {}


@dataclass(frozen=True)
class RouteScoringConfig:
    avg_weight: float = 0.70
    spike_weight: float = 0.30
    wave_weight: float = 0.60
    wind_weight: float = 0.40
    samples_per_route: int = 5
    min_sample_spacing_km: float = 8.0


@dataclass(frozen=True)
class TripEconomicsConfig:
    fuel_rate_l_per_km: float = 1.2
    fuel_price_per_l: float = 95.0
    fixed_provisions_estimate: float = 500.0
    avg_market_price_per_kg: float = 180.0
    catch_potential_kg: Dict[str, float] = field(
        default_factory=lambda: {"HIGH": 150.0, "MEDIUM": 80.0, "LOW": 30.0, "NONE": 10.0}
    )
    boat_capacity_kg: float = 300.0


# --------------------------------------------------------------------------
# Risk engine
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RiskConfig:
    """Weighted-factor risk model.

    IMPORTANT (and we say this out loud in the pitch): these weights are an
    engineering starting point informed by small-boat safety guidance, NOT a
    peer-reviewed maritime standard. They are configurable and every factor's
    contribution is shown to the user. Deterministic overrides below cannot be
    out-voted by the weighted score.
    """

    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "wave": 0.25,     # dominant capsize driver for small craft
            "cyclone": 0.25,  # official alerts / storm proximity
            "wind": 0.20,
            "weather": 0.10,  # rain, lightning, visibility
            "ocean": 0.10,    # sea state, currents
            "gis": 0.10,      # distance offshore, restricted-zone proximity
        }
    )

    # Category thresholds (upper bound of each band, 0-100).
    thresholds: Dict[str, int] = field(
        default_factory=lambda: {"LOW": 25, "MODERATE": 50, "HIGH": 79, "EXTREME": 100}
    )

    # --- deterministic safety floors -------------------------------------
    severe_warning_floor: int = 92     # cyclone / tsunami / severe marine warning
    fishermen_warning_floor: int = 70  # "fishermen advised not to venture"
    wave_danger_m: float = 4.0
    wave_danger_floor: int = 85
    wind_danger_kmh: float = 62.0      # ~34 kt, gale force
    wind_danger_floor: int = 85
    restricted_zone_floor: int = 60
    condition_floors: Dict[str, Any] = field(
        default_factory=lambda: {
            "CAUTION_FLOOR": {"wave_height_m": 1.2, "wind_speed_kmph": 37},
            "NO_GO_FLOOR": {"wave_height_m": 3.0, "wind_speed_kmph": 63, "official_advisory": True},
            "CYCLONE_FLOOR": {"gdacs_alert_level": ["orange", "red"]},
        }
    )
    route_scoring: RouteScoringConfig = field(default_factory=RouteScoringConfig)

    def categorise(self, score: float) -> str:
        s = round(score)
        if s <= self.thresholds.get("LOW", 25):
            return "LOW"
        if s <= self.thresholds.get("MODERATE", 50):
            return "MODERATE"
        if s <= self.thresholds.get("HIGH", 79):
            return "HIGH"
        return "EXTREME"


def _init_risk_config() -> RiskConfig:
    data = _load_yaml_dict("risk_thresholds.yaml")
    defaults = {
        "wave": 0.25,
        "cyclone": 0.25,
        "wind": 0.20,
        "weather": 0.10,
        "ocean": 0.10,
        "gis": 0.10,
    }
    weights = data.get("weights") if isinstance(data.get("weights"), dict) else defaults
    thresholds = data.get("thresholds") if isinstance(data.get("thresholds"), dict) else {
        "LOW": 25, "MODERATE": 50, "HIGH": 79, "EXTREME": 100
    }
    floors = data.get("floors") if isinstance(data.get("floors"), dict) else {}
    condition_floors = data.get("condition_floors") if isinstance(data.get("condition_floors"), dict) else {
        "CAUTION_FLOOR": {"wave_height_m": 1.2, "wind_speed_kmph": 37},
        "NO_GO_FLOOR": {"wave_height_m": 3.0, "wind_speed_kmph": 63, "official_advisory": True},
        "CYCLONE_FLOOR": {"gdacs_alert_level": ["orange", "red"]},
    }
    rs_data = data.get("route_scoring") if isinstance(data.get("route_scoring"), dict) else {}
    route_scoring = RouteScoringConfig(
        avg_weight=float(rs_data.get("avg_weight", 0.70)),
        spike_weight=float(rs_data.get("spike_weight", 0.30)),
        wave_weight=float(rs_data.get("wave_weight", 0.60)),
        wind_weight=float(rs_data.get("wind_weight", 0.40)),
        samples_per_route=int(rs_data.get("samples_per_route", 5)),
        min_sample_spacing_km=float(rs_data.get("min_sample_spacing_km", 8.0)),
    )
    return RiskConfig(
        weights=weights,
        thresholds=thresholds,
        severe_warning_floor=int(floors.get("severe_warning_floor", 92)),
        fishermen_warning_floor=int(floors.get("fishermen_warning_floor", 70)),
        wave_danger_m=float(floors.get("wave_danger_m", 4.0)),
        wave_danger_floor=int(floors.get("wave_danger_floor", 85)),
        wind_danger_kmh=float(floors.get("wind_danger_kmh", 62.0)),
        wind_danger_floor=int(floors.get("wind_danger_floor", 85)),
        restricted_zone_floor=int(floors.get("restricted_zone_floor", 60)),
        condition_floors=condition_floors,
        route_scoring=route_scoring,
    )


def _init_trip_economics() -> TripEconomicsConfig:
    data = _load_yaml_dict("trip_economics.yaml")
    return TripEconomicsConfig(
        fuel_rate_l_per_km=float(data.get("fuel_rate_l_per_km", 1.2)),
        fuel_price_per_l=float(data.get("fuel_price_per_l", 95.0)),
        fixed_provisions_estimate=float(data.get("fixed_provisions_estimate", 500.0)),
        avg_market_price_per_kg=float(data.get("avg_market_price_per_kg", 180.0)),
        catch_potential_kg=data.get("catch_potential_kg", {
            "HIGH": 150.0, "MEDIUM": 80.0, "LOW": 30.0, "NONE": 10.0
        }),
        boat_capacity_kg=float(data.get("boat_capacity_kg", 300.0)),
    )


RISK = _init_risk_config()
ROUTE_SCORING = RISK.route_scoring
TRIP_ECONOMICS = _init_trip_economics()


# --------------------------------------------------------------------------
# Geofencing
# --------------------------------------------------------------------------
GEOFENCE_WARN_KM = 5.0     # warn when this close to a restricted zone
GEOFENCE_ALERT_KM = 2.5    # urgent alert threshold


# --------------------------------------------------------------------------
# Provenance labels
# --------------------------------------------------------------------------
SOURCE_LABELS = {
    "INCOIS": "INCOIS (Indian National Centre for Ocean Information Services)",
    "IMD": "IMD (India Meteorological Department)",
    "MOSDAC": "ISRO MOSDAC",
    "OPEN_METEO": "Open-Meteo Marine (open fallback source)",
    "DEMO": "ORCA demo dataset - SIMULATED, not official data",
    "ORCA_GIS": "ORCA geospatial layer (OpenStreetMap derived)",
}

# Text appended to every synthetic value so simulated data can never be
# mistaken for a live government feed.
DEMO_DISCLAIMER = "Demo / simulated data - not a live government feed"

