"""Explanation agent — the only component allowed to speak in sentences.

It answers the five questions every ORCA recommendation must answer:
WHAT (the verdict), WHY (ranked factors), WHERE, WHEN, and from WHICH SOURCE
with what confidence. It renders from structured agent output only; it cannot
invent a number, because it never sees free text — only typed measurements.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..config import SOURCE_LABELS
from ..schemas import (AgentResult, EvidenceRow, Language, Location, PFZZone,
                       RiskAssessment, RouteOption)
from ..services.i18n import SUGGESTIONS, humanise_duration, t, verdict_key
from .base import timed

# LLM rephrase path ? imported lazily so the module loads without groq.
import logging as _logging
import time as _time
_log = _logging.getLogger(__name__)

# Localised names for the risk factors (rendering concern, kept next to the renderer)
FACTOR_LABELS: Dict[str, Dict[str, str]] = {
    "wave":    {"en": "Wave height",        "hi": "लहरों की ऊँचाई", "mr": "लाटांची उंची"},
    "wind":    {"en": "Wind speed",         "hi": "हवा की गति",     "mr": "वाऱ्याचा वेग"},
    "cyclone": {"en": "Official warning",   "hi": "आधिकारिक चेतावनी", "mr": "अधिकृत इशारा"},
    "weather": {"en": "Rain / visibility",  "hi": "बारिश / दृश्यता", "mr": "पाऊस / दृश्यमानता"},
    "ocean":   {"en": "Sea state",          "hi": "समुद्र की स्थिति", "mr": "समुद्राची स्थिती"},
    "gis":     {"en": "Position & zones",   "hi": "स्थिति व क्षेत्र",  "mr": "स्थान व क्षेत्रे"},
}


def _factor_label(key: str, lang: Language) -> str:
    return FACTOR_LABELS.get(key, {}).get(lang) or FACTOR_LABELS.get(key, {}).get("en", key)


WARNING_STATE = {"active": {"en": "active", "hi": "सक्रिय", "mr": "सक्रिय"},
                 "none": {"en": "none", "hi": "कोई नहीं", "mr": "नाही"}}
SEA_STATE_L10N = {
    "calm":       {"en": "calm", "hi": "शांत", "mr": "शांत"},
    "slight":     {"en": "slight", "hi": "हल्का", "mr": "किंचित"},
    "moderate":   {"en": "moderate", "hi": "मध्यम", "mr": "मध्यम"},
    "rough":      {"en": "rough", "hi": "उग्र", "mr": "खवळलेला"},
    "very rough": {"en": "very rough", "hi": "अति उग्र", "mr": "अतिशय खवळलेला"},
    "phenomenal": {"en": "phenomenal", "hi": "अत्यंत भीषण", "mr": "अत्यंत धोकादायक"},
}


def _short_value(key: str, weather: Dict, ocean: Dict, cyclone: Dict, gis: Dict,
                 lang: Language = "en") -> str:
    """Compact value for the reason line — units stay numeric in every language."""
    if key == "wave" and ocean.get("wave_height_m") is not None:
        return f"{ocean['wave_height_m']:.1f} m"
    if key == "wind" and weather.get("wind_speed_kmh") is not None:
        return f"{weather['wind_speed_kmh']:.0f} km/h"
    if key == "cyclone":
        state = "active" if cyclone.get("official_warning_active") else "none"
        return WARNING_STATE[state].get(lang, state)
    if key == "weather" and weather.get("rain_probability_pct") is not None:
        return f"{weather['rain_probability_pct']:.0f}%"
    if key == "ocean":
        label = str(ocean.get("sea_state", "-"))
        return SEA_STATE_L10N.get(label, {}).get(lang, label)
    if key == "gis":
        if gis.get("inside_restricted_zone"):
            return {"en": "restricted area", "hi": "प्रतिबंधित क्षेत्र",
                    "mr": "प्रतिबंधित क्षेत्र"}.get(lang, "restricted area")
        if gis.get("distance_from_shore_km") is not None:
            offshore = {"en": "km offshore", "hi": "किमी दूर", "mr": "किमी दूर"}.get(lang, "km offshore")
            return f"{gis['distance_from_shore_km']:.0f} {offshore}"
    return "-"


def build_evidence(weather: Dict, ocean: Dict, cyclone: Dict, gis: Dict,
                   agents: Dict[str, AgentResult]) -> List[EvidenceRow]:
    """The 'tap to see the source' table behind every recommendation."""
    rows: List[EvidenceRow] = []

    def add(label: str, value: str, agent_key: str):
        a = agents.get(agent_key)
        if not a:
            return
        rows.append(EvidenceRow(label=label, value=value,
                             source=SOURCE_LABELS.get(a.source, a.source),
                             timestamp=a.timestamp, confidence=a.confidence,
                             mode=a.mode))

    if ocean.get("wave_height_m") is not None:
        add("Wave height", f"{ocean['wave_height_m']:.1f} m", "ocean")
    if ocean.get("wave_period_s") is not None:
        add("Wave period", f"{ocean['wave_period_s']:.1f} s", "ocean")
    if ocean.get("sea_state"):
        add("Sea state", str(ocean["sea_state"]), "ocean")
    if ocean.get("sst_c") is not None:
        add("Sea surface temperature", f"{ocean['sst_c']:.1f} deg C", "ocean")
    if weather.get("wind_speed_kmh") is not None:
        add("Wind", f"{weather['wind_speed_kmh']:.0f} km/h {weather.get('wind_direction', '')}".strip(), "weather")
    if weather.get("rain_probability_pct") is not None:
        add("Rain probability", f"{weather['rain_probability_pct']:.0f}%", "weather")
    if weather.get("visibility_km") is not None:
        add("Visibility", f"{weather['visibility_km']:.1f} km", "weather")
    if cyclone.get("headline"):
        add("Marine warning", str(cyclone["headline"]), "cyclone")
    if gis.get("distance_from_shore_km") is not None:
        add("Distance from shore", f"{gis['distance_from_shore_km']:.1f} km", "gis")
    if gis.get("nearest_zone_name"):
        add("Nearest restricted zone",
            f"{gis['nearest_zone_name']} ({gis.get('nearest_zone_km')} km)", "gis")
    return rows


@timed
def run(*, intent, risk: Optional[RiskAssessment], pfz: List[PFZZone],
        routes: List[RouteOption], geofence: List, weather: Dict, ocean: Dict,
        cyclone: Dict, gis: Dict, agents: Dict[str, AgentResult],
        mode: str, when: datetime, fetched_at: Optional[datetime] = None) -> AgentResult:
    lang: Language = intent.language
    parts: List[str] = []

    # ---- WHAT ------------------------------------------------------------
    if risk is not None:
        verdict = t(verdict_key(risk.category), lang)
        parts.append(f"{verdict}. {t('risk_score', lang)}: {risk.score}/100.")

        # ---- WHY ---------------------------------------------------------
        top = [f for f in risk.factors if f.contribution > 0][:3]
        if top:
            reasons = "; ".join(
                f"{_factor_label(f.key, lang)} {_short_value(f.key, weather, ocean, cyclone, gis, lang)}"
                for f in top
            )
            parts.append(f"{t('why', lang)}: {reasons}.")

        if risk.official_warning:
            parts.append(t("official_warning", lang))

        # ---- WHEN --------------------------------------------------------
        if risk.category in ("HIGH", "EXTREME"):
            if risk.window:
                parts.append(t("improves_at", lang, hour=risk.window.split(":")[0]))
            else:
                parts.append(t("no_improvement", lang))

    # ---- fishing zones ---------------------------------------------------
    if pfz and intent.intent in ("find_pfz", "route"):
        top = pfz[0]
        parts.append(
            f"{t('pfz_intro', lang)}: #{top.rank} — {top.distance_km} km {top.bearing}, "
            f"SST {top.sst_c} deg C, chlorophyll {top.chlorophyll_mg_m3} mg/m3, "
            f"confidence {int(top.confidence * 100)}%."
        )
        parts.append(t("pfz_note", lang))

    # ---- route -----------------------------------------------------------
    if routes:
        rec = next((r for r in routes if r.recommended), routes[0])
        parts.append(
            f"{t('route_intro', lang)}: "
            + t("route_detail", lang, distance=rec.distance_km,
                eta=humanise_duration(rec.eta_minutes, lang))
        )

    # ---- geofence --------------------------------------------------------
    for alert in geofence[:2]:
        key = "geofence_inside" if alert.inside else "geofence_warn"
        parts.append(t(key, lang, zone=alert.zone_name, distance=alert.distance_km))

    # ---- provenance ------------------------------------------------------
    # Only real data providers belong in the citation line — "ORCA" is us.
    srcs = sorted({SOURCE_LABELS.get(a.source, a.source)
                   for a in agents.values() if a.ok and a.source not in ("ORCA",)})
    # Use the actual fetch time (now) for the "Updated" stamp, not the forecast
    # target time — otherwise a question about "tomorrow" shows tomorrow's date
    # which confuses users into thinking the data source is wrong.
    display_time = fetched_at if fetched_at is not None else when
    provenance_line = f"{t('sources', lang)}: {', '.join(srcs)} · {t('updated', lang)} {display_time.strftime('%d %b %Y, %H:%M IST')}"
    # If the forecast target is a different day, clarify what day was analysed
    if fetched_at is not None and when.date() != fetched_at.date():
        provenance_line += f" · Forecast for {when.strftime('%d %b, %H:%M IST')}"
    parts.append(provenance_line)
    if mode == "DEMO":
        parts.append(t("demo_mode", lang))

    # ?? Template answer (always built; never removed) ????????????????????
    template_answer = " ".join(parts)
    final_answer = template_answer
    explanation_source = "template"

    # ?? LLM rephrase path (optional, falls back silently) ?????????????????
    from ..config import LLM_ENABLED  # local import avoids circular dep
    if LLM_ENABLED:
        from ..services.llm import LLMUnavailable, rephrase_explanation
        # Build the facts dict from already-computed values only.
        # Never include raw user input here.
        facts: Dict[str, object] = {}
        # Always include what the user actually asked — the LLM uses this
        # to address their specific question rather than reciting every fact.
        facts["user_query"] = intent.raw_query
        facts["intent_type"] = intent.intent
        facts["location"] = intent.location_text or "unknown"
        if risk is not None:
            facts["risk_score"] = risk.score
            facts["risk_category"] = risk.category
            facts["go"] = risk.go
            facts["official_warning"] = risk.official_warning
            facts["overrides"] = risk.overrides
            if risk.window:
                facts["improves_after"] = risk.window
        facts["wave_height_m"] = ocean.get("wave_height_m")
        facts["wind_speed_kmh"] = weather.get("wind_speed_kmh")
        facts["rain_probability_pct"] = weather.get("rain_probability_pct")
        facts["visibility_km"] = weather.get("visibility_km")
        facts["sea_state"] = ocean.get("sea_state")
        facts["distance_from_shore_km"] = gis.get("distance_from_shore_km")
        facts["inside_restricted_zone"] = gis.get("inside_restricted_zone", False)
        if cyclone.get("headline"):
            facts["marine_warning_headline"] = cyclone["headline"]
        if pfz:
            top = pfz[0]
            facts["top_pfz_rank"] = top.rank
            facts["top_pfz_distance_km"] = top.distance_km
            facts["top_pfz_bearing"] = top.bearing
            facts["top_pfz_sst_c"] = top.sst_c
            facts["top_pfz_chlorophyll"] = top.chlorophyll_mg_m3
        if routes:
            rec = next((r for r in routes if r.recommended), routes[0])
            facts["recommended_route_km"] = rec.distance_km
            facts["recommended_route_eta_min"] = rec.eta_minutes
        # Sources line — LLM must append it verbatim.
        srcs_line = f"{t('sources', lang)}: {chr(44).join(sorted({SOURCE_LABELS.get(a.source, a.source) for a in agents.values() if a.ok and a.source not in ('ORCA',)}))}" \
                    f" · {t('updated', lang)} {display_time.strftime('%d %b %Y, %H:%M IST')}"
        if fetched_at is not None and when.date() != fetched_at.date():
            srcs_line += f" · Forecast for {when.strftime('%d %b, %H:%M IST')}"
        facts["sources_line"] = srcs_line
        facts["language"] = lang
        facts["mode"] = mode

        _llm_start = _time.perf_counter()
        try:
            final_answer = rephrase_explanation(facts, lang)
            explanation_source = "llm"
            _log.debug(
                "LLM rephrase OK lang=%s latency=%.0fms",
                lang, (_time.perf_counter() - _llm_start) * 1000,
            )
        except LLMUnavailable as exc:
            _log.debug("LLM rephrase unavailable, using template: %s", exc)
            final_answer = template_answer
            explanation_source = "template"
        except Exception as exc:  # noqa: BLE001
            _log.debug("LLM rephrase unexpected error, using template: %s", exc)
            final_answer = template_answer
            explanation_source = "template"

    return AgentResult(
        agent="explanation",
        ok=True,
        data={
            "answer": final_answer,
            "evidence": [e.model_dump() for e in build_evidence(weather, ocean, cyclone, gis, agents)],
            "suggestions": SUGGESTIONS.get(lang, SUGGESTIONS["en"]),
            "disclaimer": t("disclaimer", lang),
            "explanation_source": explanation_source,
        },
        source="ORCA",
        timestamp=when.isoformat(timespec="seconds"),
        confidence=0.9,
        mode=mode,  # type: ignore[arg-type]
    )
