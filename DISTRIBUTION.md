# Texta OCR — Distribution Bundle (v1.0.0)

Complete drop of source code, packaging configuration, and a working
Windows build.

## What's in this folder

```
OCR_texta_v01/
├── DISTRIBUTION.md          ← this file
├── README.md                ← project overview
├── LICENSE.txt              ← MIT
│
├── main.py                  ← application entry point (with splash + updater)
├── run.py                   ← alternative launcher with UTF-8 logging setup
├── config.py                ← all configuration constants and settings
├── requirements.txt         ← Python dependencies
│
├── core/                    ← OCR engine, camera thread, PDF generator,
│                              text post-processor, updater
├── gui/                     ← PyQt5 main window
├── utils/                   ← camera + image-processing helpers, word list
├── assets/                  ← splash screen and icons (PNG)
│
├── packaging/               ← PyInstaller spec, runtime hook, code-signing
│                              scripts, Inno Setup installer config,
│                              macOS entitlements
├── .github/workflows/       ← CI matrix build for Windows + macOS
├── docs/RELEASE.md          ← release runbook (signing, notarization, CI)
│
└── dist/Texta/              ← BUILT WINDOWS APPLICATION
    ├── Texta.exe              double-click to run (no install required)
    └── _internal/             bundled Python runtime + Qt + Tesseract +
                                tessdata + assets
```

## Run the built app right now

1. Open `dist/Texta/`
2. Double-click `Texta.exe`

No installation, no extra dependencies. Tesseract and `eng.traineddata`
are bundled inside `_internal/`.

> **Note:** This build is unsigned. On first launch Windows SmartScreen will
> show "Windows protected your PC". Click **More info → Run anyway**.
> Code signing is configured in CI but requires an Authenticode certificate
> (see `docs/RELEASE.md`).

## Build a Windows installer (.exe with Start Menu / uninstall)

The `dist/Texta/` folder is the input to Inno Setup:

1. Install Inno Setup 6 from <https://jrsoftware.org/isdl.php>
2. Run:
   ```
   "C:\Program Files (x86)\Inno Setup 6\iscc.exe" packaging\texta_installer.iss
   ```
3. Output: `dist/installer/Texta-Setup-1.0.0.exe`

## Build for macOS

Run on a Mac with Tesseract installed:

```bash
brew install tesseract
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm packaging/texta.spec
```

Output: `dist/Texta.app`

For a signed + notarized DMG, set Apple credentials and run
`bash packaging/sign_macos.sh` — see `docs/RELEASE.md`.

## Run from source (any OS)

```bash
pip install -r requirements.txt
python run.py
```

Requires Tesseract installed and on `PATH`.

## Versioning

`APP_VERSION` is set in `config.py` and read by both PyInstaller (for the
.app/.exe metadata) and the Inno Setup installer. Bump it there before
tagging a release.

## Source repository

The full repository (including git history) lives at
`C:\Users\alexcalo\Desktop\Texta\`. This `OCR_texta_v01` folder is a
distribution snapshot — copy the snapshot folder around, or zip it for sharing.

## Build environment used for the included `dist/`

- **OS**: Windows 11 (x64)
- **Python**: 3.11.4
- **PyInstaller**: 6.16.0
- **Tesseract**: 5.5.0
- **Build date**: 2026-04-27

The `_internal/` folder is platform-specific. Do not copy `dist/Texta/` to
macOS or Linux — rebuild on the target OS.
