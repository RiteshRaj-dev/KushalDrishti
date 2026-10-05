import os
import json
import threading
import paho.mqtt.client as mqtt
from datetime import datetime
import sys

# Ensure the shared security module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../shared")))
try:
    from security import verify_signature
except ImportError:
    print("WARNING: Could not load security.py. Signature verification will fail.")

from .db import SessionLocal, TelemetryLog, ITICentre
from .notice import generate_show_cause_notice

MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = 1883
MQTT_TOPIC = "msde/telemetry/#"

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT Listener] 🟢 Connected to broker with code {rc}. Subscribing to {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC, qos=1)

def on_message(client, userdata, msg):
    payload_str = msg.payload.decode('utf-8')
    try:
        packet = json.loads(payload_str)
    except json.JSONDecodeError:
        print("[MQTT Listener] ⚠️ Dropped invalid JSON payload.")
        return

    # 1. Cryptographic Verification
    is_valid = verify_signature(packet)
    if not is_valid:
        print(f"[MQTT Listener] ❌ TAMPER ALERT: Invalid signature from {packet.get('centre')}")
    
    centre_code = packet.get("centre")
    presence = packet.get("presence", 0.0)
    status = packet.get("status", "UNKNOWN")
    equipment = packet.get("equipment", {})

    db = SessionLocal()
    
    # 2. Log Telemetry
    log_entry = TelemetryLog(
        centre_code=centre_code,
        counted_presence=presence,
        status=status,
        equipment_status=equipment,
        tamper_verified=is_valid
    )
    db.add(log_entry)
    
    # 3. Update ITI Master Record (Create if missing for demo purposes)
    iti = db.query(ITICentre).filter(ITICentre.centre_code == centre_code).first()
    if not iti:
        # Mocking coordinates for demo (New Delhi area)
        iti = ITICentre(
            centre_code=centre_code, name=f"Training Centre {centre_code}", 
            state="Delhi", latitude=28.6139, longitude=77.2090, 
            claimed_attendance=packet.get("claimed", 0)
        )
        db.add(iti)
    else:
        iti.claimed_attendance = packet.get("claimed", 0)
    
    db.commit()
    db.close()

    # 4. Trigger Automated Actions
    if status == "BREACH_GHOST_ATTENDANCE" and is_valid:
        details = f"Portal Claim: {packet.get('claimed')} | Camera Count: {presence:.1f}"
        generate_show_cause_notice(centre_code, details)

def start_mqtt_listener():
    """Runs the MQTT client loop in a background thread."""
    client = mqtt.Client(client_id="msde_cloud_backend")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT Listener] Failed to connect to broker: {e}")