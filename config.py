"""Local Earth Engine configuration; no authentication or network calls on import."""
import json
import math
import os
import threading

import ee


class EarthEngineUnavailable(RuntimeError):
    """Configuration or credentials do not permit an Earth Engine request."""


PROJECT_ID = os.environ.get("EE_PROJECT", "").strip()
SCALE = 30
MAX_PIXELS = 10_000_000
MAX_DATE_DAYS = 366
ROI_COORDS = json.loads(os.environ.get("EE_ROI", "[75.8, 10.4, 76.5, 11.0]"))
if (not isinstance(ROI_COORDS, list) or len(ROI_COORDS) != 4
        or any(type(v) not in (int, float) or not math.isfinite(v) for v in ROI_COORDS)):
    raise ValueError("EE_ROI must contain four finite numbers: west,south,east,north")
w, s, e, n = ROI_COORDS
if not (-180 <= w < e <= 180 and -90 <= s < n <= 90) or (e-w)*(n-s) > 1:
    raise ValueError("EE_ROI must be ordered lon/lat bounds covering at most one square degree")

_ready = False
_lock = threading.Lock()


def initialize_ee():
    """Use existing Earth Engine/ADC credentials only, and initialize once per process."""
    global _ready
    if not PROJECT_ID:
        raise EarthEngineUnavailable("Set EE_PROJECT to an existing Earth Engine project and configure local credentials.")
    with _lock:
        if not _ready:
            try:
                ee.Initialize(project=PROJECT_ID)
                ee.data.setDeadline(30_000)
                ee.data.setMaxRetries(1)
            except Exception as exc:
                raise EarthEngineUnavailable(
                    "Earth Engine is unavailable. Check local credentials, EE_PROJECT and project access."
                ) from exc
            _ready = True


def get_roi():
    return ee.Geometry.Rectangle(ROI_COORDS, geodesic=False)
