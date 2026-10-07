"""Model wrappers. ultralytics is imported only when a detector is created, so the rest of the package
(and its tests) run without PyTorch."""
import cv2

class HeadcountEngine:
    def __init__(self, device="cpu", weights="yolov8n.pt"):
        from ultralytics import YOLO
        self.model, self.device = YOLO(weights), device

    def count(self, frame):
        """People in this frame, tracked with ByteTrack. Keeps no identity, only a number.
        At one frame every 5 seconds the tracker cannot follow people between frames, so the count is per frame."""
        r = self.model.track(frame, classes=[0], tracker="bytetrack.yaml", persist=True, verbose=False, device=self.device)[0]
        return len(r.boxes)

    def count_single(self, frame, device=None):
        """Count one unrelated frame (accuracy test, speed test)."""
        return len(self.model.predict(frame, classes=[0], verbose=False, device=device or self.device)[0].boxes)

class EquipmentAuditor:
    def __init__(self, items, device="cpu", weights="yolov8s-worldv2.pt"):
        from ultralytics import YOLO
        self.items, self.device = list(items), device
        self.model = YOLO(weights)
        self.model.set_classes(self.items)   # set the vocabulary once, not on every frame

    def inspect(self, frame, device=None):
        r = self.model.predict(frame, conf=0.25, verbose=False, device=device or self.device)[0]
        counts = {i: 0 for i in self.items}
        shown = frame.copy()
        for box in r.boxes:
            label = self.items[int(box.cls[0])]
            counts[label] += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(shown, (x1, y1), (x2, y2), (255, 120, 0), 2)
            cv2.putText(shown, f"{label} {float(box.conf[0]):.2f}", (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 120, 0), 2)
        return counts, shown
