import json, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_static_demo_builds_with_one_breach_and_labels_data_as_simulated(tmp_path):
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_demo.py")], check=True, capture_output=True)
    html = open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8").read()
    data = json.loads(re.search(r"const DATA=(\[.*?\]), STORY=", html, re.S).group(1))
    story = json.loads(re.search(r"STORY=(\{.*?\}), COL=", html, re.S).group(1))
    assert len(data) == 51 and sum(c["status"] == "BREACH" for c in data) == 1
    assert story["gap_held_min"] >= 30 and "SIMULATED DATA" in html
    for f in ("evidence_demo.jpg", "sample_notice_draft.pdf", "sample_notice_approved.pdf"):
        assert os.path.getsize(os.path.join(ROOT, "docs", f)) > 5000
