import cv2

class FaceAnonymizer:
    """Blur every detected face in memory. The raw frame is never written to disk.
    Limit: a basic frontal-face finder can miss faces that are turned away. Treat the blur as best effort."""
    def __init__(self):
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def anonymize(self, frame_bgr):
        frame = frame_bgr.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(24, 24))
        for (x, y, w, h) in faces:
            y1, y2 = max(0, y - 5), min(frame.shape[0], y + h + 5)
            x1, x2 = max(0, x - 5), min(frame.shape[1], x + w + 5)
            small = cv2.resize(frame[y1:y2, x1:x2], (max(1, w // 10), max(1, h // 10)), interpolation=cv2.INTER_LINEAR)
            blocky = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
            frame[y1:y2, x1:x2] = cv2.GaussianBlur(blocky, (23, 23), 30)
        return frame, len(faces)

def to_evidence(frame, height=480):
    """Shrink a blurred frame to 480p for the alert photo."""
    h, w = frame.shape[:2]
    return cv2.resize(frame, (int(w * height / h), height), interpolation=cv2.INTER_AREA)

def encode_jpeg(frame, quality=65):
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buf.tobytes() if ok else b""
