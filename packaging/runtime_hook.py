"""PyInstaller runtime hook.

Runs before any application code in a frozen build. Points the app at the
Tesseract binary and tessdata directory bundled inside the .app/.exe.
"""
import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    base = Path(getattr(sys, '_MEIPASS', sys.executable)).resolve()

    # Bundled Tesseract binary
    if sys.platform == 'win32':
        bundled = base / 'tesseract.exe'
    else:
        bundled = base / 'tesseract'
    if bundled.exists():
        os.environ['TEXTA_TESSERACT_PATH'] = str(bundled)

    # Bundled language data
    tessdata = base / 'tessdata'
    if tessdata.exists():
        os.environ['TESSDATA_PREFIX'] = str(tessdata)
