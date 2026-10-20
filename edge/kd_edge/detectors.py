"""Model wrappers. ultralytics is imported only when a detector is created, so the rest of the package
(and its tests) run without PyTorch."""
import cv2

class HeadcountEngine:
    """Counts people. weights, conf and imgsz are the knobs to tune: a bigger model, a larger image size or a
    higher confidence threshold change how many people are missed or wrongly added."""
    def __init__(self, device="cpu", weights="yolov8n.pt", conf=0.25, imgsz=640):
        from ultralytics import YOLO
        self.model, self.device, self.conf, self.imgsz = YOLO(weights), device, conf, imgsz

    def count(self, frame):
        """People in this frame, tracked with ByteTrack. Keeps no identity, only a number.
        At one frame every 5 seconds the tracker cannot follow people between frames, so the count is per frame."""
        r = self.model.track(frame, classes=[0], tracker="bytetrack.yaml", persist=True, conf=self.conf,
                             imgsz=self.imgsz, verbose=False, device=self.device)[0]
        return len(r.boxes)

    def boxes(self, frame):
        """Person boxes for drawing (x1, y1, x2, y2, confidence). No identity is kept."""
        r = self.model.predict(frame, classes=[0], conf=self.conf, imgsz=self.imgsz, verbose=False, device=self.device)[0]
        return [(*map(int, b.xyxy[0]), float(b.conf[0])) for b in r.boxes]

    def count_single(self, frame, device=None):
        """Count one unrelated frame (accuracy test, speed test)."""
        r = self.model.predict(frame, classes=[0], conf=self.conf, imgsz=self.imgsz, verbose=False, device=device or self.device)[0]
        return len(r.boxes)

class EquipmentAuditor:
    """Finds sanctioned items from text. `prompts` can give a richer description for an item,
    for example {"fire extinguisher": "red fire extinguisher"}; results are still reported under the item name."""
    def __init__(self, items, device="cpu", weights="yolov8s-worldv2.pt", conf=0.25, imgsz=640, prompts=None):
        from ultralytics import YOLO
        self.items, self.device, self.conf, self.imgsz = list(items), device, conf, imgsz
        self.model = YOLO(weights)
        self.model.set_classes([(prompts or {}).get(i, i) for i in self.items])   # set once, not on every frame

    def _predict(self, frame, device=None):
        return self.model.predict(frame, conf=self.conf, imgsz=self.imgsz, verbose=False, device=device or self.device)[0]

    def inspect(self, frame, device=None):
        r = self._predict(frame, device)
        counts = {i: 0 for i in self.items}
        shown = frame.copy()
        for box in r.boxes:
            label = self.items[int(box.cls[0])]
            counts[label] += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(shown, (x1, y1), (x2, y2), (255, 120, 0), 2)
            cv2.putText(shown, f"{label} {float(box.conf[0]):.2f}", (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 120, 0), 2)
        return counts, shown

    def detections(self, frame):
        """Equipment boxes for drawing: (x1, y1, x2, y2, label, confidence)."""
        r = self._predict(frame)
        return [(*map(int, b.xyxy[0]), self.items[int(b.cls[0])], float(b.conf[0])) for b in r.boxes]
