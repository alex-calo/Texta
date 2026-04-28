import logging
import re
from collections import deque

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QComboBox, QSlider,
    QCheckBox, QStatusBar, QSplitter, QFrame, QSizePolicy,
    QShortcut,
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QTextCharFormat, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from core.camera_thread import CameraThread
from core.ocr_engine import OCREngine
from core.pdf_generator import PDFGenerator
from utils.camera_utils import list_cameras
from utils.image_processing import is_frame_focused
from config import CONTENT_MODES, DEFAULT_RESOLUTION, SUPPORTED_RESOLUTIONS

_FRAME_BUFFER_SIZE = 5  # multi-frame Snap: keep N most recent frames, OCR the sharpest
_HIGHLIGHT_COLOR = "#fff3a0"  # yellow background for low-confidence words

logger = logging.getLogger(__name__)


class CameraScanThread(QThread):
    """Detect available cameras off the GUI thread to keep the UI responsive."""
    cameras_found = pyqtSignal(list)

    def __init__(self, max_cams: int = 5, parent=None):
        super().__init__(parent)
        self.max_cams = max_cams

    def run(self):
        try:
            cams = list_cameras(max_cams=self.max_cams)
        except Exception as e:
            logger.error(f"Camera scan error: {e}")
            cams = []
        self.cameras_found.emit(cams)


class DocCamApp(QMainWindow):
    """Main window for Texta OCR."""

    def __init__(self, ocr_engine=None, pdf_generator=None):
        super().__init__()
        self.setWindowTitle("Texta OCR")
        self.resize(960, 580)

        # Core components — accept pre-built instances to avoid double init
        self.ocr_engine = ocr_engine or OCREngine()
        self.pdf_generator = pdf_generator or PDFGenerator()
        self.current_frame = None
        self.recent_frames: deque = deque(maxlen=_FRAME_BUFFER_SIZE)
        self.crop_margin = 0.0

        self.camera_thread = CameraThread(resolution=DEFAULT_RESOLUTION)
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.camera_thread.error.connect(self.handle_camera_error)

        self._build_ui()
        self._setup_shortcuts()
        self.status("Ready.  Ctrl+G = Snap  |  Ctrl+P = PDF  |  Ctrl+L = Clear")
        logger.info("Texta OCR initialized.")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 0)
        root.setSpacing(4)

        root.addWidget(self._build_controls())

        splitter = QSplitter(Qt.Horizontal)

        self.camera_label = QLabel("No camera feed")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(320, 240)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.camera_label)

        self.text_view = QTextEdit()
        self.text_view.setPlaceholderText("OCR output will appear here…")
        self.text_view.setMinimumWidth(260)
        splitter.addWidget(self.text_view)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        self.setStatusBar(QStatusBar())

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Camera selector + refresh
        self.camera_selector = QComboBox()
        self.camera_selector.setFixedWidth(110)
        self.camera_selector.setToolTip("Active camera")
        self._populate_camera_list()
        layout.addWidget(self.camera_selector)

        self.btn_refresh = QPushButton("⟳")   # ⟳
        self.btn_refresh.setFixedWidth(26)
        self.btn_refresh.setToolTip("Re-scan cameras")
        layout.addWidget(self.btn_refresh)

        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")
        self.btn_start.setFixedWidth(46)
        self.btn_stop.setFixedWidth(46)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)

        # Resolution selector
        self.res_selector = QComboBox()
        for w, h in SUPPORTED_RESOLUTIONS:
            self.res_selector.addItem(f"{w}×{h}", (w, h))
        if DEFAULT_RESOLUTION in SUPPORTED_RESOLUTIONS:
            self.res_selector.setCurrentIndex(SUPPORTED_RESOLUTIONS.index(DEFAULT_RESOLUTION))
        self.res_selector.setFixedWidth(100)
        self.res_selector.setToolTip("Capture resolution — higher = better OCR (camera must support it)")
        layout.addWidget(self.res_selector)

        layout.addWidget(self._vline())

        # Autofocus + manual focus slider
        self.chk_autofocus = QCheckBox("Auto")
        self.chk_autofocus.setChecked(True)
        self.chk_autofocus.setToolTip("Toggle camera autofocus")
        layout.addWidget(self.chk_autofocus)

        layout.addWidget(QLabel("Focus:"))
        self.sld_focus = QSlider(Qt.Horizontal)
        self.sld_focus.setRange(0, 255)
        self.sld_focus.setValue(128)
        self.sld_focus.setFixedWidth(80)
        self.sld_focus.setEnabled(False)
        self.sld_focus.setToolTip("Manual focus (0–255) — release to apply")
        layout.addWidget(self.sld_focus)

        layout.addWidget(self._vline())

        # Crop margin slider
        layout.addWidget(QLabel("Crop:"))
        self.sld_crop = QSlider(Qt.Horizontal)
        self.sld_crop.setRange(0, 25)
        self.sld_crop.setValue(0)
        self.sld_crop.setFixedWidth(70)
        self.sld_crop.setToolTip("Crop margin from each edge (0–25%)")
        layout.addWidget(self.sld_crop)
        self.lbl_crop_val = QLabel("0%")
        self.lbl_crop_val.setFixedWidth(30)
        layout.addWidget(self.lbl_crop_val)

        layout.addWidget(self._vline())

        # Content mode
        self.mode_selector = QComboBox()
        for label in CONTENT_MODES:
            self.mode_selector.addItem(label)
        self.mode_selector.setFixedWidth(100)
        self.mode_selector.setToolTip("OCR content type — affects Tesseract layout analysis and post-processing")
        layout.addWidget(self.mode_selector)

        layout.addWidget(self._vline())

        # Action buttons
        self.btn_snap = QPushButton("Snap + OCR")
        self.btn_clear = QPushButton("Clear")
        self.btn_pdf = QPushButton("PDF")
        self.btn_pdf.setToolTip("Export OCR text as PDF  (Ctrl+P)")
        self.btn_snap.setToolTip("Capture frame and run OCR  (Ctrl+G)")
        self.btn_clear.setToolTip("Clear text output  (Ctrl+L)")
        layout.addWidget(self.btn_snap)
        layout.addWidget(self.btn_clear)
        layout.addWidget(self.btn_pdf)

        layout.addStretch()

        # Wire all signals
        self.btn_start.clicked.connect(self.start_camera)
        self.btn_stop.clicked.connect(self.stop_camera)
        self.btn_refresh.clicked.connect(self.refresh_cameras)
        self.btn_snap.clicked.connect(self.capture_and_ocr)
        self.btn_clear.clicked.connect(self.clear_text)
        self.btn_pdf.clicked.connect(self.export_pdf)
        self.camera_selector.currentIndexChanged.connect(self.switch_camera)
        self.res_selector.currentIndexChanged.connect(self._on_resolution_changed)
        self.chk_autofocus.toggled.connect(self._on_autofocus_toggled)
        self.sld_focus.sliderReleased.connect(self._on_focus_released)
        self.sld_crop.valueChanged.connect(self._on_crop_changed)

        return bar

    @staticmethod
    def _vline() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+G"), self, self.capture_and_ocr)
        QShortcut(QKeySequence("Ctrl+P"), self, self.export_pdf)
        QShortcut(QKeySequence("Ctrl+L"), self, self.clear_text)
        QShortcut(QKeySequence("Ctrl+T"), self, self.start_camera)
        QShortcut(QKeySequence("Ctrl+K"), self, self.stop_camera)

    # ------------------------------------------------------------------
    # Camera management
    # ------------------------------------------------------------------

    def _populate_camera_list(self):
        """Detect available cameras using robust threaded detection."""
        self.camera_selector.clear()
        for index in list_cameras(max_cams=5):
            self.camera_selector.addItem(f"Camera {index}", index)
        if self.camera_selector.count() == 0:
            self.camera_selector.addItem("No camera", -1)

    def refresh_cameras(self):
        """Re-detect cameras asynchronously — does not block the GUI."""
        if getattr(self, '_scan_thread', None) and self._scan_thread.isRunning():
            return  # A scan is already in progress
        was_running = self.camera_thread.isRunning()
        if was_running:
            self.stop_camera()
        self.btn_refresh.setEnabled(False)
        self.camera_selector.setEnabled(False)
        self.status("Scanning cameras…")

        self._scan_thread = CameraScanThread(max_cams=5, parent=self)
        self._scan_thread.cameras_found.connect(
            lambda cams: self._on_scan_done(cams, was_running)
        )
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.start()

    def _on_scan_done(self, cams: list, was_running: bool):
        """Update the dropdown after async camera detection finishes."""
        active_index = self.camera_thread.camera_index

        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()
        for index in cams:
            self.camera_selector.addItem(f"Camera {index}", index)
        if self.camera_selector.count() == 0:
            self.camera_selector.addItem("No camera", -1)
        # Restore selection so the dropdown reflects the actually-active camera
        for i in range(self.camera_selector.count()):
            if self.camera_selector.itemData(i) == active_index:
                self.camera_selector.setCurrentIndex(i)
                break
        self.camera_selector.blockSignals(False)

        self.camera_selector.setEnabled(True)
        self.btn_refresh.setEnabled(True)

        cam_index = self.camera_selector.currentData()
        if was_running and cam_index is not None and cam_index != -1:
            self.start_camera()

        self.status(f"Found {len(cams)} camera(s).")

    def start_camera(self):
        try:
            if not self.camera_thread.isRunning():
                self.camera_thread.start()
                self.status("Camera started.")
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            self.status(f"Error starting camera: {e}")

    def stop_camera(self):
        try:
            if self.camera_thread.isRunning():
                self.camera_thread.stop()
                self.camera_label.setText("No camera feed")
                self.recent_frames.clear()
                self.status("Camera stopped.")
        except Exception as e:
            logger.error(f"Error stopping camera: {e}")

    def switch_camera(self, _combo_index):
        cam_index = self.camera_selector.currentData()
        if cam_index is None or cam_index == -1:
            return
        try:
            self.camera_thread.switch_camera(cam_index)
            self.status(f"Switched to Camera {cam_index}.")
        except Exception as e:
            logger.error(f"Failed to switch camera: {e}")

    # ------------------------------------------------------------------
    # Focus / crop controls
    # ------------------------------------------------------------------

    def _on_autofocus_toggled(self, checked: bool):
        self.sld_focus.setEnabled(not checked)
        supported = self.camera_thread.set_autofocus(checked)
        if not self.camera_thread.isRunning():
            self.status("Start the camera first to apply focus settings.")
        elif supported:
            self.status("Autofocus " + ("on." if checked else "off — use slider to set focus."))
        else:
            self.status("Focus control not supported by this camera.")

    def _on_focus_released(self):
        value = self.sld_focus.value()
        supported = self.camera_thread.set_focus(value)
        if not self.camera_thread.isRunning():
            self.status("Start the camera first to apply focus settings.")
        elif supported:
            self.status(f"Focus set to {value}.")
        else:
            self.status("Manual focus not supported by this camera.")

    def _on_crop_changed(self, value: int):
        self.crop_margin = value / 100.0
        self.lbl_crop_val.setText(f"{value}%")

    def _on_resolution_changed(self, _idx: int):
        res = self.res_selector.currentData()
        if not res:
            return
        self.camera_thread.set_resolution(res)
        self.recent_frames.clear()  # buffer is now stale — purge
        if self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread.start()
            self.status(f"Resolution → {res[0]}×{res[1]}, camera restarted.")
        else:
            self.status(f"Resolution set to {res[0]}×{res[1]} (applies on next start).")

    # ------------------------------------------------------------------
    # Frame display
    # ------------------------------------------------------------------

    def update_frame(self, frame: np.ndarray):
        """Display camera frame, overlaying crop boundary when active."""
        try:
            self.current_frame = frame.copy()  # thread-safe copy for OCR
            self.recent_frames.append(self.current_frame)
            display = frame

            if self.crop_margin > 0:
                display = frame.copy()
                h, w = display.shape[:2]
                mx, my = int(w * self.crop_margin), int(h * self.crop_margin)
                cv2.rectangle(display, (mx, my), (w - mx, h - my), (0, 200, 0), 2)

            h, w = display.shape[:2]
            q_img = QImage(display.data, w, h, 3 * w, QImage.Format_BGR888)
            self.camera_label.setPixmap(
                QPixmap.fromImage(q_img).scaled(
                    self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        except Exception as e:
            logger.error(f"Error displaying frame: {e}")

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def capture_and_ocr(self):
        if not self.recent_frames:
            self.status("No frames — start the camera first.")
            return
        # Multi-frame Snap: pick the sharpest frame from the buffer
        frame = max(self.recent_frames, key=self._sharpness)
        if not is_frame_focused(frame):
            self.text_view.setText("[All recent frames too blurry — hold steady and try again]")
            self.status("All buffered frames blurry.")
            return
        mode = self.mode_selector.currentText()
        try:
            self.status("Running OCR…")
            result = self.ocr_engine.run_ocr(
                frame, mode=mode, crop_margin=self.crop_margin
            )
            if not result.text:
                self.text_view.setText("[No text detected]")
                self.status("OCR complete — no text detected.")
                return
            self._display_with_highlights(result.text, result.low_confidence_words)
            n_low = len(result.low_confidence_words)
            tail = f" ({n_low} low-confidence)" if n_low else ""
            self.status(f"OCR complete — {len(result.text)} chars{tail}.")
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            self.status(f"OCR error: {e}")

    @staticmethod
    def _sharpness(frame: np.ndarray) -> float:
        """Laplacian variance — higher means sharper."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _display_with_highlights(self, text: str, low_conf_words: set):
        """Render OCR output, highlighting low-confidence words with a yellow background."""
        self.text_view.clear()
        cursor = self.text_view.textCursor()

        fmt_normal = QTextCharFormat()
        fmt_highlight = QTextCharFormat()
        fmt_highlight.setBackground(QColor(_HIGHLIGHT_COLOR))

        if not low_conf_words:
            cursor.insertText(text, fmt_normal)
            return

        pattern = re.compile(
            r'\b(?:' + '|'.join(re.escape(w) for w in low_conf_words) + r')\b'
        )
        last_end = 0
        for match in pattern.finditer(text):
            if match.start() > last_end:
                cursor.insertText(text[last_end:match.start()], fmt_normal)
            cursor.insertText(match.group(0), fmt_highlight)
            last_end = match.end()
        if last_end < len(text):
            cursor.insertText(text[last_end:], fmt_normal)

    def clear_text(self):
        self.text_view.clear()
        self.status("Cleared.")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_pdf(self):
        text = self.text_view.toPlainText().strip()
        if not text:
            self.status("Nothing to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if path:
            try:
                self.pdf_generator.generate_pdf(text, path)
                self.status(f"PDF saved: {path}")
            except Exception as e:
                logger.error(f"PDF export failed: {e}")
                self.status(f"PDF error: {e}")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def handle_camera_error(self, msg: str):
        logger.error(f"Camera error: {msg}")
        self.status(f"Camera error: {msg}")

    def status(self, msg: str):
        self.statusBar().showMessage(msg)

    def closeEvent(self, event):
        logger.info("Closing — releasing camera.")
        self.stop_camera()
        event.accept()
