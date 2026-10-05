import os
import json
import time
import random
import paho.mqtt.client as mqtt
import sys

# Load the shared cryptographic module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../shared")))
try:
    from security import sign_payload
except ImportError:
    print("WARNING: Could not load security.py. Edge packets will be unsigned.")
    def sign_payload(body, prev): return "UNSIGNED"

MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = 1883

class ITIEdgeNode:
    def __init__(self, centre_code: str, claimed_attendance: int, is_cheating: bool = False):
        self.centre_code = centre_code
        self.claimed = claimed_attendance
        self.is_cheating = is_cheating
        self.prev_sig = "GENESIS"
        
        self.client = mqtt.Client(client_id=f"edge_{self.centre_code}")
        
    def connect(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"[Edge {self.centre_code}] Connection failed: {e}")

    def run_inference_cycle(self):
        """Simulates the YOLOv8 and YOLO-World output for one 15-minute window."""
        # If this centre is marked as 'cheating', the camera counts way fewer people than claimed
        if self.is_cheating:
            presence = random.uniform(2.0, 5.0)  # Only 2 to 5 people actually in the room
            status = "BREACH_GHOST_ATTENDANCE"
        else:
            presence = float(self.claimed - random.randint(0, 2))  # Normal minor variations
            status = "COMPLIANT"

        body = {
            "centre": self.centre_code,
            "claimed": self.claimed,
            "presence": round(presence, 1),
            "status": status,
            "equipment": {"chair": "PRESENT", "welding_machine": "PRESENT"}
        }

        # 1. Cryptographically sign the packet to chain it to the previous one
        sig = sign_payload(body, self.prev_sig)
        packet = {**body, "prev_sig": self.prev_sig, "sig": sig}
        
        # 2. Transmit over low-bandwidth MQTT
        topic = f"msde/telemetry/{self.centre_code}"
        self.client.publish(topic, json.dumps(packet), qos=1)
        
        # 3. Save signature for the next block
        self.prev_sig = sig
        
        if status == "BREACH_GHOST_ATTENDANCE":
            print(f"🚨 [Edge {self.centre_code}] Transmitted Ghost Attendance Alert. Claimed: {self.claimed}, Counted: {presence:.1f}")
        else:
            print(f"✅ [Edge {self.centre_code}] Transmitted Compliant packet.")