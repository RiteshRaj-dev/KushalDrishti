"""Accuracy test that fills the false-positive / false-negative table on slide 4. It needs YOUR labels:
    python -m kd_edge.evaluate prepare --video classroom.mp4        (saves frames and ground_truth.csv)
    # open the frames, fill true_headcount and a 1 or 0 for every equipment column in ground_truth.csv
    python -m kd_edge.evaluate run --claimed 18                     (writes accuracy_table.csv and evaluation_summary.json)"""
import argparse, json, os
import cv2
import numpy as np
import pandas as pd
from .config import SAFETY_ITEMS, Settings, TRADES
from .privacy import FaceAnonymizer

def prepare(video, folder, items, n=40):
    os.makedirs(folder, exist_ok=True)
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    names = []
    for i in np.linspace(0, max(0, total - 2), min(n, total)).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if ok:
            name = f"frame_{int(i):06d}.jpg"
            cv2.imwrite(os.path.join(folder, name), frame)   # raw frames: keep this folder private, never publish it
            names.append(name)
    cap.release()
    gt = pd.DataFrame({"frame_file": names, "true_headcount": np.nan})
    for item in items:
        gt[item] = np.nan
    gt.to_csv(os.path.join(folder, "ground_truth.csv"), index=False)
    return len(names)

def prf(tp, fp, fn):
    return (round(tp / (tp + fp), 3) if tp + fp else None, round(tp / (tp + fn), 3) if tp + fn else None)

def score_counts(pred, true):
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    return (int(np.minimum(pred, true).sum()), int(np.maximum(pred - true, 0).sum()), int(np.maximum(true - pred, 0).sum()))

def score_flags(pred, true):
    pred, true = np.asarray(pred, bool), np.asarray(true, bool)
    return (int((pred & true).sum()), int((pred & ~true).sum()), int((~pred & true).sum()))

def evaluate(folder, s, head, auditor):
    gt = pd.read_csv(os.path.join(folder, "ground_truth.csv"))
    cols = ["true_headcount", *s.items]
    if gt[cols].isna().any().any():
        raise SystemExit("ground_truth.csv still has blanks. Fill true_headcount and every item column (1 or 0).")
    privacy, pred_heads, pred_items = FaceAnonymizer(), [], {i: [] for i in s.items}
    for name in gt["frame_file"]:
        blurred, _ = privacy.anonymize(cv2.imread(os.path.join(folder, name)))
        pred_heads.append(max(0, head.count_single(blurred) - s.instructors_in_room))
        counts, _ = auditor.inspect(blurred)
        for i in s.items:
            pred_items[i].append(counts[i] > 0)
    pred_heads, true_heads = np.array(pred_heads), gt["true_headcount"].to_numpy(float)
    flag = lambda h: (s.claimed_attendance - h) / s.claimed_attendance > s.tolerance
    def pool(items):
        t = np.zeros(3, int)
        for i in items:
            t += np.array(score_flags(pred_items[i], gt[i].to_numpy(bool)))
        return tuple(int(x) for x in t)
    tasks = {"Classroom Headcount": score_counts(pred_heads, true_heads),
             "Equipment Present": pool([i for i in s.items if i not in SAFETY_ITEMS]),
             "Safety Items": pool([i for i in s.items if i in SAFETY_ITEMS]),
             "Attendance Mismatch": score_flags(flag(pred_heads), flag(true_heads))}
    rows = []
    for task, (tp, fp, fn) in tasks.items():
        p, r = prf(tp, fp, fn)
        rows.append({"Task": task, "Precision": p, "Recall": r, "False Positive": fp, "False Negative": fn})
    table = pd.DataFrame(rows)
    summary = {"frames": int(len(gt)), "headcount_mae": round(float(np.abs(pred_heads - true_heads).mean()), 2)}
    return table, summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "run"]); ap.add_argument("--video"); ap.add_argument("--folder", default="eval_frames")
    ap.add_argument("--trade", default="classroom_demo", choices=list(TRADES)); ap.add_argument("--claimed", type=int, default=18)
    ap.add_argument("--n", type=int, default=40); ap.add_argument("--out", default="outputs"); ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    s = Settings(trade=a.trade, claimed_attendance=a.claimed)
    if a.cmd == "prepare":
        print(f"Saved {prepare(a.video, a.folder, s.items, a.n)} frames and {a.folder}/ground_truth.csv. Fill it in, then run: run")
        return
    from .detectors import EquipmentAuditor, HeadcountEngine
    table, summary = evaluate(a.folder, s, HeadcountEngine(a.device), EquipmentAuditor(s.items, a.device))
    os.makedirs(a.out, exist_ok=True)
    table.to_csv(os.path.join(a.out, "accuracy_table.csv"), index=False)
    json.dump(summary, open(os.path.join(a.out, "evaluation_summary.json"), "w"), indent=2)
    print(table.to_string(index=False)); print(summary)

if __name__ == "__main__":
    main()
