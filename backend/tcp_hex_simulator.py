"""
CoolPet — IoT Collar HEX Simulator.

This script mimics a physical GPS tracking collar. It builds a raw HEX packet
compliant with a simplified JT/T 794-style layout, signs it with the shared
IOT_DEVICE_SECRET (HMAC-SHA256), and POSTs it to the CoolPet ingestion endpoint.

Usage:
    IOT_DEVICE_SECRET=<hex> python tcp_hex_simulator.py <IMEI_HEX> [--rounds 100] [--interval 2]

    IMEI_HEX must be 16 hex chars (8 bytes). Example: 0123456789ABCDEF
"""
import argparse
import hashlib
import hmac
import json
import os
import random
import time
import urllib.request
import urllib.error

DEFAULT_URL = os.environ.get(
    "COOLPET_INGEST_URL",
    "http://localhost:8001/api/iot/ingest",
)

def build_packet(imei_hex: str, lat: float, lng: float, bpm: int, battery: int, speed_ms: float) -> str:
    if len(imei_hex) != 16:
        raise ValueError("IMEI hex must be 16 chars (8 bytes)")
    imei_bytes = bytes.fromhex(imei_hex)
    lat_i = int(round(lat * 1_000_000)).to_bytes(4, "big", signed=True)
    lng_i = int(round(lng * 1_000_000)).to_bytes(4, "big", signed=True)
    bpm_b = int(bpm).to_bytes(2, "big")
    batt_b = bytes([battery & 0xFF])
    speed_b = int(round(speed_ms * 100)).to_bytes(2, "big")
    packet = b"\x24" + imei_bytes + lat_i + lng_i + bpm_b + batt_b + speed_b + b"\x0D"
    return packet.hex()

def post_hex(url: str, hex_str: str, secret: str) -> dict:
    body = json.dumps({"hex": hex_str}).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Device-Signature"] = sig
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imei_hex", help="8-byte IMEI as 16 hex chars")
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--secret", default=os.environ.get("IOT_DEVICE_SECRET", ""), help="HMAC secret; defaults to IOT_DEVICE_SECRET env")
    ap.add_argument("--lat", type=float, default=37.7749)
    ap.add_argument("--lng", type=float, default=-122.4194)
    args = ap.parse_args()

    lat, lng = args.lat, args.lng
    bpm = 92
    battery = 96
    print(f"[coolpet-collar] sending to {args.url} — imei={args.imei_hex} — signed={'yes' if args.secret else 'no'}")
    for i in range(args.rounds):
        lat += (random.random() - 0.5) * 0.0008
        lng += (random.random() - 0.5) * 0.0008
        bpm = max(65, min(150, bpm + random.randint(-4, 4)))
        speed = round(random.uniform(0, 3.5), 2)
        if i % 20 == 0 and battery > 5:
            battery -= 1
        pkt = build_packet(args.imei_hex, lat, lng, bpm, battery, speed)
        resp = post_hex(args.url, pkt, args.secret)
        print(f"  #{i:03d} lat={lat:.5f} lng={lng:.5f} bpm={bpm} batt={battery} → {resp}")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
