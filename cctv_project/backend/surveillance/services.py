import random
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class SurveillanceState:
    running: bool = False
    start_time: float | None = None
    detections: list[dict[str, Any]] = None  # type: ignore[assignment]
    alerts: list[dict[str, Any]] = None  # type: ignore[assignment]
    stats: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.detections is None:
            self.detections = []
        if self.alerts is None:
            self.alerts = []
        if self.stats is None:
            self.stats = {
                'totalDetections': 0,
                'normalCount': 0,
                'suspiciousCount': 0,
                'uptime': 0,
            }


STATE = SurveillanceState()


def reset_state() -> None:
    STATE.running = False
    STATE.start_time = None
    STATE.detections = []
    STATE.alerts = []
    STATE.stats = {
        'totalDetections': 0,
        'normalCount': 0,
        'suspiciousCount': 0,
        'uptime': 0,
    }


def start_session() -> None:
    if not STATE.running:
        STATE.running = True
        STATE.start_time = time.time()


def stop_session() -> None:
    STATE.running = False


def _update_uptime() -> None:
    if STATE.start_time is None or not STATE.running:
        STATE.stats['uptime'] = 0
        return
    STATE.stats['uptime'] = int(time.time() - STATE.start_time)


def tick_simulation() -> None:
    """Update uptime only - real detections come from YOLO/VideoMAE endpoints.

    The simulation is disabled to allow real AI detection to work.
    """
    _update_uptime()
    # Simulation disabled - real detection comes from /api/detect/ and /api/classify/ endpoints
    return


def get_state(activity_status: str) -> dict[str, Any]:
    _update_uptime()
    return {
        'running': STATE.running,
        'activityStatus': activity_status,
        'detections': STATE.detections,
        'alerts': STATE.alerts,
        'stats': STATE.stats,
    }
