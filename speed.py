"""Speed test: python -m kd_edge.speed [--image frame.jpg]. Fills the CPU load on slide 4 (say which machine measured it)."""
import argparse, json, os, time
import cv2
import numpy as np
from .config import Settings

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--image"); ap.add_argument("--runs", type=int, default=15)
    ap.add_argument("--out", default="outputs"); a = ap.parse_args()
    from .detectors import EquipmentAuditor, HeadcountEngine
    s = Settings()
    frame = cv2.imread(a.image) if a.image else np.full((480, 640, 3), 90, np.uint8)
    head, aud = HeadcountEngine("cpu"), EquipmentAuditor(s.items, "cpu")
    def avg_ms(fn):
        fn(); t0 = time.perf_counter()
        for _ in range(a.runs):
            fn()
        return round((time.perf_counter() - t0) / a.runs * 1000, 1)
    h, e = avg_ms(lambda: head.count_single(frame, "cpu")), avg_ms(lambda: aud.inspect(frame, "cpu"))
    rep = {"measured_on": f"CPU, {os.cpu_count()} cores, {a.runs} runs", "headcount_ms": h, "equipment_ms": e,
           "approx_cpu_busy_pct_at_one_frame_per_5s": round((h + e) / 5000 * 100, 1)}
    os.makedirs(a.out, exist_ok=True)
    json.dump(rep, open(os.path.join(a.out, "speed_report.json"), "w"), indent=2); print(rep)

if __name__ == "__main__":
    main()
