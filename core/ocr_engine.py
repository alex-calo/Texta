import logging
from typing import NamedTuple, Set

import cv2
import numpy as np
import pytesseract

from config import TESSERACT_PATH, CONTENT_MODES, TESSERACT_CONFIG, LOW_CONFIDENCE_THRESHOLD
from utils.image_processing import preprocess_frame_for_ocr, extract_roi_for_ocr
from core.text_processor import TextProcessor

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

logger = logging.getLogger(__name__)


class OcrResult(NamedTuple):
    text: str
    low_confidence_words: Set[str]


class OCREngine:
    """Wrapper around pytesseract with preprocessing and text post-processing."""

    def __init__(self, lang="eng"):
        self.lang = lang
        self.text_processor = TextProcessor()
        logger.debug("OCREngine initialized.")

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Apply contrast-adaptive preprocessing to improve OCR accuracy."""
        result = preprocess_frame_for_ocr(frame)
        if result is None:
            logger.warning("Preprocessing returned None; using grayscale fallback")
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        return result

    def run_ocr(self, frame: np.ndarray, mode: str = "Plain text", crop_margin: float = 0.0) -> OcrResult:
        """Run OCR on a frame and return text + low-confidence word set.

        Args:
            frame:        BGR image as numpy array.
            mode:         Content mode label — key in CONTENT_MODES.
            crop_margin:  Fraction of each edge to discard before OCR (0.0–0.3).
        """
        try:
            if crop_margin > 0:
                frame = extract_roi_for_ocr(frame, margin=crop_margin)
            processed = self.preprocess(frame)
            config = CONTENT_MODES.get(mode, TESSERACT_CONFIG)

            data = pytesseract.image_to_data(
                processed, lang=self.lang, config=config,
                output_type=pytesseract.Output.DICT,
            )

            raw_lines = []
            current_line = []
            last_key = None
            low_conf: Set[str] = set()

            n = len(data['text'])
            for i in range(n):
                token = (data['text'][i] or '').strip()
                if not token:
                    continue
                line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                if line_key != last_key:
                    if current_line:
                        raw_lines.append(' '.join(current_line))
                    current_line = []
                    last_key = line_key
                current_line.append(token)
                try:
                    conf = float(data['conf'][i])
                except (ValueError, TypeError):
                    conf = -1
                if 0 <= conf < LOW_CONFIDENCE_THRESHOLD:
                    low_conf.add(token)

            if current_line:
                raw_lines.append(' '.join(current_line))

            raw = '\n'.join(raw_lines)
            text = self.text_processor.process(raw, mode=mode)
            logger.debug(
                f"OCR: {len(text)} chars, {len(low_conf)} low-conf words "
                f"(mode={mode}, crop={crop_margin:.0%})"
            )
            return OcrResult(text=text, low_confidence_words=low_conf)
        except Exception as e:
            logger.error(f"OCR execution error: {e}")
            return OcrResult(text="", low_confidence_words=set())
