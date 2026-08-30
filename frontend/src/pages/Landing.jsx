import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { PawPrint, MapPin, HeartPulse, ShieldCheck, ArrowUpRight, Check, Apple, Play, Radio } from "lucide-react";
import TopNav from "../components/TopNav";
import LivePreviewMap from "../components/LivePreviewMap";
import { api } from "../lib/api";
import { toast } from "sonner";

const HERO_IMG = "https://images.unsplash.com/photo-1477936432016-8172ed08637e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwyfHxlbGVnYW50JTIwZG9nJTIwcG9ydHJhaXQlMjBkYXJrJTIwYmFja2dyb3VuZHxlbnwwfHx8fDE3ODgwOTk1MjZ8MA&ixlib=rb-4.1.0&q=85";
const TOPO_BG = "https://images.unsplash.com/photo-1768916321622-6418c1af5de5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA3MDR8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGRhcmslMjB0b3BvZ3JhcGhpYyUyMG1hcHxlbnwwfHx8fDE3ODgwOTk1Mzd8MA&ixlib=rb-4.1.0&q=85";
const CAT_IMG = "https://images.unsplash.com/photo-1503431128871-cd250803fa41?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwxfHxzbGVlayUyMGNhdCUyMHBvcnRyYWl0JTIwZGFya3xlbnwwfHx8fDE3ODgwOTk1MjZ8MA&ixlib=rb-4.1.0&q=85";

const tiers = [
  {
    id: "basic", name: "Basic", price: "$9", cadence: "/mo",
    tagline: "Everything to start tracking one companion.",
    perks: ["1 tracker collar", "Live GPS refresh 30s", "Basic geofence (single zone)", "Email alerts"],
  },
  {
    id: "pro", name: "Pro", price: "$19", cadence: "/mo",
    tagline: "Precision & health signals, for serious owners.",
    perks: ["Up to 3 collars", "1s live GPS + trail", "Biometric heartbeat + battery", "Multi-zone geofencing", "Push + SMS alerts"],
    featured: true,
  },
  {
    id: "advanced", name: "Advanced", price: "$39", cadence: "/mo",
    tagline: "Fleet-grade tracking for professionals.",
    perks: ["Unlimited collars", "Historical trails 12 months", "Team dashboard access", "Priority IoT ingestion", "24/7 concierge support"],
  },
];

export default function Landing() {
  const buy = async (pkg) => {
    try {
      const { data } = await api.post("/payments/checkout", {
        package_id: pkg,
        origin_url: window.location.origin,
      });
      window.location.href = data.checkout_url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Checkout failed");
    }
  };

  return (
    <div className="relative min-h-screen bg-[#050505] text-white overflow-hidden">
      <TopNav />

      {/* HERO */}
      <section className="relative pt-40 pb-32 px-6">
        <div className="absolute inset-0 cp-radial-gold" />
        <div
          className="absolute inset-y-0 right-0 w-full md:w-3/5 opacity-45"
          style={{
            backgroundImage: `linear-gradient(90deg, #050505 0%, rgba(5,5,5,0.5) 40%, transparent 100%), url(${HERO_IMG})`,
            backgroundSize: "cover", backgroundPosition: "center",
          }}
        />
        <div className="relative mx-auto max-w-7xl grid md:grid-cols-12 gap-10 items-center">
          <div className="md:col-span-7">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
              <span className="cp-overline inline-flex items-center gap-2">
                <span className="cp-pulse" /> live · precision iot tracking
              </span>
              <h1 className="mt-6 text-5xl sm:text-6xl md:text-7xl font-light tracking-tighter leading-[0.95]">
                The luxury of<br />
                <span className="italic font-normal bg-gradient-to-r from-[#F0D97A] via-[#D4AF37] to-[#8A6E1D] bg-clip-text text-transparent">
                  never losing them.
                </span>
              </h1>
              <p className="mt-6 text-white/60 text-lg max-w-xl leading-relaxed">
                CoolPet fuses gram-thin GPS collars with a concierge dashboard — biometric heartbeat,
                sub-meter GPS, and adaptive geofencing streamed live over encrypted IoT channels.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <Link
                  to="/signup"
                  data-testid="hero-cta-button"
                  className="group bg-[#D4AF37] text-black px-7 py-3.5 rounded-full font-medium flex items-center gap-2 hover:brightness-110 hover:-translate-y-0.5 transition-transform duration-300"
                >
                  Start tracking free
                  <ArrowUpRight size={16} className="group-hover:rotate-45 transition-transform duration-300" />
                </Link>
                <a
                  href="#features"
                  className="text-white/70 hover:text-white flex items-center gap-2 text-sm transition-colors"
                  data-testid="hero-secondary-link"
                >
                  See how it works
                  <ArrowUpRight size={14} />
                </a>
              </div>

              <div className="mt-14 grid grid-cols-3 gap-6 max-w-xl">
                {[
                  ["<1m", "GPS precision"],
                  ["24/7", "Heartbeat pulse"],
                  ["99.98%", "Signal uptime"],
                ].map(([k, v]) => (
                  <div key={v}>
                    <div className="cp-mono text-3xl text-white">{k}</div>
                    <div className="text-xs uppercase tracking-widest text-white/40 mt-1">{v}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          <motion.div
            className="md:col-span-5 relative"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <div className="cp-glass rounded-3xl p-1 shadow-[0_40px_80px_-40px_rgba(212,175,55,0.35)]">
              <div className="rounded-[22px] overflow-hidden h-[420px] relative">
                <LivePreviewMap />
                <div className="absolute top-4 left-4 cp-glass rounded-full px-3 py-1.5 flex items-center gap-2 text-xs">
                  <Radio size={12} className="text-[#00E5FF]" /> Simulated IoT collar · demo-001
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FEATURES — Tetris grid */}
      <section id="features" className="relative py-24 px-6">
        <div className="mx-auto max-w-7xl">
          <div className="flex items-end justify-between mb-14">
            <div>
              <span className="cp-overline">Capabilities</span>
              <h2 className="mt-3 text-4xl md:text-5xl font-light tracking-tighter">Three signals. One quiet peace of mind.</h2>
            </div>
            <div className="text-white/50 max-w-sm text-sm hidden md:block">
              Every collar is a fully connected node — GPS, LTE-M, BLE-mesh, and a medical-grade
              PPG sensor built into <span className="text-white">3.4 grams</span> of anodized alloy.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Live tracking — 8 cols */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="md:col-span-8 relative rounded-3xl overflow-hidden cp-panel p-10 md:p-12 min-h-[380px]"
              style={{ backgroundImage: `linear-gradient(180deg, rgba(15,15,19,0.9), rgba(15,15,19,0.7)), url(${TOPO_BG})`, backgroundSize: "cover" }}
              data-testid="feature-live-tracking"
            >
              <MapPin size={28} strokeWidth={1.5} className="text-[#00E5FF]" />
              <h3 className="mt-6 text-3xl md:text-4xl font-light tracking-tight">Live precision tracking</h3>
              <p className="mt-4 max-w-lg text-white/60 leading-relaxed">
                Sub-meter GPS fixes stream over a resilient TCP socket parser (JT/T 794 compatible).
                Every packet decoded, every position broadcast to your dashboard in under one second.
              </p>
              <div className="mt-8 flex items-center gap-6 text-sm">
                <span className="cp-mono text-white/70">37.7749° N</span>
                <span className="cp-mono text-white/70">−122.4194° W</span>
                <span className="cp-mono text-[#00E5FF]">0.8m ±</span>
              </div>
            </motion.div>

            {/* Biometrics — 4 cols */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="md:col-span-4 rounded-3xl cp-panel p-10 min-h-[380px] flex flex-col justify-between"
              data-testid="feature-biometrics"
            >
              <div>
                <HeartPulse size={28} strokeWidth={1.5} className="text-[#FF3B30] cp-heart" />
                <h3 className="mt-6 text-2xl font-light tracking-tight">Biometric heartbeat</h3>
                <p className="mt-4 text-white/60 text-sm leading-relaxed">
                  A medical-grade PPG on the collar's underside reads vitals every 12 seconds.
                  Anomalies trigger a private concierge alert.
                </p>
              </div>
              <div className="mt-8">
                <div className="cp-mono text-5xl">92<span className="text-lg text-white/50 ml-1">bpm</span></div>
                <div className="cp-divider mt-4" />
              </div>
            </motion.div>

            {/* Geofence — full width */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.15 }}
              className="md:col-span-12 rounded-3xl cp-panel p-10 md:p-12 relative overflow-hidden"
              data-testid="feature-geofence"
            >
              <div className="grid md:grid-cols-12 gap-10 items-center">
                <div className="md:col-span-7">
                  <ShieldCheck size={28} strokeWidth={1.5} className="text-[#D4AF37]" />
                  <h3 className="mt-6 text-3xl md:text-4xl font-light tracking-tight">Smart geofencing, redefined.</h3>
                  <p className="mt-4 max-w-2xl text-white/60 leading-relaxed">
                    Draw invisible territories — a home garden, a favourite park, a long weekend rental.
                    Adaptive Haversine radii recalibrate around signal noise so you're never woken by a false alarm.
                  </p>
                </div>
                <div className="md:col-span-5">
                  <div className="cp-glass rounded-2xl p-6">
                    <div className="flex items-center justify-between">
                      <span className="cp-overline">Zone · Garden</span>
                      <span className="cp-mono text-[#34C759]">SAFE</span>
                    </div>
                    <div className="mt-5 relative h-24">
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-24 h-24 rounded-full border border-[#D4AF37]/30 flex items-center justify-center">
                          <div className="w-14 h-14 rounded-full border border-[#D4AF37]/50 flex items-center justify-center">
                            <div className="w-3 h-3 bg-[#00E5FF] rounded-full" />
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-white/50 mt-4 cp-mono">
                      <span>300m radius</span>
                      <span>2 pets inside</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="relative py-24 px-6">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <span className="cp-overline">Membership</span>
            <h2 className="mt-3 text-4xl md:text-5xl font-light tracking-tighter">Elegant plans, no invisible fees.</h2>
            <p className="mt-4 text-white/60">Cancel anytime. Every plan includes the collar's IoT gateway, live map, and encrypted history.</p>
          </div>

          <div className="mt-14 grid md:grid-cols-3 gap-6">
            {tiers.map((t) => {
              const Card = (
                <div className={`h-full cp-panel rounded-3xl p-8 flex flex-col ${t.featured ? "" : "hover:-translate-y-1 transition-transform duration-500"}`}>
                  <div className="flex items-center justify-between">
                    <span className="cp-overline">{t.name}</span>
                    {t.featured && <span className="text-[10px] bg-[#D4AF37]/15 text-[#D4AF37] px-2 py-1 rounded-full tracking-widest">MOST LOVED</span>}
                  </div>
                  <div className="mt-6 flex items-baseline gap-1">
                    <span className="text-5xl font-light tracking-tighter">{t.price}</span>
                    <span className="text-white/50 text-sm">{t.cadence}</span>
                  </div>
                  <p className="mt-3 text-white/60 text-sm">{t.tagline}</p>
                  <ul className="mt-8 space-y-3 flex-1">
                    {t.perks.map((p) => (
                      <li key={p} className="flex items-start gap-3 text-sm text-white/70">
                        <Check size={16} className="mt-0.5 text-[#D4AF37] shrink-0" />
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={() => buy(t.id)}
                    data-testid={`pricing-${t.id}-tier-button`}
                    className={`mt-8 w-full py-3 rounded-full font-medium transition-all duration-300 ${
                      t.featured
                        ? "bg-[#D4AF37] text-black hover:brightness-110 hover:-translate-y-0.5"
                        : "border border-white/15 text-white hover:bg-white/5"
                    }`}
                  >
                    Choose {t.name}
                  </button>
                </div>
              );
              return t.featured ? (
                <div key={t.id} className="cp-pro-border">
                  <div className="cp-pro-inner">{Card}</div>
                </div>
              ) : (
                <div key={t.id}>{Card}</div>
              );
            })}
          </div>
        </div>
      </section>

      {/* DOWNLOAD CTA */}
      <section id="download" className="relative py-28 px-6">
        <div className="mx-auto max-w-7xl">
          <div className="cp-glass rounded-3xl overflow-hidden grid md:grid-cols-12 items-center">
            <div className="md:col-span-7 p-10 md:p-14">
              <span className="cp-overline">Pocket concierge</span>
              <h2 className="mt-4 text-3xl md:text-5xl font-light tracking-tighter">
                Their whereabouts,<br /> gently, on your wrist.
              </h2>
              <p className="mt-5 text-white/60 max-w-lg">
                The CoolPet mobile companion mirrors your dashboard, with haptic geofence alerts and
                a bottom-sheet biometric drawer designed for one-handed elegance.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <button data-testid="cta-app-store" className="flex items-center gap-3 bg-black border border-white/15 rounded-2xl px-5 py-3 hover:bg-white/5 transition-colors">
                  <Apple size={22} />
                  <div className="text-left leading-tight">
                    <div className="text-[10px] text-white/50 uppercase tracking-widest">Download on the</div>
                    <div className="text-sm">App Store</div>
                  </div>
                </button>
                <button data-testid="cta-play-store" className="flex items-center gap-3 bg-black border border-white/15 rounded-2xl px-5 py-3 hover:bg-white/5 transition-colors">
                  <Play size={22} />
                  <div className="text-left leading-tight">
                    <div className="text-[10px] text-white/50 uppercase tracking-widest">Get it on</div>
                    <div className="text-sm">Google Play</div>
                  </div>
                </button>
              </div>
            </div>
            <div className="md:col-span-5 relative min-h-[300px]">
              <div
                className="absolute inset-0"
                style={{
                  backgroundImage: `linear-gradient(270deg, transparent, rgba(5,5,5,0.6) 40%, #050505 100%), url(${CAT_IMG})`,
                  backgroundSize: "cover", backgroundPosition: "center",
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-white/5 py-10 px-6">
        <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 text-white/60 text-sm">
            <PawPrint size={14} className="text-[#D4AF37]" />
            <span className="cp-mono">CoolPet · {new Date().getFullYear()}</span>
          </div>
          <div className="text-white/40 text-xs cp-mono">Precision IoT for beloved companions.</div>
        </div>
      </footer>
    </div>
  );
}
