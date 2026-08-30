from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import random
import math
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

async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Dict[str, Any]:
    if not creds:
        raise HTTPException(401, "Missing token")
    try:
        payload = pyjwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except pyjwt.PyJWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")

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
    return {"user": {"id": user["id"], "email": user["email"], "name": user["name"], "plan": user.get("plan", "free")}}

# ------------------------------------------------------------------
# Pets routes
# ------------------------------------------------------------------
@api_router.get("/pets")
async def list_pets(user=Depends(get_current_user)):
    pets = await db.pets.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    return {"pets": pets}

@api_router.post("/pets")
async def create_pet(data: PetCreate, user=Depends(get_current_user)):
    pet = Pet(
        user_id=user["id"],
        name=data.name,
        species=data.species,
        breed=data.breed,
        imei=(data.imei or f"860{random.randint(100000000000, 999999999999)}").lower(),
        color=data.color,
        avatar=data.avatar,
    )
    doc = pet.model_dump()
    await db.pets.insert_one(doc)
    doc.pop("_id", None)
    return {"pet": doc}

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
async def pet_history(pet_id: str, user=Depends(get_current_user)):
    pet = await db.pets.find_one({"id": pet_id, "user_id": user["id"]}, {"_id": 0})
    if not pet:
        raise HTTPException(404, "Pet not found")
    points = await db.locations.find({"pet_id": pet_id}, {"_id": 0}).sort("timestamp", -1).limit(100).to_list(100)
    return {"points": list(reversed(points))}

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

@api_router.post("/iot/ingest")
async def ingest_hex(data: HexIngestRequest):
    """
    Public endpoint (IoT devices don't hold JWTs). In production, protect with a
    device shared secret / mutual TLS. Parses HEX, updates the matching pet by
    IMEI, appends a location point, and broadcasts to WebSocket subscribers.
    """
    try:
        parsed = parse_hex_packet(data.hex)
    except Exception as e:
        raise HTTPException(400, f"parse error: {e}")

    pet = await db.pets.find_one({"imei": parsed["imei"]}, {"_id": 0})
    if not pet:
        # not registered — broadcast anonymously as raw device
        payload = {"type": "raw_device", **parsed, "timestamp": datetime.now(timezone.utc).isoformat()}
        await manager.broadcast(payload)
        return {"ok": True, "matched_pet": None, "parsed": parsed}

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.pets.update_one(
        {"id": pet["id"]},
        {"$set": {
            "latest_lat": parsed["lat"],
            "latest_lng": parsed["lng"],
            "latest_bpm": parsed["bpm"],
            "latest_battery": parsed["battery"],
            "latest_speed": parsed["speed"],
            "updated_at": now_iso,
        }},
    )
    point = LocationPoint(
        pet_id=pet["id"], imei=parsed["imei"], lat=parsed["lat"], lng=parsed["lng"],
        bpm=parsed["bpm"], battery=parsed["battery"], speed=parsed["speed"],
    )
    await db.locations.insert_one(point.model_dump())

    # Geofence check
    inside = _within_geofence(parsed["lat"], parsed["lng"], pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"])
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
                    await db.pets.update_one({"id": pet["id"]}, {"$set": {
                        "latest_lat": new_lat, "latest_lng": new_lng,
                        "latest_bpm": new_bpm, "latest_battery": new_batt,
                        "latest_speed": new_speed, "updated_at": now_iso,
                    }})
                    await db.locations.insert_one({
                        "id": str(uuid.uuid4()),
                        "pet_id": pet["id"], "imei": pet["imei"],
                        "lat": new_lat, "lng": new_lng, "bpm": new_bpm,
                        "battery": new_batt, "speed": new_speed,
                        "timestamp": now_iso,
                    })
                    inside = _within_geofence(new_lat, new_lng, pet["geofence_lat"], pet["geofence_lng"], pet["geofence_radius"])
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
