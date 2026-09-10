import type {
  AlertEvent,
  AuthorityDashboard,
  ChatResponse,
  DecisionState,
  FishingOutlook,
  Language,
  ORCAState,
  PositionCheck,
  RiskCategory,
  SupportedLanguage,
  TraceEntry,
  Voyage,
  ZoneFeature,
} from "./types";

const BASE = "/api";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export function ask(params: {
  message: string;
  language?: Language;
  latitude?: number;
  longitude?: number;
  locationName?: string;
  sessionId?: string;
}): Promise<ChatResponse> {
  return json<ChatResponse>(`${BASE}/chat`, {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      language: params.language ?? null,
      latitude: params.latitude ?? null,
      longitude: params.longitude ?? null,
      location_name: params.locationName ?? null,
      session_id: params.sessionId ?? "demo",
    }),
  });
}

export interface AgentEvent {
  type: "thinking" | "agent_done";
  step?: string;
  agent: string;
  label?: string;
  summary?: string;
  status?: string;
}

/** SSE streaming ask — yields agent events then the final ChatResponse. */
export async function askStream(
  params: {
    message: string;
    language?: SupportedLanguage | string;
    latitude?: number;
    longitude?: number;
    locationName?: string;
    sessionId?: string;
  },
  onEvent: (e: AgentEvent) => void,
  onDone: (res: ChatResponse) => void,
  onError: (err: string) => void,
): Promise<void> {
  try {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: params.message,
        language: params.language ?? null,
        latitude: params.latitude ?? null,
        longitude: params.longitude ?? null,
        location_name: params.locationName ?? null,
        session_id: params.sessionId ?? "demo",
      }),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const chunk of parts) {
        if (!chunk.trim()) continue;
        const eventLine = chunk.match(/^event:\s*(.+)$/m)?.[1]?.trim();
        const dataLine = chunk.match(/^data:\s*(.+)$/m)?.[1]?.trim();
        if (!eventLine || !dataLine) continue;
        const parsed = JSON.parse(dataLine);
        if (eventLine === "done") {
          onDone(parsed as ChatResponse);
        } else {
          onEvent({ type: eventLine as AgentEvent["type"], ...parsed });
        }
      }
    }
  } catch (e) {
    onError(String(e));
  }
}

export function resetSession(sessionId = "demo") {
  return json(`${BASE}/chat/reset?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
  });
}

export function zones(): Promise<{ features: ZoneFeature[]; note: string }> {
  return json(`${BASE}/map/zones`);
}

export function authority(): Promise<AuthorityDashboard> {
  return json(`${BASE}/authority/dashboard`);
}

export function riskTimeline(lat: number, lon: number, hours = 24) {
  return json<{
    points: {
      hour: number;
      time: string;
      score: number;
      category: RiskCategory;
      wave_height_m: number | null;
      wind_speed_kmh: number | null;
      warning: boolean;
    }[];
  }>(`${BASE}/risk/timeline?lat=${lat}&lon=${lon}&hours=${hours}`);
}

/** Fast geofence check — called while the vessel marker is dragged. */
export function checkPosition(lat: number, lon: number): Promise<PositionCheck> {
  return json<PositionCheck>(`${BASE}/position?lat=${lat}&lon=${lon}`);
}

/** Everything a fisher needs for a position: safety, grounds, timing, forecast. */
export function fishingOutlook(
  lat: number,
  lon: number,
  opts: { radiusKm?: number; days?: number; lang?: SupportedLanguage | string } = {},
): Promise<FishingOutlook> {
  const p = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(opts.radiusKm ?? 100),
    days: String(opts.days ?? 3),
    lang: opts.lang ?? "en",
  });
  return json<FishingOutlook>(`${BASE}/fishing?${p}`);
}

export interface Measurement {
  value: number | null;
  unit: string;
  label: string;
  provenance: {
    source: string;
    timestamp: string;
    mode: string;
    confidence: number | null;
    note?: string | null;
  };
}

export interface AgentSnapshot {
  agent: string;
  ok: boolean;
  data: Record<string, unknown>;
  measurements: Record<string, Measurement>;
  unavailable: string[];
  source: string;
  timestamp: string;
  confidence: number | null;
  mode: string;
  latency_ms: number;
}

/** One raw pull of the sea at a position — drives the System page's live feed. */
export function forecast(lat: number, lon: number) {
  return json<{
    location: { name: string; latitude: number; longitude: number; state?: string | null };
    valid_for: string;
    weather: AgentSnapshot;
    ocean: AgentSnapshot;
  }>(`${BASE}/forecast?lat=${lat}&lon=${lon}`);
}

export interface FlowField {
  mode: string;
  generated_at?: string;
  nx: number;
  ny: number;
  lats: number[];
  lons: number[];
  points: {
    sea: boolean;
    wind_u: number;
    wind_v: number;
    cur_u: number | null;
    cur_v: number | null;
    sst: number | null;
  }[];
  /** Fine land/sea mask, row-major, "1" = sea. */
  mask?: string;
  mask_nx?: number;
  mask_ny?: number;
  note?: string;
}

/** The wind/current/SST grid for a map view — drives the flow animation. */
export function flowField(
  b: { minLat: number; maxLat: number; minLon: number; maxLon: number },
  nx = 10,
  ny = 8,
): Promise<FlowField> {
  const p = new URLSearchParams({
    min_lat: b.minLat.toFixed(3),
    max_lat: b.maxLat.toFixed(3),
    min_lon: b.minLon.toFixed(3),
    max_lon: b.maxLon.toFixed(3),
    nx: String(nx),
    ny: String(ny),
  });
  return json<FlowField>(`${BASE}/field?${p}`);
}

export function setMode(mode: "LIVE" | "DEMO") {
  return json<{ ok: boolean; data_mode: string; note: string }>(`${BASE}/config/mode`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function health() {
  return json<{ status: string; data_mode: string; version: string }>(`${BASE}/health`);
}

export function config() {
  return json<{
    data_mode: string;
    risk_weights: Record<string, number>;
    risk_thresholds: Record<string, number>;
    deterministic_overrides: Record<string, number>;
    note: string;
  }>(`${BASE}/config`);
}

// --------------------------------------------------------------------------
// ORCA 2.0 Plan, Trace, Voyage, Alert & Voice Endpoints
// --------------------------------------------------------------------------

export function fetchPlan(params: {
  query?: string;
  intent_text?: string;
  language?: SupportedLanguage | string;
  location?: { lat: number; lon: number; name?: string } | null;
}): Promise<DecisionState> {
  return json<DecisionState>("/plan", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function fetchTrace(requestId: string): Promise<TraceEntry[]> {
  return json<TraceEntry[]>(`/trace/${encodeURIComponent(requestId)}`);
}

export function fetchState(requestId: string): Promise<ORCAState> {
  return json<ORCAState>(`/state/${encodeURIComponent(requestId)}`);
}

export function startVoyage(params: {
  location: { lat: number; lon: number; name?: string };
  region_geometry?: any;
  voyage_id?: string;
}): Promise<{ voyage_id: string; started_at: string; status: string; location: any }> {
  return json("/voyages/start", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getActiveVoyages(): Promise<Voyage[]> {
  return json<Voyage[]>("/voyages/active");
}

export function endVoyage(voyageId: string): Promise<{ status: string; voyage_id: string }> {
  return json(`/voyages/${encodeURIComponent(voyageId)}/end`, {
    method: "POST",
  });
}

export function triggerAlert(params: {
  voyage_id?: string;
  evidence?: any;
  advisory?: any;
  severity?: string;
  headline?: string;
}): Promise<{ alerts: AlertEvent[] }> {
  return json<{ alerts: AlertEvent[] }>("/alerts/trigger", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function transcribeVoice(
  audioBlob: Blob,
  language = "hi-IN",
): Promise<{ transcript: string; language: string; engine: string }> {
  const formData = new FormData();
  formData.append("file", audioBlob, "recording.wav");
  formData.append("language", language);

  const res = await fetch("/voice/transcribe", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.error || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function speakText(
  text: string,
  language = "hi-IN",
  voiceId = "aditya",
): Promise<Blob> {
  const res = await fetch("/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language, voice_id: voiceId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.error || `${res.status} ${res.statusText}`);
  }
  return res.blob();
}

