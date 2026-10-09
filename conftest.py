import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("edge", "shared", "tools", "."):
    sys.path.insert(0, os.path.join(ROOT, p))
os.environ.setdefault("KD_MASTER_SECRET", "test-master")

class FakeHead:
    def __init__(self, n): self.n = n
    def count(self, frame): return self.n
    def count_single(self, frame, device=None): return self.n
    def boxes(self, frame): return [(20 + 30 * i, 60, 45 + 30 * i, 140, 0.9) for i in range(self.n)]

class FakeAuditor:
    def __init__(self, items, present): self.items, self.present = items, present
    def inspect(self, frame, device=None):
        return {i: (1 if i in self.present else 0) for i in self.items}, frame
    def detections(self, frame): return [(200, 150, 260, 210, i, 0.8) for i in self.present]
