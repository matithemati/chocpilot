#!/usr/bin/env bash
# Buduje dist/ChocPilot.app i dist/ChocPilot-<wersja>-macOS-<arch>.dmg (PyInstaller).
# Użycie (Terminal, w katalogu app):
#   ./build_macos.sh                 testy + aplikacja + DMG, podpis ad-hoc
#   ./build_macos.sh --skip-tests    bez testów
#   ./build_macos.sh --no-dmg        tylko ChocPilot.app
# Podpis Developer ID (opcjonalnie): CODESIGN_IDENTITY="Developer ID Application: …" ./build_macos.sh
# Wymagania: macOS 12+, Python 3.12+ (python.org albo Homebrew), Xcode Command Line Tools.
set -euo pipefail
cd "$(dirname "$0")"

SKIP_TESTS=0
MAKE_DMG=1
for arg in "$@"; do
  case "$arg" in
    --skip-tests) SKIP_TESTS=1 ;;
    --no-dmg) MAKE_DMG=0 ;;
    *) echo "Nieznana opcja: $arg" >&2; exit 2 ;;
  esac
done

[[ "$(uname)" == "Darwin" ]] || { echo "Ten skrypt działa tylko na macOS" >&2; exit 1; }

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || {
  echo "Potrzebny Python 3.12+ (znaleziono: $("$PYTHON" --version 2>&1)). Ustaw PYTHON=/ścieżka/python3.12" >&2
  exit 1
}

if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi
PY=.venv/bin/python
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -e ".[dev]"

if [[ $SKIP_TESTS -eq 0 ]]; then
  QT_QPA_PLATFORM=offscreen "$PY" -m pytest -q
fi

"$PY" scripts/make_icon.py
"$PY" -m PyInstaller chocpilot.spec --clean --noconfirm

APP="dist/ChocPilot.app"
VERSION="$("$PY" -c 'import chocpilot; print(chocpilot.__version__)')"
ARCH="$(uname -m)"

# Podpis: bez niego macOS gubi uprawnienia Dostępności / Monitorowania wejścia po każdej
# przebudowie, a Gatekeeper odrzuca aplikację pobraną z internetu.
if [[ -n "${CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp --sign "$CODESIGN_IDENTITY" "$APP"
else
  codesign --force --deep --sign - "$APP"
fi
codesign --verify --deep --strict "$APP"
echo "Gotowe: $APP (wersja $VERSION, $ARCH)"

if [[ $MAKE_DMG -eq 1 ]]; then
  DMG="dist/ChocPilot-$VERSION-macOS-$ARCH.dmg"
  STAGE="$(mktemp -d)"
  cp -R "$APP" "$STAGE/"
  ln -s /Applications "$STAGE/Applications"
  rm -f "$DMG"
  hdiutil create -volname "ChocPilot $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
  rm -rf "$STAGE"
  echo "Gotowe: $DMG"
fi
