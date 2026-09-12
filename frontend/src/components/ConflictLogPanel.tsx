import React from "react";
import type { Language } from "../types";

export interface ConflictRecord {
  metric: string;
  contending_sources: string[];
  winner_source: string;
  winner_authority: string;
  reason: string;
  candidates?: {
    source: string;
    value: any;
    unit?: string;
    authority?: string;
  }[];
}

interface Props {
  conflicts: ConflictRecord[];
  language?: Language;
}

export default function ConflictLogPanel({ conflicts, language = "en" }: Props) {
  return (
    <div className="bg-[#fcfaf4] border border-[#d6cfbe] rounded-lg p-4 shadow-sm text-[#1b2b34] font-sans">
      <div className="border-b border-[#e5dfd0] pb-3 mb-4">
        <h3 className="font-serif text-lg font-bold tracking-wide flex items-center gap-2 text-[#12212d]">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#c62828]"></span>
          Observational Conflict Resolution Log
        </h3>
        <p className="text-xs text-[#556975] mt-0.5">
          Deterministic authority arbitration across disparate telemetry, buoys, satellite retrievals, and regulatory bulletins.
        </p>
        
        {/* Tier hierarchy badge row */}
        <div className="flex flex-wrap gap-2 mt-2.5 pt-2 border-t border-[#eee7d8] text-[10px] text-[#425460]">
          <span className="font-semibold text-[#12212d]">Hierarchy:</span>
          <span className="bg-[#fdf2e9] text-[#9c4221] px-1.5 py-0.5 rounded border border-[#f5c6aa]">
            1. Official Regulatory (IMD/INCOIS)
          </span>
          <span>&gt;</span>
          <span className="bg-[#edf7ed] text-[#1e4620] px-1.5 py-0.5 rounded border border-[#c8e6c9]">
            2. In-Situ Buoy / StormGlass
          </span>
          <span>&gt;</span>
          <span className="bg-[#e8f4fd] text-[#0d3c61] px-1.5 py-0.5 rounded border border-[#b8dcf8]">
            3. Numerical Forecast (Open-Meteo)
          </span>
          <span>&gt;</span>
          <span className="bg-[#f5f5f5] text-[#616161] px-1.5 py-0.5 rounded border border-[#e0e0e0]">
            4. Crowd / Heuristic
          </span>
        </div>
      </div>

      {conflicts.length === 0 ? (
        <div className="text-center py-8 text-xs text-[#2e7d32] bg-[#f4faf4] border border-dashed border-[#c8e6c9] rounded flex flex-col items-center gap-1.5">
          <svg className="w-5 h-5 text-[#2e7d32]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-semibold">Zero Discrepancies Detected</span>
          <span className="text-[#556975] text-[11px]">All sensors, forecasts, and regulatory models are in complete mathematical consensus.</span>
        </div>
      ) : (
        <div className="space-y-3">
          {conflicts.map((item, idx) => (
            <div
              key={idx}
              className="bg-white border border-[#e2dacb] rounded-md p-3.5 shadow-sm space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f0eae0] pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-xs uppercase tracking-wider text-[#9c4221] bg-[#fdf2e9] px-2 py-0.5 rounded border border-[#f5c6aa]">
                    Conflict #{idx + 1}
                  </span>
                  <span className="font-serif font-bold text-sm text-[#12212d] capitalize">
                    {item.metric?.replace(/_/g, " ")} Disagreement
                  </span>
                </div>
                <span className="text-[11px] font-mono text-[#556975]">
                  Contenders: {item.contending_sources.join(" vs ")}
                </span>
              </div>

              {/* Candidates comparative breakdown */}
              {item.candidates && item.candidates.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  {item.candidates.map((cand, cIdx) => {
                    const isWinner = cand.source === item.winner_source;
                    return (
                      <div
                        key={cIdx}
                        className={`p-2 rounded border text-xs flex items-center justify-between ${
                          isWinner
                            ? "bg-[#edf7ed] border-[#c8e6c9] text-[#1e4620]"
                            : "bg-[#fafafa] border-[#e0e0e0] text-[#757575] opacity-80"
                        }`}
                      >
                        <div className="flex flex-col">
                          <span className="font-semibold flex items-center gap-1.5">
                            {isWinner && (
                              <svg className="w-3.5 h-3.5 text-[#2e7d32]" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                            )}
                            {cand.source}
                          </span>
                          <span className="text-[10px] text-[#616161]">
                            {cand.authority?.replace(/_/g, " ") || "reported"}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className={`font-mono font-bold ${!isWinner ? "line-through" : ""}`}>
                            {cand.value} {cand.unit || ""}
                          </span>
                          <div className="text-[10px]">
                            {isWinner ? (
                              <span className="font-bold text-[#1b5e20]">SELECTED</span>
                            ) : (
                              <span className="text-[#9e9e9e]">Overridden</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Rationale explanation */}
              <div className="bg-[#fcfaf4] border border-[#ece4d5] rounded p-2 text-xs text-[#3e515d]">
                <span className="font-semibold text-[#12212d]">Resolution Mandate: </span>
                <span>{item.reason}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
