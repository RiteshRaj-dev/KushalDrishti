"""Groups samples into one packet per minute. Signing is done by transport.EdgeLink."""
import json, math
from .rules import WORST_FIRST

def _num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x

class MinuteAggregator:
    def __init__(self, s, base_ts):
        self.s, self.base_ts, self.minute, self.rows = s, base_ts, None, []

    def add(self, row):
        """Returns a finished packet body when a new minute starts, otherwise None."""
        m = int(row["centre_time_sec"] // 60)
        done = self.flush() if self.minute is not None and m != self.minute else None
        self.minute = m
        self.rows.append(row)
        return done

    def flush(self):
        if not self.rows:
            return None
        rows, self.rows = self.rows, []
        heads = [_num(r["adjusted_headcount"]) for r in rows if _num(r["adjusted_headcount"]) is not None]
        smooth = [_num(r["smoothed_presence"]) for r in rows if _num(r["smoothed_presence"]) is not None]
        statuses = {r["compliance_status"] for r in rows}
        eq = rows[-1]["equipment_status"]
        return {"centre_code": self.s.centre_code, "trade": self.s.trade, "ts": int(self.base_ts + (self.minute + 1) * 60),
                "minute": int(self.minute), "claimed_roll": int(rows[-1]["claimed_attendance"]),
                "mean_headcount": round(sum(heads) / len(heads), 1) if heads else None,
                "smoothed_presence": float(smooth[-1]) if smooth else None,
                "status": next(x for x in WORST_FIRST if x in statuses), "camera_health": str(rows[-1]["camera_health"]),
                "equipment": json.loads(eq) if isinstance(eq, str) else eq, "faces_blurred": True}
