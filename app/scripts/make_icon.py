"""Generuje ikony aplikacji z logo rysowanego w kodzie (gui/icons.py).

chocpilot/assets/chocpilot.png (256 px, okno i zasobnik), chocpilot.ico (Windows, exe)
oraz chocpilot.icns (macOS, pakiet .app; 1024 px – system sam skaluje).
"""

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
    results = {
        "chocpilot.png": png.save(str(assets / "chocpilot.png"), "PNG"),
        "chocpilot.ico": png.save(str(assets / "chocpilot.ico"), "ICO"),
        "chocpilot.icns": app_pixmap(1024).save(str(assets / "chocpilot.icns"), "ICNS"),
    }
    print(", ".join(f"{name}: {ok}" for name, ok in results.items()))
    del app
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
