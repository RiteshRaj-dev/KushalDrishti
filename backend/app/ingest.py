"""Turns a verified MQTT packet into database rows and alerts."""
import logging, os, re, sys
from datetime import datetime, timezone
from psycopg.types.json import Jsonb
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
sys.path.insert(0, "/app/shared")
import security
from .db import pool

log = logging.getLogger("ingest")
EVIDENCE_DIR = os.environ.get("EVIDENCE_DIR", "/tmp/kd_evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)
SIG_RE = re.compile(r"^[0-9a-f]{64}$")
stats = {"accepted": 0, "duplicate": 0, "rejected": 0}

def ingest_packet(topic_centre: str, packet: dict):
    """Returns an event dict for the dashboard, or None if the packet was not accepted."""
    if packet.get("centre_code") != topic_centre or not security.verify(packet):
        stats["rejected"] += 1
        log.warning("rejected packet from topic %s", topic_centre)
        return None
    with pool.connection() as c:
        last = c.execute("SELECT sig FROM packets WHERE centre_code=%s ORDER BY ts DESC, id DESC LIMIT 1",
                         (topic_centre,)).fetchone()
        chain_ok = last is None or last["sig"] == packet["prev_sig"] or packet["prev_sig"] == "GENESIS"
        row = c.execute("""INSERT INTO packets (centre_code, ts, status, claimed, headcount, smoothed, camera_health,
                           equipment, prev_sig, sig, chain_ok)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (sig) DO NOTHING RETURNING id""",
                        (topic_centre, datetime.fromtimestamp(packet["ts"], timezone.utc), packet["status"],
                         packet.get("claimed_roll"), packet.get("mean_headcount"), packet.get("smoothed_presence"),
                         packet.get("camera_health"), Jsonb(packet.get("equipment", {})), packet["prev_sig"],
                         packet["sig"], chain_ok)).fetchone()
        if row is None:                       # QoS 1 can deliver twice; the signature makes it safe to ignore
            stats["duplicate"] += 1
            return None
        stats["accepted"] += 1
        kinds = []
        if packet["status"] == "BREACH_GHOST_ATTENDANCE":
            kinds.append("GHOST_ATTENDANCE")
        if any(v == "ABSENT" for v in packet.get("equipment", {}).values()):
            kinds.append("EQUIPMENT_MISSING")
        new_alerts = []
        for kind in kinds:                    # one open alert per centre and kind, so officers are not flooded
            exists = c.execute("SELECT 1 FROM alerts WHERE centre_code=%s AND kind=%s AND status='OPEN'",
                               (topic_centre, kind)).fetchone()
            if not exists:
                a = c.execute("INSERT INTO alerts (centre_code, packet_id, kind) VALUES (%s,%s,%s) RETURNING id",
                              (topic_centre, row["id"], kind)).fetchone()
                new_alerts.append({"alert_id": a["id"], "kind": kind})
    return {"type": "packet", "centre": topic_centre, "status": packet["status"], "new_alerts": new_alerts}

def save_evidence(sig: str, data: bytes):
    if not SIG_RE.match(sig) or len(data) > 2_000_000:
        return False
    with open(os.path.join(EVIDENCE_DIR, f"{sig}.jpg"), "wb") as f:
        f.write(data)
    return True

def evidence_path(sig):
    p = os.path.join(EVIDENCE_DIR, f"{sig}.jpg")
    return p if sig and SIG_RE.match(sig) and os.path.exists(p) else None
