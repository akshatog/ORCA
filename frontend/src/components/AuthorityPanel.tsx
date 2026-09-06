import { useEffect, useState } from "react";
import * as api from "../api";
import type { AuthorityDashboard, Language } from "../types";
import { CrosshairGlyph, LockGlyph, WarnGlyph } from "./glyphs";
import { RISK_COLOR } from "./RiskDial";

const T: Record<Language, Record<string, string>> = {
  en: {
    centres: "Landing centres",
    extreme: "Extreme risk",
    high: "High risk",
    warnings: "Official warnings",
    board: "Coastal risk board",
    refresh: "refreshes every 30 s",
    export: "Export CSV",
    hCentre: "Landing centre",
    hState: "State",
    hRisk: "Risk",
    hWave: "Wave",
    hWind: "Wind",
    hWarning: "Active warning",
    loading: "Loading coastline…",
  },
  hi: {
    centres: "लैंडिंग सेंटर",
    extreme: "अत्यधिक जोखिम",
    high: "उच्च जोखिम",
    warnings: "आधिकारिक चेतावनियाँ",
    board: "तटीय जोखिम बोर्ड",
    refresh: "हर 30 सेकंड में ताज़ा",
    export: "CSV निर्यात",
    hCentre: "लैंडिंग सेंटर",
    hState: "राज्य",
    hRisk: "जोखिम",
    hWave: "लहर",
    hWind: "हवा",
    hWarning: "सक्रिय चेतावनी",
    loading: "तटरेखा लोड हो रही है…",
  },
  mr: {
    centres: "लँडिंग सेंटर",
    extreme: "अत्यंत धोका",
    high: "जास्त धोका",
    warnings: "अधिकृत इशारे",
    board: "किनारी धोका फलक",
    refresh: "दर ३० सेकंदांनी ताजे",
    export: "CSV निर्यात",
    hCentre: "लँडिंग सेंटर",
    hState: "राज्य",
    hRisk: "धोका",
    hWave: "लाट",
    hWind: "वारा",
    hWarning: "सक्रिय इशारा",
    loading: "किनारपट्टी लोड होत आहे…",
  },
};

/** The board as a CSV file — the format an administration actually circulates. */
function exportCsv(data: AuthorityDashboard) {
  const q = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const rows = [
    ["Landing centre", "State", "Risk score", "Category", "Official warning",
     "Wave (m)", "Wind (km/h)", "Active warning"].join(","),
    ...data.locations.map((r) =>
      [q(r.name), q(r.state), r.risk_score, r.risk_category,
       r.official_warning ? "YES" : "", r.wave_height_m ?? "",
       r.wind_speed_kmh ?? "", q(r.headline)].join(","),
    ),
    "",
    q(`Generated ${data.generated_at} IST by ORCA (SIH26176). Demo / simulated data is labelled — this sheet is decision support, not an official advisory.`),
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([rows], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `orca-coastal-risk-board-${data.generated_at.slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * The district-administration view: every monitored landing centre, ranked by
 * risk. Same engine, same evidence — one screen that shows ORCA scales beyond
 * a single fisher to the people who issue the warnings.
 */
export default function AuthorityPanel({ language = "en" }: { language?: Language }) {
  const t = T[language] ?? T.en;
  const [data, setData] = useState<AuthorityDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .authority()
        .then((d) => alive && setData(d))
        .catch((e) => alive && setError(String(e)));
    load();
    const timer = setInterval(load, 30_000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  if (error)
    return <div className="panel p-6 text-sm text-risk-extreme">Failed to load: {error}</div>;
  if (!data) return <div className="panel p-6 text-sm italic text-ink-400">{t.loading}</div>;

  const tiles = [
    { key: "monitored", label: t.centres, color: "#1E5F7A", icon: <CrosshairGlyph size={13} /> },
    { key: "extreme", label: t.extreme, color: RISK_COLOR.EXTREME, icon: <WarnGlyph size={13} /> },
    { key: "high", label: t.high, color: RISK_COLOR.HIGH, icon: <WarnGlyph size={13} /> },
    { key: "official_warnings", label: t.warnings, color: "#A17000", icon: <LockGlyph size={12} /> },
  ];

  return (
    <div className="space-y-4">
      <div className="panel grid grid-cols-2 overflow-hidden sm:grid-cols-4">
        {tiles.map((tile, i) => (
          <div
            key={tile.key}
            className={`group px-5 py-4 transition-colors hover:bg-chart-100/40 ${i > 0 ? "border-l" : ""}`}
            style={{ borderColor: "var(--rule-faint)", borderTop: `2px solid ${tile.color}` }}
          >
            <div
              className="font-display text-[34px] font-black leading-none tabular-nums"
              style={{ color: tile.color }}
            >
              {data.summary[tile.key] ?? 0}
            </div>
            <div className="label mt-1.5 flex items-center gap-1.5">
              <span className="shrink-0 opacity-70" style={{ color: tile.color }}>
                {tile.icon}
              </span>
              {tile.label}
            </div>
          </div>
        ))}
      </div>

      <div className="panel rule-double overflow-hidden">
        <div className="hd">
          <span className="label">{t.board}</span>
          <span className="flex items-center gap-3">
            <span className="font-mono text-[10px] tabular-nums text-ink-400">
              {data.generated_at.slice(0, 16).replace("T", " ")} IST · {t.refresh}
            </span>
            {/* The day's advisory board as a file the administration can circulate. */}
            <button
              onClick={() => exportCsv(data)}
              className="btn-line !px-2.5 !py-1 !text-[9.5px]"
              title="Download the board as a CSV advisory sheet"
            >
              {t.export}
            </button>
          </span>
        </div>
        <div className="max-h-[520px] overflow-auto">
          <table className="w-full min-w-[640px] border-separate border-spacing-0 text-left text-[12.5px]">
            <thead>
              <tr>
                {[t.hCentre, t.hState, t.hRisk, t.hWave, t.hWind, t.hWarning].map((h, i) => (
                  <th
                    key={h}
                    className={`sticky top-0 z-10 border-b bg-paper-50/95 py-2.5 font-mono text-[9px] font-bold uppercase tracking-[0.14em] text-ink-400 backdrop-blur-sm ${
                      i === 0 ? "pl-4 pr-3" : i === 5 ? "px-4" : "px-3"
                    }`}
                    style={{ borderColor: "var(--rule-strong)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.locations.map((row, ri) => {
                const color = RISK_COLOR[row.risk_category];
                const critical = row.risk_category === "EXTREME" || row.risk_category === "HIGH";
                return (
                  <tr
                    key={row.name}
                    className={`border-b transition last:border-0 hover:bg-paper-150 ${
                      ri % 2 === 1 ? "bg-paper-100/50" : ""
                    }`}
                    style={{ borderColor: "var(--rule-faint)" }}
                  >
                    <td
                      className="relative py-2.5 pl-4 pr-3 font-display text-[13.5px] font-bold text-ink-900"
                      style={critical ? { boxShadow: `inset 3px 0 0 ${color}` } : undefined}
                    >
                      {row.name}
                    </td>
                    <td className="px-3 py-2.5 text-ink-500">{row.state}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span
                          className="font-mono text-[13px] font-bold tabular-nums"
                          style={{ color }}
                        >
                          {row.risk_score}
                        </span>
                        <span className="risk-chip" style={{ color, borderColor: color }}>
                          {row.risk_category}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-ink-800">
                      {row.wave_height_m ?? "—"} m
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-ink-800">
                      {row.wind_speed_kmh ?? "—"} km/h
                    </td>
                    <td className="max-w-[280px] truncate px-4 py-2.5 text-[12px] text-ink-500">
                      {row.headline ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}