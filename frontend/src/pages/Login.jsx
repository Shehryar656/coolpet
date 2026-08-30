import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowUpRight, PawPrint } from "lucide-react";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import GoogleAuthButton from "../components/GoogleAuthButton";

export default function Login() {
  const nav = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back.");
      nav("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex cp-radial-gold">
      <div className="hidden md:flex w-1/2 relative overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `linear-gradient(45deg, rgba(5,5,5,0.85), rgba(5,5,5,0.4)), url(https://images.unsplash.com/photo-1477936432016-8172ed08637e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwyfHxlbGVnYW50JTIwZG9nJTIwcG9ydHJhaXQlMjBkYXJrJTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3ODgwOTk1MjZ8MA&ixlib=rb-4.1.0&q=85)`,
            backgroundSize: "cover", backgroundPosition: "center",
          }}
        />
        <div className="relative z-10 p-12 flex flex-col justify-between text-white">
          <Link to="/" className="flex items-center gap-2.5" data-testid="login-logo">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#8A6E1D] flex items-center justify-center">
              <PawPrint size={16} className="text-black" />
            </div>
            <span className="tracking-widest uppercase text-sm">CoolPet</span>
          </Link>
          <div>
            <p className="cp-overline">Concierge access</p>
            <h2 className="mt-3 text-4xl font-light tracking-tight max-w-md">
              Sign back into the quiet reassurance of knowing.
            </h2>
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <motion.form
          onSubmit={submit}
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="w-full max-w-md cp-glass rounded-3xl p-10"
          data-testid="login-form"
        >
          <span className="cp-overline">Welcome back</span>
          <h1 className="mt-3 text-3xl font-light tracking-tight">Sign in</h1>

          <div className="mt-8 space-y-5">
            <div>
              <label className="text-xs uppercase tracking-widest text-white/50">Email</label>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full bg-transparent border-b border-white/15 focus:border-[#D4AF37] outline-none py-2 text-white placeholder:text-white/30 transition-colors"
                placeholder="you@coolpet.io"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-widest text-white/50">Password</label>
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="mt-2 w-full bg-transparent border-b border-white/15 focus:border-[#D4AF37] outline-none py-2 text-white placeholder:text-white/30 transition-colors"
                placeholder="••••••••"
                data-testid="login-password-input"
              />
            </div>
          </div>

          <button
            type="submit" disabled={busy}
            className="mt-10 w-full bg-[#D4AF37] text-black py-3 rounded-full font-medium hover:brightness-110 hover:-translate-y-0.5 transition-transform duration-300 flex items-center justify-center gap-2 disabled:opacity-60"
            data-testid="login-submit-button"
          >
            {busy ? "Signing in…" : "Sign in"} <ArrowUpRight size={16} />
          </button>

          <div className="mt-6 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] uppercase tracking-widest text-white/40">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>
          <div className="mt-4">
            <GoogleAuthButton testId="login-google-button" />
          </div>

          <p className="mt-6 text-sm text-white/50">
            No account yet?{" "}
            <Link to="/signup" className="text-[#D4AF37] hover:underline" data-testid="login-signup-link">Create one</Link>
          </p>
        </motion.form>
      </div>
    </div>
  );
}
