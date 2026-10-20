from dataclasses import dataclass, replace

TRADES = {   # sanctioned equipment per trade: type the names, no training needed
    "classroom_demo": ["chair", "laptop", "workbench", "fire extinguisher"],
    "welder": ["welding transformer", "gas cylinder", "protective booth", "fire extinguisher"],
    "tailoring": ["sewing machine", "workbench", "fire extinguisher"],
    "fitter": ["lathe", "workbench", "fire extinguisher"],
}
SAFETY_ITEMS = ["fire extinguisher"]

@dataclass(frozen=True)
class Settings:
    centre_code: str = "DEMO-CENTRE"
    trade: str = "classroom_demo"
    claimed_attendance: int = 18       # what the centre filed on the portal
    instructors_in_room: int = 0       # removed from the count before comparing
    sample_sec: int = 5                # centre time per sample (one frame every 5 seconds)
    window_samples: int = 180          # 15 minutes at one frame per 5 seconds
    sustain_samples: int = 360         # 30 minutes at one frame per 5 seconds
    tolerance: float = 0.20            # a gap above 20% counts as a mismatch
    video_sample_sec: float = 5.0      # how often a frame is taken from a test video
    equipment_votes: int = 3           # an item must be seen in most of the last 3 samples
    min_sharpness: float = 15.0
    min_brightness: float = 25.0
    min_contrast: float = 8.0

    def demo(self):
        """Short timings so a short video can show the whole alert logic. Never quote demo timing as deployment timing."""
        return replace(self, video_sample_sec=1.0, window_samples=6, sustain_samples=12)

    @property
    def items(self):
        return TRADES[self.trade]
