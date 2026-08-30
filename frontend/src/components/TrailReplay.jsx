import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Polyline, useMap } from "react-leaflet";
import { Play, Pause, RotateCcw, Clock } from "lucide-react";
import { Slider } from "./ui/slider";
import { api } from "../lib/api";

// Speed → color (m/s). 0 = deep cyan; 3+ = gold; 6+ = red.
const speedColor = (v) => {
  if (v == null) return "#00E5FF";
  if (v < 0.5) return "#00506A";
  if (v < 1.5) return "#00E5FF";
  if (v < 3.0) return "#D4AF37";
  return "#FF3B30";
};

/**
 * Fetches the last 24h of `petId` history, renders speed-shaded polyline
 * segments, and lets the user scrub through time with a slider.
 * onFocus(point) is called with the currently focused point so the parent
 * dashboard can move the marker.
 */
export default function TrailReplay({ petId, onFocus, onClose }) {
  const [points, setPoints] = useState([]);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const tickRef = useRef(null);
  const map = useMap();

  useEffect(() => {
    let alive = true;
    (async () => {
      const { data } = await api.get(`/pets/${petId}/history?hours=24&limit=1000`);
      if (!alive) return;
      setPoints(data.points || []);
      setIdx(Math.max(0, (data.points || []).length - 1));
    })();
    return () => { alive = false; };
  }, [petId]);

  useEffect(() => {
    if (!playing) return;
    tickRef.current = setInterval(() => {
      setIdx((i) => {
        if (i >= points.length - 1) { setPlaying(false); return i; }
        return i + 1;
      });
    }, 120);
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, [playing, points.length]);

  useEffect(() => {
    if (!points.length) return;
    const p = points[idx];
    if (!p) return;
    onFocus?.(p);
    map.panTo([p.lat, p.lng], { animate: true, duration: 0.4 });
  }, [idx, points, onFocus, map]);

  const segments = useMemo(() => {
    if (!points.length) return [];
    const out = [];
    for (let i = 1; i <= idx; i++) {
      const a = points[i - 1], b = points[i];
      out.push({
        positions: [[a.lat, a.lng], [b.lat, b.lng]],
        color: speedColor((a.speed + b.speed) / 2),
      });
    }
    return out;
  }, [points, idx]);

  const cur = points[idx];

  return (
    <>
      {segments.map((s, i) => (
        <Polyline key={i} positions={s.positions} pathOptions={{ color: s.color, weight: 3, opacity: 0.85 }} />
      ))}

      <motion.div
        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
        className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] cp-glass rounded-2xl px-6 py-4 w-[560px] max-w-[92vw]"
        data-testid="trail-replay-panel"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPlaying((p) => !p)}
              data-testid="trail-play-toggle"
              className="w-9 h-9 rounded-full bg-[#D4AF37] text-black flex items-center justify-center hover:brightness-110 hover:-translate-y-0.5 transition-transform duration-300"
              aria-label="Play/Pause"
            >
              {playing ? <Pause size={14} /> : <Play size={14} />}
            </button>
            <button
              onClick={() => { setIdx(0); setPlaying(false); }}
              className="w-9 h-9 rounded-full border border-white/15 flex items-center justify-center hover:bg-white/5 transition-colors"
              data-testid="trail-restart"
              aria-label="Restart"
            >
              <RotateCcw size={14} />
            </button>
            <div className="text-xs text-white/50 flex items-center gap-1.5 cp-mono">
              <Clock size={11} />
              {cur ? new Date(cur.timestamp).toLocaleString() : "—"}
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="trail-close"
            className="text-white/50 hover:text-white text-xs uppercase tracking-widest transition-colors"
          >
            Live view
          </button>
        </div>

        <Slider
          data-testid="trail-scrubber"
          value={[idx]} min={0} max={Math.max(0, points.length - 1)} step={1}
          onValueChange={(v) => { setIdx(v[0]); setPlaying(false); }}
        />

        <div className="mt-3 flex items-center justify-between text-[11px] text-white/40 cp-mono">
          <span>{points.length} points · 24h</span>
          {cur && <span>{cur.speed?.toFixed?.(1) ?? 0} m/s · {cur.bpm} bpm</span>}
          <span>#{idx + 1}/{points.length}</span>
        </div>
      </motion.div>
    </>
  );
}
