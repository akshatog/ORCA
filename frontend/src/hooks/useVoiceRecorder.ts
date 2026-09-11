import { useState, useRef, useCallback } from "react";
import { transcribeVoice } from "../api";

export type VoiceRecorderState = "idle" | "recording" | "processing" | "error";

interface UseVoiceRecorderProps {
  language: string; // e.g. "hi-IN"
  onTranscript: (text: string) => void;
  onFallback: () => void;
}

// ---------------------------------------------------------------------------
// WAV encoder — converts a decoded AudioBuffer to a 16-bit PCM WAV blob.
// No external libraries needed: WAV is a simple container format.
// ---------------------------------------------------------------------------
function encodeWav(audioBuffer: AudioBuffer): Blob {
  const numChannels = 1; // mono
  const sampleRate = audioBuffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  // Downmix to mono by averaging all input channels
  const length = audioBuffer.length;
  const samples = new Float32Array(length);
  for (let ch = 0; ch < audioBuffer.numberOfChannels; ch++) {
    const channelData = audioBuffer.getChannelData(ch);
    for (let i = 0; i < length; i++) {
      samples[i] += channelData[i] / audioBuffer.numberOfChannels;
    }
  }

  // Convert float32 → int16 with clipping
  const pcm = new Int16Array(length);
  for (let i = 0; i < length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  const dataByteLength = pcm.byteLength;
  const buffer = new ArrayBuffer(44 + dataByteLength);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  const u16 = (offset: number, v: number) => view.setUint16(offset, v, true);
  const u32 = (offset: number, v: number) => view.setUint32(offset, v, true);

  writeStr(0, "RIFF");
  u32(4, 36 + dataByteLength);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  u32(16, 16);
  u16(20, format);
  u16(22, numChannels);
  u32(24, sampleRate);
  u32(28, sampleRate * numChannels * (bitDepth / 8)); // byte rate
  u16(32, numChannels * (bitDepth / 8));              // block align
  u16(34, bitDepth);
  writeStr(36, "data");
  u32(40, dataByteLength);

  // Write PCM samples
  const pcmView = new Uint8Array(buffer, 44);
  pcmView.set(new Uint8Array(pcm.buffer));

  return new Blob([buffer], { type: "audio/wav" });
}

// ---------------------------------------------------------------------------
// Convert any audio blob (webm, mp4, ogg…) → WAV blob via Web Audio API.
// Sarvam Saaras v3 only accepts: audio/wav, audio/mp3, audio/ogg.
// Chrome MediaRecorder defaults to audio/webm;codecs=opus — we must convert.
// ---------------------------------------------------------------------------
async function convertToWav(inputBlob: Blob): Promise<Blob> {
  const arrayBuffer = await inputBlob.arrayBuffer();
  // Prefer 16 kHz for Sarvam (speech model), fall back to browser default
  const audioCtx = new AudioContext({ sampleRate: 16000 });
  try {
    const decoded = await audioCtx.decodeAudioData(arrayBuffer);
    return encodeWav(decoded);
  } finally {
    audioCtx.close();
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useVoiceRecorder({ language, onTranscript, onFallback }: UseVoiceRecorderProps) {
  const [state, setState] = useState<VoiceRecorderState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Pick the best available format. webm/opus is preferred for quality;
      // we'll convert it to WAV before uploading. mp4 and ogg are also fine.
      let options: MediaRecorderOptions | undefined;
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        options = { mimeType: "audio/webm;codecs=opus" };
      } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
        options = { mimeType: "audio/mp4" };
      } else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
        options = { mimeType: "audio/ogg;codecs=opus" };
      }

      const recorder = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setState("processing");

        const rawType = options?.mimeType || "audio/webm";
        const rawBlob = new Blob(audioChunksRef.current, { type: rawType });

        try {
          // Always convert to WAV — Sarvam Saaras v3 rejects audio/webm.
          const wavBlob = await convertToWav(rawBlob);
          const res = await transcribeVoice(wavBlob, language);
          setState("idle");
          onTranscript(res.transcript);
        } catch (convertOrUploadErr: any) {
          console.warn("Sarvam STT failed (will use browser SpeechRecognition fallback):", convertOrUploadErr);
          setState("error");
          setErrorMessage("Voice recognition failed — trying browser fallback…");
          setTimeout(() => setErrorMessage(null), 4000);
          onFallback();
        }
      };

      recorder.start(100); // collect chunks every 100 ms
      mediaRecorderRef.current = recorder;
      setState("recording");
      setErrorMessage(null);

      // Hard cap at 20 seconds
      timerRef.current = window.setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
        }
      }, 20000);
    } catch (err: any) {
      console.error("Failed to start MediaRecorder:", err);
      setState("error");
      setErrorMessage("Microphone access denied or unavailable.");
      setTimeout(() => setErrorMessage(null), 5000);
      onFallback();
    }
  }, [language, onTranscript, onFallback]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const toggleRecording = useCallback(() => {
    if (state === "recording") {
      stopRecording();
    } else if (state === "idle" || state === "error") {
      startRecording();
    }
  }, [state, startRecording, stopRecording]);

  return { state, errorMessage, toggleRecording };
}
