"""
Fixed image processing utilities for OCR with adjusted blur detection
"""
import cv2
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def is_frame_focused(frame: np.ndarray, min_sharpness: float = 50.0) -> bool:
    """
    Check if frame is sufficiently focused for OCR.
    Returns True if frame is sharp enough, False if too blurry.

    Reduced min_sharpness from 80.0 to 50.0 to be less sensitive.
    """
    if frame is None:
        return False

    try:
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Calculate Laplacian variance as focus measure
        focus_measure = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Debug logging (comment out in production)
        # logger.debug(f"Focus measure: {focus_measure:.2f} (threshold: {min_sharpness})")

        return focus_measure > min_sharpness

    except Exception as e:
        logger.debug(f"Focus check error: {e}")
        return True  # Default to processing if check fails

def preprocess_frame_for_ocr(frame: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """
    OPTIMIZED frame preprocessing for better OCR accuracy and performance.
    """
    if frame is None:
        return None

    try:
        # Early size validation
        height, width = frame.shape[:2]
        if height < 100 or width < 100:
            logger.debug("Frame too small for processing")
            return None

        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # Smart resizing only when needed
        if height < 400 or width < 400:
            scale = max(600/height, 600/width)
            new_height = int(height * scale)
            new_width = int(width * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # Measure image contrast to choose optimal processing
        contrast = np.std(gray)

        if contrast < 25:  # Low contrast - use CLAHE + Otsu
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            _, final_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            logger.debug("Used CLAHE + Otsu (low contrast)")
        else:  # Good contrast - use adaptive thresholding
            final_thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            logger.debug("Used adaptive thresholding (good contrast)")

        # Ensure white text on black background
        white_ratio = np.sum(final_thresh == 255) / final_thresh.size
        if white_ratio > 0.6:
            final_thresh = cv2.bitwise_not(final_thresh)
            logger.debug("Inverted image for white text on black background")

        return final_thresh

    except Exception as e:
        logger.error(f"Optimized image preprocessing error: {e}")
        # Return original grayscale as fallback
        if 'frame' in locals() and frame is not None:
            if len(frame.shape) == 3:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                return frame
        return None

def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Simple deskew - skip if it causes issues.
    """
    return image  # Disabled for now to avoid errors

def remove_shadow(image: np.ndarray) -> np.ndarray:
    """
    Simple shadow removal - skip if it causes issues.
    """
    return image  # Disabled for now to avoid errors

def enhance_contrast_brightness(image: np.ndarray, alpha: float = 1.3, beta: int = 10) -> np.ndarray:
    """
    Safe contrast and brightness adjustment.
    """
    try:
        if len(image.shape) == 3:
            return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        else:
            # For grayscale images
            return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    except:
        return image

def extract_roi_for_ocr(frame: np.ndarray, margin: float = 0.1) -> np.ndarray:
    """
    Extract region of interest for faster OCR processing.
    """
    try:
        if len(frame.shape) == 3:
            height, width, _ = frame.shape
        else:
            height, width = frame.shape

        margin_x = int(width * margin)
        margin_y = int(height * margin)
        roi = frame[margin_y:height-margin_y, margin_x:width-margin_x]
        return roi
    except Exception as e:
        logger.error(f"ROI extraction error: {e}")
        return frame