"""
Camera utility functions with robust error handling and OpenCV backend management
"""
import cv2
import logging
import time
from typing import Dict, List, Tuple, Optional
import threading
import platform
import os

from config import MAX_CAMERAS, SUPPORTED_RESOLUTIONS, DEFAULT_RESOLUTION

logger = logging.getLogger(__name__)

# In-memory cache of last-known-good backend per camera index.
# Lets us skip backends that have already failed for a given camera —
# saves the multi-second per-backend timeout on every reopen.
_BACKEND_CACHE: Dict[int, str] = {}


def _get_priority_backends(camera_index: int) -> List[str]:
    """Return backend list with the cached working backend tried first."""
    if platform.system() == 'Windows':
        default = ['MSMF', 'DSHOW', 'ANY']
    else:
        default = ['ANY']
    cached = _BACKEND_CACHE.get(camera_index)
    if cached and cached in default:
        return [cached] + [b for b in default if b != cached]
    return default

# Suppress OpenCV warnings
def suppress_opencv_warnings():
    """Suppress OpenCV warning messages."""
    # Method 1: Environment variable
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'

    # Method 2: Set OpenCV logging level (compatible with different OpenCV versions)
    try:
        # For newer OpenCV versions
        cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
    except AttributeError:
        try:
            # For older OpenCV versions
            cv2.setLogLevel(cv2.LOG_LEVEL_OFF)
        except AttributeError:
            # If neither works, just continue
            pass

suppress_opencv_warnings()

def is_virtual_camera(camera_index: int) -> bool:
    """Check if camera index might be virtual."""
    # Less aggressive filtering on Windows
    if platform.system() == 'Windows':
        return camera_index >= 15  # Only filter very high indices
    return False

def list_cameras(max_cams: int = MAX_CAMERAS) -> List[int]:
    """Reliable camera listing with suppressed OpenCV errors."""
    available = []

    logger.info("Starting camera detection...")

    for i in range(max_cams):
        if is_virtual_camera(i):
            continue

        try:
            backends_to_try = _get_priority_backends(i)

            for backend_name in backends_to_try:
                try:
                    backend = getattr(cv2, f'CAP_{backend_name}')

                    # Use context manager to suppress OpenCV errors
                    result = _silent_camera_test(i, backend, timeout=2.0)

                    if result:
                        available.append(i)
                        _BACKEND_CACHE[i] = backend_name
                        logger.info(f"Found camera {i} with backend {backend_name}")
                        break

                except Exception as e:
                    # Don't log backend-specific errors to reduce noise
                    continue

        except Exception:
            continue

    logger.info(f"Camera detection complete: Found {len(available)} cameras: {available}")
    return available

def _silent_camera_test(camera_index: int, backend: int, timeout: float = 2.0) -> bool:
    """Camera test that suppresses OpenCV error messages."""
    result = [False]

    def test_camera():
        try:
            # Use a more robust approach to handle OpenCV backend issues
            cap = None
            try:
                cap = cv2.VideoCapture(camera_index, backend)
                if cap.isOpened():
                    # Set minimal properties
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Try to read a frame with multiple attempts
                    for attempt in range(3):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            # Basic validation
                            if frame.shape[0] > 10 and frame.shape[1] > 10:
                                result[0] = True
                                break
                        time.sleep(0.05)
            except Exception:
                # Suppress all exceptions during testing
                pass
            finally:
                if cap:
                    try:
                        cap.release()
                    except:
                        pass
        except Exception:
            # Suppress thread exceptions
            pass

    thread = threading.Thread(target=test_camera)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return False

    return result[0]

def open_camera(index: int, width: int, height: int) -> Optional[cv2.VideoCapture]:
    """Reliable camera opening with error suppression."""
    cap = None

    backends_to_try = _get_priority_backends(index)

    for backend_name in backends_to_try:
        try:
            backend = getattr(cv2, f'CAP_{backend_name}')
            logger.info(f"Opening camera {index} with {backend_name} at {width}x{height}")

            cap = _robust_camera_open(index, backend, width, height, timeout=3.0)

            if cap and cap.isOpened():
                # Apply minimal settings
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except:
                    pass

                # Quick verification
                if _verify_camera_quick(cap, timeout=1.0):
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    logger.info(f"Camera {index} ready at {actual_width}x{actual_height}")
                    _BACKEND_CACHE[index] = backend_name
                    return cap
                else:
                    safe_release_camera(cap)
                    cap = None

        except Exception as e:
            if cap:
                safe_release_camera(cap)
                cap = None
            continue

    logger.error(f"Failed to open camera {index}")
    return None

def _robust_camera_open(index: int, backend: int, width: int, height: int, timeout: float = 3.0) -> Optional[cv2.VideoCapture]:
    """Robust camera opening with error handling."""
    result = [None]

    def open_camera_thread():
        try:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                # Set only essential properties
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except:
                    pass
                result[0] = cap
        except Exception:
            # Suppress OpenCV errors
            pass

    thread = threading.Thread(target=open_camera_thread)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        if result[0]:
            safe_release_camera(result[0])
        return None

    return result[0]

def _verify_camera_quick(cap: cv2.VideoCapture, timeout: float = 1.0) -> bool:
    """Quick camera verification."""
    if not cap or not cap.isOpened():
        return False

    result = [False]

    def verify_thread():
        try:
            # Try to read just one frame
            for attempt in range(2):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    result[0] = True
                    break
                time.sleep(0.1)
        except Exception:
            pass

    thread = threading.Thread(target=verify_thread)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    return result[0]

def safe_release_camera(cap: cv2.VideoCapture) -> None:
    """Safely release camera resources."""
    if cap:
        try:
            cap.release()
            time.sleep(0.1)
        except Exception:
            pass

def get_camera_backends(camera_index: int):
    """Simple backend selection."""
    if platform.system() == 'Windows':
        return ['MSMF', 'DSHOW', 'ANY']
    else:
        return ['ANY']