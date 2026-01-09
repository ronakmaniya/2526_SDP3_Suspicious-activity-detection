"""VideoMAE-based activity classifier.

This module loads a fine-tuned `MCG-NJU/videomae-base` checkpoint and
classifies a short clip as `normal` or `suspicious`.

Input is expected as a list of base64-encoded JPEG frames (data URLs are OK).
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image


_MODEL = None
_PROCESSOR = None
_DEVICE = None


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


def _get_default_model_dir() -> Path:
    # .../cctv_project/backend/surveillance/videomae_classifier.py
    # parents[2] => .../cctv_project
    project_dir = Path(__file__).resolve().parents[2]
    return project_dir / "model_training" / "checkpoints" / "final_model"


def _load_model(model_dir: Optional[str] = None):
    global _MODEL, _PROCESSOR, _DEVICE
    if _MODEL is not None and _PROCESSOR is not None and _DEVICE is not None:
        return _MODEL, _PROCESSOR, _DEVICE

    try:
        import torch
        from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor
    except Exception as e:
        raise RuntimeError(
            "Missing dependencies for VideoMAE inference. Install: torch, torchvision, transformers"
        ) from e

    # Determine model path with proper fallback
    env_model_dir = os.environ.get("VIDEOMAE_MODEL_DIR", "").strip()
    if model_dir and str(model_dir).strip():
        model_path = Path(model_dir)
    elif env_model_dir:
        model_path = Path(env_model_dir)
    else:
        model_path = _get_default_model_dir()

    if not model_path.exists():
        raise RuntimeError(f"VideoMAE model directory not found: {model_path}")

    print(f"Loading VideoMAE model from: {model_path}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    processor = VideoMAEImageProcessor.from_pretrained(str(model_path))
    model = VideoMAEForVideoClassification.from_pretrained(str(model_path))
    model = model.to(device)  # type: ignore
    model.eval()

    _MODEL = model
    _PROCESSOR = processor
    _DEVICE = device

    return model, processor, device


def classify_activity(
    frame_data_urls: List[str],
    *,
    num_frames: int = 16,
    model_dir: Optional[str] = None,
) -> ClassificationResult:
    model, processor, device = _load_model(model_dir=model_dir)

    frames = [_decode_data_url_jpeg(s) for s in frame_data_urls]
    frames = _pick_frames(frames, num_frames=num_frames)
    if not frames:
        raise RuntimeError("No frames provided")

    inputs = processor(frames, return_tensors="pt")

    import torch

    pixel_values = inputs["pixel_values"].to(device)

    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)[0]

    pred_idx = int(torch.argmax(probs).item())
    id2label: Dict[int, str] = {}
    if hasattr(model.config, "id2label") and model.config.id2label is not None:
        id2label = {int(k): v for k, v in model.config.id2label.items()}
    else:
        id2label = {0: "normal", 1: "suspicious"}
    pred_label = id2label.get(pred_idx, str(pred_idx))

    probabilities: Dict[str, float] = {}
    for i in range(int(probs.shape[0])):
        label = id2label.get(i, str(i))
        probabilities[label] = float(probs[i].item() * 100.0)

    confidence = float(probs[pred_idx].item() * 100.0)

    return ClassificationResult(
        prediction=str(pred_label),
        confidence=confidence,
        probabilities=probabilities,
    )
