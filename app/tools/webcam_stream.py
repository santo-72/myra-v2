import cv2
import structlog
import time
from typing import Optional

logger = structlog.get_logger(__name__)

class WebcamStream:
    """Handles taking snapshots from a webcam using OpenCV"""
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        logger.info(f"WebcamStream initialized with camera {camera_index}")

    def take_snapshot(self, output_path: str) -> bool:
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                logger.error("Could not open webcam.")
                return False

            # Allow camera sensor to warm up
            time.sleep(0.5)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                cv2.imwrite(output_path, frame)
                logger.info(f"Snapshot saved to {output_path}")
                return True
            else:
                logger.error("Failed to read frame from webcam.")
                return False
        except Exception as e:
            logger.error("Error capturing webcam snapshot", error=str(e))
            return False
