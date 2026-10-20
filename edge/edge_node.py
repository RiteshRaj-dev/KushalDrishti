"""Simulated centre for demos and load tests (no camera needed). The real pipeline is `python -m kd_edge.run`.
    python edge/edge_node.py --centre ITI-DL-001 --scenario ghost --interval 1 --outage-after 2 --outage-packets 4"""
import argparse, io, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kd_edge.transport import EdgeLink

class EdgeNode:
    def __init__(self, centre, host, port, db_path, scenario="ok", claimed=18):
        self.centre, self.scenario, self.claimed, self.minute = centre, scenario, claimed, 0
        self.link = EdgeLink(centre, host, port, db_path)
        self.offline, self.pending = self.link.offline, self.link.pending

    def simulate_minute(self):
        self.minute += 1
        if self.scenario == "ghost":
            heads, status = random.randint(5, 7), ("BREACH_GHOST_ATTENDANCE" if self.minute > 3 else "WARNING_SUSPECTED_GAP")
        else:
            heads, status = random.randint(16, 19), "COMPLIANT"
        equip = {"chair": "PRESENT", "laptop": "PRESENT", "workbench": "PRESENT",
                 "fire extinguisher": "ABSENT" if self.scenario == "equipment" and self.minute > 2 else "PRESENT"}
        return {"centre_code": self.centre, "trade": "classroom_demo", "ts": int(time.time()), "minute": self.minute,
                "claimed_roll": self.claimed, "mean_headcount": float(heads), "smoothed_presence": float(heads),
                "status": status, "camera_health": "OK", "equipment": equip, "faces_blurred": True}

    def evidence_jpeg(self, sig):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (854, 480), (60, 66, 80)); d = ImageDraw.Draw(img)
        d.text((20, 20), f"SIMULATED BLURRED EVIDENCE | {self.centre}", fill=(255, 255, 255)); d.text((20, 40), f"packet {sig[:16]}", fill=(200, 200, 200))
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=65)
        return buf.getvalue()

    def tick(self):
        packet = self.link.send_packet(self.simulate_minute())
        if packet["status"] == "BREACH_GHOST_ATTENDANCE" and packet["minute"] % 4 == 0:
            self.link.send_evidence(packet["sig"], self.evidence_jpeg(packet["sig"]))
        return self.link.flush()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--centre", default="ITI-DL-001"); ap.add_argument("--host", default="localhost"); ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--scenario", default="ghost", choices=["ok", "ghost", "equipment"]); ap.add_argument("--interval", type=float, default=3)
    ap.add_argument("--outage-after", type=int, default=0); ap.add_argument("--outage-packets", type=int, default=5)
    a = ap.parse_args()
    node, n = EdgeNode(a.centre, a.host, a.port, f"data/{a.centre}.db", a.scenario), 0
    while True:
        n += 1
        if a.outage_after and n == a.outage_after + 1:
            node.offline.set(); print("!! line cut: packets will queue")
        if a.outage_after and n == a.outage_after + a.outage_packets + 1:
            node.offline.clear(); print(f"!! line back: {node.pending()} queued, flushing")
        print(f"packet {n} made, sent {node.tick()}, waiting {node.pending()}"); time.sleep(a.interval)
