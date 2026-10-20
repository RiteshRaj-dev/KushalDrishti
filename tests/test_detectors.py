import sys, types
import numpy as np
import conftest  # noqa: F401  (sets sys.path)

class FakeModel:
    last = None
    def __init__(self, weights): self.weights, self.classes, self.kw = weights, None, None; FakeModel.last = self
    def set_classes(self, c): self.classes = c
    def predict(self, frame, **kw):
        self.kw = kw
        return [types.SimpleNamespace(boxes=[])]
    track = predict

def test_detector_knobs_are_passed_to_the_model(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeModel))
    from kd_edge.detectors import EquipmentAuditor, HeadcountEngine
    h = HeadcountEngine("cpu", weights="yolov8m.pt", conf=0.4, imgsz=960)
    assert h.count_single(np.zeros((10, 10, 3), np.uint8)) == 0
    assert FakeModel.last.weights == "yolov8m.pt" and FakeModel.last.kw["conf"] == 0.4 and FakeModel.last.kw["imgsz"] == 960
    a = EquipmentAuditor(["chair", "fire extinguisher"], "cpu", prompts={"fire extinguisher": "red fire extinguisher"})
    assert FakeModel.last.classes == ["chair", "red fire extinguisher"]
    counts, _ = a.inspect(np.zeros((10, 10, 3), np.uint8))
    assert counts == {"chair": 0, "fire extinguisher": 0}          # reported under the item name
