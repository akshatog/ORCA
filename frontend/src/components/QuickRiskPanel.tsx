/**
 * QuickRiskPanel — calls GET /api/risk and shows a full per-agent
 * risk breakdown: score, category, each contributing factor, and
 * any deterministic overrides (official warnings).
 *
 * Used in: App.tsx Home tab (compact) and SystemPanel (full).
 */
import { useEffect, useState, useCallback } from "react";
import * as api from "../api";
import type { RiskCategory } from "../types";
import RiskDial, { RISK_COLOR } from "./RiskDial";
import { WarnGlyph, LockGlyph, ClockGlyph, WaveGlyph, WindGlyph, FishGlyph } from "./glyphs";

/** Picks a small contextual icon for a free-text advice line, so the list
 * reads as more than a wall of identical bullets. Falls back to a plain
 * tick mark when nothing matches — works across en/hi/mr text. */
function adviceIcon(line: string) {
  const s = line.toLowerCase();
  if (/\d\s?(am|pm)|समय|वेळ|सुबह|सकाळ/.test(s)) return <ClockGlyph size={13} className="shrink-0" />;
  if (/wave|लहर|लाट|swell|sea/.test(s)) return <WaveGlyph size={13} className="shrink-0" />;
  if (/wind|हवा|वारा|breeze/.test(s)) return <WindGlyph size={13} className="shrink-0" />;
  if (/fish|मछली|मासे|catch/.test(s)) return <FishGlyph size={13} className="shrink-0" />;
  return <WarnGlyph size={13} className="shrink-0" />;
}

interface QuickRiskPanelProps {
  lat: number;
  lon: number;
  /** Show full factor table (default false = compact headline only) */
  full?: boolean;
}

const CATEGORY_LABEL: Record<string, string> = {
  LOW: "SAFE TO GO",
  MODERATE: "MODERATE RISK",
  HIGH: "STAY ASHORE",
  EXTREME: "DO NOT GO",
};

export default function QuickRiskPanel({ lat, lon, full = false }: QuickRiskPanelProps) {
  const [data, setData] = useState<api.RiskBreakdown | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchRisk = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.quickRisk(lat, lon);
      setData(result);
    } catch {
      // silently fail — data will be shown by FishingPanel anyway
    } finally {
      setLoading(false);
    }
  }, [lat, lon]);

  useEffect(() => {
    fetchRisk();
  }, [fetchRisk]);

  if (loading && !data) {
    return (
      <div className="panel px-4 py-3 text-[12px] italic text-ink-400">
        Computing risk…
      </div>
    );
  }

  if (!data) return null;

  const risk = data.risk;
  const cat = risk.category as RiskCategory;
  const color = RISK_COLOR[cat];

  return (
    <div
      className="panel overflow-hidden border-l-4"
      style={{ borderLeftColor: color }}
    >
      <div className="hd" style={{ borderBottom: `2px solid ${color}20`, background: `${color}0a` }}>
        <span className="label flex items-center gap-2">
          <span
            className="grid h-5 w-5 shrink-0 place-items-center rounded-full"
            style={{ color, background: `${color}18` }}
          >
            <LockGlyph size={11} />
          </span>
          Risk Assessment
        </span>
        <span
          className="stamp font-bold"
          style={{ color, border: `1px solid ${color}60`, background: `${color}12` }}
        >
          {CATEGORY_LABEL[cat] ?? cat}
        </span>
      </div>

      {/* Score — the same animated instrument dial used on the Ask tab,
          sized down for this compact card. */}
      <div className="flex items-center gap-4 px-4 pt-4 pb-1">
        <RiskDial score={risk.score} category={cat} size={92} />
        <div className="min-w-0 flex-1">
          <span className="font-mono text-[10px] uppercase tracking-wide text-ink-400">
            out of 100 · risk score
          </span>
          {risk.headline && (
            <div className="mt-1 text-[13.5px] font-semibold leading-snug text-ink-800">{risk.headline}</div>
          )}
        </div>
      </div>

      <div className="px-4 pb-1">
        {risk.official_warning && (
          <div
            className="mb-1.5 flex items-center gap-1.5 rounded-[2px] px-2 py-1 font-mono text-[11px] font-bold text-risk-extreme"
            style={{ background: "rgba(175,35,24,0.08)" }}
          >
            <WarnGlyph size={12} />
            Official advisory active
          </div>
        )}
        {risk.window && (
          <div className="flex items-center gap-1.5 text-[11.5px] italic text-ink-500">
            <ClockGlyph size={12} className="shrink-0 text-ink-400" />
            Conditions improve: {risk.window}
          </div>
        )}
      </div>

      {/* Factor breakdown — shown when full=true */}
      {full && risk.factors.length > 0 && (
        <div className="border-t px-4 pt-2 pb-3.5" style={{ borderColor: "var(--rule-faint)" }}>
          <div className="mb-2 label">Risk Factors</div>
          <div className="space-y-1.5">
            {risk.factors.map((f) => {
              const pct = Math.round(f.contribution * 100);
              return (
                <div key={f.key}>
                  <div className="flex items-center justify-between text-[11.5px]">
                    <span className="text-ink-700">{f.label}</span>
                    <span className="font-mono text-[10.5px] tabular-nums text-ink-500">
                      {pct}%
                    </span>
                  </div>
                  <div className="mt-0.5 h-1 rounded-full" style={{ background: "var(--rule-faint)" }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(100, pct)}%`,
                        background: pct > 30 ? color : "var(--chart-500)",
                      }}
                    />
                  </div>
                  {f.detail && (
                    <div className="text-[10.5px] text-ink-400">{f.detail}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Advice */}
      {risk.advice?.length > 0 && (
        <div className="border-t px-4 pt-3 pb-3.5" style={{ borderColor: "var(--rule-faint)" }}>
          <ul className="space-y-1.5">
            {risk.advice.map((tip, i) => (
              <li
                key={i}
                className="group flex items-center gap-2.5 rounded-[3px] px-2 py-1.5 text-[12px] leading-relaxed text-ink-700 transition-colors hover:bg-chart-100/35"
              >
                <span
                  className="grid h-6 w-6 shrink-0 place-items-center rounded-full transition-transform duration-200 group-hover:scale-110"
                  style={{ color, background: `${color}14` }}
                >
                  {adviceIcon(tip)}
                </span>
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div
        className="flex items-center justify-between border-t bg-paper-150/50 px-4 py-2 font-mono text-[9.5px] uppercase tracking-wide text-ink-400"
        style={{ borderColor: "var(--rule-faint)" }}
      >
        <span>{risk.sources.join(" · ")}</span>
        <span className="font-bold" style={{ color }}>{risk.mode}</span>
      </div>
    </div>
  );
}