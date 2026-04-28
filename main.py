"""Texta OCR — main entry point with splash, real-init progress, and update check."""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

from PyQt5.QtWidgets import QApplication, QSplashScreen, QProgressBar, QMessageBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer

from config import APP_NAME, APP_VERSION, ORGANIZATION, ASSETS_DIR, UPDATE_REPO, LOG_FILE

# Reduce OpenCV verbosity
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['OPENCV_VIDEOIO_DEBUG'] = 'FALSE'


def _check_for_update_async(parent):
    """Background update check — never blocks startup."""
    if not UPDATE_REPO:
        return
    try:
        from core.updater import check_for_update
        info = check_for_update(UPDATE_REPO, APP_VERSION)
    except Exception as e:
        logging.getLogger(__name__).debug(f"Update check skipped: {e}")
        return
    if info:
        msg = QMessageBox(parent)
        msg.setWindowTitle(f"{APP_NAME} update available")
        msg.setText(
            f"<b>{APP_NAME} {info.version}</b> is available "
            f"(you're on {APP_VERSION}).<br><br>"
            f"<a href='{info.url}'>Open release page</a>"
        )
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.show()  # non-modal


def main():
    """Launch the main application window with splash and real-time progress."""
    # Route log file to the user-writable LOG_DIR (Documents/Texta/logs/) —
    # NOT relative to the executable, which is in Program Files for installed builds.
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=1_000_000, backupCount=5, encoding='utf-8',
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting {APP_NAME} {APP_VERSION}...")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(ORGANIZATION)

        # === Splash screen setup ===
        splash_image = str(ASSETS_DIR / "Texta.png")
        splash = None
        progress = None
        if os.path.exists(splash_image):
            pixmap = QPixmap(splash_image)
            splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
            splash.setMask(pixmap.mask())
            splash.show()
            app.processEvents()

            progress = QProgressBar(splash)
            progress.setGeometry(50, pixmap.height() - 50, pixmap.width() - 100, 20)
            progress.setMaximum(100)
            progress.setValue(0)
            progress.setTextVisible(True)
            app.processEvents()

        def update_progress(value, message=None):
            if progress:
                progress.setValue(value)
            if splash and message:
                splash.showMessage(message, Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            app.processEvents()

        # === Real initialization steps ===
        update_progress(10, "Loading GUI modules...")
        from gui.main_window import DocCamApp
        update_progress(30, "GUI modules loaded.")

        update_progress(40, "Initializing OCR engine...")
        from core.ocr_engine import OCREngine
        ocr_engine = OCREngine()
        update_progress(60, "OCR engine ready.")

        update_progress(65, "Initializing PDF generator...")
        from core.pdf_generator import PDFGenerator
        pdf_generator = PDFGenerator()
        update_progress(80, "PDF generator ready.")

        update_progress(85, "Setting up main window...")
        window = DocCamApp(ocr_engine=ocr_engine, pdf_generator=pdf_generator)
        update_progress(95, "Main window ready.")

        window.show()
        update_progress(100, "Ready.")
        QTimer.singleShot(500, splash.close if splash else lambda: None)

        # Update check — runs after window is up so it doesn't slow startup
        QTimer.singleShot(3000, lambda: _check_for_update_async(window))

        logger.info("Application started successfully.")
        return app.exec()

    except Exception as e:
        logger.critical(f"Application failed to start: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
