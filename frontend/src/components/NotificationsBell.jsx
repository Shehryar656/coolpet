import React, { useEffect, useState } from "react";
import { Bell, Check, AlertTriangle, LogIn as LogInIcon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../lib/api";
import { toast } from "sonner";

/**
 * Notifications bell with a dropdown of geofence breach events.
 * Listens to the parent-passed `latestBreach` prop (from WebSocket in Dashboard)
 * to flash a toast and refresh the list.
 */
export default function NotificationsBell({ latestBreach }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);

  const load = async () => {
    try {
      const { data } = await api.get("/breaches?limit=30");
      setItems(data.breaches);
    } catch { /* noop */ }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!latestBreach) return;
    // toast + refresh
    toast(
      `${latestBreach.pet_name} ${latestBreach.event === "exit" ? "left" : "returned to"} their zone`,
      {
        description: `${latestBreach.lat.toFixed(5)}°, ${latestBreach.lng.toFixed(5)}°`,
        icon: latestBreach.event === "exit"
          ? <AlertTriangle size={16} className="text-[#FF3B30]" />
          : <LogInIcon size={16} className="text-[#34C759]" />,
      }
    );
    load();
  }, [latestBreach]);

  const unread = items.filter((i) => !i.read).length;

  const markAllRead = async () => {
    await api.post("/breaches/read-all");
    load();
  };
  const markOneRead = async (id) => {
    await api.patch(`/breaches/${id}/read`);
    load();
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="cp-glass rounded-full px-3.5 py-2 flex items-center gap-2 text-sm hover:bg-white/10 transition-colors"
        data-testid="notifications-bell"
        aria-label="Notifications"
      >
        <Bell size={14} className={unread > 0 ? "text-[#D4AF37]" : "text-white/60"} />
        {unread > 0 && (
          <span className="cp-mono text-[10px] bg-[#FF3B30] text-white rounded-full px-1.5 py-0.5 leading-none" data-testid="notifications-count">
            {unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="absolute top-12 right-0 w-[380px] cp-panel rounded-2xl shadow-2xl overflow-hidden z-[1500]"
            data-testid="notifications-panel"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
              <span className="cp-overline">Breach feed</span>
              {unread > 0 && (
                <button onClick={markAllRead} className="text-[11px] text-[#D4AF37] hover:underline" data-testid="notifications-mark-all-read">
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-[360px] overflow-y-auto no-scrollbar">
              {items.length === 0 ? (
                <div className="p-8 text-center text-white/40 text-sm">No breach events yet. Every zone is quiet.</div>
              ) : (
                items.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => markOneRead(b.id)}
                    data-testid={`breach-${b.id}`}
                    className={`w-full text-left px-4 py-3 flex items-start gap-3 border-b border-white/5 hover:bg-white/[0.03] transition-colors ${!b.read ? "bg-white/[0.02]" : ""}`}
                  >
                    <div className="mt-0.5">
                      {b.event === "exit"
                        ? <AlertTriangle size={16} className="text-[#FF3B30]" />
                        : <LogInIcon size={16} className="text-[#34C759]" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm">
                        <span style={{ color: b.pet_color }}>{b.pet_name}</span>
                        <span className="text-white/60"> {b.event === "exit" ? "left the safe zone" : "returned to the zone"}</span>
                      </div>
                      <div className="cp-mono text-[10px] text-white/40 mt-1">
                        {b.lat.toFixed(4)}°, {b.lng.toFixed(4)}° · {new Date(b.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                    {!b.read && <span className="cp-pulse mt-2" />}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
