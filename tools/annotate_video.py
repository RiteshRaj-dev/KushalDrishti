"""Makes the "processed" demo video: faces blurred, teal boxes on people (no names), amber boxes on equipment,
live counted vs claimed, status and an equipment checklist. Works on a real clip with the real models.
    python tools/annotate_video.py --video classroom.mp4 --out processed.mp4 --claimed 18 --demo --max-seconds 30"""
import argparse, os, shutil, subprocess, sys
from collections import deque
import cv2
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edge"))
from kd_edge.config import Settings, TRADES
from kd_edge.health import check_camera_health
from kd_edge.privacy import FaceAnonymizer
from kd_edge.rules import EquipmentMemory, judge_sample

TEAL, AMBER, GREEN, RED, GREY, NAVY, WHITE = (150, 168, 0), (11, 158, 245), (90, 158, 46), (46, 87, 228), (154, 134, 122), (74, 42, 11), (255, 255, 255)
STATUS_COLOUR = {"COMPLIANT": GREEN, "WARNING_SUSPECTED_GAP": AMBER, "BREACH_GHOST_ATTENDANCE": RED, "CAMERA_ISSUE": GREY}
STATUS_TEXT = {"COMPLIANT": "COMPLIANT", "WARNING_SUSPECTED_GAP": "WARNING: GAP", "BREACH_GHOST_ATTENDANCE": "BREACH: GHOST ATTENDANCE", "CAMERA_ISSUE": "CAMERA ISSUE"}
ITEM_COLOUR = {"PRESENT": GREEN, "ABSENT": RED, "UNVERIFIED": GREY}

def panel(img, x, y, w, h, alpha=0.65):
    over = img.copy(); cv2.rectangle(over, (x, y), (x + w, y + h), NAVY, -1); cv2.addWeighted(over, alpha, img, 1 - alpha, 0, img)

def text(img, t, x, y, scale=0.55, colour=WHITE, bold=1):
    cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, colour, bold, cv2.LINE_AA)

def annotate(video, out, s, head, auditor, every=2, max_seconds=None, log=print):
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = out + ".tmp.mp4"
    writer = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    privacy, memory = FaceAnonymizer(), EquipmentMemory(s.items, s.equipment_votes)
    window, breach_run, status, equip = deque(maxlen=s.window_samples), 0, "COMPLIANT", memory.unverified()
    people, things, smoothed, step, idx, n_sample = [], [], 0.0, max(1, int(fps * s.video_sample_sec)), 0, 0
    limit = int(max_seconds * fps) if max_seconds else None
    while limit is None or idx < limit:
        ok, raw = cap.read()
        if not ok:
            break
        health = check_camera_health(raw, s)
        frame, _ = privacy.anonymize(raw)                       # blur first, then draw
        if health == "OK" and idx % every == 0:
            people, things = head.boxes(frame), auditor.detections(frame)
        if idx % step == 0:
            n_sample += 1
            if health != "OK":
                status, equip = "CAMERA_ISSUE", memory.unverified()
            else:
                counted = max(0, len(people) - s.instructors_in_room)
                window.append(counted); smoothed = float(np.mean(window))
                counts = {i: 0 for i in s.items}
                for d in things:
                    counts[d[4]] = counts.get(d[4], 0) + 1
                memory.update(counts); equip = memory.status()
                status, breach_run, _ = judge_sample(s, s.claimed_attendance, smoothed, breach_run)
        for (x1, y1, x2, y2, _c) in people:
            cv2.rectangle(frame, (x1, y1), (x2, y2), TEAL, 2)
        for (x1, y1, x2, y2, label, _c) in things:
            cv2.rectangle(frame, (x1, y1), (x2, y2), AMBER, 2); text(frame, str(label), x1, max(14, y1 - 6), 0.5, AMBER)
        gap = max(0.0, (s.claimed_attendance - smoothed) / s.claimed_attendance) * 100
        panel(frame, 10, 10, 330, 150)
        text(frame, "KushalDrishti | Team VeriGuard", 20, 32, 0.55, WHITE, 2)
        text(frame, f"Counted now: {len(people)}", 20, 58); text(frame, f"Average (window): {smoothed:.1f}", 20, 80)
        text(frame, f"Claimed on portal: {s.claimed_attendance}", 20, 102); text(frame, f"Gap: {gap:.0f}%   Camera: {health}", 20, 124)
        cv2.rectangle(frame, (20, 134), (330, 152), STATUS_COLOUR[status], -1); text(frame, STATUS_TEXT[status], 26, 148, 0.5, WHITE, 2)
        panel(frame, W - 250, 10, 240, 34 + 24 * len(equip))
        text(frame, "Equipment", W - 240, 32, 0.55, WHITE, 2)
        for k, (item, st) in enumerate(equip.items()):
            y = 56 + 24 * k; cv2.circle(frame, (W - 236, y - 5), 6, ITEM_COLOUR[st], -1); text(frame, f"{item}: {st.lower()}", W - 224, y, 0.45)
        panel(frame, 10, H - 40, W - 20, 30, 0.55)
        text(frame, "Faces blurred at the centre. People counted as a number only. No identity stored.", 20, H - 20, 0.5)
        writer.write(frame); idx += 1
    cap.release(); writer.release()
    if shutil.which("ffmpeg"):                                  # H.264 plays in browsers and Google Drive
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-vcodec", "libx264", "-pix_fmt", "yuv420p", out], check=False)
        if os.path.exists(out): os.remove(tmp)
        else: os.replace(tmp, out)
    else:
        os.replace(tmp, out)
    log(f"Wrote {out} ({idx} frames)")
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True); ap.add_argument("--out", default="processed.mp4")
    ap.add_argument("--trade", default="classroom_demo", choices=list(TRADES)); ap.add_argument("--claimed", type=int, default=18)
    ap.add_argument("--demo", action="store_true"); ap.add_argument("--max-seconds", type=float, default=30); ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    s = Settings(trade=a.trade, claimed_attendance=a.claimed)
    s = s.demo() if a.demo else s
    from kd_edge.detectors import EquipmentAuditor, HeadcountEngine
    annotate(a.video, a.out, s, HeadcountEngine(a.device), EquipmentAuditor(s.items, a.device), max_seconds=a.max_seconds)
