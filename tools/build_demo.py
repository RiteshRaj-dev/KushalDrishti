"""Builds the static demo for GitHub Pages into docs/: index.html, evidence_demo.jpg and two sample notice PDFs.
All data is SIMULATED and labelled so on the page. Run: python tools/build_demo.py"""
import json, os, random, sys
from datetime import datetime, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "edge")); sys.path.insert(0, os.path.join(ROOT, "shared")); sys.path.insert(0, ROOT)
from PIL import Image, ImageDraw, ImageFilter
import security
from kd_edge.config import Settings
from kd_edge.rules import judge_sample
from backend.app.notice import build_notice
DOCS = os.path.join(ROOT, "docs")
REPO = "https://github.com/RiteshRaj-dev/KushalDrishti"
CITIES = """Delhi,Delhi,28.61,77.21;Mumbai,Maharashtra,19.08,72.88;Kolkata,West Bengal,22.57,88.36;Chennai,Tamil Nadu,13.08,80.27;Bengaluru,Karnataka,12.97,77.59;Hyderabad,Telangana,17.39,78.49;Ahmedabad,Gujarat,23.02,72.57;Pune,Maharashtra,18.52,73.86;Jaipur,Rajasthan,26.91,75.79;Lucknow,Uttar Pradesh,26.85,80.95;Kanpur,Uttar Pradesh,26.45,80.35;Nagpur,Maharashtra,21.15,79.09;Indore,Madhya Pradesh,22.72,75.86;Bhopal,Madhya Pradesh,23.26,77.41;Patna,Bihar,25.59,85.14;Ranchi,Jharkhand,23.34,85.31;Bhubaneswar,Odisha,20.30,85.82;Guwahati,Assam,26.14,91.74;Chandigarh,Chandigarh,30.73,76.78;Amritsar,Punjab,31.63,74.87;Dehradun,Uttarakhand,30.32,78.03;Shimla,Himachal Pradesh,31.10,77.17;Srinagar,Jammu and Kashmir,34.08,74.80;Jammu,Jammu and Kashmir,32.73,74.86;Varanasi,Uttar Pradesh,25.32,83.01;Agra,Uttar Pradesh,27.18,78.02;Jodhpur,Rajasthan,26.24,73.02;Udaipur,Rajasthan,24.59,73.71;Surat,Gujarat,21.17,72.83;Vadodara,Gujarat,22.31,73.18;Rajkot,Gujarat,22.30,70.80;Nashik,Maharashtra,19.99,73.79;Aurangabad,Maharashtra,19.88,75.34;Raipur,Chhattisgarh,21.25,81.63;Visakhapatnam,Andhra Pradesh,17.69,83.22;Vijayawada,Andhra Pradesh,16.51,80.65;Mysuru,Karnataka,12.30,76.64;Kochi,Kerala,9.93,76.27;Thiruvananthapuram,Kerala,8.52,76.94;Coimbatore,Tamil Nadu,11.02,76.96;Madurai,Tamil Nadu,9.93,78.12;Mangaluru,Karnataka,12.91,74.86;Panaji,Goa,15.50,73.83;Gorakhpur,Uttar Pradesh,26.76,83.37;Prayagraj,Uttar Pradesh,25.44,81.85;Meerut,Uttar Pradesh,28.98,77.71;Ludhiana,Punjab,30.90,75.86;Siliguri,West Bengal,26.73,88.40;Imphal,Manipur,24.82,93.94;Shillong,Meghalaya,25.58,91.89;Agartala,Tripura,23.83,91.29"""
RED_CITY, AMBER_CITIES, GREY_CITIES = "Nagpur", ["Kanpur", "Raipur", "Madurai"], ["Imphal", "Srinagar"]

def centres():
    rnd, out = random.Random(26245), []
    for i, row in enumerate(CITIES.split(";")):
        city, state, lat, lon = row.split(",")
        claimed = rnd.randint(18, 36)
        st = "BREACH" if city == RED_CITY else "WATCH" if city in AMBER_CITIES else "NO_SIGNAL" if city in GREY_CITIES else "OK"
        counted = 6.2 if st == "BREACH" else round(claimed * rnd.uniform(0.62, 0.78), 1) if st == "WATCH" else None if st == "NO_SIGNAL" else round(claimed - rnd.choice([0, 0, 1, 1, 2]), 1)
        if city == RED_CITY: claimed = 30
        out.append({"code": f"DEMO-{i + 1:03d}", "name": f"Demo ITI {city}", "state": state, "lat": float(lat), "lon": float(lon),
                    "status": st, "claimed": claimed, "counted": counted})
    return out

def red_story():
    """Claimed 30; people arrive, then leave. Uses the real rule engine on 5-minute samples (15 min window, 30 min sustain)."""
    s = Settings(sustain_samples=6, tolerance=0.20)
    counted = [27, 29, 28, 26, 9, 7, 6, 6, 5, 6, 6]
    smooth, run, breach_at, first_gap = [], 0, None, None
    for k, c in enumerate(counted):
        window = counted[max(0, k - 2):k + 1]; sm = sum(window) / len(window); smooth.append(round(sm, 1))
        st, run, _ = judge_sample(s, 30, sm, run)
        if run == 1 and first_gap is None: first_gap = k
        if st == "BREACH_GHOST_ATTENDANCE" and breach_at is None: breach_at = k
    last = len(counted) - 1
    return {"minutes": [5 * k for k in range(len(counted))], "counted": counted, "smoothed": smooth, "claimed": 30,
            "first_gap_min": 5 * first_gap, "breach_min": 5 * breach_at, "gap_held_min": 5 * (last - first_gap) + 5, "now_min": 5 * last}

def evidence(path):
    img = Image.new("RGB", (854, 480), (52, 60, 76)); d = ImageDraw.Draw(img)
    for r in range(5):
        for c in range(6):
            x, y = 90 + c * 120, 70 + r * 72
            d.rounded_rectangle((x, y, x + 56, y + 40), 6, fill=(96, 106, 124))
    for (r, c) in [(0, 1), (1, 4), (2, 2), (3, 5), (3, 0), (4, 3)]:       # six people, shown as blurred blobs
        x, y = 90 + c * 120 + 28, 70 + r * 72 + 20
        d.ellipse((x - 18, y - 18, x + 18, y + 18), fill=(0, 168, 150))
    img = img.filter(ImageFilter.GaussianBlur(2.2)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 854, 34), fill=(11, 42, 74)); d.text((14, 11), "SIMULATED EVIDENCE | faces blurred | Demo ITI Nagpur", fill=(255, 255, 255))
    img.save(path, "JPEG", quality=70)

def notices(story):
    body = {"centre_code": "DEMO-012", "ts": int(datetime.now(timezone.utc).timestamp()), "status": "BREACH_GHOST_ATTENDANCE", "claimed_roll": 30}
    sig = security.seal("DEMO-012", body, "GENESIS")["sig"]
    packet = {"sig": sig, "claimed": 30, "headcount": 6.2, "camera_health": "OK", "ts": datetime.now(timezone.utc),
              "equipment": {"lathe": "PRESENT", "workbench": "PRESENT", "fire extinguisher": "PRESENT", "welding machine": "UNVERIFIED"}}
    centre = {"code": "DEMO-012", "name": "Demo ITI Nagpur (SIMULATED)", "state": "Maharashtra"}
    for name, ok in (("sample_notice_draft.pdf", False), ("sample_notice_approved.pdf", True)):
        alert = {"id": 1, "kind": "GHOST_ATTENDANCE", "reviewed_by": "Officer-17 (demo)", "reviewed_at": datetime.now()}
        pdf, _ = build_notice(alert, packet, centre, os.path.join(DOCS, "evidence_demo.jpg"), approved=ok)
        open(os.path.join(DOCS, name), "wb").write(pdf)

HTML = open(os.path.join(ROOT, "tools", "demo_template.html")).read()

def main():
    os.makedirs(DOCS, exist_ok=True); story = red_story()
    evidence(os.path.join(DOCS, "evidence_demo.jpg")); notices(story)
    html = HTML.replace("__DATA__", json.dumps(centres())).replace("__STORY__", json.dumps(story)).replace("__REPO__", REPO)
    open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(html)
    print("Built docs/index.html, evidence_demo.jpg, sample_notice_draft.pdf, sample_notice_approved.pdf |", story["first_gap_min"], story["breach_min"], story["gap_held_min"])

if __name__ == "__main__":
    main()
