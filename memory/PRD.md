# CoolPet — Product Requirements

**Original problem statement**: Premium luxury Pet Tracking SaaS ("Omni-Track", renamed to **CoolPet**) featuring landing page, dashboard with live Leaflet map, JWT auth, Stripe checkout, HEX-packet IoT ingestion, and a React Native mobile scaffold. Dark-mode luxury aesthetic with glassmorphism and gold/cyan accents.

## Stack (adapted)
- **Frontend**: React (CRA + craco), Tailwind, shadcn/ui, Framer Motion, react-leaflet + OpenStreetMap (dark-inverted), sonner toasts.
- **Backend**: FastAPI + Motor (MongoDB), JWT (pyjwt + bcrypt), `emergentintegrations` Stripe (Flow B with `sk_test_emergent`), WebSocket broadcast.
- **Mobile scaffold**: React Native / Expo files at `/app/mobile-app` (non-running).

## User personas
1. **Premium pet owner** — wants elegant, worry-free live tracking + biometrics for 1–3 pets.
2. **Professional / breeder / kennel** — needs fleet-grade unlimited-collar dashboard.
3. **IoT integrator** — needs a reliable HEX/JT-T-794-style ingestion endpoint.

## Core requirements (static)
- Luxury dark-mode landing (Hero, Features tetris grid, Pricing 3 tiers, App/Play CTA).
- JWT auth (signup/login/me), password bcrypt-hashed.
- Pets CRUD, geofence PATCH, location history.
- IoT `/api/iot/ingest` HEX parser (start=0x24, IMEI 8B, lat/lng ×1e6 i32, bpm u16, batt u8, speed cm/s u16, end=0x0D).
- Live WebSocket `/api/ws/live` broadcasting `pet_update` + `demo_device` messages.
- Simulator that runs on backend startup + standalone `tcp_hex_simulator.py`.
- Stripe checkout (basic $9, pro $19, advanced $39) via `emergentintegrations` Flow B, webhook at `/api/webhook/stripe`, status polling at `/api/payments/status/{session_id}`.

## Implemented — 2026-02
- Landing page, Login, Signup, Dashboard, Payment success/cancel routes.
- Full backend endpoints listed above (21/21 tests passing).
- Dashboard: live map, geofence circle, biometric floating card with bpm/battery/speed, sidebar with pets list, add-pet dialog, geofence radius slider.
- WebSocket-driven live marker + trail polyline, geofence status pill.
- Mobile scaffold with LoginScreen, MapScreen, HealthBottomSheet, GeofenceScreen.

## Prioritized backlog
- **P1** Real device auth on `/api/iot/ingest` (shared HMAC header) — currently public.
- **P1** TTL index / cap on `locations` collection (writes every 2s per pet).
- **P2** Email/SMS geofence-breach notifications (Resend/Twilio).
- **P2** Historical trail replay + speed heatmap.
- **P2** Multi-zone geofences (currently one per pet).
- **P3** Migrate FastAPI startup hooks to lifespan context manager.
- **P3** Split `server.py` into `routers/{auth,pets,iot,payments,ws}.py`.

## Stripe tax mode
Selected automatically — **DIY** (Stripe just processes payment; no tax help). This is the safest default for the pre-injected `sk_test_emergent` shared sandbox in a country not eligible for claimable-sandbox managed payments. Switch later via a message to the agent.
