# Texta — Release Runbook

End-to-end guide for cutting a Texta desktop release on Windows + macOS.

---

## TL;DR (once everything is set up)

```bash
# Bump APP_VERSION in config.py
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build, sign, notarize, and attach Windows + macOS installers
to a GitHub Release.

---

## One-time setup

### Windows code signing

You need an **OV** or **EV** Authenticode certificate (from DigiCert, Sectigo,
SSL.com, etc.). EV gives instant SmartScreen reputation; OV builds reputation
over time.

1. Export the cert as `.pfx` with a password.
2. Base64-encode it:
   ```bash
   base64 -i texta_cert.pfx -o texta_cert.b64
   ```
3. In the GitHub repo: **Settings → Secrets and variables → Actions**, add:
   - `WIN_CODESIGN_CERT_BASE64` — paste the contents of `texta_cert.b64`
   - `WIN_CODESIGN_PASSWORD` — the cert password

### macOS code signing + notarization

Requires an active **Apple Developer Program** membership ($99/yr).

1. In Xcode → Settings → Accounts → Manage Certificates, create a
   **Developer ID Application** certificate.
2. Export it from Keychain Access as `.p12` with a password.
3. Base64-encode it:
   ```bash
   base64 -i texta_cert.p12 -o texta_cert.b64
   ```
4. Generate an **app-specific password** at <https://appleid.apple.com>
   (Sign-In and Security → App-Specific Passwords).
5. Find your **Team ID** in <https://developer.apple.com/account> (top-right).
6. Add these GitHub secrets:
   - `MACOS_CERTIFICATE_BASE64` — contents of `texta_cert.b64`
   - `MACOS_CERTIFICATE_PASSWORD` — `.p12` password
   - `APPLE_DEV_ID` — full common name, e.g.
     `Developer ID Application: Jane Doe (ABC123XYZ)`
   - `APPLE_NOTARY_USER` — your Apple ID email
   - `APPLE_NOTARY_PASSWORD` — the app-specific password from step 4
   - `APPLE_TEAM_ID` — the 10-character team identifier

### App icons (optional but expected)

Place these in `assets/`:

- `Texta.ico` — Windows icon (256×256, 48×48, 32×32, 16×16 multi-resolution)
- `Texta.icns` — macOS icon (1024×1024 source, generated via `iconutil`)

The build still works without them; the OS-default icon is used as fallback.

To generate `.icns` from a `Texta.png` (1024×1024):
```bash
mkdir Texta.iconset
sips -z 16 16     Texta.png --out Texta.iconset/icon_16x16.png
sips -z 32 32     Texta.png --out Texta.iconset/icon_16x16@2x.png
sips -z 32 32     Texta.png --out Texta.iconset/icon_32x32.png
sips -z 64 64     Texta.png --out Texta.iconset/icon_32x32@2x.png
sips -z 128 128   Texta.png --out Texta.iconset/icon_128x128.png
sips -z 256 256   Texta.png --out Texta.iconset/icon_128x128@2x.png
sips -z 256 256   Texta.png --out Texta.iconset/icon_256x256.png
sips -z 512 512   Texta.png --out Texta.iconset/icon_256x256@2x.png
sips -z 512 512   Texta.png --out Texta.iconset/icon_512x512.png
cp Texta.png      Texta.iconset/icon_512x512@2x.png
iconutil -c icns Texta.iconset
```

To generate `.ico` from PNG, use ImageMagick: `magick Texta.png -define icon:auto-resize=16,32,48,256 Texta.ico`.

### Update feed

In `config.py`, set:
```python
UPDATE_REPO = "yourorg/texta"
```

The app will check `https://api.github.com/repos/yourorg/texta/releases/latest`
on startup and prompt the user when a newer tagged release exists.
Leave empty (`""`) to disable update checks.

---

## Cutting a release

1. **Bump version** in `config.py`:
   ```python
   APP_VERSION = "1.0.1"
   ```
2. Commit:
   ```bash
   git commit -am "Release 1.0.1"
   git push
   ```
3. Tag and push:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
4. GitHub Actions runs `release.yml`:
   - Builds Windows installer (`Texta-Setup-1.0.1.exe`)
   - Builds macOS Intel DMG (`Texta-1.0.1-x86_64.dmg`)
   - Builds macOS Apple Silicon DMG (`Texta-1.0.1-arm64.dmg`)
   - Creates a GitHub Release and attaches all three.
5. Edit the GitHub Release page to add release notes.

---

## Local builds (for testing without GitHub)

Prerequisite: Tesseract installed and on `PATH`.

```bash
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --clean --noconfirm packaging/texta.spec
```

Output:

| Platform | Result |
|----------|--------|
| Windows  | `dist/Texta/Texta.exe` (folder build) |
| macOS    | `dist/Texta.app` |
| Linux    | `dist/Texta/Texta` |

To produce a signed local build:

```bash
# macOS
export APPLE_DEV_ID="Developer ID Application: ..."
export APPLE_NOTARY_USER="you@example.com"
export APPLE_NOTARY_PASSWORD="abcd-efgh-ijkl-mnop"
export APPLE_TEAM_ID="ABC123XYZ"
bash packaging/sign_macos.sh

# Windows (PowerShell)
$env:WIN_CODESIGN_CERT_PATH = "C:\path\to\cert.pfx"
$env:WIN_CODESIGN_PASSWORD = "your-pfx-password"
.\packaging\sign_windows.ps1
```

---

## Smoke test checklist

After downloading a built artifact, verify on a clean machine:

- [ ] Installer runs without admin prompt (Windows: `PrivilegesRequired=lowest`)
- [ ] App launches; splash screen appears with progress bar
- [ ] First camera frame appears within 5 seconds
- [ ] `Snap + OCR` produces text from a test document
- [ ] PDF export creates a valid PDF
- [ ] On macOS: camera permission prompt appears on first run
- [ ] Quitting and relaunching is fast (<3s second startup)
- [ ] Update check fires (visible in `doc_cam_ocr.log` if `UPDATE_REPO` set)
- [ ] Uninstaller removes app + Start Menu / Applications shortcut

---

## Troubleshooting

**macOS: "Texta is damaged and can't be opened"**
The DMG was not notarized. Either re-run `sign_macos.sh` with notary
credentials set, or — for testing only — strip the quarantine attribute:
```bash
xattr -cr /Applications/Texta.app
```

**Windows: SmartScreen blocks the installer**
Expected for a new OV cert. Click "More info" → "Run anyway". Reputation
builds after enough downloads. EV certs avoid this entirely.

**PyInstaller: "tesseract binary not found on PATH"**
Install Tesseract on the build machine first:
- Windows: `choco install tesseract`
- macOS: `brew install tesseract`
- Linux: `apt-get install tesseract-ocr libtesseract-dev`

**`eng.traineddata` not found**
Set `TESSDATA_PREFIX` to the directory containing it before running PyInstaller.

**macOS notarization fails with "The signature does not include a secure timestamp"**
The signing step must use `--timestamp` (not `--timestamp=none`). The provided
`sign_macos.sh` does this; if you bypass it, mirror that flag.
