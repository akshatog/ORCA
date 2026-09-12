import React, { useState } from "react";
import type { Evidence_v2, Language } from "../types";

interface Props {
  evidence: Evidence_v2[];
  language?: Language;
  onRefresh?: () => void;
  isLoading?: boolean;
}

const AUTHORITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  official_advisory: { bg: "#fdf2e9", text: "#9c4221", border: "#f5c6aa" },
  official_forecast: { bg: "#edf7ed", text: "#1e4620", border: "#c8e6c9" },
  external_forecast: { bg: "#e8f4fd", text: "#0d3c61", border: "#b8dcf8" },
  derived: { bg: "#f3e8fd", text: "#4a154b", border: "#e1bee7" },
  heuristic: { bg: "#f5f5f5", text: "#616161", border: "#e0e0e0" },
};

const MODE_COLORS: Record<string, { bg: string; text: string }> = {
  LIVE: { bg: "#d4edda", text: "#155724" },
  CACHED: { bg: "#fff3cd", text: "#856404" },
  STALE: { bg: "#f8d7da", text: "#721c24" },
  DEMO: { bg: "#e2e3e5", text: "#383d41" },
};

export default function EvidenceProvenancePanel({
  evidence,
  language = "en",
  onRefresh,
  isLoading = false,
}: Props) {
  const [filterAuthority, setFilterAuthority] = useState<string>("all");
  const [filterMode, setFilterMode] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filtered = evidence.filter((item) => {
    if (filterAuthority !== "all" && item.authority_level !== filterAuthority) return false;
    if (filterMode !== "all" && item.mode !== filterMode) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchMetric = item.metric.toLowerCase().includes(q);
      const matchSource = item.source.toLowerCase().includes(q);
      return matchMetric || matchSource;
    }
    return true;
  });

  return (
    <div className="bg-[#fcfaf4] border border-[#d6cfbe] rounded-lg p-4 shadow-sm text-[#1b2b34] font-sans">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5dfd0] pb-3 mb-4">
        <div>
          <h3 className="font-serif text-lg font-bold tracking-wide flex items-center gap-2 text-[#12212d]">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#2a7391]"></span>
            Evidence Provenance & Audit Trail
          </h3>
          <p className="text-xs text-[#556975]">
            Multi-source observational evidence with authority ranking, calibration confidence, and freshness telemetry.
          </p>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="px-3 py-1 text-xs font-medium rounded border border-[#2a7391] text-[#2a7391] hover:bg-[#2a7391] hover:text-white transition-colors disabled:opacity-50"
          >
            {isLoading ? "Syncing…" : "Sync Evidence"}
          </button>
        )}
      </div>

      {/* Filter and Search Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
        <input
          type="text"
          placeholder="Filter by metric or source…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-3 py-1.5 text-xs bg-white border border-[#d6cfbe] rounded focus:outline-none focus:border-[#2a7391]"
        />
        <select
          value={filterAuthority}
          onChange={(e) => setFilterAuthority(e.target.value)}
          className="px-2 py-1.5 text-xs bg-white border border-[#d6cfbe] rounded focus:outline-none focus:border-[#2a7391]"
        >
          <option value="all">All Authority Levels</option>
          <option value="official_advisory">Official Advisory (Tier 1)</option>
          <option value="official_forecast">Official Forecast (Tier 2)</option>
          <option value="external_forecast">External Forecast (Tier 3)</option>
          <option value="derived">Derived / Inferred</option>
          <option value="heuristic">Heuristic Default</option>
        </select>
        <select
          value={filterMode}
          onChange={(e) => setFilterMode(e.target.value)}
          className="px-2 py-1.5 text-xs bg-white border border-[#d6cfbe] rounded focus:outline-none focus:border-[#2a7391]"
        >
          <option value="all">All Freshness Modes</option>
          <option value="LIVE">LIVE Only</option>
          <option value="CACHED">CACHED Only</option>
          <option value="STALE">STALE Only</option>
          <option value="DEMO">DEMO Only</option>
        </select>
      </div>

      {/* Evidence Table / Cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-8 text-xs text-[#70808b] bg-white/60 border border-dashed border-[#d6cfbe] rounded">
          No evidence records match the current filter criteria.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#e5dfd0] bg-[#f2ecde] text-[#3e515d] uppercase tracking-wider font-semibold">
                <th className="py-2 px-3">Metric</th>
                <th className="py-2 px-3">Value</th>
                <th className="py-2 px-3">Source & Authority</th>
                <th className="py-2 px-3">Confidence</th>
                <th className="py-2 px-3">Freshness</th>
                <th className="py-2 px-3">Observed At</th>
                <th className="py-2 px-3">Conflict State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ece6d8]">
              {filtered.map((item, idx) => {
                const authStyle = AUTHORITY_COLORS[item.authority_level] || AUTHORITY_COLORS.heuristic;
                const modeStyle = MODE_COLORS[item.mode] || MODE_COLORS.DEMO;
                const confPct = Math.round(item.confidence * 100);

                return (
                  <tr key={idx} className="hover:bg-white/80 transition-colors">
                    <td className="py-2.5 px-3 font-semibold text-[#12212d] capitalize">
                      {item.metric?.replace(/_/g, " ")}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-[#1b2b34]">
                      {typeof item.value === "object"
                        ? JSON.stringify(item.value)
                        : `${item.value} ${item.unit || ""}`}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-[#12212d]">{item.source}</span>
                        <span
                          className="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium border"
                          style={{
                            backgroundColor: authStyle.bg,
                            color: authStyle.text,
                            borderColor: authStyle.border,
                          }}
                        >
                          {item.authority_level?.replace(/_/g, " ").toUpperCase()}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="w-24">
                        <div className="flex justify-between text-[10px] text-[#556975] mb-0.5 font-mono">
                          <span>{confPct}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-[#e0d9cb] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              confPct >= 80
                                ? "bg-[#2e7d32]"
                                : confPct >= 50
                                ? "bg-[#f57c00]"
                                : "bg-[#c62828]"
                            }`}
                            style={{ width: `${confPct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-[10px] font-bold"
                        style={{
                          backgroundColor: modeStyle.bg,
                          color: modeStyle.text,
                        }}
                      >
                        {item.mode}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[#556975] font-mono text-[11px]">
                      {new Date(item.observed_at || item.retrieved_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="py-2.5 px-3">
                      {item.conflict_status ? (
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            item.conflict_status === "selected"
                              ? "bg-green-100 text-green-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                          title={item.conflict_reason || ""}
                        >
                          {item.conflict_status.toUpperCase()}
                        </span>
                      ) : (
                        <span className="text-[#a0aab0] text-[10px]">Uncontested</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
