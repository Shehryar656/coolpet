import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, PawPrint, Loader2 } from "lucide-react";
import { api } from "../lib/api";

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sid = params.get("session_id");
  const [status, setStatus] = useState("polling");
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!sid) { setStatus("error"); return; }
    let alive = true;
    const poll = async () => {
      try {
        const { data } = await api.get(`/payments/status/${sid}`);
        if (!alive) return;
        if (data.payment_status === "paid") setStatus("paid");
        else if (["expired", "failed"].includes(data.payment_status)) setStatus("failed");
        else if (attempts >= 12) setStatus("timeout");
        else { setAttempts((a) => a + 1); setTimeout(poll, 2000); }
      } catch {
        if (attempts >= 12) setStatus("timeout");
        else { setAttempts((a) => a + 1); setTimeout(poll, 2000); }
      }
    };
    poll();
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid]);

  return (
    <div className="min-h-screen cp-radial-gold flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="cp-glass rounded-3xl p-10 max-w-md w-full text-center"
        data-testid="payment-success-card"
      >
        <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-[#D4AF37] to-[#8A6E1D] flex items-center justify-center">
          {status === "paid" ? <Check size={28} className="text-black" /> : <Loader2 size={26} className="text-black animate-spin" />}
        </div>
        <h1 className="mt-6 text-3xl font-light tracking-tight">
          {status === "paid" && "Membership activated"}
          {status === "polling" && "Confirming payment…"}
          {status === "failed" && "Payment could not complete"}
          {status === "timeout" && "Taking longer than expected"}
          {status === "error" && "Missing session"}
        </h1>
        <p className="mt-4 text-white/60 text-sm">
          {status === "paid" && "Your CoolPet membership is live. Head to the dashboard to enroll your first collar."}
          {status === "polling" && "Stripe is finalising the transaction. This usually takes a few seconds."}
          {status === "failed" && "No charge was applied. You can retry from the pricing section."}
          {status === "timeout" && "Refresh in a moment or return to the dashboard — the webhook will reconcile automatically."}
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/" className="text-white/60 text-sm hover:text-white transition-colors" data-testid="payment-back-home">Back home</Link>
          <Link to="/dashboard" className="bg-[#D4AF37] text-black rounded-full px-5 py-2.5 font-medium text-sm hover:brightness-110 transition" data-testid="payment-go-dashboard">
            Open dashboard
          </Link>
        </div>
        <div className="mt-6 flex items-center justify-center gap-2 text-white/30 text-[11px] cp-mono">
          <PawPrint size={11} /> {sid?.slice(0, 22)}…
        </div>
      </motion.div>
    </div>
  );
}
