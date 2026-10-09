import json, os, time
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DSN = os.environ.get("DATABASE_URL", "postgresql://kd:kd@localhost:5432/kd")
pool = ConnectionPool(DSN, min_size=1, max_size=10, kwargs={"row_factory": dict_row}, open=False)

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS centres (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, state TEXT,
  geom GEOGRAPHY(Point, 4326) NOT NULL);
CREATE TABLE IF NOT EXISTS packets (
  id BIGSERIAL PRIMARY KEY,
  centre_code TEXT NOT NULL REFERENCES centres(code),
  ts TIMESTAMPTZ NOT NULL, status TEXT NOT NULL, claimed INT, headcount REAL, smoothed REAL,
  camera_health TEXT, equipment JSONB, prev_sig TEXT, sig TEXT UNIQUE NOT NULL,
  chain_ok BOOLEAN NOT NULL, received_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX IF NOT EXISTS packets_centre_ts ON packets (centre_code, ts DESC);
CREATE TABLE IF NOT EXISTS alerts (
  id BIGSERIAL PRIMARY KEY, centre_code TEXT NOT NULL REFERENCES centres(code),
  packet_id BIGINT REFERENCES packets(id), kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN',
  reviewed_by TEXT, reviewed_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS notices (
  id BIGSERIAL PRIMARY KEY, alert_id BIGINT REFERENCES alerts(id), sha256 TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now());
"""

def wait_for_db(timeout=90):
    """The database may still be starting (first start runs set-up scripts). Retry instead of crashing."""
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            psycopg.connect(DSN, connect_timeout=3).close()
            return
        except psycopg.OperationalError as err:
            last = err
            time.sleep(2)
    raise RuntimeError(f"Database not reachable after {timeout} s: {last}")

def init(centres_file: str):
    wait_for_db()
    pool.open(wait=True, timeout=30)
    with pool.connection() as c:
        c.execute(SCHEMA)
        for ct in json.load(open(centres_file)):
            c.execute("""INSERT INTO centres (code, name, state, geom)
                         VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
                         ON CONFLICT (code) DO NOTHING""",
                      (ct["code"], ct["name"], ct["state"], ct["lon"], ct["lat"]))
