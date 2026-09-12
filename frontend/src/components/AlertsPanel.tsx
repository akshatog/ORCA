/**
 * AlertsPanel — displays live marine + geofence alerts from GET /api/alerts.
 * Used in both the desktop Home tab and MobileApp Today tab.
 */
import { useEffect, useState, useCallback } from "react";
import * as api from "../api";
import { CheckGlyph, WarnGlyph } from "./glyphs";

interface AlertsPanelProps {
  lat: number;
  lon: number;
  /** Auto-refresh interval in ms. Default: 60000 (1 min). Pass 0 to disable. */
  refreshMs?: number;
  compact?: boolean;
}

const SEV_COLOR: Record<string, string> = {
  critical: "var(--risk-extreme)",
  warning: "var(--risk-high)",
  info: "var(--risk-moderate)",
  EXTREME: "var(--risk-extreme)",
  HIGH: "var(--risk-high)",
  MODERATE: "var(--risk-moderate)",
  LOW: "var(--risk-low)",
};

export default function AlertsPanel({ lat, lon, refreshMs = 60_000, compact = false }: AlertsPanelProps) {
  const [data, setData] = useState<api.LocationAlerts | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState(0);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.locationAlerts(lat, lon);
      setData(result);
      setLastFetch(Date.now());
    } catch {
      // silently fail — alerts are supplemental info
    } finally {
      setLoading(false);
    }
  }, [lat, lon]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  useEffect(() => {
    if (!refreshMs) return;
    const id = setInterval(fetchAlerts, refreshMs);
    return () => clearInterval(id);
  }, [fetchAlerts, refreshMs]);

  const marine = data?.marine_alerts ?? [];
  const geofence = data?.geofence_alerts ?? [];
  const totalAlerts = marine.length + geofence.filter((g) => g.severity !== "info").length;

  if (loading && !data) {
    return (
      <div className="panel flex items-center gap-3 px-4 py-3.5">
        <span className="text-[12px] italic text-ink-400">Checking for marine warnings…</span>
      </div>
    );
  }

  if (totalAlerts === 0 && geofence.length === 0) {
    if (compact) return null; // hide when clear in compact mode
    return (
      <div className="panel animate-rise flex items-center gap-3 overflow-hidden px-4 py-3.5" style={{ borderLeft: "3px solid var(--risk-low)" }}>
        <span className="popin grid h-8 w-8 shrink-0 place-items-center rounded-full bg-risk-low/15 text-risk-low">
          <CheckGlyph size={15} />
        </span>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold text-risk-low">No active marine warnings</div>
          {lastFetch > 0 && (
            <div className="font-mono text-[10px] text-ink-400">
              Checked {new Date(lastFetch).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="panel rule-double animate-rise overflow-hidden" style={{ borderTopColor: "var(--risk-extreme)" }}>
      <div className="hd border-risk-extreme/25">
        <span className="label flex items-center gap-2" style={{ color: "var(--risk-extreme)" }}>
          <WarnGlyph size={13} />
          Marine Warnings
        </span>
        <span className="font-mono text-[10px] text-ink-400">
          {totalAlerts} active
        </span>
      </div>

      <div className={`space-y-2 px-4 ${compact ? "py-2" : "py-3.5"}`}>
        {marine.map((alert, i) => (
          <div
            key={i}
            className="rounded-[2px] border px-3 py-2.5"
            style={{
              borderColor: SEV_COLOR[alert.severity] || "var(--rule)",
              background: `color-mix(in srgb, ${SEV_COLOR[alert.severity] || "transparent"} 6%, transparent)`,
            }}
          >
            <div
              className="font-display text-[13.5px] font-bold leading-snug"
              style={{ color: SEV_COLOR[alert.severity] || "inherit" }}
            >
              {alert.headline}
            </div>
            {!compact && (
              <div className="mt-1 text-[11.5px] leading-relaxed text-ink-600">
                {alert.detail}
              </div>
            )}
            <div className="mt-1 font-mono text-[10px] uppercase tracking-wide text-ink-400">
              {alert.source}
              {alert.severity && ` · ${alert.severity}`}
              {alert.valid_till && ` · till ${alert.valid_till}`}
              {alert.official && (
                <span className="ml-2 rounded-[2px] bg-ink-800 px-1 py-0.5 text-paper-50">
                  OFFICIAL
                </span>
              )}
            </div>
          </div>
        ))}

        {geofence
          .filter((g) => g.severity !== "info")
          .map((g, i) => (
            <div
              key={`gf-${i}`}
              className="rounded-[2px] border px-3 py-2"
              style={{
                borderColor: SEV_COLOR[g.severity] || "var(--rule)",
                background: `color-mix(in srgb, ${SEV_COLOR[g.severity] || "transparent"} 5%, transparent)`,
              }}
            >
              <div
                className="text-[12.5px] font-semibold"
                style={{ color: SEV_COLOR[g.severity] || "inherit" }}
              >
                ⚓ {g.zone_name}
              </div>
              <div className="text-[11.5px] text-ink-600">{g.message}</div>
              <div className="font-mono text-[10px] text-ink-400">
                {g.distance_km.toFixed(1)} km · {g.zone_type}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}