import { WarnGlyph } from "./glyphs";

function PhoneGlyph({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
      <line x1="12" y1="18" x2="12.01" y2="18" strokeWidth="2" />
    </svg>
  );
}

function ShareGlyph({ size = 20, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

import { useState, useRef } from "react";
export default function EmergencyModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [holdProgress, setHoldProgress] = useState(0);
  const holdTimer = useRef<number | null>(null);

  if (!isOpen) return null;

  const handleShare = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const text = `Emergency! My current location is: https://maps.google.com/?q=${pos.coords.latitude},${pos.coords.longitude}`;
          if (navigator.share) {
            navigator.share({
              title: "Emergency Location",
              text: text,
            }).catch(console.error);
          } else {
            window.location.href = `sms:?body=${encodeURIComponent(text)}`;
          }
        },
        () => {
          alert("Could not get location. Please enable location services.");
        }
      );
    } else {
      alert("Geolocation is not supported by this browser.");
    }
  };

  const startHold = () => {
    let progress = 0;
    // 20ms interval, +2% each tick = 1000ms (1 second to hold)
    holdTimer.current = window.setInterval(() => {
      progress += 2;
      setHoldProgress(progress);
      if (progress >= 100) {
        clearInterval(holdTimer.current!);
        holdTimer.current = null;
        alert("DEMO: Nearest station has been notified!");
        setHoldProgress(0);
        onClose();
      }
    }, 20);
  };

  const stopHold = () => {
    if (holdTimer.current) {
      clearInterval(holdTimer.current);
      holdTimer.current = null;
    }
    setHoldProgress(0);
  };


  return (
    <div className="fixed inset-0 z-[800] flex items-center justify-center bg-ink-900/50 p-4 backdrop-blur-sm">
      <div className="popin relative w-full max-w-[380px] rounded-[3px] bg-paper-50 p-6 shadow-2xl">
        <h2 className="flex items-center gap-2 font-display text-[26px] font-black tracking-tight text-risk-extreme">
          <WarnGlyph size={24} /> Emergency
        </h2>

        <div className="mt-5 space-y-3">
          <a
            href="tel:1554"
            className="flex items-center gap-3 rounded-[3px] bg-risk-extreme px-4 py-3.5 transition-transform active:scale-[0.98]"
          >
            <PhoneGlyph size={26} className="text-paper-50" />
            <div>
              <div className="font-display text-[18px] font-bold leading-tight text-paper-50">
                Call Coast Guard · 1554
              </div>
              <div className="mt-1 font-mono text-[11px] text-paper-50/80">
                Toll-free · 1554 · opens your dialer
              </div>
            </div>
          </a>

          <button
            onClick={handleShare}
            className="flex w-full items-center gap-3 rounded-[3px] border-[1.5px] border-ink-900 bg-paper-50 px-4 py-3.5 text-left transition-transform active:scale-[0.98]"
          >
            <ShareGlyph size={26} className="text-ink-900" />
            <div>
              <div className="font-display text-[18px] font-bold leading-tight text-ink-900">
                Share my location
              </div>
              <div className="mt-1 font-mono text-[11px] text-ink-500">
                Sends position + conditions via SMS/WhatsApp
              </div>
            </div>
          </button>
        </div>

        <div className="my-7 flex items-center gap-3">
          <span className="h-px flex-1 bg-rule-faint" style={{ background: "var(--rule-faint)" }} />
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink-400">
            OR SIMULATE AUTOMATIC DISPATCH
          </span>
          <span className="h-px flex-1 bg-rule-faint" style={{ background: "var(--rule-faint)" }} />
        </div>

        <div className="flex flex-col items-center">
          <button
            onPointerDown={startHold}
            onPointerUp={stopHold}
            onPointerLeave={stopHold}
            className="relative grid h-[120px] w-[120px] place-items-center overflow-hidden rounded-full border-[6px] border-[#5D7386] bg-paper-50 text-center font-mono text-[11px] font-bold uppercase leading-tight tracking-[0.15em] text-ink-900 transition-transform active:scale-95"
          >
            <div
              className="absolute bottom-0 left-0 right-0 bg-[#5D7386]/20 transition-all duration-75"
              style={{ height: `${holdProgress}%` }}
            />
            <span className="relative z-10">
              HOLD TO<br />NOTIFY<br />NEAREST<br />STATION
            </span>
          </button>
          <div className="mt-5 font-mono text-[11px] text-ink-500">
            DEMO — hold to notify nearest station
          </div>
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full rounded-[3px] border-[1.5px] border-ink-200 py-3.5 font-mono text-[13px] font-bold uppercase tracking-wider text-ink-900 transition-colors active:bg-paper-150 hover:bg-paper-150"
        >
          CANCEL
        </button>
      </div>
    </div>
  );
}
