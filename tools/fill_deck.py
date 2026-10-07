"""Writes YOUR measured results into the blanks of the SIH deck (python-pptx). Nothing is invented: a blank stays
blank unless you pass its value.
    python tools/fill_deck.py SIH26245.pptx SIH26245_filled.pptx --accuracy outputs/accuracy_table.csv \
        --summary outputs/evaluation_summary.json --speed outputs/speed_report.json --video https://youtu.be/xxxx"""
import argparse, csv, json
from pptx import Presentation

def fmt(v):
    return "n/a" if v in (None, "", "None") else str(v)

def fill(src, dst, accuracy=None, summary=None, speed=None, video=None):
    prs, done = Presentation(src), []
    table = {}
    if accuracy:
        for r in csv.DictReader(open(accuracy)):
            table[r["Task"]] = r
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_table:
                t = sh.table
                if [c.text for c in t.rows[0].cells][:1] != ["Task"]:
                    continue
                for row in list(t.rows)[1:]:
                    cells = list(row.cells); r = table.get(cells[0].text.strip())
                    if not r:
                        continue
                    for cell, key in zip(cells[1:5], ["Precision", "Recall", "False Positive", "False Negative"]):
                        for p in cell.text_frame.paragraphs:
                            for run in p.runs:
                                if run.text.strip() == "[ ]":
                                    run.text = fmt(r[key]); done.append(f"{cells[0].text.strip()} {key}")
            if not sh.has_text_frame:
                continue
            for p in sh.text_frame.paragraphs:
                for run in p.runs:
                    if "[measure on test footage]" in run.text and summary:
                        run.text = run.text.replace("[measure on test footage]", f"{summary['headcount_mae']} people average error"); done.append("headcount error")
                    if "CPU load: [measure]" in run.text and speed:
                        run.text = run.text.replace("CPU load: [measure]", f"CPU load: about {speed['approx_cpu_busy_pct_at_one_frame_per_5s']}%"); done.append("cpu load")
                    if "[Insert unlisted YouTube URL]" in run.text and video:
                        run.text = video; run.hyperlink.address = video; done.append("video link")
    prs.save(dst)
    return done

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--accuracy"); ap.add_argument("--summary"); ap.add_argument("--speed"); ap.add_argument("--video")
    a = ap.parse_args()
    d = fill(a.src, a.dst, a.accuracy, json.load(open(a.summary)) if a.summary else None, json.load(open(a.speed)) if a.speed else None, a.video)
    print("Filled:", ", ".join(d) or "nothing (no matching blanks)")
