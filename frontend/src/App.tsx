import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api";
import AgentTracePanel from "./components/AgentTrace";
import AlertsPanel from "./components/AlertsPanel";
import AuthorityPanel from "./components/AuthorityPanel";
import ChatPanel from "./components/ChatPanel";
import ConditionsStrip from "./components/ConditionsStrip";
import FishingPanel from "./components/FishingPanel";
import QuickRiskPanel from "./components/QuickRiskPanel";
import {
  ChartDefs,
  CompassMark,
  CourseArrow,
  CrosshairGlyph,
  LockGlyph,
  PlayGlyph,
  SpeakerGlyph,
  SpeakerOffGlyph,
  StopGlyph,
  WarnGlyph,
  WaveGlyph,
  WindGlyph,
} from "./components/glyphs";
import GuidedTour, { TOUR } from "./components/GuidedTour";
import Landing from "./components/Landing";
import LocationPicker, { PORTS, type PickedLocation } from "./components/LocationPicker";
import MarineMap from "./components/MarineMap";
import PFZList from "./components/PFZList";
import RiskCard from "./components/RiskCard";
import { RISK_COLOR } from "./components/RiskDial";
import SystemPanel from "./components/SystemPanel";
import RiskTimeline from "./components/RiskTimeline";
import EvidenceProvenancePanel from "./components/EvidenceProvenancePanel";
import ConflictLogPanel from "./components/ConflictLogPanel";
import DecisionPipelineVisualizer from "./components/DecisionPipelineVisualizer";
import VoyageTracker from "./components/VoyageTracker";
import AlertBanner from "./components/AlertBanner";
import type {
  AlertEvent,
  ChatMessage,
  ChatResponse,
  DecisionState,
  Evidence_v2,
  FishingOutlook,
  Language,
  Location,
  SupportedLanguage,
  TraceEntry,
  Voyage,
  ZoneFeature,
} from "./types";

const SESSION = "demo";
const RADIUS_KM = 100;
const DEFAULT_PORT = PORTS[0]; // Mumbai — used only if location is unavailable

type AppTab = "home" | "ask" | "authority" | "system" | "ops";
/** "landing" is the front door; every deep link (?tab, ?demo, ?tour, ?at) skips it. */
type Tab = AppTab | "landing";

const DEFAULT_SCENARIOS: {
  id: string;
  n: string;
  label: Record<Language, string>;
  ask: string;
  hint: string;
}[] = [
  { id: "safe", n: "1", label: { en: "Safe", hi: "सुरक्षित", mr: "सुरक्षित" }, ask: "Is it safe to go fishing tomorrow morning near Goa?", hint: "Goa · LOW" },
  { id: "danger", n: "2", label: { en: "Rough", hi: "ख़राब मौसम", mr: "खराब हवामान" }, ask: "मी उद्या सकाळी ६ वाजता मुंबईजवळ मासेमारीला जाऊ शकतो का?", hint: "Mumbai · मराठी" },
  { id: "cyclone", n: "3", label: { en: "Cyclone", hi: "चक्रवात", mr: "चक्रीवादळ" }, ask: "Is there a cyclone near Paradip? Can I go fishing?", hint: "Paradip · EXTREME" },
  { id: "pfz", n: "4", label: { en: "Fishing zones", hi: "मत्स्य क्षेत्र", mr: "मासेमारी क्षेत्रे" }, ask: "कोच्चि के पास मछली पकड़ने का क्षेत्र कहाँ है?", hint: "Kochi · हिंदी" },
  { id: "route", n: "5", label: { en: "Safe route", hi: "सुरक्षित मार्ग", mr: "सुरक्षित मार्ग" }, ask: "Give me the safest route to the nearest fishing zone near Mumbai", hint: "Mumbai · geofence" },
];

const TAB_LABEL: Record<Language, Record<AppTab, string>> = {
  en: { home: "Today", ask: "Ask ORCA", authority: "Authority", system: "System", ops: "Ops & Provenance" },
  hi: { home: "आज", ask: "ORCA से पूछें", authority: "प्रशासन", system: "प्रणाली", ops: "अभियान व साक्ष्य" },
  mr: { home: "आज", ask: "ORCA ला विचारा", authority: "प्रशासन", system: "प्रणाली", ops: "मोहीम व पुरावे" },
};

/** The app chrome, in the fisher's language. */
const UI: Record<Language, Record<string, string>> = {
  en: {
    chartNo: "Chart №",
    dataEdition: "Data edition",
    voice: "Voice",
    lang: "Language",
    tour: "Guided tour",
    stopTour: "Stop tour",
    marginalia: "Soundings in metres · WGS 84",
    scenarios: "Rehearsed scenarios",
    courses: "Plotted courses",
    recommended: "Recommended",
    warnings: "Official marine warnings",
    validTill: "valid till",
  },
  hi: {
    chartNo: "चार्ट क्र.",
    dataEdition: "डेटा संस्करण",
    voice: "आवाज़",
    lang: "भाषा",
    tour: "गाइडेड टूर",
    stopTour: "टूर रोकें",
    marginalia: "गहराई मीटर में · WGS 84",
    scenarios: "तैयार परिदृश्य",
    courses: "आँके गए मार्ग",
    recommended: "सुझाया गया",
    warnings: "आधिकारिक समुद्री चेतावनियाँ",
    validTill: "मान्य",
  },
  mr: {
    chartNo: "तक्ता क्र.",
    dataEdition: "डेटा आवृत्ती",
    voice: "आवाज",
    lang: "भाषा",
    tour: "गाइडेड टूर",
    stopTour: "टूर थांबवा",
    marginalia: "खोली मीटरमध्ये · WGS 84",
    scenarios: "तयार परिस्थिती",
    courses: "आखलेले मार्ग",
    recommended: "सुचवलेला",
    warnings: "अधिकृत सागरी इशारे",
    validTill: "पर्यंत",
  },
};

export default function App() {
  const [tab, setTab] = useState<Tab>("landing");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [latest, setLatest] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [langChoice, setLangChoice] = useState<SupportedLanguage | null>(null);
  const [detected, setDetected] = useState<SupportedLanguage>("en");
  const language: SupportedLanguage = langChoice ?? detected;
  const uiLang: Language = (language === "hi" || language === "mr") ? language : "en";

  // ---- ORCA 2.0 Operational & Provenance state ----
  const [activeAlert, setActiveAlert] = useState<AlertEvent | null>(null);
  const [activeVoyages, setActiveVoyages] = useState<Voyage[]>([]);
  const [planDecision, setPlanDecision] = useState<DecisionState | null>(null);
  const [planEvidence, setPlanEvidence] = useState<Evidence_v2[]>([]);
  const [planTrace, setPlanTrace] = useState<TraceEntry[]>([]);
  const [planConflicts, setPlanConflicts] = useState<any[]>([]);
  const [planRequestId, setPlanRequestId] = useState<string | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);

  const [zones, setZones] = useState<ZoneFeature[]>([]);
  const [portFeatures, setPortFeatures] = useState<Array<{ name: string; state: string; lat: number; lon: number }>>([]);
  const [pfzGeoJson, setPfzGeoJson] = useState<Array<{ lat: number; lon: number; label?: string; confidence?: number }>>([]);
  const [mode, setMode] = useState<string>("DEMO");
  const [switching, setSwitching] = useState(false);
  const [speak, setSpeak] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---- fisher's own position + outlook ----
  const [place, setPlace] = useState<PickedLocation | null>(null);
  const [outlook, setOutlook] = useState<FishingOutlook | null>(null);
  const [loadingOutlook, setLoadingOutlook] = useState(false);
  const [focusRank, setFocusRank] = useState<number | null>(null);

  const handleRunPlan = useCallback(async () => {
    setLoadingPlan(true);
    try {
      const p = await api.fetchPlan({
        location: place ? { lat: place.latitude, lon: place.longitude, name: place.label } : null,
        query: "Can I safely go fishing near here tomorrow morning?",
        language: language,
      });
      setPlanDecision(p);
      const reqId = p.request_id;
      if (reqId) {
        setPlanRequestId(reqId);
        const state = await api.fetchState(reqId).catch(() => null);
        if (state) {
          setPlanEvidence(state.evidence || []);
          setPlanTrace(state.trace || []);
          setPlanConflicts(state.conflict_log || []);
        } else {
          const tr = await api.fetchTrace(reqId).catch(() => []);
          setPlanTrace(tr);
        }
      }
    } catch (e) {
      console.warn("Live plan fetch error:", e);
      setError("Could not fetch safety plan — check that the backend is running.");
      setTimeout(() => setError(null), 8000);
    } finally {
      setLoadingPlan(false);
    }
  }, [place, language]);

  const handleStartVoyage = async (loc: { name?: string; lat: number; lon: number }) => {
    try {
      await api.startVoyage({
        location: loc,
        voyage_id: `voyage-${Date.now().toString().slice(-4)}`,
      });
      const refreshed = await api.getActiveVoyages().catch(() => []);
      setActiveVoyages(refreshed);
    } catch (e) {
      console.error("Start voyage failed:", e);
      setError("Could not start voyage — check connection and try again.");
      setTimeout(() => setError(null), 8000);
    }
  };

  const handleEndVoyage = async (voyageId: string) => {
    try {
      await api.endVoyage(voyageId);
      const refreshed = await api.getActiveVoyages().catch(() => []);
      setActiveVoyages(refreshed);
      if (activeAlert?.voyage_id === voyageId) {
        setActiveAlert(null);
      }
    } catch (e) {
      console.error("End voyage failed:", e);
      setError("Could not end voyage — check connection.");
      setTimeout(() => setError(null), 8000);
    }
  };

  const handleTriggerTestAlert = async (voyageId: string) => {
    try {
    const res = await api.triggerAlert({
      voyage_id: voyageId,
      severity: "SEVERE",
      headline: "Rapid Storm Intensification: Cyclonic gusts detected offshore",
      advisory: {
        authority: "IMD",
        constraint_type: "NO_GO",
        named_region: place?.label || "Coastal Sector",
        severity: "SEVERE",
        valid_from: new Date().toISOString(),
        valid_until: new Date(Date.now() + 86400000).toISOString(),
        source_text: "Squally wind speed reaching 55-65 kmph gusting to 75 kmph over sea areas.",
        source_reference: "IMD-EMERGENCY-BULLETIN",
        confidence: 0.95,
      },
    });
    if (res.alerts && res.alerts.length > 0) {
      setActiveAlert(res.alerts[0]);
    }
    } catch (e) {
      console.error("Trigger alert failed:", e);
      setError("Could not trigger alert — check connection.");
      setTimeout(() => setError(null), 8000);
    }
  };

  const handleDivertSafePort = (safePort: { name: string; lat: number; lon: number }) => {
    setPlace({
      latitude: safePort.lat,
      longitude: safePort.lon,
      label: safePort.name,
      source: "map",
    });
    setActiveAlert(null);
    setTab("home");
  };

  // ---- guided tour ----
  const [tourOn, setTourOn] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [tourPaused, setTourPaused] = useState(false);
  const tourActionDone = useRef(-1);
  const [scenarios, setScenarios] = useState(DEFAULT_SCENARIOS);

  // ---------------------------------------------------------------- boot
  useEffect(() => {
    api.zones().then((z) => setZones(z.features)).catch(() => setZones([]));
    api.health().then((h) => setMode(h.data_mode)).catch(() => setMode("DEMO"));
    // Warm up live scenarios from backend (falls back to hardcoded DEFAULT_SCENARIOS)
    api.liveScenarios()
      .then((res) => {
        if (res.scenarios && res.scenarios.length > 0) {
          setScenarios(res.scenarios);
        }
      })
      .catch(() => { /* keep hardcoded fallback */ });
    // Fetch all port markers once at boot for the map layer
    api.mapPorts()
      .then((fc) => setPortFeatures(fc.features.map((f) => ({
        name: f.properties.name,
        state: f.properties.state,
        lat: f.geometry.coordinates[1],
        lon: f.geometry.coordinates[0],
      }))))
      .catch(() => {});

    // The app must be useful the moment it opens: find the fisher, then load
    // safety, grounds and warnings without them touching anything.
    const fallback = () =>
      setPlace({
        latitude: DEFAULT_PORT.lat,
        longitude: DEFAULT_PORT.lon,
        label: DEFAULT_PORT.name,
        source: "default",
      });

    // ?at=lat,lon pins the starting position (demos, judge-tap re-creation);
    // it must win over geolocation, so GPS is skipped entirely when present.
    const params = new URLSearchParams(window.location.search);
    const at = (params.get("at") ?? "").split(",").map(Number);
    if (at.length === 2 && at.every(Number.isFinite)) {
      setPlace({ latitude: at[0], longitude: at[1], label: "Selected point", source: "map" });
      setTab("home");
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          setPlace({
            latitude: +pos.coords.latitude.toFixed(4),
            longitude: +pos.coords.longitude.toFixed(4),
            label: "Your location",
            source: "gps",
          }),
        fallback,
        { enableHighAccuracy: true, timeout: 7000, maximumAge: 300_000 },
      );
    } else {
      fallback();
    }

    const tabParam = params.get("tab");
    if (tabParam === "home" || tabParam === "ask" || tabParam === "authority" || tabParam === "system")
      setTab(tabParam);
    const langParam = params.get("lang");
    if (langParam === "en" || langParam === "hi" || langParam === "mr") setLangChoice(langParam);
    const wanted = params.get("demo");
    if (wanted) {
      const s = scenarios.find((x) => x.id === wanted || x.n === wanted);
      if (s) setTimeout(() => runScenario(s.ask), 250);
    }
    if (params.get("tour") === "1") setTimeout(() => startTour(), 500);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------- outlook on position
  useEffect(() => {
    if (!place) return;
    let alive = true;
    setLoadingOutlook(true);
    setFocusRank(null);
    api
      .fishingOutlook(place.latitude, place.longitude, {
        radiusKm: RADIUS_KM,
        days: 3,
        lang: language,
      })
      .then((d) => alive && setOutlook(d))
      .catch(() => alive && setOutlook(null))
      .finally(() => alive && setLoadingOutlook(false));
    // Fetch PFZ advisory points for the new location
    api.mapPfz(place.latitude, place.longitude, 8)
      .then((fc) => {
        if (!alive) return;
        setPfzGeoJson(fc.features.map((f) => ({
          lat: f.geometry.coordinates[1],
          lon: f.geometry.coordinates[0],
          label: String(f.properties.label ?? f.properties.zone_type ?? "PFZ Advisory"),
          confidence: typeof f.properties.confidence === "number" ? f.properties.confidence : undefined,
        })));
      })
      .catch(() => {}); // PFZ is supplemental — fail silently
    return () => {
      alive = false;
    };
  }, [place?.latitude, place?.longitude, language]);


  // ------------------------------------------------------------- chat
  const [agentEvents, setAgentEvents] = useState<api.AgentEvent[]>([]);

  const send = async (text: string) => {
    setError(null);
    setBusy(true);
    setAgentEvents([]);
    setMessages((m) => [...m, { id: `${Date.now()}-u`, role: "user", text }]);
    await api.askStream(
      {
        message: text,
        language: langChoice ?? undefined,
        sessionId: SESSION,
      },
      (e) => {
        setAgentEvents((prev) => {
          // replace last "thinking" if new thinking arrives, otherwise append
          if (e.type === "thinking") {
            return [...prev.filter((x) => x.type !== "thinking"), e];
          }
          return [...prev.filter((x) => !(x.type === "thinking" && x.agent === e.agent)), e];
        });
      },
      (res) => {
        // Keep the thinking panel visible for at least 1.5s so judges can read
        // the agent names — backend hits demo data in ~1s which is too fast.
        setTimeout(() => {
          setLatest(res);
          setDetected(res.language);
          setMode(res.mode);
          setAgentEvents([]);
          setMessages((m) => [
            ...m,
            { id: `${Date.now()}-o`, role: "orca", text: res.answer, response: res },
          ]);
          if (speak) {
            try {
              const u = new SpeechSynthesisUtterance(res.answer.split(". ").slice(0, 2).join(". "));
              u.lang = res.language === "mr" ? "mr-IN" : res.language === "hi" ? "hi-IN" : "en-IN";
              u.rate = 0.98;
              window.speechSynthesis.cancel();
              window.speechSynthesis.speak(u);
            } catch {
              /* TTS unavailable */
            }
          }
          setBusy(false);
        }, 1500);
      },
      (err) => {
        setError(err);
        setMessages((m) => [
          ...m,
          {
            id: `${Date.now()}-e`,
            role: "orca",
            text: "I could not reach the ORCA backend. Is it running on port 8000?",
          },
        ]);
        setAgentEvents([]);
        setBusy(false);
      },
    );
  };

  const runScenario = async (ask: string) => {
    setTab("ask");
    await api.resetSession(SESSION).catch(() => {});
    setMessages([]);
    setLatest(null);
    setLangChoice(null);
    await send(ask);
  };

  // ------------------------------------------------------------- tour
  useEffect(() => {
    if (!tourOn || tourPaused) return;
    const s = TOUR[tourStep];
    if (!s) return;
    let cancelled = false;
    let timer = 0;

    (async () => {
      if (tourActionDone.current !== tourStep) {
        tourActionDone.current = tourStep;
        if (s.tab) setTab(s.tab as Tab);
        if (s.ask) {
          if (s.followUp) await send(s.ask);
          else await runScenario(s.ask);
        }
      }
      if (cancelled) return;
      timer = window.setTimeout(() => {
        if (cancelled) return;
        if (tourStep + 1 < TOUR.length) setTourStep(tourStep + 1);
        else setTourOn(false);
      }, s.dwell);
    })();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tourOn, tourStep, tourPaused]);

  const startTour = async () => {
    await api.resetSession(SESSION).catch(() => {});
    setMessages([]);
    setLatest(null);
    setLangChoice(null);
    setTab("home");
    tourActionDone.current = -1;
    setTourStep(0);
    setTourPaused(false);
    setTourOn(true);
  };

  const gotoStep = (n: number) => {
    tourActionDone.current = -1;
    setTourStep(Math.max(0, Math.min(TOUR.length - 1, n)));
  };

  const toggleMode = async () => {
    const next = mode === "LIVE" ? "DEMO" : "LIVE";
    setSwitching(true);
    try {
      const r = await api.setMode(next);
      setMode(r.data_mode);
      if (place) setPlace({ ...place }); // re-fetch the outlook under the new mode
    } catch {
      /* keep current mode */
    } finally {
      setSwitching(false);
    }
  };
  const cycleMode = toggleMode;

  const pickLocation = useCallback((lat: number, lon: number) => {
    setPlace({ latitude: lat, longitude: lon, label: "Selected point", source: "map" });
  }, []);

  const suggestions = useMemo(() => latest?.suggestions ?? [], [latest]);
  const tabLabels = TAB_LABEL[uiLang] ?? TAB_LABEL.en;
  const ui = UI[uiLang] ?? UI.en;

  const homeOrigin: Location | null = place
    ? {
        name: outlook?.location.name ?? place.label,
        latitude: place.latitude,
        longitude: place.longitude,
        state: outlook?.location.state ?? null,
      }
    : null;

  if (tab === "landing") {
    return (
      <>
        <ChartDefs />
        <Landing
          mode={mode}
          language={uiLang}
          onLanguage={(l) => setLangChoice(l)}
          onEnter={setTab}
          onTour={startTour}
          onScenario={runScenario}
        />
      </>
    );
  }

  return (
    <div className="mx-auto flex min-h-full max-w-[1580px] flex-col gap-4 p-4 lg:p-6">
      <ChartDefs />
      <div className="sea-drift" aria-hidden />
      <div className="fish-drift" aria-hidden />

      {/* ---------------- title block, drafted like a chart's cartouche ---------------- */}
      <header className="panel rule-double">
        <div className="flex flex-wrap items-stretch">
          {/* identity — clicking it returns to the front page */}
          <button
            onClick={() => setTab("landing")}
            title="Back to the front page"
            className="flex items-center gap-4 py-3.5 pl-5 pr-6 text-left"
          >
            <CompassMark size={46} className="shrink-0 text-ink-900" />
            <div>
              <h1 className="font-display text-[30px] font-black leading-none tracking-tight text-ink-900">
                ORCA
              </h1>
              <p className="mt-1 font-mono text-[9px] font-semibold uppercase tracking-[0.18em] text-chart-600">
                Marine EcOsystem Reasoning · Collaborative Agents
              </p>
            </div>
          </button>

          {/* title-block cells */}
          <div className="ml-auto flex flex-wrap items-stretch">
            <div className="hidden flex-col justify-center border-l px-5 py-3 sm:flex" style={{ borderColor: "var(--rule-faint)" }}>
              <span className="label">{ui.chartNo}</span>
              <span className="mt-1 font-mono text-[13px] font-bold text-ink-800">SIH26176</span>
            </div>

            {/* mode switch */}
            <button
              onClick={cycleMode}
              disabled={switching}
              title={`Running on ${mode} data — click to switch`}
              className="group flex flex-col justify-center border-l px-5 py-3 text-left transition hover:bg-paper-150 disabled:opacity-50"
              style={{ borderColor: "var(--rule-faint)" }}
            >
              <span className="label">{ui.dataEdition}</span>
              <span
                className={`mt-1 font-mono text-[13px] font-bold ${
                  mode === "LIVE" ? "text-risk-low" : "text-chart-600"
                }`}
              >
                {switching ? "…" : mode}
                <span className="ml-1.5 text-ink-300 transition group-hover:text-ink-700">⇄</span>
              </span>
            </button>

            <button
              onClick={() => setSpeak((v) => !v)}
              title="Speak answers aloud"
              className="flex flex-col justify-center border-l px-5 py-3 text-left transition hover:bg-paper-150"
              style={{ borderColor: "var(--rule-faint)" }}
            >
              <span className="label">{ui.voice}</span>
              <span className="mt-1 flex items-center gap-1.5 font-mono text-[13px] font-bold text-ink-800">
                {speak ? <SpeakerGlyph /> : <SpeakerOffGlyph className="text-ink-300" />}
                {speak ? "ON" : "OFF"}
              </span>
            </button>

            <div
              className="flex flex-col justify-center border-l px-4 py-3"
              style={{ borderColor: "var(--rule-faint)" }}
            >
              <span className="label">{ui.lang}</span>
              <span className="mt-1 flex flex-wrap gap-1">
                {([
                  { code: "en", label: "EN" },
                  { code: "hi", label: "हिं" },
                  { code: "mr", label: "मरा" },
                  { code: "ta", label: "தமி" },
                  { code: "te", label: "తెలు" },
                  { code: "bn", label: "বাং" },
                  { code: "ml", label: "മല" },
                ] as { code: SupportedLanguage; label: string }[]).map((l) => (
                  <button
                    key={l.code}
                    onClick={() => setLangChoice(l.code)}
                    className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[10px] font-bold transition ${
                      language === l.code
                        ? "border-ink-900 bg-ink-900 text-paper-50"
                        : "text-ink-400 hover:text-ink-800"
                    }`}
                    style={language === l.code ? undefined : { borderColor: "var(--rule)" }}
                  >
                    {l.label}
                  </button>
                ))}
              </span>
            </div>

            <div className="flex items-center border-l px-4" style={{ borderColor: "var(--rule-faint)" }}>
              <button onClick={() => (tourOn ? setTourOn(false) : startTour())} className="btn-ink">
                {tourOn ? <StopGlyph size={11} /> : <PlayGlyph size={11} />}
                {tourOn ? ui.stopTour : ui.tour}
              </button>
            </div>
          </div>
        </div>

        {/* folio tabs */}
        <nav
          className="flex items-end gap-6 border-t px-5"
          style={{ borderColor: "var(--rule-faint)" }}
        >
          {(["home", "ask", "authority", "system", "ops"] as AppTab[]).map((x) => (
            <button
              key={x}
              onClick={() => setTab(x)}
              className={`tab mt-2 ${tab === x ? "tab-on" : ""}`}
            >
              {tabLabels[x]}
            </button>
          ))}
          <span className="label ml-auto hidden pb-2.5 !tracking-[0.12em] !text-chart-500 md:block">
            {ui.marginalia}
          </span>
        </nav>
      </header>

      <AlertBanner
        alert={activeAlert}
        onDismiss={() => setActiveAlert(null)}
        onDivert={handleDivertSafePort}
        language={uiLang}
      />

      {tourOn && (
        <GuidedTour
          step={tourStep}
          language={uiLang}
          paused={tourPaused}
          onPause={() => setTourPaused((p) => !p)}
          onNext={() => gotoStep(tourStep + 1)}
          onPrev={() => gotoStep(tourStep - 1)}
          onExit={() => setTourOn(false)}
        />
      )}

      {error && (
        <div className="panel hatch-danger flex items-center gap-3 border-signal/60 px-4 py-2.5 text-[12.5px] text-risk-extreme">
          <WarnGlyph size={15} className="shrink-0" />
          <span>
            {error} — start the backend with{" "}
            <code className="font-mono font-bold">uvicorn app.main:app --port 8000</code>
          </span>
        </div>
      )}

      {/* ================= HOME : location + today's plan ================= */}
      {tab === "home" && (
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1.35fr_minmax(370px,1fr)]">
          <div className="space-y-4">
            <LocationPicker current={place} language={uiLang} onPick={setPlace} />

            <MarineMap
              origin={homeOrigin}
              zones={zones}
              pfz={[]}
              areas={outlook?.areas ?? []}
              radiusKm={outlook?.radius_km ?? RADIUS_KM}
              routes={outlook?.routes ?? []}
              geofence={[]}
              language={uiLang}
              onPickLocation={pickLocation}
              focusRank={focusRank}
              portFeatures={portFeatures}
              pfzGeoJson={pfzGeoJson}
            />

            {outlook && (
              <div className="panel grid grid-cols-2 overflow-hidden sm:grid-cols-4">
                {[
                  {
                    k: language === "mr" ? "सुरक्षा" : language === "hi" ? "सुरक्षा" : "Safety",
                    v: `${outlook.safety.score}`,
                    s: outlook.safety.category,
                    color: RISK_COLOR[outlook.safety.category],
                    icon: <LockGlyph size={11} />,
                  },
                  {
                    k: language === "mr" ? "लाटा" : language === "hi" ? "लहरें" : "Waves",
                    v: `${outlook.safety.wave_height_m ?? "—"}`,
                    s: "m",
                    icon: <WaveGlyph size={12} />,
                  },
                  {
                    k: language === "mr" ? "वारा" : language === "hi" ? "हवा" : "Wind",
                    v: outlook.safety.wind_speed_kmh != null ? `${Math.round(outlook.safety.wind_speed_kmh)}` : "—",
                    s: "km/h",
                    icon: <WindGlyph size={12} />,
                  },
                  {
                    k: language === "mr" ? "जागा" : language === "hi" ? "जगहें" : "Areas",
                    v: `${outlook.areas.length}`,
                    s: `in ${outlook.radius_km} km`,
                    icon: <CrosshairGlyph size={11} />,
                  },
                ].map((x, i) => (
                  <div
                    key={x.k}
                    className={`group relative px-4 py-3 transition-colors hover:bg-chart-100/40 ${i > 0 ? "border-l" : ""}`}
                    style={{
                      borderColor: "var(--rule-faint)",
                      borderTop: x.color ? `2px solid ${x.color}` : "2px solid transparent",
                    }}
                  >
                    <div className="label flex items-center gap-1.5 truncate">
                      <span
                        className="shrink-0 text-ink-300 transition-colors group-hover:text-chart-500"
                        style={x.color ? { color: x.color, opacity: 0.75 } : undefined}
                      >
                        {x.icon}
                      </span>
                      {x.k}
                    </div>
                    <div
                      className={`mt-1 font-mono text-[20px] font-bold tabular-nums leading-none text-ink-900 ${
                        x.color ? "" : "transition-colors group-hover:text-chart-600"
                      }`}
                      style={x.color ? { color: x.color } : undefined}
                    >
                      {x.v}
                      <span className="ml-1.5 text-[10px] font-semibold opacity-60">{x.s}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-4 lg:h-[calc(100vh-235px)] lg:overflow-y-auto lg:pr-1">
            {loadingOutlook && !outlook && (
              <div className="panel flex flex-col items-center gap-3 p-8 text-center">
                <span className="relative grid h-9 w-9 place-items-center text-chart-600">
                  <CompassMark size={30} className="animate-[spin_5s_linear_infinite] opacity-70" />
                  <span
                    className="pulse-dot absolute -right-0.5 -top-0.5"
                    style={{ background: "#2a7391", color: "#2a7391" }}
                  />
                </span>
                <span className="text-[13px] italic text-ink-400">
                  {language === "mr"
                    ? "तुमच्या ठिकाणाची माहिती घेत आहे…"
                    : language === "hi"
                      ? "आपके स्थान की जानकारी ले रहे हैं…"
                      : "Reading the sea at your location…"}
                </span>
              </div>
            )}
            {/* Live Alerts — calls GET /api/alerts */}
            {place && (
              <AlertsPanel lat={place.latitude} lon={place.longitude} compact />
            )}
            {/* Quick Risk Breakdown — calls GET /api/risk */}
            {place && (
              <QuickRiskPanel lat={place.latitude} lon={place.longitude} />
            )}
            {outlook && (
              <FishingPanel
                data={outlook}
                language={uiLang}
                onSelectArea={(rank) => setFocusRank(rank)}
              />
            )}
          </div>
        </div>
      )}

      {/* ================= ASK : the conversational view ================= */}
      {tab === "ask" && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="label mr-1">{ui.scenarios}</span>
            {scenarios.map((s) => (
              <button
                key={s.id}
                onClick={() => runScenario(s.ask)}
                disabled={busy}
                title={s.ask}
                className="chip disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span className="grid w-[18px] shrink-0 place-items-center rounded-full bg-ink-900 font-display text-[10px] font-bold leading-none text-paper-50" style={{ height: 18 }}>
                  {s.n}
                </span>
                <span className="font-semibold">{s.label[uiLang] ?? s.label.en}</span>
                <span className="font-mono text-[10px] uppercase tracking-wide opacity-60">{s.hint}</span>
              </button>
            ))}
          </div>

          <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(350px,1fr)_1.6fr]">
            <div className="min-h-[540px] lg:h-[calc(100vh-280px)]">
              <ChatPanel
                messages={messages}
                busy={busy}
                agentEvents={agentEvents}
                language={uiLang}
                suggestions={suggestions}
                onSend={send}
                onLanguage={(l) => setLangChoice(l)}
                onReset={async () => {
                  await api.resetSession(SESSION).catch(() => {});
                  setMessages([]);
                  setLatest(null);
                  setAgentEvents([]);
                }}
              />
            </div>

            <div className="space-y-4 lg:h-[calc(100vh-280px)] lg:overflow-y-auto lg:pr-1">
              {latest && <ConditionsStrip res={latest} language={latest.language} />}

              <MarineMap
                origin={latest?.intent.location ?? null}
                zones={zones}
                pfz={latest?.pfz ?? []}
                routes={latest?.routes ?? []}
                geofence={latest?.geofence ?? []}
                alerts={latest?.alerts ?? []}
                language={uiLang}
                portFeatures={portFeatures}
              />

              {latest?.risk && (
                <RiskCard
                  risk={latest.risk}
                  evidence={latest.evidence}
                  language={latest.language}
                />
              )}

              {latest && (
                <RiskTimeline location={latest.intent.location} language={latest.language} />
              )}

              {latest && latest.alerts.length > 0 && (
                <div className="panel hatch-danger overflow-hidden border-risk-extreme/60">
                  <div className="hd border-risk-extreme/25">
                    <span className="label flex items-center gap-2 !text-risk-extreme">
                      <WarnGlyph size={13} /> {ui.warnings}
                    </span>
                  </div>
                  <div className="px-4 py-3.5">
                    {latest.alerts.map((a, i) => (
                      <div key={i} className="mb-3 last:mb-0">
                        <div className="font-display text-[15px] font-bold leading-snug text-risk-extreme">
                          {a.headline}
                        </div>
                        <div className="mt-1 text-[12px] leading-relaxed text-ink-700">
                          {a.detail}
                        </div>
                        <div className="mt-1 font-mono text-[10px] uppercase tracking-wide text-ink-400">
                          {a.source} · {a.severity}
                          {a.valid_till ? ` · ${ui.validTill} ${a.valid_till}` : ""}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {latest && <PFZList zones={latest.pfz} language={latest.language} />}

              {latest && latest.routes.length > 0 && (
                <div className="panel overflow-hidden">
                  <div className="hd">
                    <span className="label flex items-center gap-2">
                      <CourseArrow size={12} className="text-chart-500" /> {ui.courses}
                    </span>
                    <span className="font-mono text-[10px] tabular-nums text-ink-400">
                      {latest.routes.length}
                    </span>
                  </div>
                  <div className="space-y-2 px-4 py-3.5">
                    {latest.routes.map((r) => (
                      <div
                        key={r.name}
                        className={`rounded-[2px] border px-3.5 py-3 ${
                          r.recommended ? "border-risk-low/70 bg-risk-low/[0.06]" : "bg-paper-100"
                        }`}
                        style={r.recommended ? undefined : { borderColor: "var(--rule)" }}
                      >
                        <div className="flex items-baseline justify-between gap-3">
                          <span className="flex items-center gap-2.5 font-display text-[14.5px] font-bold text-ink-900">
                            {/* course symbology, drawn as plotted */}
                            <svg width="26" height="8" aria-hidden>
                              <line
                                x1="1"
                                y1="4"
                                x2="25"
                                y2="4"
                                stroke={r.recommended ? "#1D7A50" : "#5D7386"}
                                strokeWidth="2"
                                strokeDasharray={r.recommended ? "7 4" : "2 4"}
                              />
                            </svg>
                            {r.name}
                            {r.recommended && (
                              <span className="stamp !px-1.5 !py-0.5 !text-[9px] text-risk-low">
                                {ui.recommended}
                              </span>
                            )}
                          </span>
                          <span className="shrink-0 font-mono text-[11.5px] tabular-nums text-ink-500">
                            {r.distance_km} km · {Math.round(r.eta_minutes)} min
                          </span>
                        </div>
                        <div className="mt-1 pl-[36px] text-[11.5px] leading-relaxed text-ink-500">
                          {r.notes}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {latest && (
                <AgentTracePanel trace={latest.trace} elapsed={latest.elapsed_ms} language={latest.language} explanationSource={latest.explanation_source} />
              )}

              {latest && (
                <p className="px-1 pb-2 font-mono text-[10.5px] leading-relaxed text-ink-400">
                  {latest.disclaimer}
                </p>
              )}
            </div>
          </div>
        </>
      )}

      {tab === "authority" && <AuthorityPanel language={uiLang} />}

      {tab === "system" && <SystemPanel mode={mode} language={uiLang} />}

      {tab === "ops" && (
        <div className="mx-auto w-full space-y-6">
          <VoyageTracker
            activeVoyages={activeVoyages}
            onStartVoyage={handleStartVoyage}
            onEndVoyage={handleEndVoyage}
            onTriggerTestAlert={handleTriggerTestAlert}
            currentPort={{
              name: place?.label || DEFAULT_PORT.name,
              lat: place?.latitude || DEFAULT_PORT.lat,
              lon: place?.longitude || DEFAULT_PORT.lon,
            }}
            language={uiLang}
            isLoading={loadingPlan}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ConflictLogPanel conflicts={planConflicts} language={uiLang} />
            <DecisionPipelineVisualizer
              trace={planTrace}
              requestId={planRequestId || undefined}
              onRefresh={handleRunPlan}
              isLoading={loadingPlan}
            />
          </div>

          <EvidenceProvenancePanel
            evidence={planEvidence}
            language={uiLang}
            onRefresh={handleRunPlan}
            isLoading={loadingPlan}
          />
        </div>
      )}
    </div>
  );
}