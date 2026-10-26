"""Różnice między systemami: nazwy procesów, katalog konfiguracji, powłoki.

Funkcje przyjmują opcjonalne os_name, żeby dało się je testować na dowolnym systemie.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

OsName = Literal["windows", "macos", "linux"]

APP_DIR_NAME = "ChocPilot"

# Powłoki dostępne w akcji „Polecenie” (pierwsza = domyślna dla systemu).
SHELLS: dict[str, tuple[str, ...]] = {
    "windows": ("cmd", "powershell"),
    "macos": ("zsh", "bash", "sh"),
    "linux": ("bash", "sh", "zsh"),
}
ALL_SHELLS = ("cmd", "powershell", "sh", "bash", "zsh")


def current_os() -> OsName:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _os(os_name: OsName | None) -> OsName:
    return os_name or current_os()


# --------------------------------------------------------------------------- procesy


def process_key(name: str) -> str:
    """Klucz porównania nazw procesów: bez wielkości liter i rozszerzeń .exe/.app.

    Dzięki temu „obs64.exe” = „OBS64”, a „Spotify.app” = „spotify”.
    """
    key = name.strip().lower()
    for suffix in (".exe", ".app"):
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def same_process(a: str, b: str) -> bool:
    return process_key(a) == process_key(b)


def process_name_from_path(path: str, os_name: OsName | None = None) -> str:
    """Nazwa procesu z ścieżki programu.

    Windows: „C:\\App\\app.exe” → „app.exe”; macOS: „/Applications/Safari.app” → „Safari”.
    """
    base = path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    if _os(os_name) == "macos" and base.lower().endswith(".app"):
        return base[:-4]
    return base


def normalize_process_entry(name: str, os_name: OsName | None = None) -> str:
    """Wpis listy „automatyczne przełączanie” w postaci typowej dla systemu."""
    name = name.strip()
    if not name:
        return name
    if _os(os_name) == "windows":
        return name if "." in name else name + ".exe"
    if name.lower().endswith(".app"):
        return name[:-4]
    return name


def is_user_process(name: str, os_name: OsName | None = None) -> bool:
    """Czy proces warto pokazać na liście podpowiedzi (Windows: tylko pliki .exe)."""
    if not name:
        return False
    if _os(os_name) == "windows":
        return name.lower().endswith(".exe")
    return True


def example_process(kind: Literal["app", "audio"], os_name: OsName | None = None) -> str:
    """Przykładowa nazwa procesu do podpowiedzi w polach tekstowych."""
    windows = _os(os_name) == "windows"
    if kind == "audio":
        return "spotify.exe" if windows else "Spotify"
    return "obs64.exe" if windows else "OBS"


# --------------------------------------------------------------------------- katalogi


def config_base_dir(
    os_name: OsName | None = None,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Katalog konfiguracji.

    Windows: %APPDATA%\\ChocPilot, macOS: ~/Library/Application Support/ChocPilot,
    Linux: $XDG_CONFIG_HOME/chocpilot lub ~/.config/chocpilot.
    """
    env = os.environ if env is None else env
    home = Path.home() if home is None else home
    system = _os(os_name)
    if system == "windows" and env.get("APPDATA"):
        return Path(env["APPDATA"]) / APP_DIR_NAME
    if system == "macos":
        return home / "Library" / "Application Support" / APP_DIR_NAME
    base = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else home / ".config"
    return base / APP_DIR_NAME.lower()


# --------------------------------------------------------------------------- powłoki


def shells(os_name: OsName | None = None) -> tuple[str, ...]:
    return SHELLS[_os(os_name)]


def default_shell(os_name: OsName | None = None) -> str:
    return shells(os_name)[0]
