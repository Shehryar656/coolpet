from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import random
import math
import hmac
import hashlib
import jwt as pyjwt
import bcrypt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta

# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'dev_secret')
JWT_ALG = 'HS256'
JWT_TTL_HOURS = 24 * 7
IOT_DEVICE_SECRET = os.environ.get('IOT_DEVICE_SECRET', '')

PET_PALETTE = ["#00E5FF", "#D4AF37", "#34C759", "#FF3B30", "#B983FF", "#FF9F0A", "#5AC8FA", "#FF375F"]

app = FastAPI(title="CoolPet API")
api_router = APIRouter(prefix="/api")
bearer_scheme = HTTPBearer(auto_error=False)

logger = logging.getLogger("coolpet")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    plan: str = "free"

class Pet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    species: str = "Dog"
    breed: str = ""
    imei: str
    color: str = "#00E5FF"
    avatar: Optional[str] = None
    geofence_lat: float = 37.7749
    geofence_lng: float = -122.4194
    geofence_radius: int = 300  # meters
    latest_lat: float = 37.7749
    latest_lng: float = -122.4194
    latest_bpm: int = 92
    latest_battery: int = 88
    latest_speed: float = 0.0
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PetCreate(BaseModel):
    name: str
    species: str = "Dog"
    breed: str = ""
    imei: Optional[str] = None
    color: str = "#00E5FF"
    avatar: Optional[str] = None

class PetGeofenceUpdate(BaseModel):
    geofence_lat: Optional[float] = None
    geofence_lng: Optional[float] = None
    geofence_radius: Optional[int] = None

class LocationPoint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pet_id: str
    imei: str
    lat: float
    lng: float
    bpm: int
    battery: int
    speed: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CheckoutRequest(BaseModel):
    package_id: str
    origin_url: str

# ------------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def _resolve_user_from_session_token(session_token: str) -> Optional[Dict[str, Any]]:
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        return None
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at)
        except Exception:
            return None
    if expires_at is None:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return await db.users.find_one({"id": session["user_id"]}, {"_id": 0, "password_hash": 0})

async def get_current_user(request: Request) -> Dict[str, Any]:
    # 1) Emergent session cookie (Google OAuth flow)
    session_token = request.cookies.get("session_token")
    if session_token:
        user = await _resolve_user_from_session_token(session_token)
        if user:
            return user
    # 2) Authorization header — either session_token or JWT
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        # Try as Emergent session first
        user = await _resolve_user_from_session_token(token)
        if user:
            return user
        # Fallback to legacy JWT
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
            if user:
                return user
        except pyjwt.PyJWTError:
            pass
    raise HTTPException(401, "Not authenticated")

# ------------------------------------------------------------------
# WebSocket manager for live pet updates
# ------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------
@api_router.post("/auth/signup")
async def signup(data: UserSignup):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": data.email.lower(),
        "name": data.name,
        "password_hash": hash_password(data.password),
        "plan": "free",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = make_token(user_id)
    return {"token": token, "user": {"id": user_id, "email": data.email.lower(), "name": data.name, "plan": "free"}}

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = make_token(user["id"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user.get("plan", "free")}}

@api_router.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return {"user": {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "plan": user.get("plan", "free"),
        "picture": user.get("picture"),
        "provider": user.get("provider", "email"),
    }}

# ------------------------------------------------------------------
# Emergent-managed Google OAuth
# ------------------------------------------------------------------
import requests as _requests  # sync HTTP; called via asyncio.to_thread

EMERGENT_OAUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

class GoogleSessionRequest(BaseModel):
    session_id: str

def _fetch_emergent_session(session_id: str) -> Dict[str, Any]:
    r = _requests.get(EMERGENT_OAUTH_SESSION_URL, headers={"X-Session-ID": session_id}, timeout=10)
    if r.status_code != 200:
        raise HTTPException(401, f"Emergent session lookup failed ({r.status_code})")
    return r.json()

@api_router.post("/auth/google/session")
async def google_session(body: GoogleSessionRequest, response: Response):
    """Exchange an Emergent Google session_id for a signed-in user + session cookie."""
    data = await asyncio.to_thread(_fetch_emergent_session, body.session_id)
    email = (data.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "Emergent response missing email")
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data.get("session_token")
    if not session_token:
        raise HTTPException(400, "Emergent response missing session_token")

    # Upsert user by email
    user = await db.users.find_one({"email": email}, {"_id": 0})
    now_iso = datetime.now(timezone.utc).isoformat()
    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "plan": "free",
            "provider": "google",
            "created_at": now_iso,
        }
        await db.users.insert_one(user)
    else:
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"name": name, "picture": picture, "provider": user.get("provider", "google")}},
        )

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": user["id"],
            "expires_at": expires_at.isoformat(),
            "created_at": now_iso,
        }},
        upsert=True,
    )
    response.set_cookie(
        key="session_token", value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True, secure=True, samesite="none", path="/",
    )
    return {"user": {
        "id": user["id"], "email": email, "name": name,
        "picture": picture, "plan": user.get("plan", "free"), "provider": "google",
    }}

@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    st = request.cookies.get("session_token")
    if st:
        await db.user_sessions.delete_one({"session_token": st})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}

# ------------------------------------------------------------------
# Pets routes
# ------------------------------------------------------------------
@api_router.get("/pets")
async def list_pets(user=Depends(get_current_user)):
    pets = await db.pets.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    return {"pets": pets}

@api_router.post("/pets")
async def create_pet(data: PetCreate, user=Depends(get_current_user)):
    existing = await db.pets.count_documents({"user_id": user["id"]})
    color = data.color if data.color and data.color != "#00E5FF" else PET_PALETTE[existing % len(PET_PALETTE)]
    # IMEI: accept 15-digit real IMEI, 16-hex device id, or generate a synthetic 15-digit one
    imei_raw = (data.imei or f"860{random.randint(100000000000, 999999999999)}").strip().lower()
    pet = Pet(
        user_id=user["id"],
        name=data.name,
        species=data.species,
        breed=data.breed,
        imei=imei_raw,
        color=color,
        avatar=data.avatar,
    )
    doc = pet.model_dump()
    await db.pets.insert_one(doc)
    doc.pop("_id", None)

    # Instant-live: fire the first pet_update immediately so the marker appears
    # on connected dashboards without waiting for the main simulator tick.
    asyncio.create_task(_broadcast_initial_pet(doc))

    return {"pet": doc}

async def _broadcast_initial_pet(pet: Dict[str, Any]):
    """Emit two immediate pet_update frames + append ONE location point so the
    marker appears (and appears to move) the instant a collar is enrolled and
    history is non-empty. The main simulator loop (every 2s) and real
    /api/iot/ingest packets take it from there.

    NOTE: intentionally does NOT mutate db.pets (esp. inside_geofence) — that
    would race with concurrent /iot/ingest calls and the main simulator loop
    (which owns geofence transitions + breach events).
    """
    try:
        base_lat, base_lng = pet["latest_lat"], pet["latest_lng"]
        now_iso = datetime.now(timezone.utc).isoformat()
        inside = _within_geofence(
            base_lat, base_lng,
            pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"],
        )
        # Append-only: cannot race with breach detection.
        await db.locations.insert_one({
            "id": str(uuid.uuid4()),
            "pet_id": pet["id"], "imei": pet["imei"],
            "lat": base_lat, "lng": base_lng,
            "bpm": pet["latest_bpm"], "battery": pet["latest_battery"],
            "speed": pet.get("latest_speed", 0.0),
            "timestamp": now_iso,
        })
        await manager.broadcast({
            "type": "pet_update",
            "pet_id": pet["id"], "user_id": pet["user_id"],
            "name": pet["name"], "color": pet.get("color", "#00E5FF"),
            "lat": base_lat, "lng": base_lng,
            "bpm": pet["latest_bpm"], "battery": pet["latest_battery"],
            "speed": pet.get("latest_speed", 0.0),
            "inside_geofence": inside,
            "timestamp": now_iso,
        })
        # Second broadcast ~500ms later — broadcast-only, no persistence.
        await asyncio.sleep(0.5)
        jitter_lat = base_lat + (random.random() - 0.5) * 0.0003
        jitter_lng = base_lng + (random.random() - 0.5) * 0.0003
        inside2 = _within_geofence(
            jitter_lat, jitter_lng,
            pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"],
        )
        await manager.broadcast({
            "type": "pet_update",
            "pet_id": pet["id"], "user_id": pet["user_id"],
            "name": pet["name"], "color": pet.get("color", "#00E5FF"),
            "lat": jitter_lat, "lng": jitter_lng,
            "bpm": pet["latest_bpm"], "battery": pet["latest_battery"],
            "speed": pet.get("latest_speed", 0.0),
            "inside_geofence": inside2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"initial broadcast failed for pet {pet.get('id')}: {e}")

@api_router.patch("/pets/{pet_id}/geofence")
async def update_geofence(pet_id: str, data: PetGeofenceUpdate, user=Depends(get_current_user)):
    pet = await db.pets.find_one({"id": pet_id, "user_id": user["id"]}, {"_id": 0})
    if not pet:
        raise HTTPException(404, "Pet not found")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.pets.update_one({"id": pet_id}, {"$set": update})
    pet.update(update)
    return {"pet": pet}

@api_router.delete("/pets/{pet_id}")
async def delete_pet(pet_id: str, user=Depends(get_current_user)):
    res = await db.pets.delete_one({"id": pet_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Pet not found")
    await db.locations.delete_many({"pet_id": pet_id})
    return {"ok": True}

@api_router.get("/pets/{pet_id}/history")
async def pet_history(pet_id: str, hours: int = 24, limit: int = 500, user=Depends(get_current_user)):
    pet = await db.pets.find_one({"id": pet_id, "user_id": user["id"]}, {"_id": 0})
    if not pet:
        raise HTTPException(404, "Pet not found")
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    points = await db.locations.find(
        {"pet_id": pet_id, "timestamp": {"$gte": since}},
        {"_id": 0},
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"points": list(reversed(points))}

# ------------------------------------------------------------------
# Breach alerts (in-app)
# ------------------------------------------------------------------
async def record_breach(pet: Dict[str, Any], lat: float, lng: float, event_type: str, timestamp: str):
    """event_type = 'exit' | 'enter'"""
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": pet["user_id"],
        "pet_id": pet["id"],
        "pet_name": pet["name"],
        "pet_color": pet.get("color", "#00E5FF"),
        "event": event_type,
        "lat": lat,
        "lng": lng,
        "geofence_lat": pet["geofence_lat"],
        "geofence_lng": pet["geofence_lng"],
        "geofence_radius": pet["geofence_radius"],
        "read": False,
        "created_at": timestamp,
    }
    await db.breaches.insert_one(doc)
    payload = {"type": "breach_alert", **{k: v for k, v in doc.items() if k != "_id"}}
    await manager.broadcast(payload)
    return doc

@api_router.get("/breaches")
async def list_breaches(unread_only: bool = False, limit: int = 50, user=Depends(get_current_user)):
    q = {"user_id": user["id"]}
    if unread_only:
        q["read"] = False
    docs = await db.breaches.find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"breaches": docs}

@api_router.patch("/breaches/{breach_id}/read")
async def mark_breach_read(breach_id: str, user=Depends(get_current_user)):
    res = await db.breaches.update_one(
        {"id": breach_id, "user_id": user["id"]},
        {"$set": {"read": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Breach not found")
    return {"ok": True}

@api_router.post("/breaches/read-all")
async def mark_all_breaches_read(user=Depends(get_current_user)):
    await db.breaches.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}

# ------------------------------------------------------------------
# IoT ingestion — HEX packet parser (JT/T 794 inspired)
# ------------------------------------------------------------------
def parse_hex_packet(hex_str: str) -> Dict[str, Any]:
    """
    Simplified JT/T 794 style packet:
    Layout (bytes):
      [0]     start marker (0x24 '$')
      [1..8]  IMEI (8 bytes, BCD-encoded 15 digits, but we accept ASCII hex here)
      [9..12] latitude *1e6 (4 bytes signed big-endian)
      [13..16] longitude *1e6 (4 bytes signed big-endian)
      [17..18] BPM (2 bytes)
      [19]    battery percentage
      [20..21] speed cm/s (2 bytes)
      [22]    end marker (0x0D)
    """
    hex_str = hex_str.strip().replace(" ", "").replace("\n", "")
    b = bytes.fromhex(hex_str)
    if len(b) < 23:
        raise ValueError(f"packet too short: {len(b)} bytes")
    if b[0] != 0x24:
        raise ValueError("bad start marker")
    imei = b[1:9].hex()
    def s32(x: bytes) -> int:
        n = int.from_bytes(x, "big", signed=True)
        return n
    lat = s32(b[9:13]) / 1_000_000.0
    lng = s32(b[13:17]) / 1_000_000.0
    bpm = int.from_bytes(b[17:19], "big")
    battery = b[19]
    speed = int.from_bytes(b[20:22], "big") / 100.0  # m/s
    return {"imei": imei, "lat": lat, "lng": lng, "bpm": bpm, "battery": battery, "speed": speed}

class HexIngestRequest(BaseModel):
    hex: str

def verify_device_signature(body: bytes, signature: Optional[str]) -> bool:
    """HMAC-SHA256 of the raw request body, hex-encoded, sent in X-Device-Signature."""
    if not IOT_DEVICE_SECRET:
        # secret not configured — accept everything (dev fallback)
        return True
    if not signature:
        return False
    expected = hmac.new(IOT_DEVICE_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())

@api_router.post("/iot/ingest")
async def ingest_hex(request: Request):
    """
    Authenticated device endpoint. Requires header:
        X-Device-Signature: <hex HMAC-SHA256 of raw body using IOT_DEVICE_SECRET>
    Parses the HEX packet, updates the matching pet by IMEI, appends a location
    point, detects geofence-boundary crossings, and broadcasts over WebSocket.
    """
    body = await request.body()
    sig = request.headers.get("X-Device-Signature") or request.headers.get("x-device-signature")
    if not verify_device_signature(body, sig):
        raise HTTPException(401, "Invalid or missing X-Device-Signature")

    try:
        payload_json = HexIngestRequest.model_validate_json(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    try:
        parsed = parse_hex_packet(payload_json.hex)
    except Exception as e:
        raise HTTPException(400, f"parse error: {e}")

    pet = await db.pets.find_one({"imei": parsed["imei"]}, {"_id": 0})
    if not pet:
        payload = {"type": "raw_device", **parsed, "timestamp": datetime.now(timezone.utc).isoformat()}
        await manager.broadcast(payload)
        return {"ok": True, "matched_pet": None, "parsed": parsed}

    now_iso = datetime.now(timezone.utc).isoformat()
    prev_inside = pet.get("inside_geofence", True)
    inside = _within_geofence(parsed["lat"], parsed["lng"], pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"])

    await db.pets.update_one(
        {"id": pet["id"]},
        {"$set": {
            "latest_lat": parsed["lat"],
            "latest_lng": parsed["lng"],
            "latest_bpm": parsed["bpm"],
            "latest_battery": parsed["battery"],
            "latest_speed": parsed["speed"],
            "inside_geofence": inside,
            "updated_at": now_iso,
        }},
    )
    point = LocationPoint(
        pet_id=pet["id"], imei=parsed["imei"], lat=parsed["lat"], lng=parsed["lng"],
        bpm=parsed["bpm"], battery=parsed["battery"], speed=parsed["speed"],
    )
    await db.locations.insert_one(point.model_dump())

    # Boundary crossing → breach event
    if prev_inside and not inside:
        await record_breach(pet, parsed["lat"], parsed["lng"], "exit", now_iso)
    elif not prev_inside and inside:
        await record_breach(pet, parsed["lat"], parsed["lng"], "enter", now_iso)

    payload = {
        "type": "pet_update",
        "pet_id": pet["id"],
        "user_id": pet["user_id"],
        "name": pet["name"],
        "color": pet.get("color", "#00E5FF"),
        "lat": parsed["lat"],
        "lng": parsed["lng"],
        "bpm": parsed["bpm"],
        "battery": parsed["battery"],
        "speed": parsed["speed"],
        "inside_geofence": inside,
        "timestamp": now_iso,
    }
    await manager.broadcast(payload)
    return {"ok": True, "matched_pet": pet["id"], "parsed": parsed, "inside_geofence": inside}

def _within_geofence(lat: float, lng: float, clat: float, clng: float, radius_m: int) -> bool:
    # Haversine
    R = 6371000.0
    phi1, phi2 = math.radians(lat), math.radians(clat)
    dphi = math.radians(clat - lat)
    dl = math.radians(clng - lng)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c <= radius_m

# ------------------------------------------------------------------
# WebSocket
# ------------------------------------------------------------------
@app.websocket("/api/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # keep alive; client may send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)

# ------------------------------------------------------------------
# Stripe (Flow B — using pre-injected sk_test_emergent)
# ------------------------------------------------------------------
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest,
)

# Server-side fixed packages. Never trust amounts from the frontend.
PACKAGES = {
    "basic":    {"amount": 9.0,  "currency": "usd", "label": "CoolPet Basic (Monthly)"},
    "pro":      {"amount": 19.0, "currency": "usd", "label": "CoolPet Pro (Monthly)"},
    "advanced": {"amount": 39.0, "currency": "usd", "label": "CoolPet Advanced (Monthly)"},
}

@api_router.post("/payments/checkout")
async def create_checkout(req: CheckoutRequest, request: Request):
    if req.package_id not in PACKAGES:
        raise HTTPException(400, "Invalid package")
    pkg = PACKAGES[req.package_id]

    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)

    success_url = f"{req.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url  = f"{req.origin_url}/payment/cancel"

    session_req = CheckoutSessionRequest(
        amount=pkg["amount"],
        currency=pkg["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"package_id": req.package_id, "label": pkg["label"]},
    )
    session = await stripe_checkout.create_checkout_session(session_req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "package_id": req.package_id,
        "amount": pkg["amount"],
        "currency": pkg["currency"],
        "status": "initiated",
        "payment_status": "pending",
        "metadata": {"label": pkg["label"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"checkout_url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request):
    record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Transaction not found")

    if record.get("payment_status") != "paid":
        try:
            host_url = str(request.base_url)
            webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
            sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
            status = await sc.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {
                        "status": "completed",
                        "payment_status": "paid",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
                record = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception as e:
            logger.warning(f"stripe status poll failed: {e}")

    return {
        "session_id": record["session_id"],
        "status": record["status"],
        "payment_status": record["payment_status"],
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
    try:
        result = await sc.handle_webhook(body, sig)
    except Exception as e:
        raise HTTPException(400, f"Invalid webhook: {e}")

    if result.session_id:
        await db.payment_transactions.update_one(
            {"session_id": result.session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {
                "status": "completed" if result.payment_status == "paid" else result.payment_status,
                "payment_status": result.payment_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    return {"ok": True}

# ------------------------------------------------------------------
# Live simulator (auto-runs on startup with a demo pet)
# ------------------------------------------------------------------
SIMULATOR_STATE: Dict[str, Any] = {"running": False, "task": None}

async def _simulator_loop():
    """
    For every registered pet, emit a slight jitter around its last known
    position every 2s to simulate live GPS + heartbeat. Also broadcasts a
    'demo-collar' device for landing-page previews when there are 0 pets.
    """
    SIMULATOR_STATE["running"] = True
    # Demo baseline location (San Francisco)
    demo_lat, demo_lng = 37.7749, -122.4194
    demo_bpm = 92
    tick = 0
    while SIMULATOR_STATE["running"]:
        try:
            pets = await db.pets.find({}, {"_id": 0}).to_list(500)
            if not pets:
                # broadcast demo device
                demo_lat += (random.random() - 0.5) * 0.0006
                demo_lng += (random.random() - 0.5) * 0.0006
                demo_bpm = max(70, min(140, demo_bpm + random.randint(-3, 3)))
                await manager.broadcast({
                    "type": "demo_device",
                    "imei": "demo-collar-001",
                    "name": "Demo Collar",
                    "color": "#00E5FF",
                    "lat": demo_lat,
                    "lng": demo_lng,
                    "bpm": demo_bpm,
                    "battery": 87,
                    "speed": round(random.uniform(0.2, 2.5), 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                for pet in pets:
                    new_lat = pet["latest_lat"] + (random.random() - 0.5) * 0.0008
                    new_lng = pet["latest_lng"] + (random.random() - 0.5) * 0.0008
                    new_bpm = max(65, min(150, pet["latest_bpm"] + random.randint(-4, 4)))
                    new_batt = max(5, pet["latest_battery"] - (1 if tick % 30 == 0 else 0))
                    new_speed = round(random.uniform(0.0, 3.5), 2)
                    now_iso = datetime.now(timezone.utc).isoformat()
                    prev_inside = pet.get("inside_geofence", True)
                    inside = _within_geofence(new_lat, new_lng, pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"])
                    await db.pets.update_one({"id": pet["id"]}, {"$set": {
                        "latest_lat": new_lat, "latest_lng": new_lng,
                        "latest_bpm": new_bpm, "latest_battery": new_batt,
                        "latest_speed": new_speed, "inside_geofence": inside,
                        "updated_at": now_iso,
                    }})
                    await db.locations.insert_one({
                        "id": str(uuid.uuid4()),
                        "pet_id": pet["id"], "imei": pet["imei"],
                        "lat": new_lat, "lng": new_lng, "bpm": new_bpm,
                        "battery": new_batt, "speed": new_speed,
                        "timestamp": now_iso,
                    })
                    if prev_inside and not inside:
                        await record_breach(pet, new_lat, new_lng, "exit", now_iso)
                    elif not prev_inside and inside:
                        await record_breach(pet, new_lat, new_lng, "enter", now_iso)
                    await manager.broadcast({
                        "type": "pet_update",
                        "pet_id": pet["id"],
                        "user_id": pet["user_id"],
                        "name": pet["name"],
                        "color": pet.get("color", "#00E5FF"),
                        "lat": new_lat, "lng": new_lng,
                        "bpm": new_bpm, "battery": new_batt, "speed": new_speed,
                        "inside_geofence": inside,
                        "timestamp": now_iso,
                    })
            tick += 1
        except Exception as e:
            logger.warning(f"simulator tick error: {e}")
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def on_startup():
    SIMULATOR_STATE["task"] = asyncio.create_task(_simulator_loop())

@app.on_event("shutdown")
async def on_shutdown():
    SIMULATOR_STATE["running"] = False
    t = SIMULATOR_STATE.get("task")
    if t:
        t.cancel()
    client.close()

# ------------------------------------------------------------------
# Root
# ------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"service": "CoolPet API", "status": "ok"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
