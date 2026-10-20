import asyncio, hmac, json, logging, os
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from . import db, ingest
from .notice import build_notice

log = logging.getLogger("kd")
logging.basicConfig(level=logging.INFO)
MQTT_HOST, MQTT_PORT = os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "1883"))
SILENT_AFTER_MIN = int(os.environ.get("SILENT_AFTER_MIN", "10"))   # no packet for this long = "no signal"
HERE = os.path.dirname(__file__)
API_KEY = os.environ.get("KD_API_KEY")   # if set, reviewing alerts and opening notices needs this key

def require_key(x_api_key: str = Header(default="")):
    if API_KEY and not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(401, "API key required")

class Hub:
    """Pushes events to every open dashboard."""
    def __init__(self):
        self.sockets, self.loop = set(), None
    async def send(self, msg):
        for ws in list(self.sockets):
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:
                self.sockets.discard(ws)
    def push_from_thread(self, msg):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.send(msg), self.loop)
hub = Hub()

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="kd-cloud-listener", clean_session=False)
    def on_connect(c, u, flags, rc, props=None):
        log.info("MQTT connected (%s)", rc)
        c.subscribe([("msde/telemetry/+", 1), ("msde/evidence/+/+", 1)])
    def on_message(c, u, msg):
        try:
            parts = msg.topic.split("/")
            if parts[1] == "telemetry":
                event = ingest.ingest_packet(parts[2], json.loads(msg.payload))
                if event:
                    hub.push_from_thread(event)
            elif parts[1] == "evidence" and len(parts) == 4:
                ingest.save_evidence(parts[3], msg.payload)
        except Exception:
            log.exception("bad message on %s", msg.topic)
    client.on_connect, client.on_message = on_connect, on_message
    client.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    return client

@asynccontextmanager
async def lifespan(app):
    hub.loop = asyncio.get_running_loop()
    db.init(os.environ.get("CENTRES_FILE", os.path.join(HERE, "..", "..", "data", "centres.json")))
    client = start_mqtt()
    yield
    client.loop_stop(); client.disconnect(); db.pool.close()

app = FastAPI(title="KushalDrishti Cloud", lifespan=lifespan)

CENTRE_SQL = """
SELECT c.code, c.name, c.state, ST_Y(c.geom::geometry) AS lat, ST_X(c.geom::geometry) AS lon,
       p.status, p.claimed, p.headcount, p.camera_health, p.ts AS last_seen,
       (SELECT id FROM alerts a WHERE a.centre_code = c.code AND a.status = 'OPEN' ORDER BY id DESC LIMIT 1) AS open_alert,
       CASE WHEN EXISTS (SELECT 1 FROM alerts a WHERE a.centre_code = c.code AND a.status = 'OPEN') THEN 'BREACH'
            WHEN p.ts IS NULL OR p.ts < now() - make_interval(mins => %(silent)s) THEN 'NO_SIGNAL'
            WHEN p.status = 'BREACH_GHOST_ATTENDANCE' THEN 'BREACH'
            WHEN p.status IN ('WARNING_SUSPECTED_GAP', 'CAMERA_ISSUE') THEN 'WATCH' ELSE 'OK' END AS colour_state
FROM centres c
LEFT JOIN LATERAL (SELECT * FROM packets WHERE centre_code = c.code ORDER BY ts DESC LIMIT 1) p ON true
{where}
ORDER BY c.code"""

def centres(where="", params=None):
    params = {"silent": SILENT_AFTER_MIN, **(params or {})}
    with db.pool.connection() as c:
        return c.execute(CENTRE_SQL.format(where=where), params).fetchall()

@app.get("/api/centres")
def api_centres():
    feats = []
    for r in centres():
        lat, lon = r.pop("lat"), r.pop("lon")
        r["last_seen"] = r["last_seen"].isoformat() if r["last_seen"] else None
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": r})
    return {"type": "FeatureCollection", "features": feats}

@app.get("/api/centres/near")
def api_near(lat: float, lon: float, km: float = 50, only_problems: bool = True):
    """GIS query: centres within km of a point (example: breaches within 50 km of Delhi)."""
    where = "WHERE ST_DWithin(c.geom, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(m)s)"
    rows = centres(where, {"lat": lat, "lon": lon, "m": km * 1000})
    if only_problems:
        rows = [r for r in rows if r["colour_state"] in ("BREACH", "WATCH", "NO_SIGNAL")]
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()} for r in rows]

@app.get("/api/alerts")
def api_alerts(status: str = "OPEN"):
    with db.pool.connection() as c:
        rows = c.execute("""SELECT a.id, a.kind, a.status, a.created_at, a.reviewed_by, c.code, c.name, c.state
                            FROM alerts a JOIN centres c ON c.code = a.centre_code
                            WHERE a.status = %s ORDER BY a.id DESC LIMIT 100""", (status,)).fetchall()
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()} for r in rows]

class Review(BaseModel):
    decision: str      # APPROVE or DISMISS
    officer: str

@app.post("/api/alerts/{alert_id}/review", dependencies=[Depends(require_key)])
async def api_review(alert_id: int, body: Review):
    if body.decision not in ("APPROVE", "DISMISS") or not body.officer.strip():
        raise HTTPException(400, "decision must be APPROVE or DISMISS, and officer is required")
    with db.pool.connection() as c:
        r = c.execute("""UPDATE alerts SET status = %s, reviewed_by = %s, reviewed_at = now()
                         WHERE id = %s AND status = 'OPEN' RETURNING id""",
                      ("APPROVED" if body.decision == "APPROVE" else "DISMISSED", body.officer.strip(), alert_id)).fetchone()
    if not r:
        raise HTTPException(404, "alert not found or already reviewed")
    await hub.send({"type": "review", "alert_id": alert_id})
    return {"ok": True}

@app.get("/api/alerts/{alert_id}/notice.pdf", dependencies=[Depends(require_key)])
def api_notice(alert_id: int):
    with db.pool.connection() as c:
        a = c.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,)).fetchone()
        if not a:
            raise HTTPException(404, "alert not found")
        p = c.execute("SELECT * FROM packets WHERE id = %s", (a["packet_id"],)).fetchone()
        ctr = c.execute("SELECT code, name, state FROM centres WHERE code = %s", (a["centre_code"],)).fetchone()
        pdf, digest = build_notice(a, p, ctr, ingest.evidence_path(p["sig"]), approved=a["status"] == "APPROVED")
        c.execute("INSERT INTO notices (alert_id, sha256) VALUES (%s, %s)", (alert_id, digest))
    return Response(pdf, media_type="application/pdf", headers={"X-Notice-SHA256": digest,
                    "Content-Disposition": f'inline; filename="notice_{alert_id}.pdf"'})

@app.get("/api/summary")
def api_summary():
    rows = centres()
    out = {s: sum(1 for r in rows if r["colour_state"] == s) for s in ("OK", "WATCH", "BREACH", "NO_SIGNAL")}
    return {"centres": len(rows), **out, "packets": ingest.stats}

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept(); hub.sockets.add(sock)
    try:
        while True:
            await sock.receive_text()
    except WebSocketDisconnect:
        hub.sockets.discard(sock)

app.mount("/", StaticFiles(directory=os.environ.get("DASHBOARD_DIR", os.path.join(HERE, "..", "..", "dashboard")), html=True), name="ui")
