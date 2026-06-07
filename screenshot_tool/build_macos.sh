#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

TARGET_ARCH="${1:-${PYI_TARGET_ARCH:-}}"
if [[ -z "${TARGET_ARCH}" ]]; then
  TARGET_ARCH="$(uname -m)"
fi

case "${TARGET_ARCH}" in
  x86_64|arm64|universal2) ;;
  aarch64) TARGET_ARCH="arm64" ;;
  *)
    echo "[ERROR] Unsupported arch: ${TARGET_ARCH}"
    echo "Supported: x86_64 / arm64 / universal2"
    exit 1
    ;;
esac

export PYI_TARGET_ARCH="${TARGET_ARCH}"

echo "========================================"
echo "  Build macOS portable package"
echo "  Target arch: ${TARGET_ARCH}"
echo "========================================"

echo "[1/6] Install dependencies..."
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

echo "[2/6] Clean old outputs..."
rm -rf build dist dist_portable

echo "[3/6] Build updater..."
python3 -m PyInstaller updater_macos.spec --clean --noconfirm

echo "[4/6] Build app bundle..."
python3 -m PyInstaller app_macos.spec --clean --noconfirm

APP_PATH=""
if [[ -d "dist/??????.app" ]]; then
  APP_PATH="dist/??????.app"
else
  APP_PATH="$(find dist -maxdepth 1 -type d -name '*.app' | head -n 1 || true)"
fi

if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "[ERROR] No .app bundle found in dist/"
  exit 1
fi

echo "[5/6] Inject updater binary..."
UPDATER_BIN=""
if [[ -f "dist/updater" ]]; then
  UPDATER_BIN="dist/updater"
elif [[ -f "dist/updater/updater" ]]; then
  UPDATER_BIN="dist/updater/updater"
fi

if [[ -n "$UPDATER_BIN" ]]; then
  cp "$UPDATER_BIN" "$APP_PATH/Contents/MacOS/updater"
  chmod +x "$APP_PATH/Contents/MacOS/updater"
else
  echo "[WARN] updater binary not found, skipped"
fi

echo "[6/6] Create portable zip..."
mkdir -p dist_portable
ZIP_PATH="dist_portable/screenshot_tool_mac_${TARGET_ARCH}_portable.zip"
rm -f "$ZIP_PATH"

if command -v ditto >/dev/null 2>&1; then
  ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
else
  (cd dist && zip -r "../$ZIP_PATH" "$(basename "$APP_PATH")")
fi

echo "========================================"
echo "  Build complete"
echo "  App: $APP_PATH"
echo "  Portable: $ZIP_PATH"
echo "========================================"
