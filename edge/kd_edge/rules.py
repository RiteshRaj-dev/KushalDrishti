"""The attendance and equipment rules, exactly as written on the slides. No model code here, so it is easy to test."""
from collections import deque

WORST_FIRST = ["BREACH_GHOST_ATTENDANCE", "WARNING_SUSPECTED_GAP", "CAMERA_ISSUE", "COMPLIANT"]

def judge_sample(s, claimed, smoothed, breach_run):
    """Returns (status, new breach_run, gap_ratio). A mismatch becomes a BREACH only after the sustain time."""
    gap_ratio = (claimed - smoothed) / claimed
    if gap_ratio > s.tolerance:
        breach_run += 1
        status = "BREACH_GHOST_ATTENDANCE" if breach_run >= s.sustain_samples else "WARNING_SUSPECTED_GAP"
    else:
        breach_run, status = 0, "COMPLIANT"
    return status, breach_run, gap_ratio

class EquipmentMemory:
    """PRESENT if seen in most of the last N samples, ABSENT if never seen, otherwise UNVERIFIED."""
    def __init__(self, items, votes):
        self.votes, self.need = votes, votes // 2 + 1
        self.history = {i: deque(maxlen=votes) for i in items}

    def update(self, counts):
        for item, n in counts.items():
            self.history[item].append(n > 0)

    def status(self):
        out = {}
        for item, h in self.history.items():
            seen = sum(h)
            if len(h) < self.votes:
                out[item] = "UNVERIFIED"
            elif seen >= self.need:
                out[item] = "PRESENT"
            elif seen == 0:
                out[item] = "ABSENT"
            else:
                out[item] = "UNVERIFIED"
        return out

    def unverified(self):
        return {i: "UNVERIFIED" for i in self.history}
