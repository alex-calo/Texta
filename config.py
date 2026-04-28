"""
Configuration constants and settings for DocCamOCR with USB camera optimizations
"""

import os
import sys
import logging
from pathlib import Path
from PyQt5.QtCore import QSettings

logger = logging.getLogger(__name__)

# Application info
APP_NAME = "Texta"
APP_VERSION = "1.0.0"
ORGANIZATION = "Texta"

# Update feed — set to your GitHub "owner/repo". Empty string disables update checks.
UPDATE_REPO = ""

# Resource roots — work both in dev and inside a PyInstaller bundle
def _resource_root() -> Path:
    """Return the directory where bundled resources (assets/, tessdata/) live."""
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', sys.executable)).resolve()
    return Path(__file__).resolve().parent

RESOURCE_ROOT = _resource_root()
ASSETS_DIR = RESOURCE_ROOT / "assets"

# File paths — these MUST be in user-writable locations.
# When the app is installed to Program Files / Applications, the install
# directory is read-only for the user.
SAVE_DIR = Path.home() / "Documents" / APP_NAME
SAVE_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = SAVE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "texta.log"

# Camera settings
DEFAULT_RESOLUTION = (1920, 1080)  # OCR needs ≥1280×720 for legible documents
SUPPORTED_RESOLUTIONS = [
    (640, 480),
    (1280, 720),
    (1920, 1080),
    (2560, 1440),
]
MAX_CAMERAS = 10
CAMERA_FPS = 30

# Tesseract per-word confidence threshold (0–100). Words below this are flagged.
LOW_CONFIDENCE_THRESHOLD = 60

# Simple backend selection
def get_camera_backends(camera_index: int):
    """Simple backend selection without complex hardware detection."""
    import platform
    if platform.system() == 'Windows':
        return ['DSHOW', 'MSMF', 'ANY']
    else:
        return ['ANY']

# OCR settings
OCR_PROCESSING_FPS = 5

# PDF settings
PDF_MARGIN = 10
PDF_PAGE_WIDTH = 210
PDF_IMAGE_WIDTH = 190

# OCR Preprocessing Settings
OCR_PREPROCESSING = {
    "blur_kernel_size": 3,
    "clahe_clip_limit": 2.0,
    "clahe_grid_size": 8,
    "adaptive_threshold_block": 11,
    "adaptive_threshold_c": 2,
    "use_roi": True,
    "roi_margin": 0.1
}

# Tesseract OCR Paths
TESSERACT_PATHS = {
    "windows": [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ],
    "darwin": "/usr/local/bin/tesseract",
    "linux": "/usr/bin/tesseract"
}

def get_tesseract_path():
    """Resolve the Tesseract binary.

    Order of precedence:
      1. Bundled binary inside a PyInstaller frozen build (set by runtime hook)
      2. `tesseract` on PATH
      3. Known install locations per platform
    """
    bundled = os.environ.get("TEXTA_TESSERACT_PATH")
    if bundled and os.path.exists(bundled):
        return bundled

    import shutil
    in_path = shutil.which("tesseract")
    if in_path:
        return in_path
    system = sys.platform
    if system.startswith('win'):
        for path in TESSERACT_PATHS["windows"]:
            if os.path.exists(path):
                return path
        return TESSERACT_PATHS["windows"][0]
    elif system == 'darwin':
        return TESSERACT_PATHS["darwin"]
    else:
        return TESSERACT_PATHS["linux"]

TESSERACT_PATH = get_tesseract_path()

def validate_tesseract_path() -> bool:
    """Validate Tesseract installation and accessibility."""
    try:
        import pytesseract
        tesseract_version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {tesseract_version}")
        return True
    except Exception as e:
        logger.error(f"Tesseract validation failed: {e}")
        return False

# USB Camera Specific Settings
USB_CAMERA_SETTINGS = {
    "warm_up_frames": 5,           # Number of frames to discard during warm-up
    "frame_timeout": 3.0,          # Timeout for frame reading
    "retry_attempts": 3,           # Number of retry attempts
    "buffer_size": 1,              # Camera buffer size
    "preferred_fps": 30,           # Preferred FPS
    "exposure_compensation": 0.5,  # Exposure compensation
}

class AppSettings:
    def __init__(self):
        self.settings = QSettings(ORGANIZATION, APP_NAME)

    def get_camera_index(self) -> int:
        return self.settings.value("camera/index", 0, type=int)

    def set_camera_index(self, index: int):
        self.settings.setValue("camera/index", index)

    def get_resolution(self) -> str:
        return self.settings.value("camera/resolution", "640x480", type=str)

    def set_resolution(self, resolution: str):
        self.settings.setValue("camera/resolution", resolution)

    def get_save_directory(self) -> str:
        return self.settings.value("files/save_directory", str(SAVE_DIR), type=str)

    def set_save_directory(self, directory: str):
        self.settings.setValue("files/save_directory", directory)

# OCR configurations
TESSERACT_CONFIGS = {
    "default": "--oem 3 --psm 6",
    "single_line": "--oem 3 --psm 7",
    "single_word": "--oem 3 --psm 8",
    "sparse_text": "--oem 3 --psm 11",
    "uniform_block": "--oem 3 --psm 6"
}

TESSERACT_CONFIG = TESSERACT_CONFIGS["uniform_block"]

# Human-readable content modes shown in the GUI
CONTENT_MODES = {
    "Plain text":  TESSERACT_CONFIGS["default"],
    "Single line": TESSERACT_CONFIGS["single_line"],
    "Sparse text": TESSERACT_CONFIGS["sparse_text"],
    "Table":       TESSERACT_CONFIGS["uniform_block"],
}

# Enhanced OCR Settings
OCR_ENHANCEMENT = {
    "preprocessing_strategies": 4,
    "min_confidence_threshold": 50,
    "max_processing_fps": 3,
    "spell_check_enabled": True,
    "grammar_check_enabled": True,
    "text_correction_enabled": True,
    "ensemble_voting": True,
}

# Language Settings
LANGUAGE_SETTINGS = {
    "primary_language": "eng",
    "fallback_languages": ["eng", "fra", "spa"],
    "custom_dictionary": [
        "homo", "deus", "yuval", "harari", "history", "tomorrow", "brief",
        "document", "camera", "ocr", "york", "university"
    ]
}

