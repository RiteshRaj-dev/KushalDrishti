"""Run the full edge pipeline on a video file or a camera stream URL.
    python -m kd_edge.run --video classroom.mp4 --centre ITI-DL-001 --claimed 18 --demo --mqtt-host localhost"""
import argparse, json, os, time
from dataclasses import asdict, replace
from .config import Settings, TRADES

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="video file or RTSP URL")
    ap.add_argument("--centre", default="DEMO-CENTRE"); ap.add_argument("--trade", default="classroom_demo", choices=list(TRADES))
    ap.add_argument("--claimed", type=int, default=18); ap.add_argument("--instructors", type=int, default=0)
    ap.add_argument("--demo", action="store_true", help="short timings for a short video (not deployment timing)")
    ap.add_argument("--mqtt-host", default=None); ap.add_argument("--mqtt-port", type=int, default=1883)
    ap.add_argument("--out", default="outputs"); ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    s = Settings(centre_code=a.centre, trade=a.trade, claimed_attendance=a.claimed, instructors_in_room=a.instructors)
    if a.demo:
        s = s.demo(); print("DEMO TIMING ON: window 6 samples, sustain 12 samples. Not the deployment timing (180 / 360).")
    from .detectors import EquipmentAuditor, HeadcountEngine
    from .pipeline import run_video
    from .transport import EdgeLink
    os.makedirs(a.out, exist_ok=True)
    link = EdgeLink(a.centre, a.mqtt_host, a.mqtt_port, os.path.join(a.out, f"{a.centre}_outbox.db"))
    df = run_video(a.video, s, HeadcountEngine(a.device), EquipmentAuditor(s.items, a.device), link=link, evidence_dir=os.path.join(a.out, "evidence_frames"))
    df.to_csv(os.path.join(a.out, "telemetry_audit_stream.csv"), index=False)
    with open(os.path.join(a.out, "run_info.json"), "w") as f:
        json.dump({"demo_mode": a.demo, "synthetic_video": False, "settings": asdict(s)}, f, indent=2)
    if a.mqtt_host:
        time.sleep(3); link.flush()
    print(df["compliance_status"].value_counts().to_string(), f"\npackets waiting: {link.pending()}")
    link.close()

if __name__ == "__main__":
    main()
