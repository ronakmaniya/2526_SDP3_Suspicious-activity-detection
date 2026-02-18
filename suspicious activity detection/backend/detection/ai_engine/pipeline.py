"""
Main AI Processing Pipeline — Optimized for Speed.
Orchestrates YOLO human detection + SlowFast-R101 activity classification.
Manages the 32-frame sliding window and produces annotated frames.

Performance features:
  - Frame skipping: Only runs YOLO every Nth frame (default 3)
  - Classifier cooldown: Only re-classifies every K frames (default 8)
  - Skip-annotation mode: Skips OpenCV drawing when frontend draws its own overlay
"""
import logging
import threading
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np

logger = logging.getLogger('detection')


class SurveillancePipeline:
    """
    Main pipeline that coordinates:
    1. YOLOv8 for human detection (with frame skipping)
    2. SlowFast-R101 for activity classification (with cooldown)
    3. Frame annotation (bounding boxes + timestamps)
    4. Event logging
    """

    def __init__(self, settings=None):
        self.settings = settings or {}
        self.human_detector = None
        self.activity_classifier = None

        # Sliding window buffer
        self.frame_windows = {}  # person_id -> deque of frames
        self.window_size = self.settings.get('SLIDING_WINDOW_SIZE', 16)
        # Allow early classification with fewer frames (preprocess pads to 32)
        # Critical for short uploaded videos that never fill the full window
        self._min_classify_frames = max(self.window_size // 2, 8)

        # Track frame count
        self.frame_count = 0
        self._lock = threading.Lock()

        # --- Performance: detection frame skipping ---
        self._detect_every_n = self.settings.get('DETECT_EVERY_N_FRAMES', 3)
        self._cached_detections = []  # Last YOLO detections (reused on skipped frames)
        self._cached_human_detections = []  # Raw human detector output

        # --- Performance: classifier cooldown ---
        self._classify_cooldown = self.settings.get('CLASSIFY_COOLDOWN', 8)
        self._classify_counters = {}  # person_id -> frames since last classification
        self._cached_classifications = {}  # person_id -> last classification result

        # --- Temporal smoothing for stable labels ---
        self._label_history = {}      # person_id -> deque of last N labels
        self._prob_ema = {}           # person_id -> EMA of {normal, suspicious} probs
        self._SMOOTHING_ALPHA = 0.55  # weight for current reading (0.55 new + 0.45 old)
        self._HISTORY_LEN = 3         # majority-vote window

        self._initialized = False

    def initialize(self):
        """Load AI models. Called lazily on first use."""
        if self._initialized:
            return

        try:
            from .human_detector import HumanDetector
            from .activity_classifier import SlowFastClassifier

            yolo_model = self.settings.get('YOLO_MODEL', 'yolov8n.pt')
            yolo_conf = self.settings.get('YOLO_CONFIDENCE_THRESHOLD', 0.4)
            yolo_imgsz = self.settings.get('YOLO_IMGSZ', 320)
            activity_conf = self.settings.get('ACTIVITY_CONFIDENCE_THRESHOLD', 0.6)

            logger.info("Initializing AI models...")

            self.human_detector = HumanDetector(
                model_path=yolo_model,
                confidence_threshold=yolo_conf,
                imgsz=yolo_imgsz,
            )

            self.activity_classifier = SlowFastClassifier(
                confidence_threshold=activity_conf
            )

            self._initialized = True
            logger.info("AI Pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AI pipeline: {e}")
            raise

    def process_frame(self, frame, frame_number=None, skip_annotation=False):
        """
        Process a single frame through the full pipeline.

        Args:
            frame: numpy array (H, W, C) BGR format
            frame_number: optional frame counter
            skip_annotation: if True, skip drawing on the frame (frontend draws its own overlay)

        Returns:
            dict:
                - annotated_frame: frame with bounding boxes (or original if skip_annotation)
                - detections: list of detection results
                - timestamp: current timestamp string
                - frame_number: int
        """
        if not self._initialized:
            self.initialize()

        with self._lock:
            self.frame_count += 1
            if frame_number is None:
                frame_number = self.frame_count

        timestamp = datetime.now().strftime('%H:%M:%S')

        # --- Frame skipping: only run YOLO every Nth frame ---
        run_detection = (frame_number % self._detect_every_n == 1) or self._detect_every_n <= 1

        if run_detection:
            human_detections = self.human_detector.detect_humans(frame)
            self._cached_human_detections = human_detections
        else:
            human_detections = self._cached_human_detections

        # Build detection results
        detections = []
        h_frame, w_frame = frame.shape[:2]

        for idx, detection in enumerate(human_detections):
            person_id = f"person_{idx}"
            bbox = detection['bbox']
            det_confidence = detection['confidence']
            x1, y1, x2, y2 = bbox

            # --- Expanded crop: include surrounding context for better
            #     SlowFast classification (model was trained on full scenes,
            #     tight person crops lose important context). ---
            bw, bh = x2 - x1, y2 - y1
            expand_x = int(bw * 0.4)
            expand_y = int(bh * 0.2)
            ex1 = max(0, x1 - expand_x)
            ey1 = max(0, y1 - expand_y)
            ex2 = min(w_frame, x2 + expand_x)
            ey2 = min(h_frame, y2 + expand_y)
            expanded_crop = frame[ey1:ey2, ex1:ex2].copy()

            # Add expanded crop to sliding window
            if person_id not in self.frame_windows:
                self.frame_windows[person_id] = deque(maxlen=self.window_size)
            self.frame_windows[person_id].append(expanded_crop)

            # --- Classifier cooldown: only re-classify every K frames ---
            if person_id not in self._classify_counters:
                self._classify_counters[person_id] = 0
            self._classify_counters[person_id] += 1

            need_classify = (
                len(self.frame_windows[person_id]) >= self._min_classify_frames
                and (
                    person_id not in self._cached_classifications
                    or self._classify_counters[person_id] >= self._classify_cooldown
                )
            )

            if need_classify:
                frames_list = list(self.frame_windows[person_id])
                classification = self.activity_classifier.classify_activity(frames_list)

                # --- Temporal smoothing: EMA on probabilities ---
                raw_probs = classification['probabilities']
                if (person_id in self._prob_ema
                        and self._prob_ema[person_id] is not None):
                    prev = self._prob_ema[person_id]
                    a = self._SMOOTHING_ALPHA
                    smoothed = {
                        'normal': a * raw_probs['normal'] + (1 - a) * prev['normal'],
                        'suspicious': a * raw_probs['suspicious'] + (1 - a) * prev['suspicious'],
                    }
                else:
                    smoothed = raw_probs.copy()
                self._prob_ema[person_id] = smoothed
                classification['probabilities'] = {
                    'normal': round(smoothed['normal'], 4),
                    'suspicious': round(smoothed['suspicious'], 4),
                }

                # --- Temporal smoothing: majority vote on label ---
                if person_id not in self._label_history:
                    self._label_history[person_id] = deque(maxlen=self._HISTORY_LEN)
                self._label_history[person_id].append(classification['label'])
                recent = list(self._label_history[person_id])
                sus_votes = recent.count('suspicious')
                if len(recent) >= 2:
                    classification['label'] = (
                        'suspicious' if sus_votes >= 2 else 'normal'
                    )

                self._cached_classifications[person_id] = classification
                self._classify_counters[person_id] = 0
            elif person_id in self._cached_classifications:
                classification = self._cached_classifications[person_id]
            else:
                classification = {
                    'label': 'normal',
                    'confidence': 0.0,
                    'probabilities': {'normal': 1.0, 'suspicious': 0.0}
                }

            detections.append({
                'bbox': bbox,
                'detection_confidence': det_confidence,
                'activity_label': classification['label'],
                'activity': classification.get('activity', 'unknown'),
                'activity_confidence': classification['confidence'],
                'probabilities': classification['probabilities'],
                'person_id': person_id,
                'timestamp': timestamp,
                'frame_number': frame_number
            })

        # Annotate frame (skip for live stream when frontend draws its own overlay)
        if skip_annotation:
            annotated_frame = frame
        else:
            annotated_frame = self._annotate_frame(frame.copy(), detections, timestamp)

        return {
            'annotated_frame': annotated_frame,
            'detections': detections,
            'timestamp': timestamp,
            'frame_number': frame_number
        }

    def _annotate_frame(self, frame, detections, timestamp):
        """
        Draw bounding boxes, labels, and timestamp on the frame.

        Args:
            frame: numpy array to annotate
            detections: list of detection dicts
            timestamp: timestamp string

        Returns:
            annotated frame
        """
        for det in detections:
            bbox = det['bbox']
            label = det['activity_label']
            confidence = det['activity_confidence']
            x1, y1, x2, y2 = bbox

            # Color based on classification
            activity_name = det.get('activity', label)
            if label == 'suspicious':
                color = (0, 0, 255)  # Red (BGR)
                label_text = f"SUSPICIOUS: {activity_name} | {confidence:.2f}"
            else:
                color = (0, 255, 0)  # Green (BGR)
                label_text = f"{activity_name} | {confidence:.2f}"

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(
                frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0] + 5, y1),
                color,
                -1  # Filled
            )

            # Draw label text
            cv2.putText(
                frame,
                label_text,
                (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),  # White text
                1,
                cv2.LINE_AA
            )

        # Draw timestamp overlay at top-right corner
        ts_text = f"CCTV | {timestamp}"
        ts_size = cv2.getTextSize(ts_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        h, w = frame.shape[:2]
        ts_x = w - ts_size[0] - 10
        ts_y = 30

        # Background for timestamp
        cv2.rectangle(
            frame,
            (ts_x - 5, ts_y - ts_size[1] - 5),
            (ts_x + ts_size[0] + 5, ts_y + 5),
            (0, 0, 0),
            -1
        )
        cv2.putText(
            frame,
            ts_text,
            (ts_x, ts_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        return frame

    def reset_windows(self):
        """Reset sliding windows (e.g., for a new session)."""
        with self._lock:
            self.frame_windows.clear()
            self.frame_count = 0
            self._cached_detections.clear()
            self._cached_human_detections.clear()
            self._cached_classifications.clear()
            self._classify_counters.clear()
            self._label_history.clear()
            self._prob_ema.clear()


# Singleton pipeline instance
_pipeline_instance = None
_pipeline_lock = threading.Lock()


def get_pipeline(settings=None):
    """
    Get or create the singleton pipeline instance.

    Args:
        settings: AI model configuration dict

    Returns:
        SurveillancePipeline instance
    """
    global _pipeline_instance
    with _pipeline_lock:
        if _pipeline_instance is None:
            _pipeline_instance = SurveillancePipeline(settings=settings)
        return _pipeline_instance
