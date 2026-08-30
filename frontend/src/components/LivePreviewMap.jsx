import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { wsURL } from "../lib/api";

// Suppress default marker icon 404s
delete L.Icon.Default.prototype._getIconUrl;

const petIcon = (color = "#00E5FF") =>
  L.divIcon({
    className: "",
    html: `<div class="cp-pet-marker" style="background:${color};box-shadow:0 0 0 4px ${color}33, 0 0 20px ${color};"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

function Recenter({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], map.getZoom(), { animate: true });
  }, [lat, lng, map]);
  return null;
}

/**
 * Read-only preview map used on landing page.
 * Subscribes to WebSocket and follows the demo device broadcast.
 */
export default function LivePreviewMap() {
  const [pos, setPos] = useState({ lat: 37.7749, lng: -122.4194, bpm: 92 });
  const wsRef = useRef(null);

  useEffect(() => {
    let alive = true;
    const connect = () => {
      try {
        const ws = new WebSocket(wsURL());
        wsRef.current = ws;
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === "demo_device" || msg.type === "pet_update") {
              setPos({ lat: msg.lat, lng: msg.lng, bpm: msg.bpm });
            }
          } catch { /* noop */ }
        };
        ws.onclose = () => { if (alive) setTimeout(connect, 2000); };
        ws.onerror = () => { try { ws.close(); } catch { /* noop */ } };
      } catch { /* noop */ }
    };
    connect();
    return () => { alive = false; if (wsRef.current) try { wsRef.current.close(); } catch { /* noop */ } };
  }, []);

  return (
    <MapContainer
      center={[pos.lat, pos.lng]}
      zoom={16}
      zoomControl={false}
      attributionControl={true}
      style={{ height: "100%", width: "100%" }}
      scrollWheelZoom={false}
    >
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap'
      />
      <Circle center={[pos.lat, pos.lng]} radius={80} pathOptions={{ color: "#00E5FF", weight: 1, fillOpacity: 0.08 }} />
      <Marker position={[pos.lat, pos.lng]} icon={petIcon("#00E5FF")} />
      <Recenter lat={pos.lat} lng={pos.lng} />
    </MapContainer>
  );
}
