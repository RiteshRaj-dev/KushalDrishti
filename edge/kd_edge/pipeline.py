import json, os, time
from collections import deque
import cv2
import numpy as np
import pandas as pd
from .health import check_camera_health
from .packets import MinuteAggregator
from .privacy import FaceAnonymizer, encode_jpeg, to_evidence
from .rules import EquipmentMemory, judge_sample

def run_video(video_path, s, head, auditor, link=None, evidence_dir=None, max_samples=300, base_ts=None, log=print):
    """Reads a video as if it were a live camera: health check, face blur, count, equipment, rules, signed packets.
    `head` needs .count(frame); `auditor` needs .inspect(frame) -> (counts, annotated)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(fps * s.video_sample_sec))
    privacy, memory = FaceAnonymizer(), EquipmentMemory(s.items, s.equipment_votes)
    window, rows, breach_run, frame_idx, n = deque(maxlen=s.window_samples), [], 0, 0, 0
    agg = MinuteAggregator(s, base_ts if base_ts is not None else int(time.time()))
    claimed, last_evidence = s.claimed_attendance, None
    if evidence_dir:
        os.makedirs(evidence_dir, exist_ok=True)

    def emit(body):
        nonlocal last_evidence
        if body is None or link is None:
            return
        packet = link.send_packet(body)
        if packet["status"] == "BREACH_GHOST_ATTENDANCE" and last_evidence:
            link.send_evidence(packet["sig"], last_evidence)
        link.flush()

    while n < max_samples:
        ok, raw = cap.read()
        if not ok:
            break
        if frame_idx % step == 0:
            n += 1
            row = {"sample_no": n, "centre_time_sec": n * s.sample_sec, "video_time_sec": round(frame_idx / fps, 2),
                   "claimed_attendance": claimed}
            health = check_camera_health(raw, s)
            row["camera_health"] = health
            if health != "OK":
                row.update(counted_headcount=np.nan, adjusted_headcount=np.nan, smoothed_presence=np.nan, gap_ratio=np.nan,
                           discrepancy_gap=np.nan, compliance_status="CAMERA_ISSUE", breach_run=breach_run, faces_anonymized=0,
                           equipment_status=json.dumps(memory.unverified()), equipment_counts="{}")
            else:
                blurred, faces = privacy.anonymize(raw)              # blur first, then analyse
                heads = int(head.count(blurred))
                adjusted = max(0, heads - s.instructors_in_room)
                window.append(adjusted)
                smoothed = float(np.mean(window))
                counts, shown = auditor.inspect(blurred)
                memory.update(counts)
                status, breach_run, gap = judge_sample(s, claimed, smoothed, breach_run)
                row.update(counted_headcount=heads, adjusted_headcount=adjusted, smoothed_presence=round(smoothed, 2),
                           gap_ratio=round(gap, 3), discrepancy_gap=round(claimed - smoothed, 2), compliance_status=status,
                           breach_run=breach_run, faces_anonymized=faces, equipment_status=json.dumps(memory.status()),
                           equipment_counts=json.dumps(counts))
                if status == "BREACH_GHOST_ATTENDANCE":              # evidence photo only on a confirmed breach
                    last_evidence = encode_jpeg(to_evidence(shown))
                    if evidence_dir and (breach_run - s.sustain_samples) % 10 == 0:
                        with open(os.path.join(evidence_dir, f"breach_sample{n}.jpg"), "wb") as f:
                            f.write(last_evidence)
            rows.append(row)
            emit(agg.add(row))
        frame_idx += 1
    cap.release()
    emit(agg.flush())
    if not rows:
        raise RuntimeError("No frames were read from the video.")
    log(f"{len(rows)} samples processed.")
    return pd.DataFrame(rows)
