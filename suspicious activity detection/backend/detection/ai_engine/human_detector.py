"""
YOLOv8x Human Detection Module.
Detects humans in video frames and returns bounding box coordinates.
"""
import logging
import numpy as np

logger = logging.getLogger('detection')


class HumanDetector:
    """
    Human detection using YOLOv8 (Ultralytics).
    Provides high-accuracy real-time human detection with bounding boxes.
    """

    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.4, device=None, imgsz=320):
        """
        Initialize the YOLO human detector.

        Args:
            model_path: Path to YOLO model weights (default: yolov8n.pt auto-downloads)
            confidence_threshold: Minimum confidence for detections
            device: 'cuda', 'cpu', or None for auto-detection
            imgsz: Input image size for YOLO inference (smaller = faster)
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.model_path = model_path
        self.device = device
        self.imgsz = imgsz
        self._load_model()

    def _load_model(self):
        """Load the YOLOv8x model."""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)

            # Set device
            if self.device:
                self.model.to(self.device)

            logger.info(f"YOLOv8x model loaded successfully from {self.model_path}")
            logger.info(f"Device: {self.device or 'auto'}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def detect_humans(self, frame):
        """
        Detect humans in a single frame.

        Args:
            frame: numpy array (H, W, C) BGR format

        Returns:
            list of dict: Each detection contains:
                - bbox: [x1, y1, x2, y2] coordinates
                - confidence: float confidence score
                - class_name: 'person'
                - crop: cropped image of the detected person
        """
        if self.model is None:
            logger.error("YOLO model not loaded")
            return []

        try:
            # Run YOLO inference (imgsz controls input resolution — smaller = faster)
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                classes=[0],  # Class 0 = person in COCO dataset
                verbose=False,
                imgsz=self.imgsz,
            )

            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())

                    # Ensure coordinates are within frame bounds
                    h, w = frame.shape[:2]
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(w, x2)
                    y2 = min(h, y2)

                    # Crop the detected person region
                    person_crop = frame[y1:y2, x1:x2].copy()

                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': round(conf, 4),
                        'class_name': 'person',
                        'crop': person_crop
                    })

            logger.debug(f"Detected {len(detections)} humans in frame")
            return detections

        except Exception as e:
            logger.error(f"Error during human detection: {e}")
            return []

    def detect_batch(self, frames):
        """
        Detect humans in a batch of frames.

        Args:
            frames: list of numpy arrays

        Returns:
            list of list of detections
        """
        all_detections = []
        for frame in frames:
            detections = self.detect_humans(frame)
            all_detections.append(detections)
        return all_detections
