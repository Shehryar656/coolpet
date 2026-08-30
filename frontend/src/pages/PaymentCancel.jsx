import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { X } from "lucide-react";

export default function PaymentCancel() {
  return (
    <div className="min-h-screen cp-radial-gold flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="cp-glass rounded-3xl p-10 max-w-md w-full text-center"
        data-testid="payment-cancel-card"
      >
        <div className="w-16 h-16 mx-auto rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
          <X size={26} className="text-white/60" />
        </div>
        <h1 className="mt-6 text-3xl font-light tracking-tight">Checkout paused</h1>
        <p className="mt-4 text-white/60 text-sm">
          No charge was applied. Your collar's still ready when you are.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/" className="text-white/60 text-sm hover:text-white transition-colors" data-testid="cancel-back-home">Back home</Link>
          <Link to="/#pricing" className="bg-[#D4AF37] text-black rounded-full px-5 py-2.5 font-medium text-sm hover:brightness-110 transition" data-testid="cancel-see-plans">
            See plans again
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
