#!/usr/bin/env bash
# Sign + notarize a built Texta.app and package it as a DMG.
#
# Required env vars (set as GitHub secrets in CI, or export locally):
#   APPLE_DEV_ID            Common name from your "Developer ID Application" cert
#                           e.g. "Developer ID Application: Jane Doe (ABC123XYZ)"
#   APPLE_NOTARY_USER       Your Apple ID (email)
#   APPLE_NOTARY_PASSWORD   App-specific password (NOT your Apple ID password)
#   APPLE_TEAM_ID           10-char team identifier
#
# When run without APPLE_DEV_ID, builds an unsigned DMG (dev convenience).
set -euo pipefail

cd "$(dirname "$0")/.."

APP="dist/Texta.app"
DMG="dist/Texta.dmg"
ENTITLEMENTS="packaging/entitlements.plist"

if [ ! -d "$APP" ]; then
    echo "ERROR: $APP not found. Run 'pyinstaller --clean --noconfirm packaging/texta.spec' first." >&2
    exit 1
fi

if [ -z "${APPLE_DEV_ID:-}" ]; then
    echo "APPLE_DEV_ID not set — building unsigned DMG (Gatekeeper will block end users)."
    rm -f "$DMG"
    hdiutil create -volname "Texta" -srcfolder "$APP" -ov -format UDZO "$DMG"
    echo "Unsigned DMG: $DMG"
    exit 0
fi

echo "==> Signing $APP with: $APPLE_DEV_ID"
# --deep is deprecated in newer codesign but still required for nested binaries
# inside Python frameworks. --options runtime is mandatory for notarization.
codesign --force --deep --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$APPLE_DEV_ID" \
    "$APP"

echo "==> Verifying signature"
codesign --verify --deep --strict --verbose=2 "$APP"

echo "==> Building DMG"
rm -f "$DMG"
hdiutil create -volname "Texta" -srcfolder "$APP" -ov -format UDZO "$DMG"

echo "==> Signing DMG"
codesign --force --sign "$APPLE_DEV_ID" --timestamp "$DMG"

if [ -n "${APPLE_NOTARY_USER:-}" ] && [ -n "${APPLE_NOTARY_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
    echo "==> Submitting for notarization (this can take 1–10 minutes)"
    xcrun notarytool submit "$DMG" \
        --apple-id "$APPLE_NOTARY_USER" \
        --password "$APPLE_NOTARY_PASSWORD" \
        --team-id "$APPLE_TEAM_ID" \
        --wait

    echo "==> Stapling notarization ticket"
    xcrun stapler staple "$DMG"

    echo "==> Verifying notarization"
    spctl --assess --type open --context context:primary-signature -vv "$DMG" || true
else
    echo "Notarization credentials not set — DMG signed but NOT notarized."
fi

echo "==> Done: $DMG"
