import json, os, sqlite3
import cv2, numpy as np, pytest
import security
from conftest import FakeAuditor, FakeHead
from kd_edge.config import Settings
from kd_edge.health import check_camera_health
from kd_edge.packets import MinuteAggregator
from kd_edge.pipeline import run_video
from kd_edge.privacy import FaceAnonymizer, to_evidence
from kd_edge.rules import EquipmentMemory, judge_sample
from kd_edge.transport import EdgeLink

S = Settings(sustain_samples=3)

def test_rule_engine_warns_then_breaches_then_recovers():
    run, seq = 0, []
    for smoothed in [18, 10, 10, 10, 10, 18]:
        st, run, _ = judge_sample(S, 18, smoothed, run); seq.append(st)
    assert seq == ["COMPLIANT", "WARNING_SUSPECTED_GAP", "WARNING_SUSPECTED_GAP", "BREACH_GHOST_ATTENDANCE", "BREACH_GHOST_ATTENDANCE", "COMPLIANT"]

def test_short_break_is_not_a_breach():
    run = 0
    for smoothed in [10, 10, 18, 10, 10, 18]:
        st, run, _ = judge_sample(S, 18, smoothed, run)
        assert st != "BREACH_GHOST_ATTENDANCE"

def test_equipment_memory_present_absent_unverified():
    m = EquipmentMemory(["a", "b", "c"], 3)
    assert set(m.status().values()) == {"UNVERIFIED"}
    for seen in [(1, 0, 1), (1, 0, 0), (1, 0, 0)]:
        m.update({"a": seen[0], "b": seen[1], "c": seen[2]})
    assert m.status() == {"a": "PRESENT", "b": "ABSENT", "c": "UNVERIFIED"}

def test_camera_health():
    rng = np.random.default_rng(1)
    good = rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)
    assert check_camera_health(good, S) == "OK"
    assert check_camera_health(None, S) == "OFFLINE"
    assert check_camera_health(np.full((120, 160, 3), 128, np.uint8), S) == "BLOCKED"
    assert check_camera_health((good * 0.03).astype(np.uint8), S) in ("TOO_DARK", "BLOCKED")
    assert check_camera_health(cv2.GaussianBlur(good, (51, 51), 20), S) in ("BLURRED", "BLOCKED")

def test_face_blur_keeps_shape_and_evidence_is_480p():
    img = np.random.default_rng(2).integers(0, 255, (720, 1280, 3), dtype=np.uint8)
    out, n = FaceAnonymizer().anonymize(img)
    assert out.shape == img.shape and n >= 0 and to_evidence(out).shape[0] == 480

def test_signature_chain_survives_restart_and_detects_tampering(tmp_path):
    db = str(tmp_path / "o.db")
    link = EdgeLink("ITI-T-1", None, 1883, db)
    p1 = link.send_packet({"centre_code": "ITI-T-1", "ts": 1, "status": "COMPLIANT", "claimed_roll": 18})
    p2 = link.send_packet({"centre_code": "ITI-T-1", "ts": 2, "status": "COMPLIANT", "claimed_roll": 18})
    assert p2["prev_sig"] == p1["sig"] and security.verify(p1) and security.verify(p2) and link.pending() == 2
    assert not security.verify({**p2, "claimed_roll": 99})
    assert EdgeLink("ITI-T-1", None, 1883, db).prev_sig == p2["sig"]       # chain continues after a restart
    assert link.flush() == 0 and link.pending() == 2                       # no broker: nothing is lost

def test_aggregator_one_packet_per_minute_with_worst_status():
    agg = MinuteAggregator(S, 1000); out = []
    for t, st in [(5, "COMPLIANT"), (30, "WARNING_SUSPECTED_GAP"), (55, "COMPLIANT"), (65, "COMPLIANT")]:
        out.append(agg.add({"centre_time_sec": t, "claimed_attendance": 18, "adjusted_headcount": 10.0, "smoothed_presence": 10.0,
                            "compliance_status": st, "camera_health": "OK", "equipment_status": json.dumps({"x": "PRESENT"})}))
    out.append(agg.flush())
    done = [o for o in out if o]
    assert len(done) == 2 and done[0]["status"] == "WARNING_SUSPECTED_GAP" and done[1]["status"] == "COMPLIANT" and done[0]["ts"] == 1060

def make_video(path, seconds=30, fps=10):
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    rng = np.random.default_rng(3)
    for _ in range(seconds * fps):
        w.write(rng.integers(0, 255, (240, 320, 3), dtype=np.uint8))
    w.release()

def test_full_pipeline_on_video_finds_ghost_attendance_and_sends_signed_chain(tmp_path):
    video = str(tmp_path / "v.mp4"); make_video(video)
    s = Settings(centre_code="ITI-T-2").demo()
    link = EdgeLink("ITI-T-2", None, 1883, str(tmp_path / "o.db"))
    df = run_video(video, s, FakeHead(6), FakeAuditor(s.items, {"chair"}), link=link, evidence_dir=str(tmp_path / "ev"), base_ts=5000, log=lambda *_: None)
    st = df["compliance_status"].tolist()
    assert st[0] == "WARNING_SUSPECTED_GAP" and "BREACH_GHOST_ATTENDANCE" in st and st.index("BREACH_GHOST_ATTENDANCE") == s.sustain_samples - 1
    rows = sqlite3.connect(str(tmp_path / "o.db")).execute("SELECT topic, payload FROM outbox ORDER BY id").fetchall()
    tele = [json.loads(p) for t, p in rows if "telemetry" in t]
    assert len(tele) == 3 and all(security.verify(p) for p in tele)
    assert tele[1]["prev_sig"] == tele[0]["sig"] and tele[0]["equipment"]["chair"] in ("PRESENT", "UNVERIFIED")
    assert any("evidence" in t for t, _ in rows) and os.listdir(tmp_path / "ev")

def test_camera_issue_is_never_a_breach(tmp_path):
    video = str(tmp_path / "dark.mp4")
    w = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
    for _ in range(200): w.write(np.zeros((240, 320, 3), np.uint8))
    w.release()
    s = Settings().demo()
    df = run_video(video, s, FakeHead(0), FakeAuditor(s.items, set()), log=lambda *_: None)
    assert set(df["compliance_status"]) == {"CAMERA_ISSUE"}

def test_evaluation_math():
    from kd_edge.evaluate import prf, score_counts, score_flags
    assert score_counts([5, 7], [6, 6]) == (11, 1, 1)
    assert score_flags([1, 1, 0, 0], [1, 0, 1, 0]) == (1, 1, 1)
    assert prf(0, 0, 0) == (None, None)
