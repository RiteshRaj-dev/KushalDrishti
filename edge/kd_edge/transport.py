"""Store-and-forward link: every packet goes into a local SQLite buffer first and is marked sent only after the
broker confirms it (MQTT QoS 1). A multi-day outage loses nothing, and the signature chain survives restarts."""
import json, os, sqlite3, threading
import paho.mqtt.client as mqtt
import security

class EdgeLink:
    def __init__(self, centre, host, port, db_path):
        self.centre = centre
        self.offline = threading.Event()            # set it to simulate a cut internet line
        self.lock, self.flush_lock, self.wake = threading.Lock(), threading.Lock(), threading.Event()
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, topic TEXT, payload BLOB, sent INTEGER DEFAULT 0)")
        row = self.db.execute("SELECT payload FROM outbox WHERE topic LIKE 'msde/telemetry/%' ORDER BY id DESC LIMIT 1").fetchone()
        self.prev_sig = json.loads(row[0])["sig"] if row else "GENESIS"
        self.client = None
        if host:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"edge-{centre}", clean_session=False)
            self.client.on_connect = lambda c, u, f, rc, p=None: self.wake.set()   # never block inside a paho callback
            self.client.connect_async(host, port, keepalive=30)
            self.client.loop_start()
            threading.Thread(target=self._flusher, daemon=True).start()

    def pending(self):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM outbox WHERE sent = 0").fetchone()[0]

    def enqueue(self, topic, payload: bytes):
        with self.lock:
            self.db.execute("INSERT INTO outbox (topic, payload) VALUES (?, ?)", (topic, payload))
            self.db.commit()

    def send_packet(self, body):
        packet = security.seal(self.centre, body, self.prev_sig)
        self.prev_sig = packet["sig"]
        self.enqueue(f"msde/telemetry/{self.centre}", security.canonical(packet).encode())
        return packet

    def send_evidence(self, sig, jpeg: bytes):
        if jpeg:
            self.enqueue(f"msde/evidence/{self.centre}/{sig}", jpeg)

    def _flusher(self):
        while True:
            self.wake.wait(timeout=2)
            self.wake.clear()
            try:
                self.flush()
            except Exception as err:
                print(f"[{self.centre}] flush error: {err}")

    def flush(self):
        """Send everything pending, oldest first."""
        if self.client is None or self.offline.is_set() or not self.client.is_connected() or not self.flush_lock.acquire(blocking=False):
            return 0
        try:
            with self.lock:
                rows = self.db.execute("SELECT id, topic, payload FROM outbox WHERE sent = 0 ORDER BY id").fetchall()
            sent = 0
            for pid, topic, payload in rows:
                try:
                    info = self.client.publish(topic, payload, qos=1)
                    info.wait_for_publish(timeout=5)
                except (RuntimeError, ValueError):
                    break
                if not info.is_published():
                    break
                with self.lock:
                    self.db.execute("UPDATE outbox SET sent = 1 WHERE id = ?", (pid,))
                    self.db.commit()
                sent += 1
            return sent
        finally:
            self.flush_lock.release()

    def close(self):
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
