"""
YOLO Human Detection Service

Uses YOLOv8 to detect humans in video frames.
Only returns bounding boxes for person class (class_id=0).
"""

import base64
import io
import logging
from typing import List, Dict, Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Global model instance (lazy loaded)
_model = None


def get_model():
    """Lazy load the YOLO model."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            # Use YOLOv8n (nano) for speed, can use 's', 'm', 'l', 'x' for better accuracy
            _model = YOLO('yolov8n.pt')
            logger.info("YOLO model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    return _model


def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode a base64 image string to numpy array."""
    # Remove data URL prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    image_data = base64.b64decode(base64_string)
    image = Image.open(io.BytesIO(image_data))
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return np.array(image)


def detect_humans(image_data: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """
    Detect humans in an image.
    
    Args:
        image_data: Base64 encoded image string
        confidence_threshold: Minimum confidence score (0-1)
    
    Returns:
        List of detections with bounding boxes in percentage coordinates
    """
    try:
        model = get_model()
        
        # Decode the image
        image = decode_base64_image(image_data)
        img_height, img_width = image.shape[:2]
        
        # Run detection
        results = model(image, verbose=False)
        
        detections = []
        detection_id = 0
        
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                # Get class ID - 0 is 'person' in COCO dataset
                class_id = int(box.cls[0])
                if class_id != 0:  # Only detect humans (person class)
                    continue
                
                confidence = float(box.conf[0])
                if confidence < confidence_threshold:
                    continue
                
                # Get bounding box coordinates (xyxy format)
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Convert to percentage of image dimensions
                x_percent = (x1 / img_width) * 100
                y_percent = (y1 / img_height) * 100
                width_percent = ((x2 - x1) / img_width) * 100
                height_percent = ((y2 - y1) / img_height) * 100
                
                detections.append({
                    'id': f'human_{detection_id}',
                    'x': round(x_percent, 2),
                    'y': round(y_percent, 2),
                    'width': round(width_percent, 2),
                    'height': round(height_percent, 2),
                    'confidence': round(confidence * 100, 1),
                    'label': 'Human',
                    'status': 'normal'  # Can be extended for activity classification
                })
                detection_id += 1
        
        return detections
    
    except Exception as e:
        logger.error(f"Detection error: {e}")
        return []


def preload_model():
    """Preload the model at startup for faster first detection."""
    try:
        get_model()
        logger.info("YOLO model preloaded")
    except Exception as e:
        logger.warning(f"Could not preload YOLO model: {e}")
