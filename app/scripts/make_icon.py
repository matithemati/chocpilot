"""Generuje chocpilot/assets/chocpilot.ico i chocpilot.png z logo rysowanego w kodzie (gui/icons.py)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from chocpilot.gui.icons import app_pixmap  # noqa: E402


def main() -> int:
    app = QGuiApplication([])
    assets = ROOT / "chocpilot" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    png = app_pixmap(256)
    ok_png = png.save(str(assets / "chocpilot.png"), "PNG")
    ok_ico = png.save(str(assets / "chocpilot.ico"), "ICO")
    print(f"chocpilot.png: {ok_png}, chocpilot.ico: {ok_ico}")
    del app
    return 0 if ok_png and ok_ico else 1


if __name__ == "__main__":
    sys.exit(main())
