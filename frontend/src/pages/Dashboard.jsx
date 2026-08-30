import React, { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Circle, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { motion, AnimatePresence } from "framer-motion";
import { PawPrint, LogOut, Plus, HeartPulse, BatteryMedium, Gauge, MapPin, Radio, Trash2, Signal } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, wsURL } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Slider } from "../components/ui/slider";
import { toast } from "sonner";

delete L.Icon.Default.prototype._getIconUrl;

const petIcon = (color = "#00E5FF") =>
  L.divIcon({
    className: "",
    html: `<div class="cp-pet-marker" style="background:${color};box-shadow:0 0 0 4px ${color}33, 0 0 20px ${color};"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

function Recenter({ lat, lng, trigger }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lng], map.getZoom(), { duration: 0.6 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger]);
  return null;
}

export default function Dashboard() {
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const [pets, setPets] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [trail, setTrail] = useState([]);
  const [recenterKey, setRecenterKey] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [newPet, setNewPet] = useState({ name: "", species: "Dog", breed: "" });
  const [flash, setFlash] = useState(false);
  const wsRef = useRef(null);

  const selected = useMemo(() => pets.find((p) => p.id === selectedId) || pets[0], [pets, selectedId]);

  const loadPets = async () => {
    const { data } = await api.get("/pets");
    setPets(data.pets);
    if (data.pets.length && !selectedId) setSelectedId(data.pets[0].id);
  };

  const loadTrail = async (petId) => {
    if (!petId) return setTrail([]);
    const { data } = await api.get(`/pets/${petId}/history`);
    setTrail(data.points.map((p) => [p.lat, p.lng]));
  };

  useEffect(() => { loadPets(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { if (selected) { loadTrail(selected.id); setRecenterKey((k) => k + 1); } /* eslint-disable-next-line */ }, [selectedId]);

  // WebSocket live updates
  useEffect(() => {
    let alive = true;
    const connect = () => {
      const ws = new WebSocket(wsURL());
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type !== "pet_update") return;
          setPets((prev) => prev.map((p) => p.id === msg.pet_id ? {
            ...p, latest_lat: msg.lat, latest_lng: msg.lng, latest_bpm: msg.bpm,
            latest_battery: msg.battery, latest_speed: msg.speed,
            inside_geofence: msg.inside_geofence,
          } : p));
          if (selectedId === msg.pet_id || (!selectedId && msg.pet_id)) {
            setTrail((prev) => [...prev.slice(-99), [msg.lat, msg.lng]]);
            setFlash(true);
            setTimeout(() => setFlash(false), 500);
          }
        } catch { /* noop */ }
      };
      ws.onclose = () => { if (alive) setTimeout(connect, 1500); };
      ws.onerror = () => { try { ws.close(); } catch { /* noop */ } };
    };
    connect();
    return () => { alive = false; if (wsRef.current) try { wsRef.current.close(); } catch { /* noop */ } };
  }, [selectedId]);

  const createPet = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/pets", newPet);
      toast.success(`Enrolled ${data.pet.name}`);
      setAddOpen(false);
      setNewPet({ name: "", species: "Dog", breed: "" });
      await loadPets();
      setSelectedId(data.pet.id);
    } catch (e) {
      toast.error("Could not enroll pet");
    }
  };

  const deletePet = async (id) => {
    if (!window.confirm("Remove this collar?")) return;
    await api.delete(`/pets/${id}`);
    if (selectedId === id) setSelectedId(null);
    await loadPets();
  };

  const updateGeofence = async (radius) => {
    if (!selected) return;
    await api.patch(`/pets/${selected.id}/geofence`, {
      geofence_lat: selected.latest_lat,
      geofence_lng: selected.latest_lng,
      geofence_radius: radius,
    });
    setPets((prev) => prev.map((p) => p.id === selected.id ? { ...p, geofence_lat: selected.latest_lat, geofence_lng: selected.latest_lng, geofence_radius: radius } : p));
    toast.success(`Geofence set to ${radius}m`);
  };

  const handleLogout = () => { logout(); nav("/"); };

  return (
    <div className="min-h-screen bg-[#050505] text-white flex">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 border-r border-white/5 h-screen sticky top-0 flex flex-col cp-glass" data-testid="dashboard-sidebar">
        <div className="p-6 flex items-center gap-2.5 border-b border-white/5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#8A6E1D] flex items-center justify-center">
            <PawPrint size={14} className="text-black" />
          </div>
          <span className="tracking-widest uppercase text-sm">CoolPet</span>
        </div>

        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="cp-overline">My pets</span>
            <button
              onClick={() => setAddOpen(true)}
              className="w-7 h-7 rounded-full border border-white/15 flex items-center justify-center hover:bg-[#D4AF37] hover:text-black hover:border-[#D4AF37] transition-colors"
              data-testid="dashboard-add-pet-button"
              aria-label="Add pet"
            >
              <Plus size={14} />
            </button>
          </div>

          <div className="space-y-2" data-testid="dashboard-pet-list">
            {pets.length === 0 && (
              <div className="text-white/40 text-sm border border-dashed border-white/10 rounded-xl p-4">
                No collars enrolled yet. Add one to start streaming.
              </div>
            )}
            {pets.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                data-testid={`dashboard-pet-${p.id}`}
                className={`w-full text-left rounded-xl p-3 border transition-colors duration-300 ${
                  selected?.id === p.id ? "border-[#D4AF37]/60 bg-[#D4AF37]/5" : "border-white/5 hover:border-white/15"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: p.color + "22", border: `1px solid ${p.color}55` }}>
                    <PawPrint size={14} style={{ color: p.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{p.name}</div>
                    <div className="text-[10px] cp-mono text-white/40 truncate">IMEI · {p.imei.slice(-8)}</div>
                  </div>
                  <span onClick={(e) => { e.stopPropagation(); deletePet(p.id); }} className="opacity-0 group-hover:opacity-100 text-white/40 hover:text-[#FF3B30] cursor-pointer" data-testid={`delete-pet-${p.id}`}>
                    <Trash2 size={13} />
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-auto p-6 border-t border-white/5">
          <div className="text-xs text-white/40 mb-1 cp-mono">Signed in as</div>
          <div className="text-sm truncate">{user?.name}</div>
          <div className="text-xs text-white/40 truncate cp-mono">{user?.email}</div>
          <button
            onClick={handleLogout}
            className="mt-4 flex items-center gap-2 text-xs text-white/60 hover:text-white transition-colors"
            data-testid="dashboard-logout-button"
          >
            <LogOut size={12} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main map area */}
      <main className="flex-1 relative">
        {/* Header strip */}
        <div className="absolute top-4 left-4 right-4 z-[1000] flex items-center justify-between">
          <div className="cp-glass rounded-full px-4 py-2 flex items-center gap-3 text-sm" data-testid="dashboard-live-indicator">
            <span className="cp-pulse" />
            <span className="text-white/70">Live IoT ingestion</span>
            <span className="text-white/30">·</span>
            <span className="cp-mono text-white/50 text-xs"><Signal size={11} className="inline mr-1" />JT/T 794 · 2s</span>
          </div>
          {selected && (
            <div className="cp-glass rounded-full px-5 py-2 text-sm flex items-center gap-3">
              <MapPin size={14} className="text-[#D4AF37]" />
              <span className="cp-mono text-xs text-white/70">
                {selected.latest_lat.toFixed(5)}° · {selected.latest_lng.toFixed(5)}°
              </span>
            </div>
          )}
        </div>

        <div className="h-screen">
          <MapContainer
            center={selected ? [selected.latest_lat, selected.latest_lng] : [37.7749, -122.4194]}
            zoom={16}
            zoomControl={true}
            attributionControl={true}
            style={{ height: "100%", width: "100%" }}
            data-testid="dashboard-map"
          >
            <TileLayer
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap'
            />
            {selected && (
              <>
                <Circle
                  center={[selected.geofence_lat, selected.geofence_lng]}
                  radius={selected.geofence_radius}
                  pathOptions={{ color: "#D4AF37", weight: 1.5, fillOpacity: 0.06 }}
                />
                <Polyline positions={trail} pathOptions={{ color: "#00E5FF", weight: 2, opacity: 0.6 }} />
                <Marker
                  position={[selected.latest_lat, selected.latest_lng]}
                  icon={petIcon(selected.color)}
                />
                <Recenter lat={selected.latest_lat} lng={selected.latest_lng} trigger={recenterKey} />
              </>
            )}
          </MapContainer>
        </div>

        {/* Floating health card */}
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="absolute bottom-6 left-6 cp-glass rounded-3xl p-6 w-[360px] z-[1000]"
            data-testid="dashboard-health-card"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="cp-overline">Now tracking</span>
                <div className="mt-1 text-2xl font-light tracking-tight">{selected.name}</div>
                <div className="text-xs text-white/40 cp-mono mt-0.5">{selected.species} · {selected.breed || "—"}</div>
              </div>
              <div className={`px-3 py-1 rounded-full text-[10px] tracking-widest uppercase ${selected.inside_geofence === false ? "bg-[#FF3B30]/20 text-[#FF3B30]" : "bg-[#34C759]/15 text-[#34C759]"}`}>
                {selected.inside_geofence === false ? "OUT OF ZONE" : "SAFE"}
              </div>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3">
              <div className="cp-panel rounded-2xl p-3" data-testid="stat-bpm">
                <HeartPulse size={14} className="text-[#FF3B30] cp-heart" />
                <div className="mt-2 cp-mono text-2xl flex items-baseline gap-1">
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={selected.latest_bpm}
                      initial={{ color: "#00E5FF" }} animate={{ color: "#ffffff" }}
                      transition={{ duration: 0.6 }}
                    >{selected.latest_bpm}</motion.span>
                  </AnimatePresence>
                  <span className="text-xs text-white/40">bpm</span>
                </div>
              </div>
              <div className="cp-panel rounded-2xl p-3" data-testid="stat-battery">
                <BatteryMedium size={14} className="text-[#D4AF37]" />
                <div className="mt-2 cp-mono text-2xl flex items-baseline gap-1">
                  {selected.latest_battery}<span className="text-xs text-white/40">%</span>
                </div>
              </div>
              <div className="cp-panel rounded-2xl p-3" data-testid="stat-speed">
                <Gauge size={14} className="text-[#00E5FF]" />
                <div className="mt-2 cp-mono text-2xl flex items-baseline gap-1">
                  {selected.latest_speed.toFixed(1)}<span className="text-xs text-white/40">m/s</span>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between text-xs text-white/50">
                <span className="cp-overline text-[10px]">Geofence radius</span>
                <span className="cp-mono">{selected.geofence_radius}m</span>
              </div>
              <div className="mt-3">
                <Slider
                  data-testid="dashboard-geofence-slider"
                  value={[selected.geofence_radius]}
                  min={50} max={2000} step={25}
                  onValueChange={(v) => setPets((prev) => prev.map((p) => p.id === selected.id ? { ...p, geofence_radius: v[0] } : p))}
                  onValueCommit={(v) => updateGeofence(v[0])}
                />
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-white/5 flex items-center justify-between text-[11px] text-white/40 cp-mono">
              <span className="flex items-center gap-1.5"><Radio size={11} className={flash ? "text-[#00E5FF]" : "text-white/40"} /> Streaming</span>
              <span>IMEI · {selected.imei.slice(-10)}</span>
            </div>
          </motion.div>
        )}
      </main>

      {/* Add pet dialog */}
      {addOpen && (
        <div className="fixed inset-0 z-[2000] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.form
            onSubmit={createPet}
            initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-md cp-panel rounded-3xl p-8"
            data-testid="add-pet-dialog"
          >
            <span className="cp-overline">Enroll new collar</span>
            <h3 className="mt-3 text-2xl font-light tracking-tight">Meet your new companion</h3>

            <div className="mt-6 space-y-4">
              <div>
                <label className="text-xs uppercase tracking-widest text-white/50">Name</label>
                <input required value={newPet.name} onChange={(e) => setNewPet({ ...newPet, name: e.target.value })}
                  className="mt-2 w-full bg-transparent border-b border-white/15 focus:border-[#D4AF37] outline-none py-2 transition-colors"
                  data-testid="add-pet-name-input"
                  placeholder="Nova"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs uppercase tracking-widest text-white/50">Species</label>
                  <select
                    value={newPet.species} onChange={(e) => setNewPet({ ...newPet, species: e.target.value })}
                    className="mt-2 w-full bg-[#0F0F13] border border-white/15 rounded-lg py-2 px-2 outline-none focus:border-[#D4AF37]"
                    data-testid="add-pet-species-select"
                  >
                    <option>Dog</option><option>Cat</option><option>Other</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-widest text-white/50">Breed</label>
                  <input value={newPet.breed} onChange={(e) => setNewPet({ ...newPet, breed: e.target.value })}
                    className="mt-2 w-full bg-transparent border-b border-white/15 focus:border-[#D4AF37] outline-none py-2 transition-colors"
                    data-testid="add-pet-breed-input"
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>

            <div className="mt-8 flex items-center gap-3">
              <button type="button" onClick={() => setAddOpen(false)} className="flex-1 border border-white/15 rounded-full py-2.5 hover:bg-white/5 transition-colors" data-testid="add-pet-cancel">Cancel</button>
              <button type="submit" className="flex-1 bg-[#D4AF37] text-black rounded-full py-2.5 font-medium hover:brightness-110 transition" data-testid="add-pet-submit">Enroll</button>
            </div>
          </motion.form>
        </div>
      )}
    </div>
  );
}
