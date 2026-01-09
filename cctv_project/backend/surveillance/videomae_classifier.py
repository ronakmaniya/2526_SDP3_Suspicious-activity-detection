"""Activity classifier.

Temporary implementation: uses a custom YOLO model from Hugging Face to
classify activity as `normal` or `suspicious`.

Input is expected as a list of base64-encoded JPEG frames (data URLs are OK).
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


_MODEL = None
_MODEL_SOURCE = None


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

    # Evenly sample num_frames from the sequence
    step = (len(frames) - 1) / float(num_frames - 1)
    indices = [round(i * step) for i in range(num_frames)]
    return [frames[i] for i in indices]


def _looks_like_hf_repo_id(value: str) -> bool:
    v = value.strip()
    return bool(v) and "/" in v and "\\" not in v and ":" not in v and not v.endswith(".pt")


def _load_model(model_source: Optional[str] = None):
    """Load YOLO model.

    model_source may be:
    - local .pt file path
    - local directory containing Suspicious_Activities_nano.pt
    - Hugging Face repo id (owner/repo)
    """

    global _MODEL, _MODEL_SOURCE
    if _MODEL is not None and _MODEL_SOURCE == (model_source or ""):
        return _MODEL

    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as e:
        raise RuntimeError("Missing dependency for YOLO inference. Install: ultralytics") from e

    resolved_source = (model_source or "").strip()
    if not resolved_source:
        resolved_source = "Accurateinfosolution/Suspicious_activity_detection_Yolov11_Custom"

    # Resolve into a local weights file when using HF repo id
    weights_path = resolved_source
    if _looks_like_hf_repo_id(resolved_source):
        try:
            from huggingface_hub import hf_hub_download

            weights_path = hf_hub_download(
                repo_id=resolved_source,
                filename="Suspicious_Activities_nano.pt",
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to download YOLO weights from Hugging Face. "
                "Ensure internet access and that huggingface_hub is installed. "
                f"Repo: {resolved_source}"
            ) from e
    else:
        # If a directory is provided, try to locate the weights file inside it.
        try:
            from pathlib import Path

            p = Path(resolved_source)
            if p.exists() and p.is_dir():
                candidate = p / "Suspicious_Activities_nano.pt"
                if candidate.exists():
                    weights_path = str(candidate)
        except Exception:
            # If path parsing fails, YOLO will raise a clearer error.
            pass

    model = YOLO(weights_path)
    _MODEL = model
    _MODEL_SOURCE = (model_source or "")
    return model


def classify_activity(
    frame_data_urls: List[str],
    *,
    num_frames: int = 16,
    model_dir: Optional[str] = None,
) -> ClassificationResult:
    model = _load_model(model_source=model_dir)

    frames = [_decode_data_url_jpeg(s) for s in frame_data_urls]
    frames = _pick_frames(frames, num_frames=max(1, int(num_frames)))
    if not frames:
        raise RuntimeError("No frames provided")

    # Use the most recent frame for speed.
    frame = frames[-1]
    img = np.array(frame)

    # Run detection. Keep thresholds modest; frontend applies its own gating.
    results = model(
        img,
        verbose=False,
        conf=0.25,
        iou=0.45,
        imgsz=480,
        max_det=50,
    )

    suspicious_labels = {"people", "person"}
    max_people_conf = 0.0
    max_suspicious_conf = 0.0

    for r in results:
        names = getattr(r, "names", None) or getattr(model, "names", {})
        boxes = getattr(r, "boxes", None)
        if boxes is None:
            continue

        # Ultralytics Boxes expose cls/conf as tensors.
        for cls, conf in zip(boxes.cls, boxes.conf):
            cls_id = int(cls.item())
            c = float(conf.item())
            label = str(names.get(cls_id, cls_id)).strip().lower()

            if label in suspicious_labels:
                max_people_conf = max(max_people_conf, c)
            else:
                max_suspicious_conf = max(max_suspicious_conf, c)

    is_suspicious = max_suspicious_conf > 0.0
    if is_suspicious:
        confidence = max(70.0, max_suspicious_conf * 100.0)
        probabilities = {
            "normal": max(0.0, 100.0 - confidence),
            "suspicious": min(100.0, confidence),
        }
        return ClassificationResult(
            prediction="suspicious",
            confidence=confidence,
            probabilities=probabilities,
        )

    confidence = max(70.0, max_people_conf * 100.0 if max_people_conf > 0.0 else 80.0)
    probabilities = {
        "normal": min(100.0, confidence),
        "suspicious": max(0.0, 100.0 - confidence),
    }
    return ClassificationResult(
        prediction="normal",
        confidence=confidence,
        probabilities=probabilities,
    )
