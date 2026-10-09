"""Needs PostgreSQL with PostGIS (CI starts one). Skipped when none is reachable."""
import os, time
import pytest
psycopg = pytest.importorskip("psycopg")
DSN = os.environ.get("DATABASE_URL", "postgresql://kd:kd@localhost:5432/kd")
try:
    psycopg.connect(DSN, connect_timeout=2).close()
except Exception:
    pytest.skip("no PostGIS database reachable", allow_module_level=True)
os.environ["DATABASE_URL"] = DSN
os.environ["KD_API_KEY"] = "secret-key"
os.environ["EVIDENCE_DIR"] = "/tmp/kd_test_evidence"
import security
from backend.app import db, ingest
from backend.app.notice import build_notice

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(scope="module", autouse=True)
def database():
    db.init(os.path.join(ROOT, "data", "centres.json"))
    with db.pool.connection() as c:
        c.execute("TRUNCATE alerts, notices, packets RESTART IDENTITY CASCADE")
    yield
    db.pool.close()

def pkt(centre="ITI-DL-001", prev="GENESIS", status="COMPLIANT", equipment=None, ts=None, **kw):
    body = {"centre_code": centre, "trade": "classroom_demo", "ts": ts or int(time.time()), "minute": 1, "claimed_roll": 18,
            "mean_headcount": 6.0, "smoothed_presence": 6.0, "status": status, "camera_health": "OK",
            "equipment": equipment or {"chair": "PRESENT"}, "faces_blurred": True, **kw}
    return security.seal(centre, body, prev)

def test_valid_duplicate_forged_and_spoofed():
    p = pkt(ts=1000)
    assert ingest.ingest_packet("ITI-DL-001", p)["type"] == "packet"
    assert ingest.ingest_packet("ITI-DL-001", p) is None                       # QoS 1 duplicate ignored
    assert ingest.ingest_packet("ITI-DL-001", {**pkt(ts=1001), "claimed_roll": 99}) is None   # edited packet
    assert ingest.ingest_packet("ITI-DL-002", pkt(ts=1002)) is None            # valid packet on another centre's topic
    assert ingest.stats["rejected"] >= 2

def test_breach_makes_one_alert_and_notice_is_a_draft_pdf():
    first = pkt("ITI-UP-001", status="BREACH_GHOST_ATTENDANCE", ts=2000)
    ev = ingest.ingest_packet("ITI-UP-001", first)
    assert ev["new_alerts"][0]["kind"] == "GHOST_ATTENDANCE"
    again = ingest.ingest_packet("ITI-UP-001", pkt("ITI-UP-001", prev=first["sig"], status="BREACH_GHOST_ATTENDANCE", ts=2060))
    assert again["new_alerts"] == []                                            # one open alert per centre and kind
    with db.pool.connection() as c:
        a = c.execute("SELECT * FROM alerts WHERE centre_code='ITI-UP-001'").fetchone()
        p = c.execute("SELECT * FROM packets WHERE id=%s", (a["packet_id"],)).fetchone()
        ctr = c.execute("SELECT code, name, state FROM centres WHERE code='ITI-UP-001'").fetchone()
    pdf, digest = build_notice(a, p, ctr, None, approved=False)
    assert pdf[:4] == b"%PDF" and len(digest) == 64

def test_missing_equipment_raises_equipment_alert():
    ev = ingest.ingest_packet("ITI-RJ-001", pkt("ITI-RJ-001", equipment={"lathe": "ABSENT"}, ts=3000))
    assert ev["new_alerts"][0]["kind"] == "EQUIPMENT_MISSING"

def test_api_needs_key_and_review_works_once():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as client:
        assert client.get("/api/summary").json()["centres"] == 12
        feats = client.get("/api/centres").json()["features"]
        colour = {f["properties"]["code"]: f["properties"]["colour_state"] for f in feats}
        assert colour["ITI-UP-001"] == "BREACH" and colour["ITI-DL-002"] == "NO_SIGNAL"   # open alert stays red; silent centre is grey
        near = client.get("/api/centres/near", params={"lat": 28.61, "lon": 77.21, "km": 50, "only_problems": "false"}).json()
        assert {r["code"] for r in near} == {"ITI-DL-001", "ITI-DL-002"}       # PostGIS radius query
        alert_id = client.get("/api/alerts").json()[0]["id"]
        body = {"decision": "APPROVE", "officer": "Officer-1"}
        assert client.post(f"/api/alerts/{alert_id}/review", json=body).status_code == 401
        h = {"X-API-Key": "secret-key"}
        assert client.get(f"/api/alerts/{alert_id}/notice.pdf").status_code == 401
        assert client.post(f"/api/alerts/{alert_id}/review", json=body, headers=h).status_code == 200
        assert client.post(f"/api/alerts/{alert_id}/review", json=body, headers=h).status_code == 404   # already reviewed
        r = client.get(f"/api/alerts/{alert_id}/notice.pdf", headers=h)
        assert r.status_code == 200 and r.content[:4] == b"%PDF" and "x-notice-sha256" in r.headers
