import React from "react";
import type { AlertEvent, Language } from "../types";

interface Props {
  alert: AlertEvent | null;
  onDismiss?: () => void;
  onDivert?: (port: { name: string; lat: number; lon: number }) => void;
  language?: Language;
}

export default function AlertBanner({ alert, onDismiss, onDivert, language = "en" }: Props) {
  if (!alert) return null;

  const isUnsafe = alert.new_status === "UNSAFE" || alert.new_status === "EXTREME";

  return (
    <div
      role="alert"
      className={`border-b-2 px-4 py-3 shadow-md transition-all animate-fadeIn ${
        isUnsafe
          ? "bg-[#7a1c1c] text-[#fdf6f0] border-[#d32f2f]"
          : "bg-[#8a5314] text-[#fffdf7] border-[#f57c00]"
      }`}
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="p-1.5 bg-white/10 rounded-full flex-shrink-0 mt-0.5">
            <svg className="w-5 h-5 text-yellow-300 animate-bounce" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>

          <div className="space-y-0.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-serif font-black uppercase text-xs tracking-wider bg-black/30 px-2 py-0.5 rounded border border-white/20">
                CRITICAL AT-SEA DETERIORATION
              </span>
              <span className="text-xs font-mono font-bold">
                Voyage {alert.voyage_id}: {alert.previous_status} → {alert.new_status}
              </span>
            </div>
            <p className="text-xs font-medium text-white/90 max-w-3xl">
              {alert.reason}
            </p>
          </div>
        </div>

        {/* Emergency safe port diversion action */}
        <div className="flex items-center gap-2 ml-auto">
          {alert.safe_port && (
            <div className="bg-black/40 px-3 py-1.5 rounded border border-white/20 text-xs flex items-center gap-2.5">
              <div className="text-right">
                <div className="text-[10px] uppercase text-yellow-300 font-bold">Recommended Safe Port</div>
                <div className="font-serif font-bold text-white">
                  {alert.safe_port.name} ({alert.safe_port.distance_km.toFixed(1)} km)
                </div>
              </div>
              {onDivert && (
                <button
                  onClick={() => onDivert(alert.safe_port)}
                  className="px-2.5 py-1 bg-yellow-400 hover:bg-yellow-300 text-black font-bold text-xs rounded transition-colors"
                >
                  Divert Course
                </button>
              )}
            </div>
          )}

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 hover:bg-white/20 rounded text-white/80 hover:text-white transition-colors"
              title="Acknowledge & Dismiss"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
