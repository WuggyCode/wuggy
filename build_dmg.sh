#!/usr/bin/env bash
# Build Wuggy.app and package it as a distributable DMG.
#
# Usage: ./build_dmg.sh [--skip-pyinstaller]
#   --skip-pyinstaller   use an existing dist/Wuggy.app without rebuilding

set -e

APP_NAME="Wuggy"
VERSION="1.2.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${DMG_NAME}"

CREATE_DMG="$(brew --prefix 2>/dev/null)/bin/create-dmg"
if [[ ! -x "${CREATE_DMG}" ]]; then
    CREATE_DMG="create-dmg"
fi

# PyInstaller was installed for the system Python (3.9). Use it explicitly
# so that a Homebrew Python on PATH doesn't shadow it.
PYTHON="/Library/Developer/CommandLineTools/usr/bin/python3"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="$(command -v python3)"
fi

# --- 1. Build the app bundle (unless skipped) ---
if [[ "$1" != "--skip-pyinstaller" ]]; then
    echo "==> Building ${APP_NAME}.app with PyInstaller…"
    "${PYTHON}" -m PyInstaller wuggy.spec --noconfirm
    echo "==> Build complete: ${APP_PATH}"
fi

if [[ ! -d "${APP_PATH}" ]]; then
    echo "ERROR: ${APP_PATH} not found. Run without --skip-pyinstaller first."
    exit 1
fi

# --- 2. Create DMG ---
echo "==> Creating DMG with create-dmg…"
rm -f "${DMG_PATH}"

"${CREATE_DMG}" \
    --volname "${APP_NAME} ${VERSION}" \
    --background "assets/dmg_background.png" \
    --window-pos 200 120 \
    --window-size 540 380 \
    --icon-size 80 \
    --icon "${APP_NAME}.app" 145 255 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 395 255 \
    --hdiutil-quiet \
    "${DMG_PATH}" \
    "${APP_PATH}"

# --- 3. Done ---
DMG_SIZE=$(du -sh "${DMG_PATH}" | cut -f1)
echo ""
echo "==> Done: ${DMG_PATH} (${DMG_SIZE})"
