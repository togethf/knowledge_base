# -*- coding: utf-8 -*-
"""
YOLO Pest Detection Service
"""
from ultralytics import YOLO
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from config import YOLO_MODEL_PATH, YOLO_CLASS_NAMES


class YOLODetector:
    def __init__(self, model_path=None):
        """Initialize YOLO detector with pest model."""
        self.model_path = model_path or YOLO_MODEL_PATH
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the YOLO model."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"YOLO model not found at {self.model_path}")
        self.model = YOLO(self.model_path)
        print(f"YOLO model loaded from {self.model_path}")
    
    def detect(self, image_path, confidence_threshold=0.5):
        """
        Detect pests in an image.
        
        Args:
            image_path: Path to the image file
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of detected pests with class info and confidence
        """
        if self.model is None:
            self._load_model()
        
        # Run inference
        results = self.model(image_path, conf=confidence_threshold)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Get class info from mapping
                class_info = YOLO_CLASS_NAMES.get(cls_id, {
                    "en": f"Unknown_{cls_id}",
                    "zh": f"未知害虫_{cls_id}",
                    "kb_id": None
                })
                
                detections.append({
                    "class_id": cls_id,
                    "class_name_en": class_info["en"],
                    "class_name_zh": class_info["zh"],
                    "kb_id": class_info["kb_id"],
                    "confidence": round(confidence * 100, 2),
                    "bbox": box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                })
        
        # Sort by confidence descending
        detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        return detections
    
    def get_annotated_image(self, image_path, confidence_threshold=0.5):
        """
        Get annotated image with bounding boxes.
        
        Args:
            image_path: Path to the image file
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            Annotated image as numpy array
        """
        results = self.model(image_path, conf=confidence_threshold)
        annotated = results[0].plot()
        return annotated
    
    def save_annotated_image_chinese(self, image_path, output_path, confidence_threshold=0.5):
        """
        Save annotated image with Chinese labels and bounding boxes.
        
        Args:
            image_path: Path to the input image
            output_path: Path to save the annotated image
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of detections
        """
        # Read image
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)
        
        # Try to load Chinese font
        try:
            # Try common Chinese fonts on macOS
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode.ttf"
            ]
            font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    font = ImageFont.truetype(fp, 24)
                    break
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Run detection
        detections = self.detect(image_path, confidence_threshold)
        
        # Color palette for different classes
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
            (0, 128, 255),  # Light Blue
        ]
        
        # Draw bounding boxes with Chinese labels
        for i, det in enumerate(detections):
            bbox = det['bbox']
            x1, y1, x2, y2 = [int(c) for c in bbox]
            color = colors[det['class_id'] % len(colors)]
            
            # Draw rectangle
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            # Prepare label
            label = f"{det['class_name_zh']} {det['confidence']:.1f}%"
            
            # Draw label background
            bbox_label = draw.textbbox((x1, y1 - 30), label, font=font)
            draw.rectangle([bbox_label[0]-2, bbox_label[1]-2, bbox_label[2]+2, bbox_label[3]+2], 
                          fill=color)
            
            # Draw label text
            draw.text((x1, y1 - 30), label, fill=(255, 255, 255), font=font)
        
        # Convert back to OpenCV format and save
        img_annotated = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, img_annotated)
        
        return detections


# Singleton instance
_detector = None

def get_detector():
    """Get or create the singleton YOLODetector instance."""
    global _detector
    if _detector is None:
        _detector = YOLODetector()
    return _detector
