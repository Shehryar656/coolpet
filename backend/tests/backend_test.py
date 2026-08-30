"""CoolPet backend API test suite."""
import os
import time
import uuid
import json
import asyncio
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://omni-iot-dash.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


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
    assert "token" in data and "user" in data
    return {"email": unique_email, "password": "secret123", "token": data["token"], "user": data["user"]}


@pytest.fixture(scope="session")
def auth_headers(signup_user):
    return {"Authorization": f"Bearer {signup_user['token']}"}


# ---------- Root ----------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "CoolPet API"
    assert data.get("status") == "ok"


# ---------- Auth ----------
def test_signup_returns_jwt_and_user(signup_user):
    assert signup_user["token"]
    assert signup_user["user"]["email"] == signup_user["email"]
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


# ---------- Pets ----------
@pytest.fixture(scope="session")
def created_pet(auth_headers):
    r = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Rex", "species": "Dog"})
    assert r.status_code == 200, r.text
    pet = r.json()["pet"]
    assert pet["name"] == "TEST Rex"
    assert pet["imei"]  # auto-generated
    assert pet["imei"] == pet["imei"].lower()
    return pet


def test_list_pets_after_create(auth_headers, created_pet):
    r = requests.get(f"{API}/pets", headers=auth_headers)
    assert r.status_code == 200
    pets = r.json()["pets"]
    assert any(p["id"] == created_pet["id"] for p in pets)


def test_pets_requires_auth():
    r = requests.get(f"{API}/pets")
    assert r.status_code == 401


def test_create_pet_with_imei_lowercased(auth_headers):
    imei = "ABCDEF0123456789"
    r = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST Buddy", "imei": imei})
    assert r.status_code == 200
    pet = r.json()["pet"]
    assert pet["imei"] == imei.lower()


def test_update_geofence(auth_headers, created_pet):
    r = requests.patch(f"{API}/pets/{created_pet['id']}/geofence", headers=auth_headers,
                       json={"geofence_lat": 40.0, "geofence_lng": -74.0, "geofence_radius": 500})
    assert r.status_code == 200
    pet = r.json()["pet"]
    assert pet["geofence_lat"] == 40.0
    assert pet["geofence_lng"] == -74.0
    assert pet["geofence_radius"] == 500


def test_pet_history(auth_headers, created_pet):
    # Wait a tick for simulator to have populated some points
    time.sleep(3)
    r = requests.get(f"{API}/pets/{created_pet['id']}/history", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json().get("points"), list)


# ---------- IoT ingest ----------
def build_packet(imei_hex: str, lat: float, lng: float, bpm: int, battery: int, speed_ms: float) -> str:
    imei_bytes = bytes.fromhex(imei_hex)
    lat_i = int(round(lat * 1_000_000)).to_bytes(4, "big", signed=True)
    lng_i = int(round(lng * 1_000_000)).to_bytes(4, "big", signed=True)
    bpm_b = int(bpm).to_bytes(2, "big")
    batt_b = bytes([battery & 0xFF])
    speed_b = int(round(speed_ms * 100)).to_bytes(2, "big")
    packet = b"\x24" + imei_bytes + lat_i + lng_i + bpm_b + batt_b + speed_b + b"\x0D"
    return packet.hex()


def test_iot_ingest_matched_pet(auth_headers):
    # Create pet with a known IMEI (16 hex chars)
    imei = uuid.uuid4().hex[:16]
    rc = requests.post(f"{API}/pets", headers=auth_headers, json={"name": "TEST IoT", "imei": imei})
    assert rc.status_code == 200
    pet_id = rc.json()["pet"]["id"]

    # Set geofence around known point
    requests.patch(f"{API}/pets/{pet_id}/geofence", headers=auth_headers,
                   json={"geofence_lat": 37.7749, "geofence_lng": -122.4194, "geofence_radius": 1000})

    pkt = build_packet(imei, 37.77495, -122.4194, 105, 77, 1.5)
    r = requests.post(f"{API}/iot/ingest", json={"hex": pkt})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["matched_pet"] == pet_id
    assert data["inside_geofence"] is True
    p = data["parsed"]
    assert abs(p["lat"] - 37.77495) < 1e-5
    assert abs(p["lng"] - (-122.4194)) < 1e-5
    assert p["bpm"] == 105
    assert p["battery"] == 77
    assert abs(p["speed"] - 1.5) < 1e-6


def test_iot_ingest_unmatched():
    imei = "ffffffffffffffff"
    pkt = build_packet(imei, 1.0, 2.0, 90, 50, 0.5)
    r = requests.post(f"{API}/iot/ingest", json={"hex": pkt})
    assert r.status_code == 200
    assert r.json()["matched_pet"] is None


def test_iot_ingest_malformed():
    r = requests.post(f"{API}/iot/ingest", json={"hex": "deadbeef"})
    assert r.status_code == 400


# ---------- Payments ----------
def test_checkout_valid_package():
    r = requests.post(f"{API}/payments/checkout", json={
        "package_id": "basic", "origin_url": "https://omni-iot-dash.preview.emergentagent.com"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["checkout_url"].startswith("http")
    assert data["session_id"]
    # Poll status
    time.sleep(1)
    rs = requests.get(f"{API}/payments/status/{data['session_id']}")
    assert rs.status_code == 200
    js = rs.json()
    assert js["session_id"] == data["session_id"]
    assert js["payment_status"] in ("pending", "unpaid", "no_payment_required")


def test_checkout_invalid_package():
    r = requests.post(f"{API}/payments/checkout", json={
        "package_id": "bogus", "origin_url": "https://x.com"
    })
    assert r.status_code == 400


def test_checkout_pro_and_advanced():
    for pkg in ("pro", "advanced"):
        r = requests.post(f"{API}/payments/checkout", json={
            "package_id": pkg, "origin_url": "https://x.com"
        })
        assert r.status_code == 200, f"{pkg}: {r.text}"


# ---------- Pet deletion (do last) ----------
def test_delete_pet(auth_headers, created_pet):
    r = requests.delete(f"{API}/pets/{created_pet['id']}", headers=auth_headers)
    assert r.status_code == 200
    r2 = requests.patch(f"{API}/pets/{created_pet['id']}/geofence", headers=auth_headers, json={"geofence_radius": 100})
    assert r2.status_code == 404


# ---------- WebSocket ----------
def test_websocket_broadcast():
    """Connect to /api/ws/live and expect at least one message within 5s."""
    try:
        import websocket  # websocket-client
    except ImportError:
        pytest.skip("websocket-client not installed")

    ws_url = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws/live"
    ws = websocket.create_connection(ws_url, timeout=8)
    try:
        ws.settimeout(6)
        msg = ws.recv()
        data = json.loads(msg)
        assert data.get("type") in ("demo_device", "pet_update", "raw_device")
    finally:
        ws.close()
