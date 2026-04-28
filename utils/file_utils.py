"""
File utility functions
"""
import os
import sys
import logging
import tempfile
import datetime
from pathlib import Path
from typing import Optional

from config import SAVE_DIR

logger = logging.getLogger(__name__)

def resource_path(relative_path: str) -> str:
    """Get absolute path for PyInstaller."""
    try:
        if hasattr(sys, "_MEIPASS"):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    except Exception as e:
        logger.error(f"Error getting resource path for {relative_path}: {e}")
        return relative_path

def generate_pdf_filename(prefix: str = "DocCamOCR") -> str:
    """Generate timestamped PDF filename."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{prefix}_{timestamp}.pdf"
    return str(SAVE_DIR / filename)

def safe_remove_file(file_path: str) -> bool:
    """Safely remove a file with error handling."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")
    return False

def setup_logging(log_level: int = logging.INFO) -> None:
    """Setup application logging."""
    log_file = SAVE_DIR / "doccamocr.log"

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )