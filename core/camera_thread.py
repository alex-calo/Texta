import cv2
from PyQt5.QtCore import QThread, pyqtSignal
import logging

from config import DEFAULT_RESOLUTION
from utils.camera_utils import open_camera, safe_release_camera

logger = logging.getLogger(__name__)

_MAX_READ_FAILURES = 5


class CameraThread(QThread):
    frame_ready = pyqtSignal(object)  # Emits captured frame (np.ndarray)
    error = pyqtSignal(str)           # Emits error messages

    def __init__(self, camera_index=0, resolution=DEFAULT_RESOLUTION):
        super().__init__()
        self.camera_index = camera_index
        self.resolution = resolution
        self._running = False
        self.cap = None

    def set_resolution(self, resolution):
        """Set the capture resolution. Camera must be restarted for it to take effect."""
        self.resolution = resolution

    def run(self):
        """Thread loop to capture frames from the camera."""
        try:
            w, h = self.resolution
            self.cap = open_camera(self.camera_index, w, h)
            if self.cap is None or not self.cap.isOpened():
                self.error.emit(f"Cannot open camera {self.camera_index}")
                return
            self._running = True
            consecutive_failures = 0
            while self._running:
                ret, frame = self.cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= _MAX_READ_FAILURES:
                        self.error.emit(
                            f"Camera {self.camera_index}: too many consecutive read failures"
                        )
                        break
                    self.msleep(50)
                    continue
                consecutive_failures = 0
                self.frame_ready.emit(frame)
                self.msleep(30)  # ~30 FPS
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.cap:
                safe_release_camera(self.cap)
                self.cap = None
            logger.info(f"Camera {self.camera_index} thread stopped.")

    def stop(self):
        """Stop the camera thread safely."""
        self._running = False
        self.wait()

    def switch_camera(self, new_index):
        """Switch to a different camera device. No-op if already running this index."""
        if new_index == self.camera_index and self.isRunning():
            return
        logger.info(f"Switching camera from {self.camera_index} to {new_index}")
        was_running = self.isRunning()
        self.stop()
        self.camera_index = new_index
        if was_running:
            self.start()

    def set_autofocus(self, enabled: bool) -> bool:
        """Enable or disable camera autofocus. Returns True if the camera supports it."""
        if not (self.cap and self.cap.isOpened()):
            return False
        return self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1.0 if enabled else 0.0)

    def set_focus(self, value: int) -> bool:
        """Set manual focus value (0–255). Disables autofocus first. Returns True if supported."""
        if not (self.cap and self.cap.isOpened()):
            return False
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0.0)
        return self.cap.set(cv2.CAP_PROP_FOCUS, float(value))
