"""KushalDrishti edge software: privacy-first counting, equipment check and signed, buffered reporting."""
import os, sys
_here = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(_here, "..", "..", "shared"), "/app/shared"):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
__version__ = "1.0.0"
