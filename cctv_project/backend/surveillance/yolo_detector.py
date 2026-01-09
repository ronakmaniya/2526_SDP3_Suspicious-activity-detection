"""
YOLO Human Detection Service

Uses YOLOv8 to detect humans in video frames.
Only returns bounding boxes for person class (class_id=0).
Optimized for multi-human detection in surveillance scenarios.
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

# Detection settings optimized for surveillance - speed and accuracy balance
DETECTION_CONFIG = {
    # Use YOLOv8n (nano) for fastest speed, good for real-time
    # Options: 'yolov8n.pt' (nano/fastest), 'yolov8s.pt' (small/balanced)
    'model_name': 'yolov8n.pt',
    
    # Confidence threshold - balance between detection and false positives
    'default_confidence': 0.20,
    
    # IoU threshold for NMS - lower value = less overlapping boxes
    'iou_threshold': 0.45,
    
    # Maximum detections per image
    'max_detections': 50,
    
    # Input image size (smaller = faster, larger = more accurate)
    'img_size': 480,
    
    # Use half precision on GPU for speed (if available)
    'half_precision': True,
}


def get_model():
    """Lazy load the YOLO model with optimized settings for speed."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            import torch
            
            model_name = DETECTION_CONFIG['model_name']
            print(f"[YOLO] Loading model: {model_name}")
            _model = YOLO(model_name)
            
            # Move to GPU if available for faster inference
            if torch.cuda.is_available():
                _model.to('cuda')
                # Use half precision for faster inference on GPU
                if DETECTION_CONFIG['half_precision']:
                    _model.half()
                print(f"[YOLO] Model loaded on GPU (CUDA) with half precision")
                logger.info(f"YOLO model '{model_name}' loaded on GPU (CUDA)")
            else:
                print(f"[YOLO] Model loaded on CPU")
                logger.info(f"YOLO model '{model_name}' loaded on CPU")
            
            # Warm up the model with a dummy inference
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            _model(dummy, verbose=False)
            print("[YOLO] Model warmed up")
                
        except Exception as e:
            print(f"[YOLO] FAILED to load model: {e}")
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


def detect_humans(image_data: str, confidence_threshold: float = None) -> List[Dict[str, Any]]:
    """
    Detect humans in an image with optimized settings for multiple people.
    
    Args:
        image_data: Base64 encoded image string
        confidence_threshold: Minimum confidence score (0-1), defaults to config value
    
    Returns:
        List of detections with bounding boxes in percentage coordinates
    """
    if confidence_threshold is None:
        confidence_threshold = DETECTION_CONFIG['default_confidence']
    
    try:
        model = get_model()
        
        # Decode the image
        image = decode_base64_image(image_data)
        img_height, img_width = image.shape[:2]
        
        # Run detection with optimized settings for speed
        results = model(
            image,
            verbose=False,
            conf=confidence_threshold,
            iou=DETECTION_CONFIG['iou_threshold'],
            imgsz=DETECTION_CONFIG['img_size'],
            max_det=DETECTION_CONFIG['max_detections'],
            classes=[0],  # Only detect person class (class_id=0)
            agnostic_nms=False,
        )
        
        detections = []
        detection_id = 0
        
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            
            # Process all detected boxes
            for i in range(len(boxes)):
                # Get class ID - 0 is 'person' in COCO dataset
                class_id = int(boxes.cls[i])
                if class_id != 0:  # Only detect humans (person class)
                    continue
                
                confidence = float(boxes.conf[i])
                
                # Get bounding box coordinates (xyxy format)
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                
                # Clamp coordinates to image boundaries
                x1 = max(0, min(x1, img_width))
                y1 = max(0, min(y1, img_height))
                x2 = max(0, min(x2, img_width))
                y2 = max(0, min(y2, img_height))
                
                # Skip invalid boxes
                if x2 <= x1 or y2 <= y1:
                    continue
                
                # Convert to percentage of image dimensions
                x_percent = (x1 / img_width) * 100
                y_percent = (y1 / img_height) * 100
                width_percent = ((x2 - x1) / img_width) * 100
                height_percent = ((y2 - y1) / img_height) * 100
                
                # Skip very small detections (likely false positives)
                if width_percent < 2 or height_percent < 2:
                    continue
                
                detections.append({
                    'id': f'human_{detection_id}',
                    'x': round(x_percent, 2),
                    'y': round(y_percent, 2),
                    'width': round(width_percent, 2),
                    'height': round(height_percent, 2),
                    'confidence': round(confidence * 100, 1),
                    'label': 'Human',
                    'status': 'normal'  # Will be updated by VideoMAE classification
                })
                detection_id += 1
        
        logger.debug(f"Detected {len(detections)} humans")
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
