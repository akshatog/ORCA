import React, { useState } from "react";
import type { Language, Voyage } from "../types";

interface Props {
  activeVoyages: Voyage[];
  onStartVoyage: (location: { name?: string; lat: number; lon: number }) => Promise<void>;
  onEndVoyage: (voyageId: string) => Promise<void>;
  onTriggerTestAlert?: (voyageId: string) => Promise<void>;
  currentPort: { name: string; lat: number; lon: number };
  language?: Language;
  isLoading?: boolean;
}

export default function VoyageTracker({
  activeVoyages,
  onStartVoyage,
  onEndVoyage,
  onTriggerTestAlert,
  currentPort,
  language = "en",
  isLoading = false,
}: Props) {
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const handleStart = async () => {
    setActionInProgress("start");
    try {
      await onStartVoyage(currentPort);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleEnd = async (id: string) => {
    setActionInProgress(`end-${id}`);
    try {
      await onEndVoyage(id);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleAlert = async (id: string) => {
    if (!onTriggerTestAlert) return;
    setActionInProgress(`alert-${id}`);
    try {
      await onTriggerTestAlert(id);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="bg-[#fcfaf4] border border-[#d6cfbe] rounded-lg p-4 shadow-sm text-[#1b2b34] font-sans">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e5dfd0] pb-3 mb-4">
        <div>
          <h3 className="font-serif text-lg font-bold tracking-wide flex items-center gap-2 text-[#12212d]">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#1b5e20] animate-pulse"></span>
            Active Fleet Voyage Tracking & Deterioration Monitor
          </h3>
          <p className="text-xs text-[#556975]">
            Continuous at-sea monitoring with automatic diversion calculation to the nearest safe port upon severe weather alerts.
          </p>
        </div>

        <button
          onClick={handleStart}
          disabled={isLoading || actionInProgress === "start"}
          className="px-3.5 py-1.5 bg-[#2a7391] hover:bg-[#205971] text-white text-xs font-semibold rounded shadow-sm transition-colors disabled:opacity-50 flex items-center gap-1.5"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          {actionInProgress === "start" ? "Starting…" : `Start Voyage from ${currentPort.name}`}
        </button>
      </div>

      {activeVoyages.length === 0 ? (
        <div className="text-center py-8 text-xs text-[#70808b] bg-white/70 border border-dashed border-[#d6cfbe] rounded p-6">
          <svg className="w-8 h-8 text-[#9eaab2] mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <div className="font-semibold text-sm text-[#12212d] mb-1">No Active Monitored Voyages</div>
          <p className="max-w-md mx-auto text-[#556975]">
            When vessels cast off, start tracking here to enable automated real-time alerts if offshore conditions deteriorate.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {activeVoyages.map((voyage) => {
            const locName = voyage.location?.name || `${voyage.location?.lat.toFixed(3)}, ${voyage.location?.lon.toFixed(3)}`;
            const startTime = new Date(voyage.started_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            });
            const lastStatus = voyage.last_decision?.status || "SAFE";

            return (
              <div
                key={voyage.voyage_id}
                className="bg-white border border-[#e2dacb] rounded-md p-3.5 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between border-b border-[#f0eae0] pb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    <span className="font-mono font-bold text-xs text-[#12212d]">
                      {voyage.voyage_id}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                      lastStatus === "SAFE"
                        ? "bg-green-100 text-green-800"
                        : lastStatus === "CAUTION"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {lastStatus}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[#70808b] block text-[10px] uppercase font-semibold">Origin / Sector</span>
                    <span className="font-serif font-bold text-[#12212d]">{locName}</span>
                  </div>
                  <div>
                    <span className="text-[#70808b] block text-[10px] uppercase font-semibold">Cast Off Time</span>
                    <span className="font-mono text-[#12212d]">{startTime}</span>
                  </div>
                  <div>
                    <span className="text-[#70808b] block text-[10px] uppercase font-semibold">Position</span>
                    <span className="font-mono text-[11px] text-[#556975]">
                      {voyage.location?.lat.toFixed(4)}°N, {voyage.location?.lon.toFixed(4)}°E
                    </span>
                  </div>
                  <div>
                    <span className="text-[#70808b] block text-[10px] uppercase font-semibold">Monitor Mode</span>
                    <span className="font-semibold text-[#2a7391]">Active Beacon</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#f0eae0]">
                  {onTriggerTestAlert && (
                    <button
                      onClick={() => handleAlert(voyage.voyage_id)}
                      disabled={actionInProgress === `alert-${voyage.voyage_id}`}
                      className="px-2.5 py-1 text-[11px] font-medium rounded border border-[#c62828] text-[#c62828] hover:bg-[#c62828] hover:text-white transition-colors disabled:opacity-50"
                      title="Simulate sudden IMD storm advisory to trigger emergency diversion"
                    >
                      {actionInProgress === `alert-${voyage.voyage_id}` ? "Injecting Alert…" : "Simulate Storm Alert"}
                    </button>
                  )}

                  <button
                    onClick={() => handleEnd(voyage.voyage_id)}
                    disabled={actionInProgress === `end-${voyage.voyage_id}`}
                    className="px-3 py-1 text-[11px] font-medium rounded border border-[#70808b] text-[#556975] hover:bg-[#70808b] hover:text-white transition-colors disabled:opacity-50 ml-auto"
                  >
                    {actionInProgress === `end-${voyage.voyage_id}` ? "Ending…" : "End Voyage"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
