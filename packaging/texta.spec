# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Texta OCR.

Build with:    pyinstaller --clean --noconfirm packaging/texta.spec
Output:        dist/Texta/         (Windows & Linux folder build)
               dist/Texta.app      (macOS app bundle)

Bundles:
  * Python application
  * assets/ folder
  * tesseract binary discovered on PATH
  * eng.traineddata (and osd.traineddata if present) into tessdata/
"""
import os
import re
import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# ---------------------------------------------------------------------------
# Paths and version
# ---------------------------------------------------------------------------
ROOT = Path(SPECPATH).resolve().parent
PACKAGING = ROOT / 'packaging'

_config_text = (ROOT / 'config.py').read_text(encoding='utf-8')
_match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", _config_text)
APP_VERSION = _match.group(1) if _match else "0.0.0"


# ---------------------------------------------------------------------------
# Locate tesseract + tessdata
# ---------------------------------------------------------------------------
def _find_tesseract() -> Path:
    p = shutil.which('tesseract')
    if not p:
        raise SystemExit(
            "tesseract binary not found on PATH. Install it before building:\n"
            "  Windows:  choco install tesseract\n"
            "  macOS:    brew install tesseract\n"
            "  Linux:    apt-get install tesseract-ocr"
        )
    return Path(p).resolve()


def _find_tessdata() -> Path:
    env = os.environ.get('TESSDATA_PREFIX')
    if env and Path(env).exists() and (Path(env) / 'eng.traineddata').exists():
        return Path(env)

    candidates = []
    if sys.platform == 'darwin':
        candidates += [
            Path('/opt/homebrew/share/tessdata'),   # Apple Silicon brew
            Path('/usr/local/share/tessdata'),      # Intel brew
        ]
    elif sys.platform.startswith('linux'):
        candidates += [
            Path('/usr/share/tesseract-ocr/5/tessdata'),
            Path('/usr/share/tesseract-ocr/4.00/tessdata'),
            Path('/usr/share/tessdata'),
        ]
    elif sys.platform == 'win32':
        candidates += [
            Path(r'C:\Program Files\Tesseract-OCR\tessdata'),
            Path(r'C:\Program Files (x86)\Tesseract-OCR\tessdata'),
        ]
    for c in candidates:
        if (c / 'eng.traineddata').exists():
            return c
    raise SystemExit(
        "eng.traineddata not found. Set TESSDATA_PREFIX or install Tesseract language data."
    )


tesseract_bin = _find_tesseract()
tessdata_dir = _find_tessdata()

print(f"[texta.spec] tesseract: {tesseract_bin}")
print(f"[texta.spec] tessdata:  {tessdata_dir}")
print(f"[texta.spec] version:   {APP_VERSION}")


# ---------------------------------------------------------------------------
# Bundle inventory
# ---------------------------------------------------------------------------
binaries = [(str(tesseract_bin), '.')]

datas = [
    (str(ROOT / 'assets'), 'assets'),
    (str(tessdata_dir / 'eng.traineddata'), 'tessdata'),
]
osd = tessdata_dir / 'osd.traineddata'
if osd.exists():
    datas.append((str(osd), 'tessdata'))

# pyspellchecker ships its language dictionaries as package data — needed at runtime
try:
    datas += collect_data_files('spellchecker')
except Exception:
    pass  # Spell-correction is optional; app still runs without it.


# ---------------------------------------------------------------------------
# Platform-specific icons
# ---------------------------------------------------------------------------
icon = None
if sys.platform == 'win32':
    ico = ROOT / 'assets' / 'Texta.ico'
    if ico.exists():
        icon = str(ico)
elif sys.platform == 'darwin':
    icns = ROOT / 'assets' / 'Texta.icns'
    if icns.exists():
        icon = str(icns)


# ---------------------------------------------------------------------------
# PyInstaller graph
# ---------------------------------------------------------------------------
block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=['pkg_resources.py2_warn'],
    hookspath=[],
    runtime_hooks=[str(PACKAGING / 'runtime_hook.py')],
    excludes=['tkinter', 'unittest', 'pdb', 'doctest', 'IPython', 'pytest'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Texta',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=icon,
    bootloader_ignore_signals=False,
    runtime_tmpdir=None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name='Texta',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Texta.app',
        icon=icon,
        bundle_identifier='com.texta.ocr',
        info_plist={
            # User-facing camera permission prompt (macOS 10.14+ requires this)
            'NSCameraUsageDescription':
                'Texta uses your camera to capture documents and run OCR.',
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
            'LSMinimumSystemVersion': '10.15',
            'NSPrincipalClass': 'NSApplication',
            'CFBundleDisplayName': 'Texta',
            'CFBundleName': 'Texta',
        },
    )
