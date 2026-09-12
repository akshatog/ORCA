import { useEffect, useRef, useState, useCallback } from "react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import type { AgentEvent } from "../api";
import type { ChatMessage, Language } from "../types";
import { BoatGlyph, CompassMark, CourseArrow, MicGlyph, SchoolGlyph, StopGlyph } from "./glyphs";

const PLACEHOLDER: Record<Language, string> = {
  en: "Ask ORCA — can I go fishing tomorrow at 6 AM?",
  hi: "ORCA se puchhen — kya main kal subah 6 baje ja sakta hun?",
  mr: "ORCA la vichara — mi udya sakali 6 vajata jau shakto ka?",
};

const T: Record<Language, Record<string, string>> = {
  en: {
    title: "Ask ORCA",
    you: "You",
    emptyMain: "Ask about safety, fishing zones, routes or warnings.",
    emptySub: "ORCA keeps context — follow-ups like what about 12 PM? work.",
  },
  hi: {
    title: "ORCA se puchhen",
    you: "Aap",
    emptyMain: "Suraksha, matsya kshetra, marg ya chetavaniyon ke bare mein puchiye.",
    emptySub: "ORCA sandarbh yaad rakhta hai.",
  },
  mr: {
    title: "ORCA la vichara",
    you: "Tumhi",
    emptyMain: "Suraksha, maseemari kshetra, marg kiva isharyanbadd vichara.",
    emptySub: "ORCA sandarbh lakshat thevate.",
  },
};

const AGENT_ICON: Record<string, string> = {
  intent: "Brain",
  weather: "Cloud",
  ocean: "Wave",
  pfz: "Fish",
  cyclone: "Cyclone",
  gis: "Map",
  risk: "Scale",
  route: "Compass",
  explanation: "Write",
  specialists: "Lightning",
};

const SPEECH_LOCALE: Record<Language, string> = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
};

function getRecognition(): any | null {
  const w = window as any;
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}

function ThinkingPanel({ events }: { events: AgentEvent[] }) {
  const thinking = events.find((e) => e.type === "thinking");
  const done = events.filter((e) => e.type === "agent_done");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [done.length]);

  return (
    <div
      className="rounded-[3px] rounded-bl-none border text-left"
      style={{ borderColor: "var(--rule)", background: "var(--paper-bright)", minWidth: 220 }}
    >
      <div className="flex items-center gap-2 border-b px-3.5 py-2" style={{ borderColor: "var(--rule-faint)" }}>
        <span className="relative flex h-3 w-3 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-chart-400 opacity-60" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-chart-600" />
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-500">
          {thinking?.step ?? "Processing..."}
        </span>
      </div>
      {done.length > 0 && (
        <div ref={ref} className="max-h-[130px] overflow-y-auto px-3.5 py-2 space-y-1.5">
          {done.map((e) => (
            <div key={e.agent} className="flex items-start gap-2 animate-rise">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[10px] font-bold text-ink-700 truncate">
                    {e.label}
                  </span>
                  <span
                    className="shrink-0 font-mono text-[8px] uppercase tracking-widest px-1 rounded"
                    style={{
                      background: e.status === "ok" ? "#d1fadf" : "#fee2e2",
                      color: e.status === "ok" ? "#166534" : "#991b1b",
                    }}
                  >
                    {e.status === "ok" ? "done" : "err"}
                  </span>
                </div>
                {e.summary && (
                  <div className="text-[10px] text-ink-400 truncate">{e.summary}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChatPanel({
  messages,
  busy,
  agentEvents,
  language,
  suggestions,
  onSend,
  onLanguage,
  onReset,
}: {
  messages: ChatMessage[];
  busy: boolean;
  agentEvents: AgentEvent[];
  language: Language;
  suggestions: string[];
  onSend: (text: string) => void;
  onLanguage: (lang: Language) => void;
  onReset?: () => void;
}) {
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, busy]);

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
      setText(said);
      submit(said);
    };
    rec.start();
  }, [language]);

  const submit = (value: string) => {
    const v = value.trim();
    if (!v || busy) return;
    window.speechSynthesis.cancel();
    onSend(v);
    setText("");
  };

  const handleReset = () => {
    window.speechSynthesis.cancel();
    if (onReset) onReset();
  };

  const { state: voiceState, toggleRecording } = useVoiceRecorder({
    language: SPEECH_LOCALE[language],
    onTranscript: (said) => {
      setText(said);
      submit(said);
    },
    onFallback: fallbackRecognition,
  });

  return (
    <div className="panel rule-double flex h-full min-h-0 flex-col">
      <div className="hd !py-3">
        <div>
          <div className="font-display text-[16px] font-bold text-ink-900">
            {(T[language] ?? T.en).title}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onReset && messages.length > 0 && (
            <button
              onClick={handleReset}
              disabled={busy}
              title="Start a new conversation"
              className="ml-1 rounded-[2px] border px-2.5 py-1 font-mono text-[11px] text-ink-400 transition hover:border-ink-700 hover:text-ink-800 disabled:opacity-40"
              style={{ borderColor: "var(--rule)" }}
            >
              New ↺
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div
            className="flex flex-col items-center gap-2.5 border border-dashed px-4 py-7 text-center text-[13px] text-ink-500"
            style={{ borderColor: "var(--rule-strong)" }}
          >
            <span className="flex items-end gap-3">
              <BoatGlyph size={26} className="text-ink-300" />
              <SchoolGlyph size={30} className="swim text-chart-300" />
            </span>
            <div>
              {(T[language] ?? T.en).emptyMain}
              <br />
              <span className="text-[11px] text-ink-400">{(T[language] ?? T.en).emptySub}</span>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] animate-rise ${m.role === "user" ? "text-right" : ""}`}>
              <div
                className={`label mb-1 flex items-center gap-1 !text-[8.5px] !tracking-[0.2em] !text-ink-300 ${
                  m.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {m.role === "user" ? (
                  (T[language] ?? T.en).you
                ) : (
                  <>
                    <CompassMark size={10} className="shrink-0 text-chart-500" /> ORCA
                  </>
                )}
              </div>
              <div
                className={`inline-block rounded-[3px] px-3.5 py-2.5 text-left text-[13.5px] leading-relaxed ${
                  m.role === "user"
                    ? "rounded-br-none bg-ink-900 text-paper-50"
                    : "rounded-bl-none border bg-paper-bright text-ink-800"
                }`}
                style={
                  m.role === "user"
                    ? undefined
                    : { borderColor: "var(--rule)", background: "var(--paper-bright)" }
                }
              >
                {m.text}
              </div>
            </div>
          </div>
        ))}

        {busy && (
          <div className="flex justify-start">
            <div className="max-w-[92%] animate-rise">
              <div className="label mb-1 flex items-center gap-1 !text-[8.5px] !tracking-[0.2em] !text-ink-300">
                <CompassMark size={10} className="shrink-0 text-chart-500" /> ORCA
              </div>
              <ThinkingPanel events={agentEvents} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {suggestions.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5 border-t px-4 py-2.5"
          style={{ borderColor: "var(--rule-faint)" }}
        >
          {suggestions.slice(0, 4).map((s) => (
            <button key={s} className="chip !py-1 !text-[11.5px]" onClick={() => submit(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div
        className="flex items-center gap-2 border-t p-3"
        style={{ borderColor: "var(--rule-faint)" }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit(text)}
          placeholder={PLACEHOLDER[language]}
          disabled={busy}
          className="field min-w-0 flex-1"
        />
        {true && (
          <button
            onClick={toggleRecording}
            title="Speak"
            className={`grid h-10 w-10 shrink-0 place-items-center rounded-[2px] border transition hover:-translate-y-px ${
              voiceState === "recording"
                ? "border-risk-extreme bg-risk-extreme text-paper-50"
                : voiceState === "processing"
                ? "border-chart-400 bg-chart-400 text-paper-50"
                : "border-ink-900 bg-paper-50 text-ink-900 hover:bg-ink-900 hover:text-paper-50"
            }`}
            style={voiceState === "recording" || voiceState === "processing" ? { animation: "inkblink 1.2s ease-in-out infinite" } : undefined}
          >
            {voiceState === "recording" ? <StopGlyph size={12} /> : voiceState === "processing" ? <span className="animate-spin text-xs">...</span> : <MicGlyph size={17} />}
          </button>
        )}
        <button
          onClick={() => submit(text)}
          disabled={busy || !text.trim()}
          title="Send"
          className="group grid h-10 w-10 shrink-0 place-items-center rounded-[2px] bg-ink-900 text-paper-50 transition hover:-translate-y-px hover:bg-ink-700 disabled:opacity-35"
        >
          <CourseArrow size={17} className="transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}
