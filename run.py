"""Texta — alternate launcher with explicit UTF-8 console setup.

Equivalent to running `python main.py`, but ensures Windows console
output is UTF-8 even on systems with a legacy code page.
"""
import sys
import logging
from logging.handlers import RotatingFileHandler

from config import LOG_FILE


def setup_logging():
    """Configure logging — file goes to user-writable LOG_DIR, console to stdout."""
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=1_000_000, backupCount=5, encoding='utf-8',
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, logging.StreamHandler(sys.stdout)],
    )

    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Texta application...")
        from main import main as app_main
        return app_main()
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
