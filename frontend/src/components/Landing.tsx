import { useEffect, useRef, useState, type ReactNode } from "react";
import * as api from "../api";
import type { Language } from "../types";
import { CompassMark, CourseArrow, FishGlyph, PhoneGlyph, PlayGlyph } from "./glyphs";

/** Every word on the front door, in the fisher's three languages. */
const L10N: Record<
  Language,
  {
    tag1: string;
    tag2a: string;
    tag2b: string;
    tag2c: string;
    sub: string;
    kicker: string;
    navFeatures: string;
    navHow: string;
    navTry: string;
    ctaTour: string;
    ctaOpen: string;
    ctaPhone: string;
    ctaTry: string;
    openOrca: string;
    openWord: string;
    watchLive: string;
    pipelineTitle: string;
    stats: string[];
    cards: { kicker: string; title: string; lines: string[] }[];
    phases: { t: string; n: string }[];
    footer: string;
  }
> = {
  en: {
    tag1: "Turn marine data into decisions.",
    tag2a: "Navigate with ",
    tag2b: "intelligence",
    tag2c: ".",
    sub: "ORCA brings together satellite, oceanographic, and weather data through collaborative AI agents to deliver clear, explainable insights and actionable recommendations for safer, smarter decisions at sea.",
    kicker: "SIH26176 · ISRO · Smart India Hackathon 2026",
    navFeatures: "Features",
    navHow: "How it works",
    navTry: "Try it",
    ctaTour: "Watch the guided tour",
    ctaOpen: "Open the ORCA app",
    ctaPhone: "Phone version",
    ctaTry: "Try a scenario → cyclone near Paradip",
    openOrca: "Open ORCA",
    openWord: "Open",
    watchLive: "watch it run live →",
    pipelineTitle: "How ORCA decides",
    stats: ["Agents in the crew", "Landing centres", "Official warnings", "Languages", "Data edition"],
    cards: [
      {
        kicker: "Today's plan",
        title: "Where the fish are",
        lines: [
          "Opens knowing where you are — reads 100 km of sea unprompted",
          "Every ground scored for chance of fish, with the why behind it",
          "Trip plan: when to go, how long to stay, what it should earn",
        ],
      },
      {
        kicker: "Ask ORCA",
        title: "Your language, spoken or typed",
        lines: [
          "English · हिंदी · मराठी — detected, never configured",
          "A 0–100 risk verdict where every point is attributed",
          "Official warnings override the model. Always.",
        ],
      },
      {
        kicker: "Authority",
        title: "The district view",
        lines: [
          "Every landing centre on the coast, scored by the same engine",
          "The administration sees the same evidence the fisher sees",
          "One-click CSV export for the day's advisory board",
        ],
      },
    ],
    phases: [
      { t: "Understand", n: "parse the question, any language" },
      { t: "Gather", n: "five specialists fan out concurrently" },
      { t: "Decide", n: "weighted model + safety floors that only raise" },
      { t: "Explain", n: "plain words, with sources, spoken back" },
    ],
    footer:
      "Demo / simulated data is always labelled · ORCA is decision support — never a replacement for an official advisory",
  },
  hi: {
    tag1: "समुद्री डेटा को फ़ैसलों में बदलें।",
    tag2a: "बुद्धिमत्ता के साथ ",
    tag2b: "नेविगेट करें",
    tag2c: "।",
    sub: "ORCA उपग्रह, समुद्री और मौसम डेटा को सहयोगी AI एजेंटों के ज़रिए जोड़कर, समुद्र में सुरक्षित और समझदार फ़ैसलों के लिए स्पष्ट, समझाने योग्य जानकारी और सुझाव देता है।",
    kicker: "SIH26176 · ISRO · स्मार्ट इंडिया हैकाथॉन 2026",
    navFeatures: "विशेषताएँ",
    navHow: "यह कैसे काम करता है",
    navTry: "आज़माएँ",
    ctaTour: "गाइडेड टूर देखें",
    ctaOpen: "ORCA ऐप खोलें",
    ctaPhone: "फ़ोन संस्करण",
    ctaTry: "एक परिदृश्य आज़माएँ → पारादीप के पास चक्रवात",
    openOrca: "ORCA खोलें",
    openWord: "खोलें",
    watchLive: "इसे चलते हुए देखें →",
    pipelineTitle: "ORCA फ़ैसला कैसे करता है",
    stats: ["टीम के एजेंट", "लैंडिंग सेंटर", "आधिकारिक चेतावनियाँ", "भाषाएँ", "डेटा संस्करण"],
    cards: [
      {
        kicker: "आज की योजना",
        title: "मछली कहाँ है",
        lines: [
          "खुलते ही आपकी जगह जानता है — 100 किमी समुद्र ख़ुद पढ़ता है",
          "हर इलाक़े को मछली की संभावना पर अंक, कारण के साथ",
          "यात्रा योजना: कब जाएँ, कितना रुकें, कितना मिलेगा",
        ],
      },
      {
        kicker: "ORCA से पूछें",
        title: "आपकी भाषा, बोलकर या लिखकर",
        lines: [
          "English · हिंदी · मराठी — ख़ुद पहचानता है, कोई सेटिंग नहीं",
          "0–100 का जोखिम, हर अंक के हिसाब के साथ",
          "आधिकारिक चेतावनी मॉडल से हमेशा ऊपर।",
        ],
      },
      {
        kicker: "प्रशासन",
        title: "ज़िले का नज़ारा",
        lines: [
          "तट का हर लैंडिंग सेंटर, उसी इंजन से आँका हुआ",
          "प्रशासन वही प्रमाण देखता है जो मछुआरा देखता है",
          "दिन के बोर्ड का एक-क्लिक CSV निर्यात",
        ],
      },
    ],
    phases: [
      { t: "समझो", n: "सवाल परखो, किसी भी भाषा में" },
      { t: "जुटाओ", n: "पाँच विशेषज्ञ एक साथ निकलते हैं" },
      { t: "तय करो", n: "भारित मॉडल + नियम जो सिर्फ़ जोखिम बढ़ाते हैं" },
      { t: "समझाओ", n: "सीधी भाषा, स्रोतों के साथ, बोलकर भी" },
    ],
    footer:
      "नक़ली/डेमो डेटा पर हमेशा लेबल · ORCA निर्णय-सहायक है — आधिकारिक सलाह का विकल्प कभी नहीं",
  },
  mr: {
    tag1: "सागरी डेटाला निर्णयांमध्ये बदला.",
    tag2a: "बुद्धिमत्तेसह ",
    tag2b: "मार्गक्रमण करा",
    tag2c: ".",
    sub: "ORCA उपग्रह, सागरी आणि हवामान डेटा सहयोगी AI एजंट्सद्वारे एकत्र आणून, समुद्रातील सुरक्षित आणि हुशार निर्णयांसाठी स्पष्ट, स्पष्टीकरणासह माहिती आणि शिफारसी देते.",
    kicker: "SIH26176 · ISRO · स्मार्ट इंडिया हॅकेथॉन 2026",
    navFeatures: "वैशिष्ट्ये",
    navHow: "हे कसे कार्य करते",
    navTry: "वापरून पाहा",
    ctaTour: "गाइडेड टूर पाहा",
    ctaOpen: "ORCA अ‍ॅप उघडा",
    ctaPhone: "फोन आवृत्ती",
    ctaTry: "एक परिस्थिती वापरून पाहा → पारादीपजवळ चक्रीवादळ",
    openOrca: "ORCA उघडा",
    openWord: "उघडा",
    watchLive: "हे चालताना पाहा →",
    pipelineTitle: "ORCA निर्णय कसा घेते",
    stats: ["टीममधील एजंट", "लँडिंग सेंटर", "अधिकृत इशारे", "भाषा", "डेटा आवृत्ती"],
    cards: [
      {
        kicker: "आजची योजना",
        title: "मासे कुठे आहेत",
        lines: [
          "उघडताच तुमचे ठिकाण ओळखते — १०० किमी समुद्र स्वतः वाचते",
          "प्रत्येक जागेला माशांच्या शक्यतेवर गुण, कारणासह",
          "फेरीची योजना: कधी जायचे, किती थांबायचे, किती मिळेल",
        ],
      },
      {
        kicker: "ORCA ला विचारा",
        title: "तुमची भाषा, बोलून किंवा लिहून",
        lines: [
          "English · हिंदी · मराठी — स्वतः ओळखते, सेटिंग नाही",
          "0–100 धोका, प्रत्येक गुणाच्या हिशेबासह",
          "अधिकृत इशारा मॉडेलच्या नेहमी वर.",
        ],
      },
      {
        kicker: "प्रशासन",
        title: "जिल्ह्याचे दृश्य",
        lines: [
          "किनाऱ्यावरील प्रत्येक लँडिंग सेंटर, त्याच इंजिनने तपासलेले",
          "प्रशासनाला तेच पुरावे दिसतात जे मच्छीमाराला दिसतात",
          "दिवसाच्या बोर्डाचे एक-क्लिक CSV निर्यात",
        ],
      },
    ],
    phases: [
      { t: "समजून घ्या", n: "प्रश्न पारखा, कोणत्याही भाषेत" },
      { t: "गोळा करा", n: "पाच तज्ज्ञ एकाच वेळी निघतात" },
      { t: "ठरवा", n: "भारित मॉडेल + फक्त धोका वाढवणारे नियम" },
      { t: "समजावा", n: "सोपी भाषा, स्रोतांसह, बोलूनही" },
    ],
    footer:
      "नमुना/डेमो डेटावर नेहमी लेबल · ORCA निर्णय-सहाय्यक आहे — अधिकृत सल्ल्याचा पर्याय कधीही नाही",
  },
};

/** Honour the OS "reduce motion" setting — those users get the finished page. */
function prefersStill(): boolean {
  return (
    typeof window !== "undefined" &&
    !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Entrance choreography with a projector fail-safe: visibility is driven by
 * STATE + CSS transitions, never by keyframes with fill-mode. If rAF is
 * suspended (hidden tab, non-compositing output) the timeout still flips the
 * state, so the end position — everything visible — is always reached; with
 * reduced motion the content simply starts there.
 */
function Reveal({
  delay = 0,
  className = "",
  children,
}: {
  delay?: number;
  className?: string;
  children: ReactNode;
}) {
  const [on, setOn] = useState(prefersStill);
  useEffect(() => {
    if (on) return;
    const raf = requestAnimationFrame(() => setOn(true));
    const settle = window.setTimeout(() => setOn(true), 500);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(settle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div
      className={className}
      style={{
        opacity: on ? 1 : 0,
        transform: on ? "none" : "translateY(16px)",
        transition: prefersStill()
          ? "none"
          : `opacity 0.65s ease ${delay}ms, transform 0.65s cubic-bezier(0.2, 0.7, 0.3, 1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

/** Count-up with the same fail-safe as the risk dial: the number always lands. */
function useCountUp(target: number | null, ms = 1000): string {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (target == null) return;
    if (prefersStill()) {
      setV(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - start) / ms));
      setV(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    const settle = window.setTimeout(() => setV(target), ms + 150);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(settle);
    };
  }, [target, ms]);
  return target == null ? "—" : String(v);
}

/**
 * Wraps the hero art with a gentle, cursor-driven tilt — the chart "leans"
 * toward the pointer, like paper on a chart table. Desktop-only in effect
 * (touch devices never fire mousemove); reduced-motion users get no tilt.
 */
function HeroArt({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [t, setT] = useState({ x: 0, y: 0 });
  return (
    <div
      ref={ref}
      onMouseMove={(e) => {
        if (prefersStill()) return;
        const r = ref.current?.getBoundingClientRect();
        if (!r) return;
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        setT({ x: px * 9, y: py * 7 });
      }}
      onMouseLeave={() => setT({ x: 0, y: 0 })}
      style={{
        transform: `perspective(1000px) rotateX(${-t.y}deg) rotateY(${t.x}deg)`,
        transition: "transform 0.4s cubic-bezier(0.2, 0.7, 0.3, 1)",
        willChange: "transform",
      }}
    >
      {children}
    </div>
  );
}

/**
 * The front door — the chart sheet before you step aboard.
 *
 * One screen that says what ORCA is (ten agents, one safe, explainable
 * decision), proves it is alive (live coastline stats, a running course),
 * and hands the judge three doors in.
 */
export default function Landing({
  mode,
  language = "en",
  onLanguage,
  onEnter,
  onTour,
  onScenario,
}: {
  mode: string;
  language?: Language;
  onLanguage: (lang: Language) => void;
  onEnter: (tab: "home" | "ask" | "authority" | "system") => void;
  onTour: () => void;
  onScenario: (ask: string) => void;
}) {
  const t = L10N[language] ?? L10N.en;
  const [centres, setCentres] = useState<number | null>(null);
  const [warnings, setWarnings] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .authority()
      .then((d) => {
        if (!alive) return;
        setCentres(d.summary.monitored ?? null);
        setWarnings(d.summary.official_warnings ?? null);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const agentsN = useCountUp(10, 900);
  const centresN = useCountUp(centres, 1100);
  const warningsN = useCountUp(warnings, 1300);
  const langsN = useCountUp(3, 800);
  const heroConfidence = useCountUp(92, 1100);

  const cardTabs: ("home" | "ask" | "authority")[] = ["home", "ask", "authority"];

  const stats = [
    { k: t.stats[0], v: agentsN },
    { k: t.stats[1], v: centresN },
    { k: t.stats[2], v: warningsN, warn: (warnings ?? 0) > 0 },
    { k: t.stats[3], v: langsN },
    { k: t.stats[4], v: mode },
  ];

  return (
    <>
      {/* ================= NAVBAR — full-bleed, sticky, always reachable =================
          Deliberately minimal: wordmark, three anchor links, one CTA. Language
          switch and the hackathon badge moved out — a persistent bar is not
          the right home for controls you set once or credentials you read once. */}
      <Reveal>
        <nav className="sticky top-0 z-20 w-full border-b border-[var(--rule)] bg-paper-50/90 backdrop-blur-sm">
          <div className="mx-auto grid max-w-[1240px] grid-cols-[auto_1fr_auto] items-center gap-8 px-5 py-4">
            <span className="flex shrink-0 items-center gap-2">
              <CompassMark size={26} className="text-ink-900" />
              <span className="font-display text-[19px] font-black tracking-tight text-ink-900">ORCA</span>
            </span>
            <div className="hidden items-center justify-center gap-9 md:flex">
              <button
                onClick={() => document.getElementById("lp-features")?.scrollIntoView({ behavior: "smooth" })}
                className="nav-link relative font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500 transition-colors after:absolute after:-bottom-1 after:left-0 after:right-0 after:h-[1.5px] after:origin-center after:scale-x-0 after:bg-current after:transition-transform after:duration-300 hover:text-ink-900 hover:after:scale-x-100 focus-visible:text-ink-900 focus-visible:after:scale-x-100"
              >
                {t.navFeatures}
              </button>
              <button
                onClick={() => document.getElementById("lp-pipeline")?.scrollIntoView({ behavior: "smooth" })}
                className="nav-link relative font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500 transition-colors after:absolute after:-bottom-1 after:left-0 after:right-0 after:h-[1.5px] after:origin-center after:scale-x-0 after:bg-current after:transition-transform after:duration-300 hover:text-ink-900 hover:after:scale-x-100 focus-visible:text-ink-900 focus-visible:after:scale-x-100"
              >
                {t.navHow}
              </button>
              <button
                onClick={() => onScenario("Is there a cyclone near Paradip? Can I go fishing?")}
                className="nav-link relative font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500 transition-colors after:absolute after:-bottom-1 after:left-0 after:right-0 after:h-[1.5px] after:origin-center after:scale-x-0 after:bg-current after:transition-transform after:duration-300 hover:text-ink-900 hover:after:scale-x-100 focus-visible:text-ink-900 focus-visible:after:scale-x-100"
              >
                {t.navTry}
              </button>
            </div>
            <button onClick={() => onEnter("home")} className="btn-ink group shrink-0 justify-self-end">
              {t.openOrca}{" "}
              <CourseArrow size={13} className="transition-transform group-hover:translate-x-1" />
            </button>
          </div>
        </nav>
      </Reveal>

      <div className="mx-auto flex min-h-full max-w-[1240px] flex-col px-5 py-5">
      <div className="sea-drift" aria-hidden />
      <div className="fish-drift" aria-hidden />

      {/* ================= HERO SCREEN — fills the rest of the first viewport ================= */}
      <div className="flex min-h-[calc(100svh-70px)] flex-col justify-center py-6">
      {/* hero */}
      <div className="mt-0 grid items-center gap-10 lg:grid-cols-[1.25fr_1fr]">
        <div>
          <Reveal delay={60}>
            <div className="wave-rule max-w-[430px]" />
          </Reveal>
          <Reveal delay={200}>
            <p className="mt-5 max-w-[460px] font-display text-[42px] font-black leading-[1.08] tracking-tight text-ink-900 sm:text-[48px] lg:text-[54px]">
              {t.tag1}
              <br />
              {t.tag2a}
              <br />
              <span className="text-chart-600">{t.tag2b}</span>
              {t.tag2c}
            </p>
            <p className="mt-6 max-w-[520px] text-[16px] leading-relaxed text-ink-600 lg:text-[17px]">{t.sub}</p>
          </Reveal>

          <Reveal delay={330}>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button onClick={onTour} className="btn-line !px-5 !py-2.5">
                <PlayGlyph size={11} /> {t.ctaTour}
              </button>
              <button onClick={() => onEnter("home")} className="btn-ink group !px-5 !py-2.5">
                {t.ctaOpen}{" "}
                <CourseArrow size={13} className="transition-transform group-hover:translate-x-1" />
              </button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-5">
              {/* full reload on purpose: phone vs console is decided at boot */}
              <button
                onClick={() => (window.location.href = `/?m=1&lang=${language}`)}
                className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-500 transition-colors hover:text-ink-900"
              >
                <PhoneGlyph size={13} /> {t.ctaPhone}
              </button>
              <span className="h-3 w-px" style={{ background: "var(--rule)" }} aria-hidden />
              <button
                onClick={() => onScenario("Is there a cyclone near Paradip? Can I go fishing?")}
                className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-chart-600 underline decoration-dashed underline-offset-4 transition-colors hover:text-ink-900"
              >
                {t.ctaTry}
              </button>
            </div>
          </Reveal>
        </div>

        {/* hero art: a live marine-intelligence map, not a static illustration.
            Data layers arrive in sequence (ocean → weather → satellite),
            the safe course plots itself around the danger zone, and a
            verdict panel confirms the recommendation once it's ready —
            the same story ORCA tells inside the real app, compressed
            into one glance. Visible at every width; ~40–45% of the hero
            column on desktop, where it has room to read as a real map. */}
        <Reveal delay={260} className="mt-2 justify-self-center lg:mt-0 lg:justify-self-end">
          <HeroArt>
          <svg viewBox="0 0 440 300" className="w-full max-w-[420px] lg:max-w-[580px]" aria-hidden>
            {/* ============ layer 0 — ocean / bathymetry (always present) ============ */}
            <rect x="0" y="0" width="440" height="300" fill="#2A7391" opacity="0.06" />
            <rect x="0" y="150" width="440" height="150" fill="#2A7391" opacity="0.05" />
            {[60, 130, 200, 270].map((y) => (
              <line key={y} x1="0" y1={y} x2="440" y2={y} stroke="#2A7391" strokeWidth="0.5" opacity="0.2" />
            ))}
            {[80, 180, 280, 380].map((x) => (
              <line key={x} x1={x} y1="0" x2={x} y2="300" stroke="#2A7391" strokeWidth="0.5" opacity="0.2" />
            ))}

            {/* ============ layer 1 — weather (isobars, fades in) ============ */}
            <g className="layer-weather" fill="none" stroke="#5D7386" strokeWidth="0.8">
              <path d="M14 38 Q120 16 224 38 T424 36" opacity="0.35" />
              <path d="M6 60 Q130 40 252 60 T430 56" opacity="0.28" />
              <path d="M20 20 Q140 4 262 22 T420 16" opacity="0.22" />
            </g>

            {/* ============ layer 2 — satellite pass (dot grid, fades in) ============ */}
            <g className="layer-satellite" fill="#12212D">
              {[70, 150, 230, 310, 390].flatMap((x) =>
                [48, 108, 168, 226].map((y) => (
                  <circle key={`${x}-${y}`} cx={x} cy={y} r="1" opacity="0.3" />
                ))
              )}
            </g>

            {/* a school working the water under the course */}
            <g fill="#1E5F7A" opacity="0.5">
              <g className="svg-swim">
                <path d="M96 205 C99 201 104 200.5 108 203.8 L114 201 C113 202.3 112.5 203.6 112.5 205 C112.5 206.4 113 207.7 114 209 L108 206.2 C104 209.5 99 209 96 205 Z" />
              </g>
              <g className="svg-swim" style={{ animationDelay: "0.9s" }}>
                <path d="M126 220 C129 216 134 215.5 138 218.8 L144 216 C143 217.3 142.5 218.6 142.5 220 C142.5 221.4 143 222.7 144 224 L138 221.2 C134 224.5 129 224 126 220 Z" />
              </g>
              <g className="svg-swim" style={{ animationDelay: "1.7s" }}>
                <path d="M104 236 C107 232 112 231.5 116 234.8 L122 232 C121 233.3 120.5 234.6 120.5 236 C120.5 237.4 121 238.7 122 240 L116 237.2 C112 240.5 107 240 104 236 Z" />
              </g>
            </g>
            {/* another pair near the destination — the reason the buoy is there */}
            <g fill="#1D7A50" opacity="0.45">
              <g className="svg-swim" style={{ animationDelay: "0.4s" }}>
                <path d="M330 100 C333 96 338 95.5 342 98.8 L348 96 C347 97.3 346.5 98.6 346.5 100 C346.5 101.4 347 102.7 348 104 L342 101.2 C338 104.5 333 104 330 100 Z" />
              </g>
              <g className="svg-swim" style={{ animationDelay: "1.3s" }}>
                <path d="M352 116 C355 112 360 111.5 364 114.8 L370 112 C369 113.3 368.5 114.6 368.5 116 C368.5 117.4 369 118.7 370 120 L364 117.2 C360 120.5 355 120 352 116 Z" />
              </g>
            </g>
            {/* sea-surface symbols and soundings scattered on the water */}
            {[
              [40, 80], [120, 45], [330, 130], [70, 170], [250, 250], [380, 200],
            ].map(([x, y], i) => (
              <path
                key={i}
                d={`M${x} ${y} q4 -3.5 8 0 t8 0`}
                fill="none"
                stroke="#2A7391"
                strokeWidth="1.1"
                opacity="0.5"
                strokeLinecap="round"
              />
            ))}
            <text x="150" y="230" fontFamily="Georgia" fontStyle="italic" fontSize="11" fill="#2A7391" opacity="0.65">27</text>
            <text x="300" y="90" fontFamily="Georgia" fontStyle="italic" fontSize="11" fill="#2A7391" opacity="0.65">44</text>

            {/* ============ cyclone — tracked from satellite, breathing danger zone ============ */}
            <path
              className="cyclone-trajectory"
              d="M250 20 C 240 44 220 66 206 92"
              fill="none"
              stroke="#AF2318"
              strokeWidth="1.4"
              opacity="0.55"
              strokeLinecap="round"
            />
            <g transform="translate(250 16)" opacity="0.85" aria-hidden>
              <circle r="11" fill="none" stroke="#AF2318" strokeWidth="1.3" strokeDasharray="3 3" className="storm-spin" />
              <circle
                r="6"
                fill="none"
                stroke="#AF2318"
                strokeWidth="1.3"
                strokeDasharray="2 3"
                className="storm-spin"
                style={{ animationDirection: "reverse", animationDuration: "3.4s" }}
              />
              <circle r="2" fill="#AF2318" />
            </g>
            {/* hatched danger areas the course detours around — both breathe gently */}
            <g>
              <rect
                className="risk-pulse"
                x="150" y="95" width="105" height="62"
                fill="url(#hatch-critical)" stroke="#AF2318" strokeWidth="1.4" strokeDasharray="7 4"
              />
              <text x="202" y="130" textAnchor="middle" fontFamily="'Spline Sans Mono Variable',monospace" fontSize="8.5" fill="#AF2318" letterSpacing="1.5">
                NO ENTRY
              </text>
              <rect
                className="risk-pulse--soft"
                x="265" y="180" width="80" height="50"
                fill="url(#hatch-warning)" stroke="#BF4E12" strokeWidth="1.2" strokeDasharray="7 4"
              />
            </g>
            {/* direct track — the wrong answer */}
            <line x1="60" y1="252" x2="366" y2="60" stroke="#5D7386" strokeWidth="1.6" strokeDasharray="2 6" opacity="0.6" />
            {/* the safe course draws itself in once, then a flowing overlay
                takes over — pathLength=100 keeps the dash math simple
                regardless of the curve's real length */}
            <path
              pathLength={100}
              d="M60 252 C 105 240 120 205 138 178 C 155 152 130 120 160 84 C 185 55 260 40 320 46 C 342 48 356 52 366 60"
              fill="none"
              stroke="#1D7A50"
              strokeWidth="3"
              strokeDasharray="100"
              strokeLinecap="round"
              className="route-draw"
            />
            <path
              className="route-flow"
              d="M60 252 C 105 240 120 205 138 178 C 155 152 130 120 160 84 C 185 55 260 40 320 46 C 342 48 356 52 366 60"
              fill="none"
              stroke="#1D7A50"
              strokeWidth="3"
              strokeDasharray="11 8"
              strokeLinecap="round"
            />
            {/* live position — a ping that actually sails the plotted course,
                looping bow to buoy, fading in and out at each end so it
                reads as a tracked vessel rather than a decoration */}
            <g aria-hidden>
              <circle className="hero-sail-ring" r="7" fill="none" stroke="#1D7A50" strokeWidth="2" />
              <circle className="hero-sail hero-sail--tail" r="4" fill="#1D7A50" />
              <circle className="hero-sail hero-sail--tail2" r="5.5" fill="#1D7A50" />
              <circle className="hero-sail hero-sail--head" r="7.5" fill="#FBF7ED" stroke="#1D7A50" strokeWidth="3" />
            </g>
            {/* boat, riding the swell */}
            <g transform="translate(60 252)">
              <g className="svg-bob">
                <circle r="22" fill="none" stroke="#2A7391" strokeWidth="1.4" opacity="0.5" />
                <circle r="15" fill="#12212D" stroke="#FBF7ED" strokeWidth="2.5" />
                <path d="M0 -8 v8 M0 -6 l5.5 6 h-5.5 z" stroke="#FBF7ED" strokeWidth="1.6" fill="#FBF7ED" />
                <path d="M-6 4 q3 2.4 6 0 t6 0" stroke="#FBF7ED" strokeWidth="1.4" fill="none" />
              </g>
            </g>
            {/* destination buoy, hailing */}
            <g transform="translate(366 60)">
              <circle className="svg-ping" r="17" fill="none" stroke="#1D7A50" strokeWidth="2" />
              <g className="svg-bob" style={{ animationDelay: "1.2s" }}>
                <circle r="17" fill="#FBF7ED" stroke="#1D7A50" strokeWidth="4" />
                <text y="6" textAnchor="middle" fontFamily="'Fraunces Variable',Georgia,serif" fontWeight="800" fontSize="16" fill="#12212D">
                  1
                </text>
              </g>
            </g>
            <text x="392" y="64" fontFamily="'Fraunces Variable',Georgia,serif" fontStyle="italic" fontWeight="600" fontSize="13" fill="#1D7A50">
              82%
            </text>
            {/* compass */}
            <g transform="translate(400 250)" opacity="0.75">
              <circle r="24" fill="none" stroke="#12212D" strokeWidth="1.3" />
              <g className="compass-needle">
                <path d="M0 -20 L5 6 L0 11 L-5 6 Z" fill="#12212D" />
              </g>
              <text y="-27" textAnchor="middle" fontFamily="'Spline Sans Mono Variable',monospace" fontSize="8" fill="#12212D">
                N
              </text>
            </g>

            {/* ============ verdict panel — arrives once the course is plotted ============ */}
            <g className="hero-verdict" transform="translate(148 232)">
              <rect width="192" height="50" rx="3" fill="#FBF7ED" stroke="#1D7A50" strokeWidth="1.4" />
              <text x="10" y="16" fontFamily="'Spline Sans Mono Variable',monospace" fontSize="7.5" fill="#1D7A50" letterSpacing="1.4">
                ORCA RECOMMENDS
              </text>
              <text x="10" y="32" fontFamily="'Fraunces Variable',Georgia,serif" fontWeight="700" fontSize="13" fill="#12212D">
                Safe route found
              </text>
              <text x="10" y="44" fontFamily="'Spline Sans Mono Variable',monospace" fontSize="6.5" fill="#5D7386" letterSpacing="1">
                CONFIDENCE
              </text>
              <text x="182" y="34" textAnchor="end" fontFamily="'Fraunces Variable',Georgia,serif" fontWeight="800" fontSize="17" fill="#1D7A50">
                {heroConfidence}%
              </text>
            </g>
          </svg>
          </HeroArt>
        </Reveal>
      </div>

      {/* scroll cue — tells the visitor there is more below the fold */}
      <Reveal delay={760} className="mt-8 flex justify-center">
        <button
          onClick={() =>
            document.getElementById("lp-more")?.scrollIntoView({ behavior: "smooth" })
          }
          className="scroll-cue flex flex-col items-center gap-1 text-ink-400 transition-colors hover:text-chart-600"
          aria-label="Scroll to see more"
        >
          <span className="font-mono text-[9px] uppercase tracking-[0.18em]">More below</span>
          <CourseArrow size={13} className="rotate-90" />
        </button>
      </Reveal>
      </div>
      {/* ================= /HERO SCREEN ================= */}

      <div id="lp-more" />

      {/* live stats strip */}
      <Reveal delay={420}>
        <div className="panel mt-12 grid grid-cols-2 sm:grid-cols-5">
          {stats.map((x, i) => (
            <div
              key={x.k}
              className={`group px-4 py-3.5 transition-colors hover:bg-chart-100/40 ${i > 0 ? "border-l" : ""}`}
              style={{ borderColor: "var(--rule-faint)" }}
            >
              <div className="label truncate !text-[9px]">{x.k}</div>
              <div
                className={`mt-1 font-mono text-[21px] font-bold tabular-nums leading-none transition-colors ${
                  x.warn ? "text-risk-extreme" : "text-ink-900 group-hover:text-chart-600"
                }`}
              >
                {x.v}
              </div>
            </div>
          ))}
        </div>
      </Reveal>

      {/* feature cards */}
      <div id="lp-features" className="mt-5 scroll-mt-20 grid gap-4 md:grid-cols-3">
        {t.cards.map((c, i) => (
          <Reveal key={cardTabs[i]} delay={520 + i * 110}>
            <div className="panel rule-double lift group flex h-full flex-col">
              <div className="hd">
                <span className="label flex items-center gap-2 transition-colors group-hover:!text-chart-600">
                  {c.kicker}
                  {i === 0 && <FishGlyph size={15} className="swim text-chart-500" />}
                </span>
              </div>
              <div className="flex-1 px-4 py-4">
                <h3 className="font-display text-[19px] font-bold leading-snug text-ink-900">
                  {c.title}
                </h3>
                <ul className="mt-3 space-y-2">
                  {c.lines.map((l) => (
                    <li key={l} className="flex gap-2.5 text-[12.5px] leading-relaxed text-ink-700">
                      <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rotate-45 bg-chart-500/70 transition-transform group-hover:rotate-[135deg] group-hover:bg-chart-500" style={{ transitionDuration: "500ms" }} />
                      {l}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="border-t px-4 py-3" style={{ borderColor: "var(--rule-faint)" }}>
                <button onClick={() => onEnter(cardTabs[i])} className="btn-line group/open w-full justify-center">
                  {t.openWord}{" "}
                  <CourseArrow size={12} className="transition-transform group-hover/open:translate-x-1" />
                </button>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      {/* how it decides — the differentiator */}
      <Reveal delay={880}>
        <div id="lp-pipeline" className="panel mt-5 scroll-mt-20 overflow-hidden">
          <div className="hd">
            <span className="label">{t.pipelineTitle}</span>
            <button
              onClick={() => onEnter("system")}
              className="font-mono text-[10px] font-bold uppercase tracking-[0.1em] text-chart-600 underline decoration-dashed underline-offset-4 transition-colors hover:text-ink-900"
            >
              {t.watchLive}
            </button>
          </div>
          <div className="grid sm:grid-cols-4">
            {t.phases.map((p, i) => (
              <div
                key={p.t}
                className={`group relative px-4 py-3.5 transition-colors hover:bg-chart-100/40 ${i > 0 ? "sm:border-l" : ""}`}
                style={{ borderColor: "var(--rule-faint)" }}
              >
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-[15px] font-bold text-ink-900">{p.t}</span>
                  {i === 1 && (
                    <span className="font-mono text-[9px] font-bold text-chart-700">∥ 5</span>
                  )}
                </div>
                <p className="mt-1 text-[11.5px] italic leading-snug text-ink-500">{p.n}</p>
                {i < 3 && (
                  <CourseArrow
                    size={13}
                    className="absolute -right-1.5 top-1/2 hidden -translate-y-1/2 text-ink-300 transition-all group-hover:translate-x-0.5 group-hover:text-chart-600 sm:block"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </Reveal>

      {/* footer */}
      <Reveal delay={980}>
        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 pb-4">
          <span className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-ink-400">
            {t.footer}
          </span>
          <div className="flex items-center gap-4">
            {/* language — lives here now, not in the navbar: it's a set-once
                preference, not something reached for on every visit */}
            <span className="flex gap-1">
              {(["en", "hi", "mr"] as Language[]).map((l) => (
                <button
                  key={l}
                  onClick={() => onLanguage(l)}
                  className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[10px] font-bold transition ${
                    language === l
                      ? "border-ink-900 bg-ink-900 text-paper-50"
                      : "text-ink-400 hover:text-ink-800"
                  }`}
                  style={language === l ? undefined : { borderColor: "var(--rule)" }}
                >
                  {l === "en" ? "EN" : l === "hi" ? "हिं" : "मरा"}
                </button>
              ))}
            </span>
            <a
              href="https://github.com/SaudSatopay/orca-sih26176"
              target="_blank"
              rel="noreferrer"
              className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-chart-600 transition-colors hover:text-ink-900"
            >
              github.com/SaudSatopay/orca-sih26176
            </a>
          </div>
        </div>
      </Reveal>
    </div>
    </>
  );
}