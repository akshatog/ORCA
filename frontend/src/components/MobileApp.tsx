import { useEffect, useRef, useState, useCallback } from "react";
import * as api from "../api";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import type { AlertEvent, FishingOutlook, Language, SupportedLanguage, Voyage, ZoneFeature } from "../types";
import { RATING_COLOR } from "./FishingPanel";
import AlertBanner from "./AlertBanner";
import AlertsPanel from "./AlertsPanel";
import RiskTimeline from "./RiskTimeline";
import {
  BoatGlyph,
  ChartDefs,
  CheckGlyph,
  ChevronDownGlyph,
  CompassMark,
  CrosshairGlyph,
  FishGlyph,
  MapGlyph,
  MicGlyph,
  SpeakerGlyph,
  StopGlyph,
  WarnGlyph,
  WaveGlyph,
  WindGlyph,
} from "./glyphs";
import { PORTS } from "./LocationPicker";
import MarineMap from "./MarineMap";
import PFZList from "./PFZList";
import { RISK_COLOR } from "./RiskDial";

/**
 * The phone — ORCA for the fisher himself, many of whom read little.
 *
 * Design rules, in order:
 *   1. Zero taps to the verdict: open → GPS → the big coloured circle.
 *   2. One tap to HEAR everything (browsers demand one gesture before TTS,
 *      so the speaker button is the biggest thing on screen).
 *   3. Everything important is a symbol, a colour or a large numeral;
 *      words are short and secondary.
 *   4. Three destinations, never deeper: Today · Map · Ask (by voice).
 */

type MTab = "today" | "map" | "ask";

const SESSION = "phone";
const DEFAULT_PORT = PORTS[0];

const T: Record<Language, Record<string, string>> = {
  en: {
    today: "Today",
    map: "Map",
    ask: "Ask",
    listen: "LISTEN",
    stop: "STOP",
    bestTime: "Best time",
    returnBy: "Be back by",
    areas: "Where the fish are",
    km: "km",
    profit: "Profit est.",
    fuel: "Fuel",
    tapMic: "Tap and speak",
    listening: "Listening…",
    thinking: "Asking the crew…",
    reading: "Reading the sea…",
    warnSpeak: "Official warning",
    askExamples: "Can I go tomorrow at 6 AM?",
    bestTimeSay: "Best time to fish is {a} to {b}.",
    returnBySay: "Be back before {t}.",
    chooseLang: "Choose your language",
    voiceCta: "Ask by voice",
    moreDetails: "More details",
    lessDetails: "Show less",
    radius: "Search radius",
    tapChart: "Tap the chart to check any spot",
    legendBest: "Best",
    legendGood: "Good",
    legendFair: "Fair",
    legendPoor: "Poor",
    enterApp: "Open full app",
    wave: "Wave",
    wind: "Wind",
    sea: "Sea state",
    nearestHarbour: "Nearest safe harbour",
    away: "away",
    noZonesTitle: "No ranked zones here",
    noZonesBody: "Too far from the coast for fishing-zone data — tap the harbour name above to switch.",
  },
  hi: {
    today: "आज",
    map: "नक्शा",
    ask: "पूछें",
    listen: "सुनें",
    stop: "रोकें",
    bestTime: "सबसे अच्छा समय",
    returnBy: "इससे पहले लौटें",
    areas: "मछली कहाँ है",
    km: "किमी",
    profit: "अनुमानित मुनाफ़ा",
    fuel: "ईंधन",
    tapMic: "दबाकर बोलिए",
    listening: "सुन रहे हैं…",
    thinking: "टीम से पूछ रहे हैं…",
    reading: "समुद्र पढ़ रहे हैं…",
    warnSpeak: "आधिकारिक चेतावनी",
    askExamples: "क्या मैं कल सुबह 6 बजे जा सकता हूँ?",
    bestTimeSay: "मछली पकड़ने का सबसे अच्छा समय {a} से {b} तक है।",
    returnBySay: "{t} से पहले लौट आएँ।",
    chooseLang: "अपनी भाषा चुनें",
    voiceCta: "बोलकर पूछें",
    moreDetails: "पूरी जानकारी देखें",
    lessDetails: "कम दिखाएँ",
    radius: "खोज त्रिज्या",
    tapChart: "किसी भी जगह जाँचने के लिए टैप करें",
    legendBest: "सर्वश्रेष्ठ",
    legendGood: "अच्छा",
    legendFair: "ठीक",
    legendPoor: "कम",
    enterApp: "पूरा ऐप खोलें",
    wave: "लहरें",
    wind: "हवा",
    sea: "समुद्र",
    nearestHarbour: "निकटतम सुरक्षित बंदरगाह",
    away: "दूर",
    noZonesTitle: "यहाँ कोई क्षेत्र उपलब्ध नहीं",
    noZonesBody: "समुद्र से बहुत दूर है — बंदरगाह बदलने के लिए ऊपर नाम पर टैप करें।",
  },
  mr: {
    today: "आज",
    map: "नकाशा",
    ask: "विचारा",
    listen: "ऐका",
    stop: "थांबवा",
    bestTime: "सर्वोत्तम वेळ",
    returnBy: "याआधी परत या",
    areas: "मासे कुठे आहेत",
    km: "किमी",
    profit: "अंदाजे नफा",
    fuel: "इंधन",
    tapMic: "दाबून बोला",
    listening: "ऐकत आहोत…",
    thinking: "टीमला विचारत आहोत…",
    reading: "समुद्र वाचत आहोत…",
    warnSpeak: "अधिकृत इशारा",
    askExamples: "मी उद्या सकाळी ६ वाजता जाऊ का?",
    bestTimeSay: "मासेमारीसाठी सर्वोत्तम वेळ {a} ते {b}.",
    returnBySay: "{t} च्या आधी परत या.",
    chooseLang: "तुमची भाषा निवडा",
    voiceCta: "बोलून विचारा",
    moreDetails: "सविस्तर पहा",
    lessDetails: "कमी दाखवा",
    radius: "शोध त्रिज्या",
    tapChart: "कोणतीही जागा तपासण्यासाठी टॅप करा",
    legendBest: "सर्वोत्तम",
    legendGood: "चांगले",
    legendFair: "ठीक",
    legendPoor: "कमी",
    enterApp: "संपूर्ण अ‍ॅप उघडा",
    wave: "लाटा",
    wind: "वारा",
    sea: "समुद्र",
    nearestHarbour: "सर्वात जवळचे सुरक्षित बंदर",
    away: "अंतरावर",
    noZonesTitle: "इथे कोणतीही क्षेत्रे उपलब्ध नाहीत",
    noZonesBody: "समुद्रापासून खूप दूर आहे — बंदर बदलण्यासाठी वरील नावावर टॅप करा.",
  },
  ta: {
    today: "இன்று",     map: "மேப்",        ask: "கேளு",      listen: "கேளுங்கள்",
    stop: "நிறுத்து",   bestTime: "சிறந்த நேரம்",            returnBy: "திரும்ப வர வேண்டிய நேரம்",
    areas: "மீன் கிடைக்கும் இடம்",          km: "கி.மீ",     profit: "தேர்வு லாபம்",  fuel: "ஏதன்",
    tapMic: "தடவி பேசுங்கள்",              listening: "கேட்கிறோம்…",
    thinking: "குழுவிடம் கேட்கிறோம்…",     reading: "கடலை படிக்கிறோம்…",
    warnSpeak: "அதிகாரப்பூர்வ எச்சரிக்கை",
    askExamples: "நாளை காலை 6 மணிக்கு போகலாமா?",
    bestTimeSay: "மீன்பிடிக்க சிறந்த நேரம் {a} முதல் {b}.",
    returnBySay: "{t} முன்னாக திரும்பி வாருங்கள்.",
    chooseLang: "உங்கள் மொழியைத் தேர்ந்தெடுங்கள்",
    voiceCta: "குரலில் கேளுங்கள்",         moreDetails: "மேலும் விவரங்கள்",  lessDetails: "குறைவாக காட்டு",
    radius: "தேடல் செம்மம்",               tapChart: "ஏதாவது இடத்தை சரிபார்க்க தடவுக",
    legendBest: "சிறந்தது",               legendGood: "நல்லது",             legendFair: "பரவாயில்லை",
    legendPoor: "குறைவு",                enterApp: "முழு ஆப் திறக்கூ",      wave: "அலைகள்",
    wind: "காற்று",                        sea: "கடல்",
    nearestHarbour: "அருகிலுள்ள பட்டினம்", away: "தூரத்தில்",
    noZonesTitle: "இங்கு எந்த மேஞ்சலும் இல்லை",
    noZonesBody: "கரையிலிருந்து மிகவும் தூரம் — மேலே பட்டின பெயரை தடவுக.",
  },
  te: {
    today: "నేడు",      map: "మ్యాప్",      ask: "అడగండి",   listen: "వినండి",
    stop: "ఆపండి",     bestTime: "అత్యుత్తమ సమయం",           returnBy: "ఈ సమయానికి తిరిగి రండి",
    areas: "చేపలు ఉన్న చోటు",               km: "కి.మీ",    profit: "అంచనా లాభం",   fuel: "ఇంధనం",
    tapMic: "నొక్కి మాట్లాడండి",            listening: "వింటున్నాం…",
    thinking: "బృందాన్ని అడుగుతున్నాం…",   reading: "సముద్రాన్ని చదువుతున్నాం…",
    warnSpeak: "అధికారిక హెచ్చరిక",
    askExamples: "రేపు ఉదయం 6 గంటలకు వెళ్ళవచ్చా?",
    bestTimeSay: "చేపలు పట్టడానికి అత్యుత్తమ సమయం {a} నుండి {b}.",
    returnBySay: "{t} కి ముందు తిరిగి రండి.",
    chooseLang: "మీ భాష ఎంచుకోండి",
    voiceCta: "గాలిలో అడగండి",             moreDetails: "ఇంకా వివరాలు",     lessDetails: "తక్కువ చూపించు",
    radius: "వెతుకు వ్యాసార్ధం",            tapChart: "ఏదైనా చోటు తనిఖీ చేయడానికి టాప్ చేయండి",
    legendBest: "అత్యుత్తమం",              legendGood: "మంచిది",             legendFair: "సాధారణం",
    legendPoor: "తక్కువ",                 enterApp: "పూర్తి ఆప్ తెరవండి",   wave: "అలలు",
    wind: "గాలి",                           sea: "సముద్రం",
    nearestHarbour: "సమీప నావాశ్రయం",      away: "దూరంలో",
    noZonesTitle: "ఇక్కడ జోన్లు లేవు",
    noZonesBody: "తీరం నుండి చాలా దూరం — మారడానికి పైన పేరు నొక్కండి.",
  },
  bn: {
    today: "আজ",        map: "মানচিত্র",   ask: "জিজ্ঞেস",  listen: "শুনুন",
    stop: "থামুন",      bestTime: "সেরা সময়",                returnBy: "ফিরে আসুন",
    areas: "মাছ আছে যেখানে",               km: "কি.মি",    profit: "অনুমানিত লাভ", fuel: "তেল",
    tapMic: "ট্যাপ করে বলুন",             listening: "শুনছি…",
    thinking: "দলকে জিজ্ঞেস করছি…",       reading: "সমুদ্র পড়ছি…",
    warnSpeak: "সরকারি সতর্কতা",
    askExamples: "আমি কাল সকাল ৬টায় যেতে পারি?",
    bestTimeSay: "মাছ ধরার সেরা সময় {a} থেকে {b}.",
    returnBySay: "{t} এর আগে ফিরে আসুন.",
    chooseLang: "আপনার ভাষা বেছুন",
    voiceCta: "কণ্ঠস্বরে জিজ্ঞেস করুন",   moreDetails: "আরো বিবরণ",        lessDetails: "কম দেখান",
    radius: "অনুসন্ধান ব্যাসার্ধ",          tapChart: "যেকোনো জায়গা পরীক্ষা করতে ট্যাপ করুন",
    legendBest: "সেরা",                   legendGood: "ভালো",               legendFair: "মোটামুটি",
    legendPoor: "কম",                    enterApp: "পূর্ণ অ্যাপ খুলুন",    wave: "ঢেউ",
    wind: "বাতাস",                         sea: "সমুদ্র",
    nearestHarbour: "নিকটতম বন্দর",      away: "দূরে",
    noZonesTitle: "এখানে কোনো জোন নেই",
    noZonesBody: "উপকূল থেকে অনেক দূরে — বন্দর বদলাতে উপরের নামে ট্যাপ করুন.",
  },
  ml: {
    today: "ഇന്ന്",     map: "ഭൂപടം",      ask: "ചോദിക്കൂ", listen: "കേൾക്കൂ",
    stop: "നിർത്തുക",  bestTime: "ഏറ്റവും നല്ല സമയം",         returnBy: "ഇതിന് മുമ്പ് തിരിച്ചുവരൂ",
    areas: "മീൻ കിട്ടുന്ന ഇടം",             km: "കി.മീ",    profit: "കണക്കാക്കിയ ലാഭം", fuel: "ഇന്ധനം",
    tapMic: "ടാപ്പ് ചെയ്ത് പറയുക",         listening: "കേൾക്കുന്നു…",
    thinking: "സംഘത്തിനോട് ചോദിക്കുന്നു…", reading: "കടൽ വായിക്കുന്നു…",
    warnSpeak: "ഔദ്യോഗിക മുന്നറിയിപ്പ്",
    askExamples: "നാളെ രാവിലെ 6 മണിക്ക് പോകാമോ?",
    bestTimeSay: "മത്സ്യബന്ധനത്തിന് {a} മുതൽ {b} വരെ ഏറ്റവും നല്ലത്.",
    returnBySay: "{t} ക്ക് മുമ്പ് തിരിച്ചുവരൂ.",
    chooseLang: "നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കൂ",
    voiceCta: "ശബ്ദത്തിൽ ചോദിക്കൂ",       moreDetails: "കൂടുതൽ വിവരങ്ങൾ", lessDetails: "കുറവ് കാണിക്കൂ",
    radius: "തിരയൽ ദൂരം",               tapChart: "ഏത് പ്രദേശം പരിശോധിക്കാനും ടാപ്പ് ചെയ്യൂ",
    legendBest: "മികച്ചത്",              legendGood: "നല്ലത്",             legendFair: "സാധാരണം",
    legendPoor: "കുറവ്",               enterApp: "പൂർണ ആപ്പ് തുറക്കൂ",   wave: "തിരകൾ",
    wind: "കാറ്റ്",                        sea: "കടൽ",
    nearestHarbour: "അടുത്ത തുറമുഖം",    away: "അകലെ",
    noZonesTitle: "ഇവിടെ സോണുകൾ ഇല്ല",
    noZonesBody: "കരയിൽ നിന്ന് വളരെ അകലെ — മാറാൻ മുകളിലെ പേരിൽ ടാപ്പ് ചെയ്യൂ.",
  },
};


// First-launch language picker — each language written in its own script so a
// fisher can recognise it by sight, not by reading English.
const LANG_OPTIONS: { code: SupportedLanguage; native: string }[] = [
  { code: "en", native: "English" },
  { code: "hi", native: "हिंदी" },
  { code: "mr", native: "मराठी" },
  { code: "ta", native: "தமிழ்" },
  { code: "te", native: "తెలుగు" },
  { code: "bn", native: "বাংলা" },
  { code: "ml", native: "മലയാളം" },
];

const SPEECH_LOCALE: Record<string, string> = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
  ta: "ta-IN",
  te: "te-IN",
  bn: "bn-IN",
  ml: "ml-IN",
};

async function speak(text: string, lang: string) {
  try {
    const loc = SPEECH_LOCALE[lang] || "hi-IN";
    const audioBlob = await api.speakText(text, loc, "aditya");
    const audio = new Audio(URL.createObjectURL(audioBlob));
    audio.play();
    return audio;
  } catch {
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = SPEECH_LOCALE[lang] || "hi-IN";
      u.rate = 0.95;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch {
      /* no TTS fallback */
    }
  }
}

function clock12(h: number): string {
  const hh = h % 24;
  return `${hh % 12 || 12} ${hh < 12 ? "AM" : "PM"}`;
}

/** Great-circle distance in km — good enough for "which harbour is closest". */
function distanceKm(aLat: number, aLon: number, bLat: number, bLon: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLon = ((bLon - aLon) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

/** Ease-out count from 0 to target whenever target changes — the score
 * "computing" rather than just appearing, without looping or repeating. */
function useCountUp(target: number, ms = 850): number {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return n;
}

function getRecognition(): any | null {
  const w = window as any;
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

export default function MobileApp() {
  const [language, setLanguage] = useState<SupportedLanguage>(() => {
    const l = new URLSearchParams(window.location.search).get("lang") as SupportedLanguage;
    if (l) return l;
    const saved = window.localStorage.getItem("orca_lang") as SupportedLanguage | null;
    return saved || "en";
  });
  const uiLang: Language = language;

  const t = T[uiLang] ?? T.en;

  // First-launch language gate: shown until the fisher has actually tapped a
  // language on THIS gate at least once. A ?lang= arriving from a link (e.g.
  // the desktop site's "Phone version" button carrying its own language)
  // pre-fills the value above for convenience, but it does NOT count as a
  // choice — only an explicit tap here, remembered in localStorage, skips
  // the gate on future opens.
  const [langChosen, setLangChosen] = useState<boolean>(() =>
    Boolean(window.localStorage.getItem("orca_lang")),
  );
  const pickLanguage = (l: SupportedLanguage) => {
    setLanguage(l);
    window.localStorage.setItem("orca_lang", l);
    setLangChosen(true);
  };

  // Returning users (langChosen already true from a past visit) skip the
  // landing entirely, same as before. First-time users see the language
  // grid, then — on the SAME screen — a simplified status + voice shortcut,
  // before landingDone flips true and the full tabbed app takes over.
  const [landingDone, setLandingDone] = useState<boolean>(() =>
    Boolean(window.localStorage.getItem("orca_lang")),
  );

  // Header language dropdown (replaces the old row of always-visible chips —
  // one tidy control instead of seven competing for space).
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const langMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!langMenuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (langMenuRef.current && !langMenuRef.current.contains(e.target as Node)) {
        setLangMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [langMenuOpen]);

  // Same pattern as the language dropdown: a compact, always-available way
  // to switch harbour from the map tab, instead of a picker that only
  // appears (and only once) when the current spot has no fishing zones.
  const [portMenuOpen, setPortMenuOpen] = useState(false);
  const portMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!portMenuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (portMenuRef.current && !portMenuRef.current.contains(e.target as Node)) {
        setPortMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [portMenuOpen]);

  // Today tab opens in a short, simple summary; the fuller breakdown (risk
  // timeline, ranked grounds, fuel/profit) is one tap away, not automatic.
  const [showDetails, setShowDetails] = useState(false);

  const [activeAlert, setActiveAlert] = useState<AlertEvent | null>(null);
  const [activeVoyage, setActiveVoyage] = useState<Voyage | null>(null);
  const [voyageLoading, setVoyageLoading] = useState(false);

  const [tab, setTab] = useState<MTab>(() => {
    const tp = new URLSearchParams(window.location.search).get("tab");
    return tp === "map" || tp === "ask" ? tp : "today";
  });
  const [place, setPlace] = useState<{ lat: number; lon: number; name: string } | null>(null);
  const [outlook, setOutlook] = useState<FishingOutlook | null>(null);
  const [zones, setZones] = useState<ZoneFeature[]>([]);
  const [focusRank, setFocusRank] = useState<number | null>(null);
  const [speaking, setSpeaking] = useState(false);

  // ---- ask state ----
  const [question, setQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [agentProgress, setAgentProgress] = useState<string | null>(null);

  // ---- geofence state (for map tab) ----
  const [geofenceStatus, setGeofenceStatus] = useState<"clear" | "warning" | "critical">("clear");
  const [geofenceMsg, setGeofenceMsg] = useState<string | null>(null);

  // Temporary layout probe: ?debug=1 prints the widest elements on screen so
  // headless screenshots can carry their own diagnosis.
  const [debugInfo, setDebugInfo] = useState<string>("");
  useEffect(() => {
    if (!new URLSearchParams(window.location.search).has("debug")) return;
    const id = window.setTimeout(() => {
      const vw = document.documentElement.clientWidth;
      const rows = [...document.querySelectorAll("*")]
        .map((el) => ({ el, w: el.getBoundingClientRect().width }))
        .filter((x) => x.w > vw + 1)
        .sort((a, b) => b.w - a.w)
        .slice(0, 5)
        .map(
          (x) =>
            `${Math.round(x.w)} ${x.el.tagName}.${String((x.el as HTMLElement).className).slice(0, 44)}`,
        );
      setDebugInfo(
        `vw=${vw} sw=${document.documentElement.scrollWidth}\n${rows.join("\n") || "no wide elements"}`,
      );
    }, 3500);
    return () => window.clearTimeout(id);
  }, [outlook]);

  // The map used to be nearly the whole tab. Now that a conditions strip,
  // a harbour card and the ranked-zones list share the page with it, it
  // only needs to be big enough to read at a glance — roughly a third of
  // the screen — not the dominant element.
  const [mapH, setMapH] = useState(() => Math.min(320, Math.max(220, Math.round(window.innerHeight * 0.34))));
  useEffect(() => {
    const onR = () => setMapH(Math.min(320, Math.max(220, Math.round(window.innerHeight * 0.34))));
    window.addEventListener("resize", onR);
    return () => window.removeEventListener("resize", onR);
  }, []);

  // ---------------------------------------------------------------- boot
  useEffect(() => {
    api.zones().then((z) => setZones(z.features)).catch(() => {});
    const fallback = () =>
      setPlace({ lat: DEFAULT_PORT.lat, lon: DEFAULT_PORT.lon, name: DEFAULT_PORT.name });
    const at = (new URLSearchParams(window.location.search).get("at") ?? "")
      .split(",")
      .map(Number);
    if (at.length === 2 && at.every(Number.isFinite)) {
      setPlace({ lat: at[0], lon: at[1], name: "—" });
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          setPlace({
            lat: +pos.coords.latitude.toFixed(4),
            lon: +pos.coords.longitude.toFixed(4),
            name: "—",
          }),
        fallback,
        { enableHighAccuracy: true, timeout: 7000, maximumAge: 300_000 },
      );
    } else fallback();
  }, []);

  useEffect(() => {
    if (!place) return;
    let alive = true;
    setOutlook(null);
    api
      .fishingOutlook(place.lat, place.lon, { radiusKm: 100, days: 3, lang: language })
      .then((d) => alive && setOutlook(d))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [place?.lat, place?.lon, language]);

  // ---------------------------------------------------------------- voyage & alerts
  useEffect(() => {
    api
      .getActiveVoyages()
      .then((v) => {
        if (v.length > 0) setActiveVoyage(v[0]);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!activeVoyage) return;
    const timer = setInterval(async () => {
      try {
        const active = await api.getActiveVoyages();
        const current = active.find((v) => v.voyage_id === activeVoyage.voyage_id);
        if (current) {
          setActiveVoyage(current);
        }
      } catch {}
    }, 10000);
    return () => clearInterval(timer);
  }, [activeVoyage?.voyage_id]);

  const handleToggleVoyage = async () => {
    if (activeVoyage) {
      setVoyageLoading(true);
      try {
        await api.endVoyage(activeVoyage.voyage_id);
        setActiveVoyage(null);
        setActiveAlert(null);
      } catch (e) {
        console.error(e);
      } finally {
        setVoyageLoading(false);
      }
    } else if (place) {
      setVoyageLoading(true);
      try {
        const res = await api.startVoyage({
          location: {
            lat: place.lat,
            lon: place.lon,
            name: outlook?.location.nearest_landing_centre || place.name || "Kochi",
          },
          voyage_id: `voyage-${Date.now().toString().slice(-4)}`,
        });
        setActiveVoyage({
          voyage_id: res.voyage_id,
          location: res.location || { lat: place.lat, lon: place.lon, name: place.name },
          started_at: res.started_at,
          status: "ACTIVE",
        });
      } catch (e) {
        console.error(e);
      } finally {
        setVoyageLoading(false);
      }
    }
  };

  const handleDivertSafePort = (safePort: { name: string; lat: number; lon: number }) => {
    setPlace({ lat: safePort.lat, lon: safePort.lon, name: safePort.name });
    setActiveAlert(null);
    setTab("map");
  };

  // ---------------------------------------------------------------- voice
  const speakPlan = () => {
    if (!outlook) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const bits = [...outlook.advice.slice(0, 4)];
    if (outlook.best_window)
      bits.push(
        t.bestTimeSay
          .replace("{a}", clock12(outlook.best_window.from_hour))
          .replace("{b}", clock12(outlook.best_window.to_hour)),
      );
    if (outlook.duration?.return_by)
      bits.push(t.returnBySay.replace("{t}", outlook.duration.return_by));
    speak(bits.join(" "), language);
    setSpeaking(true);
    const check = window.setInterval(() => {
      if (!window.speechSynthesis.speaking) {
        setSpeaking(false);
        window.clearInterval(check);
      }
    }, 400);
  };

  const fallbackRecognition = useCallback(() => {
    const rec = getRecognition();
    if (!rec) {
      console.error("SpeechRecognition not supported in this browser.");
      return;
    }
    rec.lang = SPEECH_LOCALE[language];
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      const said = e.results[0][0].transcript;
      sendAsk(said);
    };
    rec.start();
  }, [language]);

  const { state: voiceState, toggleRecording } = useVoiceRecorder({
    language: SPEECH_LOCALE[language],
    onTranscript: (said) => sendAsk(said),
    onFallback: fallbackRecognition,
  });

  // One tap from the status screen straight into listening — no extra nav.
  const goToVoice = () => {
    setTab("ask");
    if (voiceState === "idle" || voiceState === "error") {
      toggleRecording();
    }
  };

  const sendAsk = async (text: string) => {
    setQuestion(text);
    setAnswer(null);
    setAgentProgress(null);
    setBusy(true);
    try {
      await api.askStream(
        { message: text, sessionId: SESSION },
        (e) => {
          // Show live agent progress: "Checking weather…", "Scoring risk…"
          if (e.type === "thinking" && e.step) {
            setAgentProgress(e.step);
          } else if (e.type === "agent_done") {
            setAgentProgress(e.label ?? e.agent);
          }
        },
        (res) => {
          setAnswer(res.answer);
          setAgentProgress(null);
          setSuggestions(res.suggestions.slice(0, 3));
          if (res.language !== language) setLanguage(res.language as SupportedLanguage);
          speak(res.answer.split(". ").slice(0, 3).join(". "), res.language);
        },
        (_err) => {
          setAnswer("Could not reach ORCA — is the backend running?");
          setAgentProgress(null);
        },
      );
    } finally {
      setBusy(false);
    }
  };

  // ---------------------------------------------------------------- bits
  const cat = outlook?.safety.category;
  const color = cat ? RISK_COLOR[cat] : "#42596D";
  const danger = cat === "HIGH" || cat === "EXTREME";
  const animatedScore = useCountUp(outlook?.safety.score ?? 0);

  const nearestPort = place
    ? PORTS.map((p) => ({ ...p, distance_km: distanceKm(place.lat, place.lon, p.lat, p.lon) })).sort(
        (a, b) => a.distance_km - b.distance_km,
      )[0]
    : null;

  const speakArea = (a: FishingOutlook["areas"][number]) => {
    const line = `${a.rank}. ${Math.round(a.distance_km)} ${t.km}. ${a.probability}%. ${(
      a.likely_species ?? []
    )
      .map((s) => s.split(" (")[0])
      .join(", ")}`;
    speak(line, language);
    setFocusRank(a.rank);
    setTab("map");
  };

  // ---------------------------------------------------------------- landing
  if (!landingDone) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-6 bg-paper-100 px-6 py-10 text-center">
        <ChartDefs />
        <div className="sea-drift" aria-hidden />

        {!langChosen ? (
          // --- step 1: pick a language ---
          <>
            <CompassMark size={60} className="animate-stampIn text-ink-900" />
            <div className="animate-rise" style={{ animationDelay: "80ms" }}>
              <div className="font-display text-[26px] font-black leading-tight text-ink-900">ORCA</div>
              <div className="mt-2 font-mono text-[12px] uppercase tracking-[0.14em] text-ink-500">
                Choose your language · अपनी भाषा चुनें
              </div>
            </div>
            <div className="grid w-full max-w-[340px] grid-cols-2 gap-3">
              {LANG_OPTIONS.map((o, i) => (
                <button
                  key={o.code}
                  onClick={() => pickLanguage(o.code)}
                  className={`panel animate-rise flex items-center justify-center px-3 py-6 transition active:scale-[0.97] active:bg-paper-150 ${
                    language === o.code ? "border-ink-900 bg-ink-900" : ""
                  }`}
                  style={{ animationDelay: `${140 + i * 40}ms` }}
                >
                  <span
                    className={`font-display text-[20px] font-bold ${
                      language === o.code ? "text-paper-50" : "text-ink-900"
                    }`}
                  >
                    {o.native}
                  </span>
                </button>
              ))}
            </div>
          </>
        ) : (
          // --- step 2: same screen, now show a simplified live status + voice shortcut ---
          <div className="popin flex w-full max-w-[360px] flex-col items-center gap-4">
            <div className="flex items-center gap-2">
              <CompassMark size={26} className="text-ink-900 compass-needle" />
              <span className="font-display text-[18px] font-black text-ink-900">ORCA</span>
            </div>

            {!outlook ? (
              <div className="panel flex flex-col items-center gap-3 p-8 text-center">
                <CompassMark
                  size={44}
                  className="animate-[spin_5s_linear_infinite] text-ink-300 opacity-80"
                />
                <span className="text-[14px] italic text-ink-400">{t.reading}</span>
              </div>
            ) : (
              <div
                className="panel rule-double relative flex w-full flex-col items-center overflow-hidden px-4 pb-4 pt-5 text-center"
                style={{ background: `${color}14` }}
              >
                <div className="font-mono text-[10.5px] text-chart-600">
                  {outlook.location.nearest_landing_centre}
                </div>
                <div
                  className="popin relative mt-2 grid h-24 w-24 place-items-center rounded-full border-[6px] bg-paper-50"
                  style={{ borderColor: color, color }}
                >
                  <span className="sonar-once" style={{ borderColor: color }} />
                  <span className="sonar-once sonar-once-2" style={{ borderColor: color }} />
                  {danger && <span className="alert-ring" style={{ borderColor: color }} />}
                  <span className="svg-bob inline-flex">
                    {danger ? <WarnGlyph size={38} /> : <BoatGlyph size={42} />}
                  </span>
                </div>
                <div className="mt-2 font-display text-[24px] font-black leading-none" style={{ color }}>
                  {animatedScore}
                  <span className="text-[13px] font-bold opacity-70"> / 100</span>
                </div>
                <p className="mt-2 font-display text-[16px] font-semibold leading-snug text-ink-900">
                  {outlook.advice[0]}
                </p>
                {outlook.best_window && (
                  <div className="mt-2 font-mono text-[11px] text-chart-700">
                    {t.bestTime}: {clock12(outlook.best_window.from_hour)}–
                    {clock12(outlook.best_window.to_hour)}
                  </div>
                )}

                {/* voice — the whole reason this screen replaced a plain gate */}
                <button
                  onClick={() => {
                    goToVoice();
                    setLandingDone(true);
                  }}
                  className="mt-4 flex w-full items-center justify-center gap-3 rounded-[3px] bg-ink-900 py-4 font-mono text-[15px] font-bold uppercase tracking-[0.14em] text-paper-50 transition active:translate-y-px active:scale-[0.98]"
                  style={{ boxShadow: "0 10px 22px -12px rgba(18,33,45,0.55)" }}
                >
                  <MicGlyph size={20} />
                  {t.voiceCta}
                </button>
              </div>
            )}

            <button
              onClick={() => setLandingDone(true)}
              className="flex items-center gap-1.5 font-mono text-[11.5px] font-bold uppercase tracking-wide text-chart-600 transition active:scale-95"
            >
              {t.enterApp}
              <ChevronDownGlyph size={11} className="-rotate-90" />
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-col">
      <ChartDefs />
      <div className="sea-drift" aria-hidden />
      {debugInfo && (
        <pre className="fixed left-0 top-0 z-[999] max-w-[300px] whitespace-pre-wrap bg-black p-1 text-[10px] leading-tight text-white">
          {debugInfo}
        </pre>
      )}

      {/* ---------------- slim header ---------------- */}
      <header
        className="sticky top-0 z-[600] flex items-center gap-2.5 border-b bg-paper-100/95 px-3 py-2.5 backdrop-blur-sm"
        style={{ borderColor: "var(--rule)", boxShadow: "0 2px 10px -6px rgba(18,33,45,0.28)" }}
      >
        <CompassMark size={30} className="shrink-0 text-ink-900 compass-needle" />
        <div className="min-w-0">
          <div className="font-display text-[17px] font-black leading-none text-ink-900">ORCA</div>
          {place && outlook && (
            <div className="truncate font-mono text-[9px] text-chart-600">
              {outlook.location.nearest_landing_centre}
            </div>
          )}
        </div>

        {/* language — one compact control instead of a row of chips */}
        <div ref={langMenuRef} className="relative ml-auto shrink-0">
          <button
            onClick={() => setLangMenuOpen((v) => !v)}
            className={`flex items-center gap-1.5 rounded-[3px] border px-2.5 py-1.5 font-mono text-[12px] font-bold transition active:scale-95 ${
              langMenuOpen ? "border-ink-900 bg-ink-900 text-paper-50" : "border-ink-900/70 bg-paper-50 text-ink-900"
            }`}
          >
            {LANG_OPTIONS.find((o) => o.code === language)?.native ?? "EN"}
            <ChevronDownGlyph
              size={10}
              className={`transition-transform duration-200 ${langMenuOpen ? "rotate-180" : ""}`}
            />
          </button>
          {langMenuOpen && (
            <div
              className="panel animate-rise absolute right-0 top-[calc(100%+6px)] z-[650] w-40 overflow-hidden !p-1"
              style={{ transformOrigin: "top right" }}
            >
              {LANG_OPTIONS.map((o) => (
                <button
                  key={o.code}
                  onClick={() => {
                    pickLanguage(o.code);
                    setLangMenuOpen(false);
                  }}
                  className={`flex w-full items-center justify-between gap-2 rounded-[2px] px-2.5 py-2 text-left font-mono text-[13px] font-semibold transition ${
                    language === o.code ? "bg-ink-900 text-paper-50" : "text-ink-800 active:bg-paper-150"
                  }`}
                >
                  {o.native}
                  {language === o.code && <CheckGlyph size={11} />}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* active alert banner */}
      {activeAlert && (
        <div className="px-3 pt-2">
          <AlertBanner
            alert={activeAlert}
            onDismiss={() => setActiveAlert(null)}
            onDivert={handleDivertSafePort}
            language={uiLang}
          />
        </div>
      )}

      {/* ================= TODAY ================= */}
      {tab === "today" && (
        <main className="flex-1 space-y-3 px-3 pb-24 pt-3">
          {/* Voyage status & quick toggle */}
          <div className="panel animate-rise flex items-center justify-between gap-3 bg-paper-50 p-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    activeVoyage ? "bg-risk-low animate-pulse" : "bg-ink-300"
                  }`}
                />
                <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-ink-700">
                  {activeVoyage ? "Voyage Active" : "In Harbour"}
                </span>
              </div>
              <div className="mt-0.5 truncate font-mono text-[10px] text-ink-500">
                {activeVoyage
                  ? `Voyage ${activeVoyage.voyage_id.slice(0, 8)} • ${activeVoyage.location?.name || "At Sea"}`
                  : "Ready to log departure"}
              </div>
            </div>
            <button
              onClick={handleToggleVoyage}
              disabled={voyageLoading || !place}
              className={`shrink-0 rounded-[3px] px-3 py-2 font-mono text-[11px] font-bold uppercase tracking-wide transition ${
                activeVoyage
                  ? "border border-risk-extreme/60 bg-risk-extreme/10 text-risk-extreme"
                  : "bg-chart-600 text-paper-50"
              }`}
            >
              {voyageLoading ? "..." : activeVoyage ? "End Trip" : "Start Trip"}
            </button>
          </div>

          {!outlook && (
            <div className="panel flex flex-col items-center gap-3 p-10 text-center">
              <CompassMark
                size={56}
                className="animate-[spin_5s_linear_infinite] text-ink-300 opacity-80"
              />
              <span className="text-[15px] italic text-ink-400">{t.reading}</span>
            </div>
          )}

          {outlook && (
            <>
              {/* the verdict — colour first, words second */}
              <div
                className="panel rule-double animate-rise relative flex flex-col items-center overflow-hidden px-4 pb-4 pt-6 text-center"
                style={{ background: `${color}14` }}
              >
                {/* soft glow behind the ring — a little life behind the flat wash */}
                <div
                  aria-hidden
                  className="pointer-events-none absolute left-1/2 top-8 h-44 w-44 -translate-x-1/2 rounded-full blur-2xl"
                  style={{ background: `${color}33` }}
                />
                <div
                  className="popin relative grid h-32 w-32 place-items-center rounded-full border-[7px] bg-paper-50"
                  style={{ borderColor: color, color, boxShadow: `0 10px 26px -12px ${color}80` }}
                >
                  <span className="sonar-once" style={{ borderColor: color }} />
                  <span className="sonar-once sonar-once-2" style={{ borderColor: color }} />
                  {danger && <span className="alert-ring" style={{ borderColor: color }} />}
                  <span className="svg-bob inline-flex">
                    {danger ? <WarnGlyph size={54} /> : <BoatGlyph size={58} />}
                  </span>
                </div>
                <div
                  className="mt-3 font-display text-[30px] font-black leading-none"
                  style={{ color }}
                >
                  {animatedScore}
                  <span className="text-[15px] font-bold opacity-70"> / 100</span>
                </div>
                <p className="mt-2.5 font-display text-[19px] font-semibold leading-snug text-ink-900">
                  {outlook.advice[0]}
                </p>

                {/* THE button — one tap, hear everything */}
                <button
                  onClick={speakPlan}
                  className="mt-4 flex w-full items-center justify-center gap-3 rounded-[3px] bg-ink-900 py-4 font-mono text-[17px] font-bold uppercase tracking-[0.14em] text-paper-50 transition active:translate-y-px active:scale-[0.98]"
                  style={{ boxShadow: "0 10px 22px -12px rgba(18,33,45,0.55)" }}
                >
                  {speaking ? <StopGlyph size={20} /> : <SpeakerGlyph size={24} />}
                  {speaking ? t.stop : t.listen}
                </button>

                {/* voice — one tap, straight into listening, no extra nav */}
                <button
                  onClick={goToVoice}
                  className="mt-2.5 flex w-full items-center justify-center gap-3 rounded-[3px] border-[2.5px] bg-paper-50 py-3.5 font-mono text-[15px] font-bold uppercase tracking-[0.14em] transition active:translate-y-px active:scale-[0.98] active:bg-paper-150"
                  style={{ borderColor: color, color }}
                >
                  <MicGlyph size={20} />
                  {t.voiceCta}
                </button>
              </div>

              {/* official warning — red, loud, speaks itself */}
              {outlook.safety.official_warning && (
                <button
                  onClick={() => speak(`${t.warnSpeak}. ${outlook.advice[0]}`, language)}
                  className="panel hatch-danger animate-rise flex w-full items-center gap-3 border-risk-extreme/70 px-4 py-3 text-left"
                  style={{ animationDelay: "60ms" }}
                >
                  <WarnGlyph size={30} className="shrink-0 text-risk-extreme" />
                  <span className="font-display text-[16px] font-bold leading-tight text-risk-extreme">
                    {t.warnSpeak}
                  </span>
                  <SpeakerGlyph size={18} className="ml-auto shrink-0 text-risk-extreme" />
                </button>
              )}

              {/* times — big numerals, tiny labels */}
              <div className="animate-rise grid grid-cols-2 gap-3" style={{ animationDelay: "100ms" }}>
                {outlook.best_window && (
                  <div className="panel px-3 py-3 text-center">
                    <div className="label !text-[9px]">{t.bestTime}</div>
                    <div className="mt-1 font-display text-[21px] font-bold leading-none text-risk-low">
                      {clock12(outlook.best_window.from_hour)}–
                      {clock12(outlook.best_window.to_hour)}
                    </div>
                  </div>
                )}
                {outlook.duration?.return_by && (
                  <div className="panel border-risk-extreme/50 bg-risk-extreme/[0.06] px-3 py-3 text-center">
                    <div className="label !text-[9px] !text-risk-extreme">{t.returnBy}</div>
                    <div className="mt-1 font-display text-[26px] font-black leading-none text-risk-extreme">
                      {outlook.duration.return_by}
                    </div>
                  </div>
                )}
              </div>

              {/* one tap to expand — everything below is optional depth */}
              <button
                onClick={() => setShowDetails((v) => !v)}
                className="flex w-full items-center justify-center gap-1.5 py-1 font-mono text-[11px] font-bold uppercase tracking-wide text-chart-600 transition active:scale-95"
              >
                {showDetails ? t.lessDetails : t.moreDetails}
                <ChevronDownGlyph
                  size={11}
                  className={`transition-transform ${showDetails ? "rotate-180" : ""}`}
                />
              </button>

              {showDetails && (
                <div className="animate-rise space-y-3">
                  {/* Live alerts from GET /api/alerts */}
                  {place && (
                    <AlertsPanel lat={place.lat} lon={place.lon} compact refreshMs={60000} />
                  )}

                  {/* Risk timeline mini-chart */}
                  {place && (
                    <div className="panel overflow-hidden">
                      <div className="hd !py-2">
                        <span className="label !text-[10px]">Risk Forecast (24h)</span>
                      </div>
                      <div className="px-2 pb-1">
                        <RiskTimeline
                          location={{ name: outlook?.location.nearest_landing_centre ?? place.name, latitude: place.lat, longitude: place.lon }}
                          language={uiLang}
                        />
                      </div>
                    </div>
                  )}

                  {/* the grounds — tap to hear + see on the chart */}
                  <div className="panel overflow-hidden">
                    <div className="hd !py-2">
                      <span className="label flex items-center gap-2 !text-[10px]">
                        {t.areas} <FishGlyph size={14} className="swim text-chart-500" />
                      </span>
                    </div>
                    <div className="divide-y" style={{ borderColor: "var(--rule-faint)" }}>
                      {outlook.areas.slice(0, 3).map((a) => (
                        <button
                          key={a.id}
                          onClick={() => speakArea(a)}
                          className="flex w-full items-center gap-3 px-3 py-3 text-left transition active:scale-[0.99] active:bg-paper-150"
                        >
                          <span
                            className="grid h-12 w-12 shrink-0 place-items-center rounded-full border-4 bg-paper-50 font-display text-[19px] font-extrabold text-ink-900"
                            style={{ borderColor: RATING_COLOR[a.rating] }}
                          >
                            {a.rank}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-[17px] font-bold text-ink-900">
                              {Math.round(a.distance_km)} {t.km}
                            </span>
                            <span className="block truncate font-mono text-[11px] text-chart-700">
                              {(a.likely_species ?? []).map((s) => s.split(" (")[0]).join(" · ")}
                            </span>
                          </span>
                          <span
                            className="sounding shrink-0 text-[26px]"
                            style={{ color: RATING_COLOR[a.rating] }}
                          >
                            {a.probability}
                            <span className="text-[14px]">%</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* money — two numbers a fisher weighs every morning */}
                  {outlook.economics && (
                    <div className="panel grid grid-cols-2 overflow-hidden">
                      <div className="px-3 py-3 text-center" style={{ borderTop: "2px solid transparent" }}>
                        <div className="label !text-[9px]">{t.fuel}</div>
                        <div className="mt-1 font-mono text-[21px] font-bold text-ink-900">
                          ₹{outlook.economics.fuel_cost_inr.toLocaleString("en-IN")}
                        </div>
                      </div>
                      <div
                        className="border-l bg-risk-low/[0.07] px-3 py-3 text-center"
                        style={{ borderColor: "var(--rule-faint)", borderTop: "2px solid #1D7A50" }}
                      >
                        <div className="label !text-[9px] !text-risk-low">{t.profit}</div>
                        <div className="mt-1 font-mono text-[21px] font-bold text-risk-low">
                          ₹{outlook.economics.profit_inr.toLocaleString("en-IN")}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </main>
      )}

      {/* ================= MAP ================= */}
      {tab === "map" && (
        <main className="animate-rise flex-1 px-2 pb-20 pt-2">
          {/* location + radius + legend, and live conditions — one card, not two stacked */}
          <div className="panel mb-2">
            <div className="flex items-center justify-between gap-2 px-3 py-2">
              <div ref={portMenuRef} className="relative min-w-0">
                <button
                  onClick={() => setPortMenuOpen((v) => !v)}
                  className="flex min-w-0 items-center gap-1 text-left active:opacity-70"
                >
                  <span className="min-w-0">
                    <span className="label !text-[9px]">{outlook?.location.nearest_landing_centre ?? t.map}</span>
                    <span className="mt-0.5 flex items-center gap-1 font-mono text-[10.5px] text-chart-600">
                      <MapGlyph size={11} /> {t.radius}: {outlook?.radius_km ?? 100} {t.km}
                    </span>
                  </span>
                  <ChevronDownGlyph
                    size={9}
                    className={`mt-2.5 shrink-0 text-ink-400 transition-transform ${portMenuOpen ? "rotate-180" : ""}`}
                  />
                </button>
                {portMenuOpen && (
                  <div
                    className="panel animate-rise absolute left-0 top-[calc(100%+6px)] z-[650] max-h-64 w-56 overflow-y-auto !p-1 shadow-2xl"
                    style={{ transformOrigin: "top left" }}
                  >
                    {PORTS.map((p) => (
                      <button
                        key={p.name}
                        onClick={() => {
                          setPlace({ lat: p.lat, lon: p.lon, name: p.name });
                          setPortMenuOpen(false);
                        }}
                        className="flex w-full items-center justify-between gap-2 rounded-[2px] px-2.5 py-2 text-left font-mono text-[12.5px] font-semibold text-ink-800 transition active:bg-paper-150"
                      >
                        {p.name}
                        {outlook?.location.nearest_landing_centre === p.name && <CheckGlyph size={10} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {/* rating legend — what the coloured pins mean */}
              <div className="flex shrink-0 items-center gap-2 overflow-x-auto no-scrollbar">
                {(
                  [
                    ["very_good", t.legendBest],
                    ["good", t.legendGood],
                    ["fair", t.legendFair],
                    ["poor", t.legendPoor],
                  ] as const
                ).map(([k, label]) => (
                  <span key={k} className="flex items-center gap-1 font-mono text-[9px] text-ink-500">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ background: RATING_COLOR[k] }}
                    />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            {/* live conditions — the numbers behind the coloured pins */}
            {outlook && (
              <div className="grid grid-cols-3 border-t" style={{ borderColor: "var(--rule-faint)" }}>
                <div className="px-2 py-2 text-center">
                  <div className="label flex items-center justify-center gap-1 !text-[8.5px]">
                    <WaveGlyph size={11} /> {t.wave}
                  </div>
                  <div className="mt-0.5 font-mono text-[13px] font-bold text-ink-900">
                    {outlook.safety.wave_height_m != null ? `${outlook.safety.wave_height_m} m` : "—"}
                  </div>
                </div>
                <div className="border-x px-2 py-2 text-center" style={{ borderColor: "var(--rule-faint)" }}>
                  <div className="label flex items-center justify-center gap-1 !text-[8.5px]">
                    <WindGlyph size={11} /> {t.wind}
                  </div>
                  <div className="mt-0.5 font-mono text-[13px] font-bold text-ink-900">
                    {outlook.safety.wind_speed_kmh != null ? `${outlook.safety.wind_speed_kmh} km/h` : "—"}
                  </div>
                </div>
                <div className="px-2 py-2 text-center">
                  <div className="label !text-[8.5px]">{t.sea}</div>
                  <div className="mt-0.5 truncate font-mono text-[13px] font-bold text-ink-900">
                    {outlook.safety.sea_state ?? "—"}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Geofence warning banner when near restricted zone */}
          {geofenceStatus !== "clear" && geofenceMsg && (
            <div
              className={`animate-rise mb-2 flex items-center gap-2 rounded-[3px] px-3 py-2 text-[12.5px] font-semibold ${
                geofenceStatus === "critical"
                  ? "bg-risk-extreme/10 text-risk-extreme"
                  : "bg-risk-high/10 text-risk-high"
              }`}
            >
              <WarnGlyph size={14} className="shrink-0" />
              {geofenceMsg}
            </div>
          )}
          <div className="panel overflow-hidden !p-0">
            <MarineMap
              origin={
                place
                  ? { name: outlook?.location.nearest_landing_centre ?? "—", latitude: place.lat, longitude: place.lon }
                  : null
              }
              zones={zones}
              pfz={[]}
              areas={outlook?.areas ?? []}
              radiusKm={outlook?.radius_km ?? 100}
              routes={outlook?.routes ?? []}
              geofence={[]}
              language={uiLang}
              onPickLocation={(lat, lon) => {
                const p = { lat, lon, name: "—" };
                setPlace(p);
                // Check geofence immediately on map click
                api.checkPosition(lat, lon)
                  .then((pos) => {
                    setGeofenceStatus(pos.status as any);
                    setGeofenceMsg(pos.status !== "clear" ? pos.headline : null);
                  })
                  .catch(() => {});
              }}
              focusRank={focusRank}
              heightPx={mapH}
            />
          </div>
          <p className="mt-2 text-center font-mono text-[10.5px] text-ink-400">{t.tapChart}</p>

          {/* nearest safe harbour — a real next-step, not just a picture */}
          {nearestPort && (
            <button
              onClick={() => setPlace({ lat: nearestPort.lat, lon: nearestPort.lon, name: nearestPort.name })}
              className="panel mt-2 flex w-full items-center gap-3 px-3 py-2.5 text-left transition active:scale-[0.99] active:bg-paper-150"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full border-[3px] border-chart-500 bg-paper-50 text-chart-600">
                <CrosshairGlyph size={16} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="label !text-[9px]">{t.nearestHarbour}</span>
                <span className="block truncate text-[14px] font-bold text-ink-900">{nearestPort.name}</span>
              </span>
              <span className="shrink-0 font-mono text-[12.5px] font-bold tabular-nums text-chart-700">
                {Math.round(nearestPort.distance_km)} {t.km} {t.away}
              </span>
            </button>
          )}

          {/* ranked fishing grounds — reuses the same list the chat panel uses.
              When the current spot is too far inland to have any (like this
              screen's own default before GPS resolves), fill the space with
              a next step instead of leaving it blank. */}
          {outlook && outlook.areas.length > 0 ? (
            <div className="mt-2">
              <PFZList zones={outlook.areas} language={uiLang} />
            </div>
          ) : outlook ? (
            <div className="panel mt-2 flex items-center gap-2.5 px-3.5 py-3">
              <FishGlyph size={16} className="shrink-0 text-ink-300" />
              <p className="text-[12px] leading-snug text-ink-500">
                <span className="font-bold text-ink-700">{t.noZonesTitle}.</span> {t.noZonesBody}
              </p>
            </div>
          ) : null}
        </main>
      )}

      {/* ================= ASK ================= */}
      {tab === "ask" && (
        <main className="animate-rise flex flex-1 flex-col items-center gap-4 px-4 pb-24 pt-6">
          {/* the mic IS the interface */}
          <div className="relative grid place-items-center">
            {voiceState === "recording" && (
              <span
                aria-hidden
                className="absolute h-36 w-36 rounded-full border-2 border-risk-extreme/50"
                style={{ animation: "ping2 1.6s cubic-bezier(0,0,0.2,1) infinite" }}
              />
            )}
            <button
              onClick={toggleRecording}
              className={`relative grid h-36 w-36 place-items-center rounded-full border-[6px] transition-all duration-200 active:scale-95 ${
                voiceState === "recording"
                  ? "border-risk-extreme bg-risk-extreme text-paper-50"
                  : voiceState === "processing"
                  ? "border-chart-400 bg-chart-400 text-paper-50"
                  : "border-ink-900 bg-paper-50 text-ink-900"
              }`}
              style={{
                boxShadow:
                  voiceState === "recording"
                    ? "0 12px 30px -10px rgba(175,35,24,0.55)"
                    : "0 12px 30px -14px rgba(18,33,45,0.5)",
                ...(voiceState === "recording" || voiceState === "processing"
                  ? { animation: "inkblink 1.1s ease-in-out infinite" }
                  : {}),
              }}
            >
              {voiceState === "recording" ? <StopGlyph size={44} /> : voiceState === "processing" ? <span className="animate-spin text-2xl">...</span> : <MicGlyph size={64} />}
            </button>
          </div>
          <div className="font-mono text-[13px] font-bold uppercase tracking-[0.14em] text-ink-500">
            {voiceState === "recording" ? t.listening : (busy || voiceState === "processing") ? (agentProgress ? agentProgress + "…" : t.thinking) : t.tapMic}
          </div>

          {question && (
            <div className="popin w-full rounded-[3px] bg-ink-900 px-4 py-3 text-[15px] text-paper-50">
              {question}
            </div>
          )}
          {busy && (
            <div className="flex gap-2">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-2.5 w-2.5 animate-bounce rounded-full bg-ink-700"
                  style={{ animationDelay: `${i * 120}ms` }}
                />
              ))}
            </div>
          )}
          {answer && (
            <button
              onClick={() => speak(answer, language)}
              className="panel popin w-full px-4 py-3.5 text-left transition active:scale-[0.98]"
            >
              <p className="text-[16px] leading-relaxed text-ink-800">{answer}</p>
              <span className="mt-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wide text-chart-600">
                <SpeakerGlyph size={14} /> {t.listen}
              </span>
            </button>
          )}
          {suggestions.length > 0 && !busy && (
            <div className="animate-rise flex w-full flex-col gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => sendAsk(s)}
                  className="chip w-full justify-center !py-3 !text-[14px] active:scale-[0.98]"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          {!question && !answer && (
            <p className="max-w-[260px] text-center text-[13px] italic text-ink-400">
              “{t.askExamples}”
            </p>
          )}
        </main>
      )}

      {/* ---------------- bottom nav: three doors, never deeper ---------------- */}
      <nav
        className="fixed inset-x-0 bottom-0 z-[700] flex border-t bg-paper-50/95 p-1.5 backdrop-blur-sm"
        style={{ borderColor: "var(--rule-strong)", boxShadow: "0 -6px 18px -14px rgba(18,33,45,0.4)" }}
      >
        {(
          [
            ["today", <BoatGlyph key="b" size={24} />],
            ["map", <MapGlyph key="m" size={20} />],
            ["ask", <MicGlyph key="a" size={24} />],
          ] as [MTab, JSX.Element][]
        ).flatMap(([m, icon], i) => [
          // a hairline rule between tabs — same divider style used elsewhere
          // in the app (conditions strip, areas list), not a new motif
          ...(i > 0
            ? [
                <span
                  key={`${m}-div`}
                  aria-hidden
                  className="my-2 w-px shrink-0"
                  style={{ background: "var(--rule-faint)" }}
                />
              ]
            : []),
          <button
            key={m}
            onClick={() => setTab(m)}
            className={`mx-0.5 flex flex-1 flex-col items-center gap-1 rounded-[3px] py-2 transition-all duration-200 active:scale-95 ${
              tab === m ? "-translate-y-0.5 bg-ink-900 text-paper-50 shadow-[0_6px_14px_-8px_rgba(18,33,45,0.6)]" : "text-ink-500"
            }`}
          >
            {icon}
            <span className="font-mono text-[10.5px] font-bold uppercase tracking-wide">{t[m]}</span>
          </button>,
        ])}
      </nav>
    </div>
  );
}