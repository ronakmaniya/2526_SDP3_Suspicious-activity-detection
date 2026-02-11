"""Activity classifier using motion-based anomaly detection.

Uses frame differencing and motion analysis to classify activity as 
`normal` or `suspicious` based on unusual movement patterns.

This approach adapts to any camera environment by learning what's normal
from recent frame history, unlike domain-specific trained models.

Input is expected as a list of base64-encoded JPEG frames (data URLs are OK).
"""

from __future__ import annotations

import base64
import io
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

# Global state for adaptive thresholding
_MOTION_HISTORY: deque = deque(maxlen=100)  # Store last 100 motion scores
_BASELINE_MOTION: float = 0.0
_FRAME_COUNT: int = 0


@dataclass(frozen=True)
class ClassificationResult:
    prediction: str
    confidence: float  # 0..100
    probabilities: Dict[str, float]  # label -> 0..100


def _decode_data_url_jpeg(data_url: str) -> Image.Image:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _pick_frames(frames: List[Image.Image], num_frames: int) -> List[Image.Image]:
    if not frames:
        return []
    if len(frames) == num_frames:
        return frames
    if len(frames) < num_frames:
        last = frames[-1]
        return frames + [last] * (num_frames - len(frames))
    step = (len(frames) - 1) / float(num_frames - 1)
    indices = [round(i * step) for i in range(num_frames)]
    return [frames[i] for i in indices]


def _preprocess_frame(img: Image.Image, size: int = 128) -> np.ndarray:
    """Convert to grayscale and resize for motion analysis."""
    gray = img.convert("L")
    resized = gray.resize((size, size), Image.Resampling.LANCZOS)
    return np.array(resized, dtype=np.float32) / 255.0


def _compute_motion_score(frames: List[np.ndarray]) -> float:
    """Compute motion score based on frame differences.
    
    Returns a score representing amount of motion/change between frames.
    Higher score = more motion/activity.
    """
    if len(frames) < 2:
        return 0.0
    
    total_motion = 0.0
    for i in range(1, len(frames)):
        # Absolute difference between consecutive frames
        diff = np.abs(frames[i] - frames[i-1])
        # Mean difference (overall motion)
        mean_diff = np.mean(diff)
        # Standard deviation (indicates sudden changes)
        std_diff = np.std(diff)
        # Count of significantly changed pixels (threshold 0.1)
        significant_pixels = np.sum(diff > 0.1) / diff.size
        
        # Combined motion score
        frame_motion = mean_diff * 0.4 + std_diff * 0.3 + significant_pixels * 0.3
        total_motion += frame_motion
    
    return float(total_motion / (len(frames) - 1))


def _compute_spatial_anomaly(frames: List[np.ndarray]) -> float:
    """Detect spatial anomalies like unusual shapes or patterns."""
    if not frames:
        return 0.0
    
    # Use the most recent frame
    frame = frames[-1]
    
    # Compute edge density using simple gradient
    gx = np.abs(np.diff(frame, axis=1))
    gy = np.abs(np.diff(frame, axis=0))
    edge_density = (np.mean(gx) + np.mean(gy)) / 2
    
    # Compute contrast
    contrast = np.std(frame)
    
    # Compute local variance (indicates texture/activity regions)
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(frame, size=8)
    local_sqr_mean = uniform_filter(frame**2, size=8)
    local_var = np.clip(local_sqr_mean - local_mean**2, 0, None)
    activity_regions = np.mean(local_var > 0.01)
    
    return float(edge_density * 0.3 + contrast * 0.3 + activity_regions * 0.4)


def _update_baseline(motion_score: float) -> tuple:
    """Update adaptive baseline and return (baseline, std_dev)."""
    global _MOTION_HISTORY, _BASELINE_MOTION, _FRAME_COUNT
    
    _MOTION_HISTORY.append(motion_score)
    _FRAME_COUNT += 1
    
    if len(_MOTION_HISTORY) >= 5:
        # Compute baseline from history (use median to be robust to outliers)
        scores = np.array(_MOTION_HISTORY)
        _BASELINE_MOTION = float(np.median(scores))
        std_dev = float(np.std(scores))
        return _BASELINE_MOTION, max(std_dev, 0.001)  # Prevent division by zero
    else:
        # Not enough history yet, use conservative defaults
        return 0.02, 0.01


def classify_activity(
    frame_data_urls: List[str],
    *,
    num_frames: int = 16,
    model_dir: Optional[str] = None,  # Kept for API compatibility
) -> ClassificationResult:
    """Classify activity using motion-based anomaly detection.
    
    Detects suspicious activity based on:
    1. Unusual amount of motion (too much or sudden changes)
    2. Motion patterns that deviate from baseline
    3. Spatial anomalies in the frame
    
    This approach adapts to the camera's environment automatically.
    """
    # Decode and pick frames
    frames = [_decode_data_url_jpeg(s) for s in frame_data_urls]
    frames = _pick_frames(frames, num_frames=max(2, int(num_frames)))
    if len(frames) < 2:
        # Not enough frames for motion analysis - assume normal
        return ClassificationResult(
            prediction="normal",
            confidence=70.0,
            probabilities={"normal": 70.0, "suspicious": 30.0},
        )

    # Preprocess frames
    preprocessed = [_preprocess_frame(f) for f in frames]
    
    # Compute motion score
    motion_score = _compute_motion_score(preprocessed)
    
    # Compute spatial anomaly score
    try:
        spatial_score = _compute_spatial_anomaly(preprocessed)
    except ImportError:
        # scipy not available, skip spatial analysis
        spatial_score = 0.0
    
    # Update adaptive baseline
    baseline, std_dev = _update_baseline(motion_score)
    
    # Calculate how many standard deviations from baseline
    if std_dev > 0:
        z_score = (motion_score - baseline) / std_dev
    else:
        z_score = 0.0
    
    # Combined anomaly score
    # High motion deviation OR high spatial anomaly = suspicious
    motion_anomaly = abs(z_score) / 3.0  # Normalize: 3 std = 1.0
    combined_score = motion_anomaly * 0.7 + spatial_score * 0.3
    
    # Threshold for suspicious activity
    # During warmup period (first 15 frames), be conservative
    if _FRAME_COUNT < 15:
        threshold = 0.8  # Higher threshold during warmup
    else:
        threshold = 0.5  # Normal threshold after baseline established
    
    is_suspicious = combined_score > threshold and z_score > 2.0
    
    # Calculate confidence
    if is_suspicious:
        # Suspicious - confidence based on how far above threshold
        confidence = min(100.0, 70.0 + (combined_score - threshold) * 60.0)
        confidence = max(70.0, confidence)
        
        return ClassificationResult(
            prediction="suspicious",
            confidence=confidence,
            probabilities={
                "normal": max(0.0, 100.0 - confidence),
                "suspicious": min(100.0, confidence),
            },
        )
    else:
        # Normal - confidence based on how stable the motion is
        stability = max(0.0, 1.0 - abs(z_score) / 2.0)
        confidence = 70.0 + stability * 30.0
        confidence = min(100.0, max(70.0, confidence))
        
        return ClassificationResult(
            prediction="normal",
            confidence=confidence,
            probabilities={
                "normal": min(100.0, confidence),
                "suspicious": max(0.0, 100.0 - confidence),
            },
        )
