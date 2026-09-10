# ORCA — Stack & Models

## Backend / agentic core
Python + FastAPI + LangGraph + Pydantic.

LangGraph replaces the old `ThreadPoolExecutor` orchestrator for the new `/plan`
endpoint. The old planner (`agents/planner.py`) stays working for backward compat
with `/api/chat` and the existing frontend.

---

## LLM — multi-provider fallback chain

**Never a single point of failure.** The fallback chain:

```
Groq (llama-3.3-70b)   → primary. Fastest (< 500ms). 30 RPM / 14400 RPD free.
Cerebras (llama-3.1-70b) → fallback 1. 1M tokens/day, very fast.
Gemini Flash 2.0          → fallback 2. Best quality, but only 1500 RPD free.
Template engine            → nuclear option. Pre-built responses, always works.
```

All three providers use OpenAI-compatible APIs. Caller catches `LLMUnavailable`,
falls back to template (already built in old codebase).

**Env vars:** `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`

**Rule:** The LLM may plan, orchestrate, interpret narrative text, explain, and
translate. **Never safety decisions, GIS math, or route calculations.**

**Advisory Compiler rule:** LLM parse confidence < 0.70 → `INSUFFICIENT_EVIDENCE`.
Never let a low-confidence parse become a NO_GO.

---

## Voice — Sarvam AI (chosen over ElevenLabs)

**Why Sarvam:** ElevenLabs was eliminated — it has **no STT capability** (TTS only).
For a voice agent you need both. Sarvam provides:

| Component | Model | Coverage |
|---|---|---|
| STT (speech → text) | Saaras v3 | 22 Indian languages, real-time streaming |
| TTS (text → speech) | Bulbul V3 | 11 Indian languages, sub-250ms, 35+ voices |
| Translation | Mayura | 22 Indian languages, code-mixed support |

Free tier: ₹100 credits on signup (no expiry). INR pay-as-you-go after.

**Env var:** `SARVAM_API_KEY`

Graceful fallback: if Sarvam is down → frontend uses browser STT/TTS for English.

---

## Multilingual support

Five layers, each handled differently:

| Layer | How |
|---|---|
| UI strings (buttons, labels) | `services/i18n.py` string tables |
| Chatbot text responses | LLM with `language` field in prompt |
| Voice input (STT) | Sarvam Saaras — pass `language_code` |
| Voice output (TTS) | Sarvam Bulbul — pass `language_code` |
| Advisory translation | Sarvam Mayura translate API |

**Priority for demo:**

| Phase | Languages |
|---|---|
| Working now | EN, HI, MR |
| Sep 11 target | + TA, TE, BN, ML |
| Post-demo | + GU, KN, OR, PA |

Language detection: Unicode script range (no LLM needed).
- Tamil: U+0B80–U+0BFF
- Telugu: U+0C00–U+0C7F
- Bengali: U+0980–U+09FF
- Malayalam: U+0D00–U+0D7F

---

## Frontend
React + TypeScript + Tailwind + Leaflet. PWA (not React Native).

**Why PWA over React Native:**
- 17 existing working components — no time to rebuild
- PWA installable via "Add to Home Screen" → looks native
- Service worker + IndexedDB for offline decision cache
- `display: standalone` in manifest → no browser chrome visible
- Judge narrative: "deliberately PWA — 2MB install, no Play Store, works offshore"

Both surfaces (fisherman app + research web) in one codebase.
Mobile layout via `?m=1` (`MobileApp.tsx`).

---

## Data sources

| Source | Status | Refresh | Provides |
|---|---|---|---|
| Open-Meteo Marine + Forecast | ✅ Live, keyless | 30 min | Wave, wind, swell, SST, rain, visibility |
| StormGlass | ✅ Live, 50 req/day | 2 hr | Tide, current (only source for these) |
| GDACS | ✅ Live, keyless RSS | **15 min** | Cyclone tracks, alert levels |
| IMD fishermen bulletins | 🟡 Scraped HTML/PDF | **1 hr** | Official advisories |
| INCOIS PFZ | 🟡 Scraped PDF | **6 hr** | PFZ zone coordinates |

**Scraper interval rationale:**
- GDACS 15 min — cyclones intensify rapidly, 6hr lag = dangerous
- IMD 1 hr — emergency bulletins issued any time, 1hr is safe + respectful to their servers
- INCOIS 6 hr — satellite-derived, updates 1-2x/day, no faster cadence useful

---

## Route optimizer upgrade — path-integrated risk

The A* route optimizer (already built) is enhanced with **waypoint risk scoring**:
- Sample conditions every ~10km along each candidate route
- Score: `0.7 × avg(waypoint_risk) + 0.3 × max_spike` — penalises storm-band routes
- Re-rank routes by path score, not just zone penalties
- Attach `waypoint_conditions[]` to each `RouteOption` for map visualization (🟢🟡🔴 dots)

Weights live in `config/risk_thresholds.yaml`. The A* itself is untouched.

---

## Storage / cache
In-memory for this round. Voyage store is a Python dict. Evidence cache uses
existing TTL system in `data/live_client.py`. SQLite is a future upgrade.

## Config files
- `backend/config/risk_thresholds.yaml` — risk weights, category boundaries, safety floors, waypoint scoring weights
- `backend/config/trip_economics.yaml` — fuel rate, catch potential, market price
- `backend/.env` — API keys, data mode, timeouts
