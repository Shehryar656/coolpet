import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { PawPrint } from "lucide-react";

export default function TopNav({ hideCTA = false }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="fixed top-0 inset-x-0 z-50"
      data-testid="top-nav"
    >
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="cp-glass rounded-full flex items-center justify-between px-5 py-2.5">
          <Link to="/" className="flex items-center gap-2.5 group" data-testid="nav-logo">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#8A6E1D] flex items-center justify-center">
              <PawPrint size={16} strokeWidth={2} className="text-black" />
            </div>
            <span className="text-[15px] tracking-widest uppercase font-medium">CoolPet</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <a href="#features" className="hover:text-white transition-colors duration-300" data-testid="nav-features">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors duration-300" data-testid="nav-pricing">Pricing</a>
            <a href="#download" className="hover:text-white transition-colors duration-300" data-testid="nav-download">Mobile</a>
          </nav>

          {!hideCTA && (
            <div className="flex items-center gap-3">
              <Link to="/login" className="text-sm text-white/70 hover:text-white hidden sm:inline transition-colors" data-testid="nav-login">Sign in</Link>
              <Link
                to="/signup"
                className="text-sm bg-[#D4AF37] text-black px-4 py-2 rounded-full font-medium hover:brightness-110 hover:-translate-y-0.5 transition-transform duration-300"
                data-testid="nav-signup"
              >
                Get access
              </Link>
            </div>
          )}
        </div>
      </div>
    </motion.header>
  );
}
