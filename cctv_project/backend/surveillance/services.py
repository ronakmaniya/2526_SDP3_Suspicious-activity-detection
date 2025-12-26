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
    """Generate the next simulated detection event and update in-memory state.

    This keeps the 'data processing' on the Django side, while React only renders.
    """
    if not STATE.running:
        _update_uptime()
        return

    is_suspicious = random.random() < 0.15
    status = 'suspicious' if is_suspicious else 'normal'

    detection = {
        'id': int(time.time() * 1000),
        'x': random.random() * 60 + 10,
        'y': random.random() * 50 + 10,
        'width': random.random() * 15 + 15,
        'height': random.random() * 20 + 25,
        'status': status,
        'confidence': f"{(random.random() * 20 + 80):.1f}",
    }

    STATE.detections = (STATE.detections + [detection])[-3:]
    STATE.stats['totalDetections'] += 1
    if status == 'normal':
        STATE.stats['normalCount'] += 1
    else:
        STATE.stats['suspiciousCount'] += 1
        STATE.alerts = ([
            {
                'id': detection['id'],
                'message': '⚠️ Suspicious Activity Detected!',
                'time': time.strftime('%H:%M:%S'),
                'confidence': detection['confidence'],
            }
        ] + STATE.alerts)[:5]

    _update_uptime()


def get_state(activity_status: str) -> dict[str, Any]:
    _update_uptime()
    return {
        'running': STATE.running,
        'activityStatus': activity_status,
        'detections': STATE.detections,
        'alerts': STATE.alerts,
        'stats': STATE.stats,
    }
