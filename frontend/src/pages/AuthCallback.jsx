import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PawPrint, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

/**
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 *
 * Consumes the `#session_id=…` fragment set by auth.emergentagent.com after a
 * successful Google sign-in, exchanges it with the backend for an authenticated
 * session cookie, then navigates to /dashboard.
 */
export default function AuthCallback() {
  const location = useLocation();
  const nav = useNavigate();
  const { applyUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      nav("/login", { replace: true });
      return;
    }
    const sessionId = decodeURIComponent(match[1]);

    (async () => {
      try {
        const { data } = await api.post("/auth/google/session", { session_id: sessionId });
        applyUser?.(data.user);
        // scrub the hash so the token isn't kept in browser history
        window.history.replaceState(null, "", window.location.pathname);
        toast.success(`Welcome, ${data.user.name.split(" ")[0]}.`);
        nav("/dashboard", { replace: true, state: { user: data.user } });
      } catch (e) {
        toast.error("Google sign-in failed. Please try again.");
        nav("/login", { replace: true });
      }
    })();
  }, [location, nav, applyUser]);

  return (
    <div className="min-h-screen cp-radial-gold flex items-center justify-center">
      <div className="cp-glass rounded-3xl px-10 py-8 flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#8A6E1D] flex items-center justify-center">
          <PawPrint size={20} className="text-black" />
        </div>
        <div className="flex items-center gap-2 text-white/70 text-sm">
          <Loader2 size={14} className="animate-spin text-[#D4AF37]" />
          Finalising sign-in…
        </div>
      </div>
    </div>
  );
}
