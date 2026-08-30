"""CoolPet backend API test suite — updated for HMAC-signed IoT ingest,
breach alerts, trail replay hours param, and pet color palette."""
import os
import time
import uuid
import json
import hmac
import hashlib
import pytest
import requests
from pathlib import Path

# ---------- Env loading (read IOT_DEVICE_SECRET from backend/.env) ----------
def _load_backend_env():
    p = Path(__file__).resolve().parents[1] / ".env"
    env = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_BE_ENV = _load_backend_env()
IOT_DEVICE_SECRET = os.environ.get("IOT_DEVICE_SECRET") or _BE_ENV.get("IOT_DEVICE_SECRET", "")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://omni-iot-dash.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Helpers ----------
def sign_body(body: bytes, secret: str = None) -> str:
    secret = secret if secret is not None else IOT_DEVICE_SECRET
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def build_packet(imei_hex: str, lat: float, lng: float, bpm: int, battery: int, speed_ms: float) -> str:
    imei_bytes = bytes.fromhex(imei_hex)
    lat_i = int(round(lat * 1_000_000)).to_bytes(4, "big", signed=True)
    lng_i = int(round(lng * 1_000_000)).to_bytes(4, "big", signed=True)
    bpm_b = int(bpm).to_bytes(2, "big")
    batt_b = bytes([battery & 0xFF])
    speed_b = int(round(speed_ms * 100)).to_bytes(2, "big")
    packet = b"\x24" + imei_bytes + lat_i + lng_i + bpm_b + batt_b + speed_b + b"\x0D"
    return packet.hex()


def post_ingest(hex_str: str, sign: bool = True, bad_sig: bool = False, secret: str = None):
    """POST raw JSON so signature matches exact bytes sent."""
    body = json.dumps({"hex": hex_str}).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        sig = sign_body(body, secret) if not bad_sig else "deadbeef" * 8
        headers["X-Device-Signature"] = sig
    return requests.post(f"{API}/iot/ingest", data=body, headers=headers)


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def unique_email():
    return f"test_{uuid.uuid4().hex[:10]}@coolpet.io"


@pytest.fixture(scope="session")
def signup_user(unique_email):
    r = requests.post(f"{API}/auth/signup", json={
        "email": unique_email, "password": "secret123", "name": "TEST User"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    return {"email": unique_email, "password": "secret123", "token": data["token"], "user": data["user"]}


@pytest.fixture(scope="session")
def auth_headers(signup_user):
    return {"Authorization": f"Bearer {signup_user['token']}"}


# ---------- Root ----------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("service") == "CoolPet API"


def test_iot_device_secret_loaded():
    assert IOT_DEVICE_SECRET, "IOT_DEVICE_SECRET must be set (read from backend/.env)"
    assert len(IOT_DEVICE_SECRET) >= 32


# ---------- Auth (regression) ----------
def test_signup_returns_jwt(signup_user):
    assert signup_user["token"]
    assert signup_user["user"]["plan"] == "free"


def test_signup_duplicate_email(signup_user):
    r = requests.post(f"{API}/auth/signup", json={
        "email": signup_user["email"], "password": "secret123", "name": "Dup"
    })
    assert r.status_code == 400


def test_signup_short_password():
    r = requests.post(f"{API}/auth/signup", json={
        "email": f"short_{uuid.uuid4().hex[:6]}@coolpet.io", "password": "abc", "name": "X"
    })
    assert r.status_code == 422


def test_login_success(signup_user):
    r = requests.post(f"{API}/auth/login", json={
        "email": signup_user["email"], "password": signup_user["password"]
    })
    assert r.status_code == 200
    assert "token" in r.json()


def test_login_wrong_password(signup_user):
    r = requests.post(f"{API}/auth/login", json={
        "email": signup_user["email"], "password": "wrongpass"
    })
    assert r.status_code == 401


def test_me_with_token(auth_headers, signup_user):
    r = requests.get(f"{API}/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == signup_user["email"]


def test_me_without_token():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


# ---------- Pets (regression + palette) ----------
@pytest.fixture(scope="session")
def created_pet(auth_headers):
    r = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Rex", "species": "Dog"})
    assert r.status_code == 200, r.text
    pet = r.json()["pet"]
    assert pet["imei"] == pet["imei"].lower()
    return pet


def test_list_pets_after_create(auth_headers, created_pet):
    r = requests.get(f"{API}/pets", headers=auth_headers)
    assert r.status_code == 200
    assert any(p["id"] == created_pet["id"] for p in r.json()["pets"])


def test_pets_requires_auth():
    r = requests.get(f"{API}/pets")
    assert r.status_code == 401


def test_create_pet_with_imei_lowercased(auth_headers):
    imei = "ABCDEF0123456789"
    r = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Buddy", "imei": imei})
    assert r.status_code == 200
    assert r.json()["pet"]["imei"] == imei.lower()


def test_pet_color_palette_auto_assigns_different_colors():
    """Fresh user with 2 default-color pets should get 2 DIFFERENT palette colors."""
    email = f"palette_{uuid.uuid4().hex[:8]}@coolpet.io"
    sig = requests.post(f"{API}/auth/signup", json={"email": email, "password": "secret123", "name": "P"})
    assert sig.status_code == 200
    hdr = {"Authorization": f"Bearer {sig.json()['token']}"}
    p1 = requests.post(f"{API}/pets", headers=hdr, json={"name": "TEST P1"}).json()["pet"]
    p2 = requests.post(f"{API}/pets", headers=hdr, json={"name": "TEST P2", "color": "#00E5FF"}).json()["pet"]
    assert p1["color"] != p2["color"], f"Both pets got same color {p1['color']}"
    # Explicit non-default color must be honored
    p3 = requests.post(f"{API}/pets", headers=hdr, json={"name": "TEST P3", "color": "#123456"}).json()["pet"]
    assert p3["color"] == "#123456"


def test_update_geofence(auth_headers, created_pet):
    r = requests.patch(f"{API}/pets/{created_pet['id']}/geofence", headers=auth_headers,
                       json={"geofence_lat": 40.0, "geofence_lng": -74.0, "geofence_radius": 500})
    assert r.status_code == 200
    pet = r.json()["pet"]
    assert pet["geofence_lat"] == 40.0 and pet["geofence_radius"] == 500


def test_pet_history_hours_param(auth_headers, created_pet):
    # Reset geofence to SF so simulator points count and stay inside
    requests.patch(f"{API}/pets/{created_pet['id']}/geofence", headers=auth_headers,
                   json={"geofence_lat": 37.7749, "geofence_lng": -122.4194, "geofence_radius": 5000})
    time.sleep(3)  # let simulator emit
    r = requests.get(f"{API}/pets/{created_pet['id']}/history?hours=24&limit=50", headers=auth_headers)
    assert r.status_code == 200
    points = r.json()["points"]
    assert isinstance(points, list)
    # hours=0 → should return empty (or near-empty) list
    r0 = requests.get(f"{API}/pets/{created_pet['id']}/history?hours=0", headers=auth_headers)
    assert r0.status_code == 200
    # Sorted ascending
    if len(points) >= 2:
        assert points[0]["timestamp"] <= points[-1]["timestamp"]


# ---------- IoT ingest HMAC ----------
def test_ingest_missing_signature_rejected():
    pkt = build_packet("ffffffffffffffff", 1.0, 2.0, 90, 50, 0.5)
    r = post_ingest(pkt, sign=False)
    assert r.status_code == 401, r.text


def test_ingest_invalid_signature_rejected():
    pkt = build_packet("ffffffffffffffff", 1.0, 2.0, 90, 50, 0.5)
    r = post_ingest(pkt, sign=True, bad_sig=True)
    assert r.status_code == 401, r.text


def test_ingest_valid_signature_unmatched_imei():
    pkt = build_packet("ffffffffffffffff", 1.0, 2.0, 90, 50, 0.5)
    r = post_ingest(pkt, sign=True)
    assert r.status_code == 200, r.text
    assert r.json()["matched_pet"] is None


def test_ingest_valid_signature_matched_pet(auth_headers):
    imei = uuid.uuid4().hex[:16]
    rc = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Signed", "imei": imei})
    assert rc.status_code == 200
    pet_id = rc.json()["pet"]["id"]
    requests.patch(f"{API}/pets/{pet_id}/geofence", headers=auth_headers,
                   json={"geofence_lat": 37.7749, "geofence_lng": -122.4194, "geofence_radius": 1000})
    pkt = build_packet(imei, 37.77495, -122.4194, 105, 77, 1.5)
    r = post_ingest(pkt, sign=True)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["matched_pet"] == pet_id
    assert data["inside_geofence"] is True
    assert data["parsed"]["bpm"] == 105


def test_ingest_malformed_hex_with_valid_sig():
    body = json.dumps({"hex": "deadbeef"}).encode()
    r = requests.post(f"{API}/iot/ingest", data=body, headers={
        "Content-Type": "application/json",
        "X-Device-Signature": sign_body(body),
    })
    assert r.status_code == 400


# ---------- Breach alerts ----------
@pytest.fixture(scope="session")
def breach_pet(auth_headers):
    """Create a pet with SF geofence and prime it INSIDE first."""
    imei = uuid.uuid4().hex[:16]
    r = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Breach", "imei": imei})
    assert r.status_code == 200
    pet = r.json()["pet"]
    # Set tight geofence at SF center
    requests.patch(f"{API}/pets/{pet['id']}/geofence", headers=auth_headers,
                   json={"geofence_lat": 37.7749, "geofence_lng": -122.4194, "geofence_radius": 300})
    # Prime inside so first ingest is inside → subsequent 'exit' will trigger
    inside_pkt = build_packet(imei, 37.7749, -122.4194, 90, 80, 0.5)
    r_in = post_ingest(inside_pkt)
    assert r_in.status_code == 200
    return {"pet_id": pet["id"], "imei": imei}


def test_breach_exit_then_enter_events(auth_headers, breach_pet):
    imei = breach_pet["imei"]
    # OUTSIDE — should record 'exit' breach
    out_pkt = build_packet(imei, 37.79, -122.44, 110, 78, 2.0)
    r1 = post_ingest(out_pkt)
    assert r1.status_code == 200
    assert r1.json()["inside_geofence"] is False
    time.sleep(0.5)
    # INSIDE again — should record 'enter'
    in_pkt = build_packet(imei, 37.7749, -122.4194, 95, 78, 1.0)
    r2 = post_ingest(in_pkt)
    assert r2.status_code == 200
    assert r2.json()["inside_geofence"] is True

    time.sleep(1.0)
    br = requests.get(f"{API}/breaches", headers=auth_headers)
    assert br.status_code == 200
    events = [b for b in br.json()["breaches"] if b["pet_id"] == breach_pet["pet_id"]]
    assert len(events) >= 2, f"Expected >=2 breaches, got {len(events)}"
    # Sorted desc by created_at → newest first should be 'enter'
    assert events[0]["event"] == "enter"
    assert any(e["event"] == "exit" for e in events)
    # Fields present
    for e in events[:2]:
        assert "lat" in e and "lng" in e and "geofence_radius" in e and e["read"] is False


def test_breach_unread_only_and_limit(auth_headers):
    r = requests.get(f"{API}/breaches?unread_only=true&limit=1", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()["breaches"]
    assert len(body) <= 1
    for b in body:
        assert b["read"] is False


def test_breach_mark_single_read(auth_headers):
    all_br = requests.get(f"{API}/breaches?unread_only=true", headers=auth_headers).json()["breaches"]
    if not all_br:
        pytest.skip("no unread breaches to mark")
    bid = all_br[0]["id"]
    r = requests.patch(f"{API}/breaches/{bid}/read", headers=auth_headers)
    assert r.status_code == 200
    # 404 for wrong id
    r404 = requests.patch(f"{API}/breaches/{uuid.uuid4()}/read", headers=auth_headers)
    assert r404.status_code == 404
    # verify persisted
    after = requests.get(f"{API}/breaches", headers=auth_headers).json()["breaches"]
    found = next((b for b in after if b["id"] == bid), None)
    assert found and found["read"] is True


def test_breach_mark_all_read(auth_headers):
    r = requests.post(f"{API}/breaches/read-all", headers=auth_headers)
    assert r.status_code == 200
    left = requests.get(f"{API}/breaches?unread_only=true", headers=auth_headers).json()["breaches"]
    assert left == []


def test_breaches_requires_auth():
    r = requests.get(f"{API}/breaches")
    assert r.status_code == 401


# ---------- Payments (regression) ----------
def test_checkout_valid_package():
    r = requests.post(f"{API}/payments/checkout", json={
        "package_id": "basic", "origin_url": BASE_URL
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["checkout_url"].startswith("http") and data["session_id"]
    time.sleep(1)
    rs = requests.get(f"{API}/payments/status/{data['session_id']}")
    assert rs.status_code == 200
    assert rs.json()["session_id"] == data["session_id"]


def test_checkout_invalid_package():
    r = requests.post(f"{API}/payments/checkout", json={
        "package_id": "bogus", "origin_url": "https://x.com"
    })
    assert r.status_code == 400


# ---------- Pet deletion (do last) ----------
def test_delete_pet(auth_headers, created_pet):
    r = requests.delete(f"{API}/pets/{created_pet['id']}", headers=auth_headers)
    assert r.status_code == 200
    r2 = requests.patch(f"{API}/pets/{created_pet['id']}/geofence", headers=auth_headers,
                       json={"geofence_radius": 100})
    assert r2.status_code == 404


# ---------- Emergent Google OAuth (mocked via seeded Mongo sessions) ----------
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

_MONGO_URL = _BE_ENV.get("MONGO_URL", "mongodb://localhost:27017")
_DB_NAME = _BE_ENV.get("DB_NAME", "test_database")


@pytest.fixture(scope="module")
def mongo_db():
    c = MongoClient(_MONGO_URL)
    yield c[_DB_NAME]
    c.close()


@pytest.fixture
def seeded_google_session(mongo_db):
    """Seed a fresh user + user_sessions doc; cleanup after test."""
    suffix = uuid.uuid4().hex[:10]
    user_id = f"test-google-user-{suffix}"
    session_token = f"test_session_{suffix}"
    email = f"test.google.{suffix}@example.com"
    now = datetime.now(timezone.utc)
    mongo_db.users.insert_one({
        "id": user_id, "email": email, "name": "Google Test User",
        "picture": "https://via.placeholder.com/150",
        "provider": "google", "plan": "free",
        "created_at": now.isoformat(),
    })
    mongo_db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "created_at": now.isoformat(),
    })
    yield {"user_id": user_id, "session_token": session_token, "email": email}
    mongo_db.user_sessions.delete_many({"session_token": session_token})
    mongo_db.users.delete_many({"id": user_id})
    mongo_db.pets.delete_many({"user_id": user_id})


@pytest.fixture
def expired_google_session(mongo_db):
    suffix = uuid.uuid4().hex[:10]
    user_id = f"test-google-user-exp-{suffix}"
    session_token = f"test_session_exp_{suffix}"
    email = f"test.google.exp.{suffix}@example.com"
    now = datetime.now(timezone.utc)
    mongo_db.users.insert_one({
        "id": user_id, "email": email, "name": "Expired User",
        "provider": "google", "plan": "free", "created_at": now.isoformat(),
    })
    mongo_db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": (now - timedelta(hours=1)).isoformat(),
        "created_at": now.isoformat(),
    })
    yield {"user_id": user_id, "session_token": session_token}
    mongo_db.user_sessions.delete_many({"session_token": session_token})
    mongo_db.users.delete_many({"id": user_id})


def test_google_session_bogus_session_id_returns_401():
    r = requests.post(f"{API}/auth/google/session", json={"session_id": "bogus-does-not-exist-xxx"})
    assert r.status_code == 401, r.text


def test_seeded_session_authenticates_me_via_cookie(seeded_google_session):
    r = requests.get(f"{API}/auth/me", cookies={"session_token": seeded_google_session["session_token"]})
    assert r.status_code == 200, r.text
    u = r.json()["user"]
    assert u["email"] == seeded_google_session["email"]
    assert u["provider"] == "google"
    assert "picture" in u


def test_seeded_session_authenticates_me_via_bearer(seeded_google_session):
    r = requests.get(f"{API}/auth/me",
                     headers={"Authorization": f"Bearer {seeded_google_session['session_token']}"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == seeded_google_session["email"]


def test_seeded_session_can_list_pets_and_breaches(seeded_google_session):
    cookies = {"session_token": seeded_google_session["session_token"]}
    r_pets = requests.get(f"{API}/pets", cookies=cookies)
    assert r_pets.status_code == 200
    assert isinstance(r_pets.json()["pets"], list)
    r_br = requests.get(f"{API}/breaches", cookies=cookies)
    assert r_br.status_code == 200
    assert isinstance(r_br.json()["breaches"], list)


def test_me_without_auth_returns_401():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


def test_legacy_jwt_me_includes_provider_email(signup_user, auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers)
    assert r.status_code == 200
    u = r.json()["user"]
    assert u["email"] == signup_user["email"]
    assert u.get("provider") == "email"
    assert "picture" in u  # may be None but should be present


def test_expired_session_rejected(expired_google_session):
    r = requests.get(f"{API}/auth/me",
                     cookies={"session_token": expired_google_session["session_token"]})
    assert r.status_code == 401
    r2 = requests.get(f"{API}/pets",
                      cookies={"session_token": expired_google_session["session_token"]})
    assert r2.status_code == 401


def test_logout_deletes_session_and_clears_cookie(seeded_google_session, mongo_db):
    st = seeded_google_session["session_token"]
    # Confirm session works pre-logout
    pre = requests.get(f"{API}/auth/me", cookies={"session_token": st})
    assert pre.status_code == 200
    # Logout
    r = requests.post(f"{API}/auth/logout", cookies={"session_token": st})
    assert r.status_code == 200
    # Set-Cookie should be present and clearing session_token
    set_cookie = r.headers.get("set-cookie", "").lower()
    assert "session_token=" in set_cookie
    assert ("max-age=0" in set_cookie
            or "expires=thu, 01 jan 1970" in set_cookie
            or "expires=" in set_cookie)
    # DB doc removed
    assert mongo_db.user_sessions.find_one({"session_token": st}) is None
    # Subsequent request fails
    post = requests.get(f"{API}/auth/me", cookies={"session_token": st})
    assert post.status_code == 401


# ---------- WebSocket ----------
def test_websocket_broadcast():
    try:
        import websocket
    except ImportError:
        pytest.skip("websocket-client not installed")
    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/live"
    ws = websocket.create_connection(ws_url, timeout=8)
    try:
        ws.settimeout(6)
        msg = ws.recv()
        data = json.loads(msg)
        assert data.get("type") in ("demo_device", "pet_update", "raw_device", "breach_alert")
    finally:
        ws.close()


# ---------- Instant Live Tracking on IMEI Registration ----------
def test_create_pet_with_15_digit_imei_persists_lowercased(auth_headers):
    """POST /api/pets accepts a real 15-digit IMEI and stores it lowercased."""
    imei = "860123456789012"
    r = requests.post(f"{API}/pets", headers=auth_headers,
                      json={"name": "TEST Instant15", "imei": imei})
    assert r.status_code == 200, r.text
    pet = r.json()["pet"]
    assert pet["imei"] == imei  # already lower/numeric
    # verify persistence via GET /pets list
    lst = requests.get(f"{API}/pets", headers=auth_headers).json()["pets"]
    match = next((p for p in lst if p["id"] == pet["id"]), None)
    assert match is not None
    assert match["imei"] == imei


def test_create_pet_without_imei_generates_15_digit_860(auth_headers):
    """When `imei` is omitted, server generates a 15-digit '860…' fallback."""
    r = requests.post(f"{API}/pets", headers=auth_headers,
                      json={"name": "TEST NoImei"})
    assert r.status_code == 200, r.text
    imei = r.json()["pet"]["imei"]
    assert imei.startswith("860")
    assert len(imei) == 15
    assert imei.isdigit()


def test_create_pet_history_populated_within_2_5s(auth_headers):
    """After POST /pets, the initial-broadcast task inserts locations; history should return >=1 point within 2.5s."""
    imei = f"860{uuid.uuid4().int % 10**12:012d}"
    r = requests.post(f"{API}/pets", headers=auth_headers,
                      json={"name": "TEST HistBurst", "imei": imei})
    assert r.status_code == 200
    pet_id = r.json()["pet"]["id"]
    # wait up to 2.5s (endpoint schedules 4 frames @400ms cadence after t=0)
    deadline = time.time() + 2.5
    points = []
    while time.time() < deadline:
        h = requests.get(f"{API}/pets/{pet_id}/history?hours=1&limit=50",
                         headers=auth_headers)
        if h.status_code == 200:
            points = h.json().get("points", [])
            if len(points) >= 1:
                break
        time.sleep(0.25)
    assert len(points) >= 1, f"Expected >=1 point within 2.5s, got {len(points)}"


def test_create_pet_broadcasts_pet_update_over_websocket(auth_headers):
    """A client connected to /api/ws/live should receive >=1 pet_update with the
    new pet_id within ~1s of POST /api/pets, and >=2 total within ~2s."""
    try:
        import websocket
    except ImportError:
        pytest.skip("websocket-client not installed")

    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/live"
    ws = websocket.create_connection(ws_url, timeout=8)
    try:
        # Drain any initial demo frames without blocking too long
        ws.settimeout(0.2)
        for _ in range(20):
            try:
                ws.recv()
            except Exception:
                break

        # Create pet AFTER the ws is connected
        imei = f"860{uuid.uuid4().int % 10**12:012d}"
        t0 = time.time()
        r = requests.post(f"{API}/pets", headers=auth_headers,
                          json={"name": "TEST WSInstant", "imei": imei})
        assert r.status_code == 200, r.text
        pet_id = r.json()["pet"]["id"]

        # Collect pet_update frames for this pet_id within a 2.5s window
        matches = []
        first_match_time = None
        ws.settimeout(2.5)
        deadline = time.time() + 2.5
        while time.time() < deadline:
            try:
                ws.settimeout(max(0.05, deadline - time.time()))
                raw = ws.recv()
            except Exception:
                break
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "pet_update" and msg.get("pet_id") == pet_id:
                if first_match_time is None:
                    first_match_time = time.time() - t0
                matches.append(msg)
                if len(matches) >= 2 and first_match_time is not None and first_match_time <= 1.5:
                    # got enough; keep going only if still within window
                    if len(matches) >= 5:
                        break
        assert first_match_time is not None, "No pet_update frame received for new pet_id"
        assert first_match_time <= 1.5, f"First frame arrived at {first_match_time:.2f}s (>1.5s)"
        assert len(matches) >= 2, f"Expected >=2 pet_update frames within 2.5s, got {len(matches)}"
    finally:
        ws.close()
