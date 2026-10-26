"""Implementacja funkcji systemowych dla macOS (szkic – wymaga sprawdzenia na Macu).

Zależności: pynput (klawiatura, mysz) i pyobjc-framework-Cocoa (NSWorkspace).
Klawiatura, mysz i przełączanie okien wymagają uprawnienia „Dostępność”
(Ustawienia systemowe → Prywatność i ochrona → Dostępność).

Funkcje pomocnicze budujące polecenia (launch_argv, shell_argv, launch_agent_plist…)
są czyste i testowane na każdym systemie; reszta korzysta z API macOS.
"""

from __future__ import annotations

import logging
import plistlib
import shlex
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.osinfo import process_key
from .base import PlatformBackend, PlatformError
from .keys import PynputInput

log = logging.getLogger("chocpilot.platform")

LAUNCH_AGENT_LABEL = "com.chocpilot.app"
LAUNCH_AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"


# --------------------------------------------------------------------------- polecenia (czyste)


def launch_argv(path: str, args: str = "") -> list[str]:
    """Polecenie uruchomienia programu.

    Pakiety .app i same nazwy programów („Safari”) przez `open -a`,
    pozostałe ścieżki (skrypty, pliki wykonywalne) bezpośrednio.
    """
    extra = shlex.split(args) if args else []
    if path.rstrip("/").lower().endswith(".app") or "/" not in path:
        argv = ["open", "-a", path]
        if extra:
            argv += ["--args", *extra]
        return argv
    return [path, *extra]


def open_url_argv(url: str, browser: str = "") -> list[str]:
    return ["open", "-a", browser, url] if browser else ["open", url]


def shell_argv(
    shell: str, command: str, which: Callable[[str], str | None] = shutil.which
) -> list[str]:
    """Polecenie dla akcji „Polecenie”; profile z Windows (cmd) używają zsh."""
    if shell == "powershell":
        pwsh = which("pwsh")
        if pwsh is None:
            raise PlatformError("PowerShell (pwsh) nie jest zainstalowany")
        return [pwsh, "-NoProfile", "-Command", command]
    if shell == "cmd":
        log.warning("Powłoka cmd niedostępna na macOS – używam zsh")
        shell = "zsh"
    exe = which(shell) or "/bin/zsh"
    return [exe, "-c", command]


def launch_agent_plist(command: str) -> bytes:
    """LaunchAgent uruchamiający ChocPilot po zalogowaniu."""
    return plistlib.dumps(
        {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": shlex.split(command),
            "RunAtLoad": True,
            "ProcessType": "Interactive",
        }
    )


def osascript(script: str, timeout_s: float = 5.0) -> str:
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=timeout_s, check=False
    )
    if result.returncode != 0:
        raise PlatformError(result.stderr.strip() or "osascript zakończony błędem")
    return result.stdout.strip()


def parse_volume(text: str) -> float | None:
    """Wynik `output volume of (get volume settings)` → 0–100 (None dla „missing value”)."""
    try:
        return max(0.0, min(100.0, float(text)))
    except ValueError:
        return None


# --------------------------------------------------------------------------- backend


class MacPlatform(PynputInput, PlatformBackend):
    name = "macos"

    def __init__(self) -> None:
        PynputInput.__init__(self)
        self._app_volume_warned = False

    # ------------------------------------------------------------------ programy

    @staticmethod
    def _workspace() -> Any:
        from AppKit import NSWorkspace  # pyobjc-framework-Cocoa

        return NSWorkspace.sharedWorkspace()

    @staticmethod
    def _app_name(app: Any) -> str:
        name = app.localizedName() or ""
        url = app.executableURL()
        exe = url.lastPathComponent() if url is not None else ""
        return str(name or exe)

    def _find_app(self, name: str) -> Any:
        key = process_key(name)
        for app in self._workspace().runningApplications():
            url = app.executableURL()
            exe = str(url.lastPathComponent()) if url is not None else ""
            if key in (process_key(str(app.localizedName() or "")), process_key(exe)):
                return app
        return None

    def launch(self, path: str, args: str = "", cwd: str = "") -> None:
        subprocess.Popen(launch_argv(path, args), cwd=cwd or None, close_fds=True)

    def focus_process(self, exe_name: str, cycle: bool = False) -> bool:
        app = self._find_app(exe_name)
        if app is None:
            return False
        if cycle and app.isActive():
            # Cmd+` przełącza okna aktywnej aplikacji (odpowiednik obchodzenia okien na Windows).
            # TODO(mac): sprawdzić na układach klawiatury bez klawisza ` (np. polski programisty).
            self.send_hotkey(["win", "`"])
            return True
        from AppKit import NSApplicationActivateAllWindows, NSApplicationActivateIgnoringOtherApps

        # TODO(mac): od macOS 14 IgnoringOtherApps jest przestarzałe – sprawdzić, czy działa
        # z tła; w razie problemów: `open -a <nazwa>`.
        app.activateWithOptions_(
            NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps
        )
        return True

    def open_path(self, path: str) -> None:
        if not Path(path).exists():
            raise PlatformError(f"nie istnieje: {path}")
        subprocess.Popen(["open", path], close_fds=True)

    def open_url(self, url: str, browser: str = "") -> None:
        subprocess.Popen(open_url_argv(url, browser), close_fds=True)

    def running_apps(self) -> list[str] | None:
        try:
            apps = self._workspace().runningApplications()
        except Exception as exc:
            log.debug("NSWorkspace niedostępne: %s", exc)
            return None
        regular = 0  # NSApplicationActivationPolicyRegular – programy z ikoną w Docku
        names = {self._app_name(a) for a in apps if a.activationPolicy() == regular}
        return sorted((n for n in names if n), key=str.lower)

    # ------------------------------------------------------------------ dźwięk

    def get_system_volume(self) -> float | None:
        try:
            return parse_volume(osascript("output volume of (get volume settings)"))
        except Exception as exc:
            log.debug("Głośność niedostępna: %s", exc)
            return None

    def change_system_volume(self, delta: float) -> float | None:
        current = self.get_system_volume()
        if current is None:
            return None
        value = max(0.0, min(100.0, current + delta))
        try:
            script = f"set volume output volume {round(value)}"
            if delta > 0:
                script += " without output muted"
            osascript(script)
        except Exception as exc:
            log.debug("Zmiana głośności nieudana: %s", exc)
            return None
        return value

    def toggle_system_mute(self) -> bool | None:
        try:
            muted = osascript("output muted of (get volume settings)") != "true"
            osascript(f"set volume output muted {'true' if muted else 'false'}")
            return muted
        except Exception as exc:
            log.debug("Wyciszenie nieudane: %s", exc)
            return None

    def _no_app_volume(self) -> None:
        if not self._app_volume_warned:
            log.warning("Głośność pojedynczego programu nie jest dostępna na macOS")
            self._app_volume_warned = True

    def change_app_volume(self, exe_name: str, delta: float) -> float | None:
        # macOS nie ma publicznego API głośności procesu (wymagałoby wirtualnego sterownika).
        self._no_app_volume()
        return None

    def toggle_app_mute(self, exe_name: str) -> bool | None:
        self._no_app_volume()
        return None

    def list_audio_processes(self) -> list[str]:
        return []

    # ------------------------------------------------------------------ polecenia i system

    def run_shell(self, command: str, shell: str, timeout_s: float, hidden: bool) -> int:
        argv = shell_argv(shell, command)
        if not hidden:
            # widoczne okno: polecenie w Terminalu (kod wyjścia nieznany)
            script = command.replace("\\", "\\\\").replace('"', '\\"')
            osascript(f'tell application "Terminal" to do script "{script}"')
            return 0
        try:
            result = subprocess.run(argv, timeout=timeout_s, check=False)
        except subprocess.TimeoutExpired as exc:
            raise PlatformError(f"przekroczono limit czasu {timeout_s} s") from exc
        return result.returncode

    def lock_screen(self) -> None:
        # Ctrl+Cmd+Q – systemowy skrót blokady (wymaga uprawnienia „Dostępność”)
        self.send_hotkey(["ctrl", "win", "q"])

    def screen_off(self) -> None:
        subprocess.run(["pmset", "displaysleepnow"], check=False)

    def foreground_process(self) -> str | None:
        try:
            app = self._workspace().frontmostApplication()
        except Exception as exc:
            log.debug("NSWorkspace niedostępne: %s", exc)
            return None
        return self._app_name(app) if app is not None else None

    # ------------------------------------------------------------------ autostart

    def get_autostart(self) -> bool:
        return LAUNCH_AGENT_PATH.exists()

    def set_autostart(self, enabled: bool, command: str) -> None:
        if enabled:
            LAUNCH_AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)
            LAUNCH_AGENT_PATH.write_bytes(launch_agent_plist(command))
        else:
            LAUNCH_AGENT_PATH.unlink(missing_ok=True)
