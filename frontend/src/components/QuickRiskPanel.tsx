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
import { RISK_COLOR } from "./RiskDial";
import { WarnGlyph, LockGlyph } from "./glyphs";

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
    <div className="panel overflow-hidden">
      <div className="hd" style={{ borderBottom: `2px solid ${color}20` }}>
        <span className="label flex items-center gap-2">
          <span style={{ color }}><LockGlyph size={12} /></span>
          Risk Assessment
        </span>
        <span
          className="stamp font-bold"
          style={{ color, border: `1px solid ${color}60`, background: `${color}12` }}
        >
          {CATEGORY_LABEL[cat] ?? cat}
        </span>
      </div>

      {/* Score bar */}
      <div className="px-4 pt-3.5 pb-1">
        <div className="flex items-end justify-between">
          <span
            className="font-mono text-[32px] font-black leading-none tabular-nums"
            style={{ color }}
          >
            {risk.score}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wide text-ink-400">
            / 100 risk score
          </span>
        </div>
        <div
          className="mt-2 h-1.5 w-full rounded-full"
          style={{ background: "var(--rule-faint)" }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${risk.score}%`, background: color }}
          />
        </div>
        {risk.headline && (
          <div className="mt-2 text-[12.5px] font-semibold text-ink-700">{risk.headline}</div>
        )}
        {risk.official_warning && (
          <div className="mt-1.5 flex items-center gap-1.5 font-mono text-[11px] font-bold text-risk-extreme">
            <WarnGlyph size={12} />
            Official advisory active
          </div>
        )}
        {risk.window && (
          <div className="mt-1 text-[11.5px] italic text-ink-500">
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
        <div className="border-t px-4 pt-2 pb-3" style={{ borderColor: "var(--rule-faint)" }}>
          <ul className="space-y-1">
            {risk.advice.map((tip, i) => (
              <li key={i} className="flex gap-2 text-[11.5px] leading-relaxed text-ink-600">
                <span className="shrink-0 text-ink-300">▸</span>
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-4 pb-3 font-mono text-[10px] text-ink-300">
        {risk.sources.join(" · ")} · {risk.mode}
      </div>
    </div>
  );
}
